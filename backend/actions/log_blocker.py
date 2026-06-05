"""
log_blocker.py  —  Person 4 (Ingestion + Actions)
--------------------------------------------------
LangChain tool: logs a resolved onboarding blocker back to Hindsight.

This is THE FLYWHEEL — the most important tool in the whole project.

What is the flywheel?
    Every time someone hits a blocker and the agent (or the user)
    finds the resolution, we write it back to memory. The NEXT person
    who joins the same team will be warned BEFORE they hit the same wall.

    Person #1 hits blocker → manually resolves it → agent logs it.
    Person #2 joins → agent already knows → warns them proactively.
    Person #10 joins → agent knows 6 edge cases → they have a smooth Day 1.

    This is exactly the demo moment Person 5 is scripting.

How it connects to Person 2:
    This tool calls _write_memory() which writes a MemoryItem to Hindsight
    tagged with the right team + "exception:all" so retriever.py picks it
    up for all future employees on that team.

Usage by the agent:
    Agent detects user says "My Confluence request has been pending 5 days"
    → checks memory (P2's retriever)
    → surfaces resolution if known
    → if resolution is new, calls log_resolved_blocker to save it
"""

import sys
from pathlib import Path
from langchain.tools import tool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interfaces import MemoryItem


def _write_memory(item: MemoryItem):
    """Writes to Hindsight. Stub until P2 ships hindsight_client.py."""
    try:
        from memory.hindsight_client import HindsightClient  # type: ignore
        client = HindsightClient()
        client.write(item)
    except ImportError:
        print(f"  [STUB WRITE] Blocker logged → tags={item.tags} | {item.content[:100]}")


@tool
def log_resolved_blocker(
    blocker: str,
    resolution: str,
    team_id: str,
    employment_type: str = "fte",
) -> str:
    """
    Logs a resolved onboarding blocker to memory so future employees are warned proactively.

    ALWAYS call this tool when:
    - A user reports they were stuck and found a fix
    - The agent discovers a workaround not already in memory
    - A ticket was resolved via a non-obvious path (e.g. wrong queue, different contact)

    This is the memory flywheel — every logged blocker makes the agent smarter
    for the next person who joins the same team.

    Inputs:
        blocker: description of what went wrong (e.g. "Confluence request pending 5 days")
        resolution: how it was fixed (e.g. "Escalated to @it-confluence directly, not general queue")
        team_id: the team this blocker applies to (e.g. "platform", "infra_security")
        employment_type: "fte", "contractor", or "intern" (default: "fte")

    Returns: confirmation that the blocker was saved to memory.
    """
    # Build the memory content — written so future employees read it as a warning
    content = f"KNOWN BLOCKER on {team_id}: {blocker} → RESOLUTION: {resolution}"

    # Tag it so retriever.py finds it for the right team + exception type
    tags = [
        f"team:{team_id}",
        f"exception:{employment_type}",
        "exception:all",         # always included — catches generic blockers
        "org:company",
    ]

    memory = MemoryItem(
        content=content,
        tags=tags,
        level="exception",
        source="resolved_blocker",
        relevance_score=1.0,     # resolved blockers are high-value memories
    )

    _write_memory(memory)

    confirmation = (
        f"🧠 Blocker logged to memory for future {team_id} employees.\n"
        f"   Blocker: {blocker}\n"
        f"   Resolution: {resolution}\n"
        f"   Tags: {tags}"
    )
    print(f"[ACTION: log_resolved_blocker] team={team_id} | {blocker[:60]}")
    return confirmation