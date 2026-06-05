"""
agent.py
--------
Main orchestrator for the Ramp onboarding assistant.

This version supports two Groq execution paths:
1. `langchain_groq` when installed
2. Direct Groq Chat Completions API fallback when it is not

The fallback uses Groq's OpenAI-compatible endpoint so the project can run
with just `requests` plus a valid `GROQ_API_KEY`.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import requests
from langchain_core.utils.function_calling import convert_to_openai_tool
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from backend.agent.prompt_builder import build_human_prompt, build_system_prompt
from backend.agent.tools import TOOL_REGISTRY
from backend.interfaces import (
    AgentResponse,
    ContextBlock,
    OnboardingRequest,
    TeamPath,
    UserProfile,
)
from backend.memory.retriever import apply_demo_mode, fetch_person1_demo_memories
from backend.memory.writer import MemoryWriter
from backend.observability import metrics
from backend.settings import integrations_mode

logger = logging.getLogger(__name__)

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
except Exception:  # pragma: no cover
    AIMessage = HumanMessage = SystemMessage = ToolMessage = None  # type: ignore

try:
    from langchain_groq import ChatGroq
except ImportError:  # pragma: no cover
    ChatGroq = None  # type: ignore


def _groq_config() -> tuple[str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Check your .env file.")
    configured = os.getenv("GROQ_MODEL", "").strip()
    model = configured or "openai/gpt-oss-20b"
    if model == "llama3-70b-8192":
        model = "openai/gpt-oss-20b"
    return api_key, model


class RampAgent:
    def __init__(self) -> None:
        self.api_key, self.model = _groq_config()
        self._tool_map = {tool.name: tool for tool in TOOL_REGISTRY}
        self._tool_schemas = [convert_to_openai_tool(tool) for tool in TOOL_REGISTRY]
        self.memory_writer = MemoryWriter()
        self._llm = self._build_langchain_llm()
        logger.info(
            "RampAgent initialized | model=%s | transport=%s | tools=%s",
            self.model,
            "langchain_groq" if self._llm is not None else "direct_groq_api",
            list(self._tool_map.keys()),
        )

    async def run(self, request: OnboardingRequest) -> AgentResponse:
        logger.info(
            "Agent run | user=%s | team=%s | query=%.80s | demo_mode=%s",
            request.name,
            request.team,
            request.query,
            request.demo_mode or "person10",
        )
        metrics.inc("agent_runs_total", team=request.team, demo_mode=request.demo_mode or "person10")

        ctx = await self._build_context(request)
        if request.demo_mode == "person1":
            ctx.memories = fetch_person1_demo_memories()
        else:
            ctx.memories = apply_demo_mode(ctx.memories, request.demo_mode)

        if self._llm is not None:
            answer, actions_taken = await self._run_langchain_flow(ctx, request)
        else:
            answer, actions_taken = self._run_direct_groq_flow(ctx, request)

        write_result = self.memory_writer.write_interaction(
            user=ctx.user,
            team_path=ctx.team_path,
            user_query=request.query,
            assistant_response=answer,
            suggested_actions=actions_taken,
            session_id=request.session_id,
        )

        tools_used = [action.split(":", 1)[0] for action in actions_taken if ":" in action]

        return AgentResponse(
            message=answer,
            memories_used=ctx.memories,
            new_memories_written=write_result.memories,
            suggested_actions=actions_taken,
            tools_used=tools_used,
            integrations_mode=integrations_mode(),
        )

    async def _build_context(self, request: OnboardingRequest) -> ContextBlock:
        try:
            from backend.context.context_builder import build_context

            return await build_context(request)
        except (ImportError, NotImplementedError):
            logger.warning("context_builder not available — using stub context")
            return self._stub_context(request)

    def _stub_context(self, request: OnboardingRequest) -> ContextBlock:
        user = UserProfile(
            name=request.name,
            team_name=request.team,
            employment_type=request.employee_type,
            role_title=request.role or None,
        )
        team_path = TeamPath(
            ids=["company", request.team.lower().replace(" ", "_")],
            names=["Company", request.team],
        )
        return ContextBlock(
            user=user,
            team_path=team_path,
            memories=[],
            exception_notes=["Contractor workflow applies"] if request.employee_type == "contractor" else [],
        )

    def _build_langchain_llm(self) -> Any | None:
        if ChatGroq is None or AIMessage is None:
            return None
        return ChatGroq(
            api_key=self.api_key,
            model=self.model,
            temperature=0.3,
            max_tokens=1024,
            timeout=30,
        ).bind_tools(TOOL_REGISTRY)

    async def _run_langchain_flow(
        self,
        ctx: ContextBlock,
        request: OnboardingRequest,
    ) -> tuple[str, list[str]]:
        system_msg = SystemMessage(content=build_system_prompt())
        human_msg = HumanMessage(content=build_human_prompt(ctx, request.query))
        messages: list[Any] = [system_msg, human_msg]

        ai_message = await self._call_langchain_with_retry(messages)
        messages.append(ai_message)

        actions_taken: list[str] = []
        safety_limit = 0
        while getattr(ai_message, "tool_calls", None) and safety_limit < 3:
            for tool_call in ai_message.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]
                result = self._invoke_tool(tool_name, tool_args)
                actions_taken.append(f"{tool_name}: {result}")
                messages.append(ToolMessage(content=str(result), tool_call_id=tool_id))

            ai_message = await self._call_langchain_with_retry(messages)
            messages.append(ai_message)
            safety_limit += 1

        answer = getattr(ai_message, "content", "") or "I couldn't generate a response."
        return answer, actions_taken

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_langchain_with_retry(self, messages: list[Any]) -> Any:
        return await self._llm.ainvoke(messages)

    def _run_direct_groq_flow(
        self,
        ctx: ContextBlock,
        request: OnboardingRequest,
    ) -> tuple[str, list[str]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": build_human_prompt(ctx, request.query)},
        ]

        actions_taken: list[str] = []
        safety_limit = 0

        while safety_limit < 3:
            response_message = self._call_groq_chat_completion(messages, include_tools=True)
            messages.append(response_message)

            tool_calls = response_message.get("tool_calls") or []
            if not tool_calls:
                answer = response_message.get("content") or "I couldn't generate a response."
                return answer, actions_taken

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                raw_args = tool_call["function"].get("arguments", "{}")
                try:
                    tool_args = json.loads(raw_args)
                except json.JSONDecodeError:
                    tool_args = {}
                result = self._invoke_tool(tool_name, tool_args)
                actions_taken.append(f"{tool_name}: {result}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": tool_name,
                        "content": str(result),
                    }
                )

            safety_limit += 1

        return "I hit an internal tool-calling limit. Please try again.", actions_taken

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _call_groq_chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        include_tools: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1024,
        }
        if include_tools:
            payload["tools"] = self._tool_schemas
            payload["tool_choice"] = "auto"

        response = requests.post(
            GROQ_CHAT_COMPLETIONS_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]

    def _invoke_tool(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        logger.info("Executing tool: %s | args=%s", tool_name, tool_args)
        metrics.inc("tool_calls_total", tool_name=tool_name)
        tool = self._tool_map.get(tool_name)
        if tool is None:
            return f"Error: tool '{tool_name}' not registered."

        try:
            return str(tool.invoke(tool_args))
        except Exception as exc:  # pragma: no cover
            logger.error("Tool '%s' failed: %s", tool_name, exc)
            metrics.inc("tool_call_failures_total", tool_name=tool_name)
            return f"Tool '{tool_name}' failed: {exc}"


_agent_instance: Optional[RampAgent] = None


def get_agent() -> RampAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RampAgent()
    return _agent_instance
