"""
interfaces.py
─────────────
Shared data contracts between all modules.
Person 1 owns this file. All teammates import from here — never the reverse.
This is the single source of truth for inter-module types.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Inbound request from frontend / API
# ─────────────────────────────────────────────

class OnboardingRequest(BaseModel):
    """What the frontend sends to POST /chat."""
    name: str = Field(..., description="Employee's full name")
    team: str = Field(..., description="Team name, e.g. 'Platform Team'")
    role: str = Field(..., description="Job role, e.g. 'Backend Engineer'")
    employee_type: str = Field(
        default="full-time",
        description="Employment type: full-time | contractor | intern",
    )
    query: str = Field(..., description="The employee's onboarding question")
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for multi-turn conversations",
    )


# ─────────────────────────────────────────────
# User profile (resolved from request)
# ─────────────────────────────────────────────

class UserProfile(BaseModel):
    name: str
    team: str
    role: str
    employee_type: str
    team_hierarchy: list[str] = Field(
        default_factory=list,
        description="Full resolved hierarchy, e.g. ['Company', 'Engineering', 'Platform Team']",
    )


# ─────────────────────────────────────────────
# Memory item returned by Person 2's retriever
# ─────────────────────────────────────────────

class MemoryItem(BaseModel):
    id: str
    content: str
    source_level: str = Field(description="Which hierarchy level this memory is from")
    tags: list[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None


# ─────────────────────────────────────────────
# Exception flags returned by Person 3's tagger
# ─────────────────────────────────────────────

class ExceptionContext(BaseModel):
    is_contractor: bool = False
    is_intern: bool = False
    needs_vpn_exception: bool = False
    needs_special_jira_workflow: bool = False
    custom_flags: dict[str, Any] = Field(default_factory=dict)


# ─────────────────────────────────────────────
# Full context bundle — assembled by context_builder
# (Person 3 fills this, Person 1 consumes it)
# ─────────────────────────────────────────────

class AgentContext(BaseModel):
    user: UserProfile
    memories: list[MemoryItem] = Field(default_factory=list)
    exceptions: ExceptionContext = Field(default_factory=ExceptionContext)
    query: str


# ─────────────────────────────────────────────
# Outbound response to frontend
# ─────────────────────────────────────────────

class OnboardingResponse(BaseModel):
    answer: str
    used_memories: list[MemoryItem] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    session_id: Optional[str] = None
