"""
interfaces.py — Shared contracts for the Ramp project.
P1 owns this file. Everyone imports from here.
Do NOT import from individual modules directly across boundaries.

Note: upstream used dataclasses; P1 uses Pydantic for FastAPI response_model
compatibility. All field names match the upstream dataclass definitions exactly
so every teammate's code continues to work without changes.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────
# UserProfile
# ─────────────────────────────────────────────

class UserProfile(BaseModel):
    """Represents the incoming user at start of onboarding session."""
    name: str
    team_name: str                          # e.g. "Infra Security" or "infra_security"
    employment_type: str = "fte"            # "fte" | "contractor" | "intern"
    role_title: Optional[str] = None        # e.g. "Software Engineer"
    manager_name: Optional[str] = None


# ─────────────────────────────────────────────
# TeamPath
# ─────────────────────────────────────────────

class TeamPath(BaseModel):
    """
    Result of team_resolver — the full ancestry from company → leaf team.
    Example:
        ids   = ["company", "engineering", "platform", "infra_security"]
        names = ["AcmeCorp", "Engineering Org", "Platform Engineering", "Infra Security"]
    """
    ids: list[str] = Field(default_factory=list)
    names: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return " → ".join(self.names)


# ─────────────────────────────────────────────
# MemoryItem
# ─────────────────────────────────────────────

class MemoryItem(BaseModel):
    """One retrieved memory from Hindsight. P2 writes this shape; everyone reads it."""
    content: str
    tags: list[str] = Field(default_factory=list)
    level: str = ""           # "company" | "division" | "team" | "sub_team" | "exception"
    source: str = ""          # "seed_data" | "interaction" | "ingestion"
    relevance_score: float = 0.0


# ─────────────────────────────────────────────
# ContextBlock
# ─────────────────────────────────────────────

class ContextBlock(BaseModel):
    """
    Assembled context object handed to P1's prompt_builder.
    Contains everything the LLM needs to know before responding.
    P3 (context_builder) fills this; P1 (agent) consumes it.
    """
    user: UserProfile
    team_path: TeamPath
    memories: list[MemoryItem] = Field(default_factory=list)
    exception_notes: list[str] = Field(default_factory=list)
    raw_accesses: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────
# AgentResponse
# ─────────────────────────────────────────────

class AgentResponse(BaseModel):
    """What the agent returns after processing a user message."""
    message: str
    memories_used: list[MemoryItem] = Field(default_factory=list)
    new_memories_written: list[MemoryItem] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    integrations_mode: str = "demo"


class FeedbackRequest(BaseModel):
    """User feedback on an agent reply."""
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    helpful: bool = True
    comment: str = ""
    team: str = ""
    query: str = ""


# ─────────────────────────────────────────────
# OnboardingRequest — FastAPI inbound (P1 + P5)
# ─────────────────────────────────────────────

class OnboardingRequest(BaseModel):
    """What the frontend sends to POST /chat."""
    name: str
    team: str
    role: str = ""
    employee_type: str = "fte"
    query: str
    session_id: Optional[str] = None
    demo_mode: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "name" not in payload and payload.get("username"):
            payload["name"] = payload["username"]
        if "employee_type" not in payload and payload.get("employment_type"):
            payload["employee_type"] = payload["employment_type"]
        if isinstance(payload.get("employee_type"), str):
            payload["employee_type"] = payload["employee_type"].lower()
        return payload


class SessionRequest(BaseModel):
    name: str = ""
    team: str = ""
    role: str = ""
    employee_type: str = "fte"
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        payload = dict(data)
        if "name" not in payload and payload.get("username"):
            payload["name"] = payload["username"]
        if "employee_type" not in payload and payload.get("employment_type"):
            payload["employee_type"] = payload["employment_type"]
        if isinstance(payload.get("employee_type"), str):
            payload["employee_type"] = payload["employee_type"].lower()
        return payload
