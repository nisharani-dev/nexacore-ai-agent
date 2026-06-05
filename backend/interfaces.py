"""
interfaces.py — Shared contracts for the Ramp project.
P1 owns this file. Everyone imports from here.
Do NOT import from individual modules directly across boundaries.
"""

from dataclasses import dataclass, field
from typing import Optional


# ── Shared input/output types ──────────────────────────────────────────────────

@dataclass
class UserProfile:
    """Represents the incoming user at start of onboarding session."""
    name: str
    team_name: str                          # e.g. "Infra Security" or "infra_security"
    employment_type: str = "fte"            # "fte" | "contractor" | "intern"
    role_title: Optional[str] = None        # e.g. "Software Engineer"
    manager_name: Optional[str] = None


@dataclass
class TeamPath:
    """
    Result of team_resolver — the full ancestry from company → leaf team.
    Example:
        ids   = ["company", "engineering", "platform", "infra_security"]
        names = ["AcmeCorp", "Engineering Org", "Platform Engineering", "Infra Security"]
    """
    ids: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)

    def __str__(self):
        return " → ".join(self.names)


@dataclass
class MemoryItem:
    """One retrieved memory from Hindsight. P2 writes this shape; everyone reads it."""
    content: str
    tags: list[str] = field(default_factory=list)
    level: str = ""           # "company" | "division" | "team" | "sub_team" | "exception"
    source: str = ""          # free text: "seed_data" | "interaction" | "ingestion"
    relevance_score: float = 0.0


@dataclass
class ContextBlock:
    """
    Assembled context object handed to P1's prompt_builder.
    Contains everything the LLM needs to know before responding.
    """
    user: UserProfile
    team_path: TeamPath
    memories: list[MemoryItem] = field(default_factory=list)
    exception_notes: list[str] = field(default_factory=list)
    raw_accesses: list[str] = field(default_factory=list)   # merged access list, all levels


@dataclass
class AgentResponse:
    """What the agent returns after processing a user message."""
    message: str
    memories_used: list[MemoryItem] = field(default_factory=list)
    new_memories_written: list[MemoryItem] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)