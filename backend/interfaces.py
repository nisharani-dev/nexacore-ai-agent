"""
interfaces.py — Shared contracts for the Ramp project.
P1 owns this file. Everyone imports from here.
Do NOT import from individual modules directly across boundaries.

Note: upstream used dataclasses; P1 uses Pydantic for FastAPI response_model
compatibility. All field names match the upstream dataclass definitions exactly
so every teammate's code continues to work without changes.
"""

from typing import Optional
from pydantic import BaseModel, Field


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
