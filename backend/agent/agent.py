"""
agent.py
─────────
The central AI orchestrator for the Ramp onboarding assistant.

Workflow:
  OnboardingRequest
      │
      ▼
  ContextBuilder  ──► team_resolver + exception_tagger + memory retrieval
      │
      ▼
  PromptBuilder   ──► system prompt + human prompt with full context
      │
      ▼
  LLM (Groq)      ──► bound with tools
      │
      ▼
  Tool Execution  ──► raise_ticket / send_reminder / log_blocker (if needed)
      │
      ▼
  OnboardingResponse

Design:
  - RampAgent is a plain class (no LangGraph overhead for this hackathon scope).
  - Uses LangChain's bind_tools for native tool calling.
  - Stateless per request — session_id support is a thin wrapper ready for future memory.
  - All teammate integrations are behind clean method calls that can be swapped.
"""

import logging
import os
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from backend.interfaces import AgentContext, OnboardingRequest, OnboardingResponse, MemoryItem
from backend.agent.prompt_builder import build_system_prompt, build_human_prompt
from backend.agent.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# LLM factory — isolated so you can swap models
# ─────────────────────────────────────────────

def _build_llm() -> ChatGroq:
    """Creates the Groq LLM instance from environment config."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY is not set. Check your .env file.")

    model = os.getenv("GROQ_MODEL", "llama3-70b-8192")

    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0.3,       # Low temp: factual onboarding guidance
        max_tokens=1024,
        timeout=30,
    )


# ─────────────────────────────────────────────
# Agent class
# ─────────────────────────────────────────────

class RampAgent:
    """
    The main orchestrator. Instantiate once at app startup (singleton pattern).

    Usage:
        agent = RampAgent()
        response = await agent.run(request)
    """

    def __init__(self) -> None:
        self.llm = _build_llm()
        # Bind tools so the LLM knows what it can call
        self.llm_with_tools = self.llm.bind_tools(TOOL_REGISTRY)
        # Build a lookup map for fast tool dispatch
        self._tool_map: dict = {t.name: t for t in TOOL_REGISTRY}
        logger.info(
            "RampAgent initialized | model=%s | tools=%s",
            os.getenv("GROQ_MODEL", "llama3-70b-8192"),
            list(self._tool_map.keys()),
        )

    # ── Public entry point ──────────────────────────────────────────────

    async def run(self, request: OnboardingRequest) -> OnboardingResponse:
        """
        Full pipeline: context → prompt → LLM → tools → response.
        This is what server.py calls.
        """
        logger.info("Agent run | user=%s | team=%s | query=%.80s", request.name, request.team, request.query)

        # Step 1: Build context (integrates with Person 2 + 3)
        ctx = await self._build_context(request)

        # Step 2: Build prompts
        system_msg = SystemMessage(content=build_system_prompt())
        human_msg = HumanMessage(content=build_human_prompt(ctx))

        # Step 3: Call LLM (with retry)
        messages = [system_msg, human_msg]
        ai_message = await self._call_llm_with_retry(messages)
        messages.append(ai_message)

        # Step 4: Handle tool calls if the LLM decided to use them
        actions_taken: list[str] = []
        if ai_message.tool_calls:
            messages, actions_taken = await self._execute_tool_calls(ai_message, messages)
            # Give the LLM a final pass to generate the user-facing answer
            final_message = await self._call_llm_with_retry(messages)
            answer = final_message.content
        else:
            answer = ai_message.content

        return OnboardingResponse(
            answer=answer,
            used_memories=ctx.memories,
            actions_taken=actions_taken,
            session_id=request.session_id,
        )

    # ── Context building ─────────────────────────────────────────────────

    async def _build_context(self, request: OnboardingRequest) -> AgentContext:
        """
        Assembles the AgentContext by calling Person 3's context_builder.

        If context_builder is not yet implemented, falls back to a minimal
        context so the agent can still run during development.
        """
        try:
            from backend.context.context_builder import build_context
            ctx = await build_context(request)
            return ctx
        except (ImportError, NotImplementedError):
            logger.warning("context_builder not available — using minimal stub context")
            return self._stub_context(request)

    def _stub_context(self, request: OnboardingRequest) -> AgentContext:
        """
        Stub context used when Person 3's module isn't ready yet.
        Returns an AgentContext with no memories and no exceptions.
        Swap this out the moment context_builder.py is delivered.
        """
        from backend.interfaces import UserProfile, ExceptionContext

        return AgentContext(
            user=UserProfile(
                name=request.name,
                team=request.team,
                role=request.role,
                employee_type=request.employee_type,
                team_hierarchy=["Company", request.team],  # minimal hierarchy
            ),
            memories=[],
            exceptions=ExceptionContext(
                is_contractor=(request.employee_type.lower() == "contractor"),
                is_intern=(request.employee_type.lower() == "intern"),
            ),
            query=request.query,
        )

    # ── LLM call with retry ──────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _call_llm_with_retry(self, messages: list) -> AIMessage:
        """Calls the LLM with exponential backoff on transient failures."""
        try:
            response = await self.llm_with_tools.ainvoke(messages)
            return response
        except Exception as e:
            logger.warning("LLM call failed, retrying... error=%s", str(e))
            raise

    # ── Tool execution ───────────────────────────────────────────────────

    async def _execute_tool_calls(
        self, ai_message: AIMessage, messages: list
    ) -> tuple[list, list[str]]:
        """
        Executes all tool calls requested by the LLM.
        Appends ToolMessages back into the conversation so the LLM
        can reference the results in its final answer.
        """
        actions_taken: list[str] = []

        for tool_call in ai_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            logger.info("Executing tool: %s | args=%s", tool_name, tool_args)

            if tool_name not in self._tool_map:
                result = f"Error: tool '{tool_name}' is not registered."
                logger.error(result)
            else:
                try:
                    tool_fn = self._tool_map[tool_name]
                    result = tool_fn.invoke(tool_args)
                    actions_taken.append(f"{tool_name}: {result}")
                except Exception as e:
                    result = f"Tool '{tool_name}' failed: {str(e)}"
                    logger.error(result)

            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_id)
            )

        return messages, actions_taken


# ─────────────────────────────────────────────
# Module-level singleton (initialized lazily)
# ─────────────────────────────────────────────
# server.py imports `get_agent()` rather than instantiating directly.
# This ensures the LLM client is created once and reused across requests.

_agent_instance: Optional[RampAgent] = None


def get_agent() -> RampAgent:
    """Returns the module-level RampAgent singleton."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = RampAgent()
    return _agent_instance
