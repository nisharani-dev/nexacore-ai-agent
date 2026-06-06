"""
raise_ticket.py  —  Person 4 (Ingestion + Actions)
----------------------------------------------------
LangChain tool: raises an IT access ticket for the new employee.

What is a LangChain tool?
    The agent (Person 1) is built with LangChain. A "tool" is just a
    Python function with a @tool decorator and a docstring that explains
    WHEN the agent should call it. The agent reads the docstring and
    decides on its own: "the user needs AWS access — I should call raise_it_ticket."

    You don't tell the agent "call this tool now." It figures it out.

Implementation:
    Posts to Jira Cloud API. Falls back to local mock if no Jira credentials.
    Also persists to local database for audit trail and monitoring.
"""

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import AppDatabase
from backend.integrations.ticket_router import create_external_ticket


def raise_ticket(
    title: str,
    description: str,
    assignee_team: str = "IT Helpdesk",
    priority: str = "medium",
) -> str:
    """
    Raises an IT support ticket via Jira (or mock if not configured).
    Also persists to local database for audit trail.
    """
    # Map priority string to Jira priority
    priority_map = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "urgent": "Highest",
    }
    jira_priority = priority_map.get(priority.lower(), "Medium")

    try:
        external_result = create_external_ticket(
            summary=title,
            description=description,
            issue_type="Task",
            assignee=assignee_team,
            priority=jira_priority,
            labels=["onboarding", "auto-generated"],
        )
        ticket_key = external_result.get(
            "ticket_key",
            f"IT-{hashlib.md5((title + assignee_team).encode()).hexdigest()[:8].upper()}",
        )
    except Exception as e:
        # Fallback to local ID if Jira fails
        seed = f"{title}|{description}|{assignee_team}|{priority}"
        ticket_num = int(hashlib.md5(seed.encode()).hexdigest(), 16) % 9000 + 1000
        ticket_key = f"IT-{ticket_num}"

    # Also persist to local database
    AppDatabase.get().upsert_ticket(
        ticket_id=ticket_key,
        title=title,
        description=description,
        assignee_team=assignee_team,
        priority=priority,
        status="open",
    )

    confirmation = (
        f"IT ticket {ticket_key} raised successfully.\n"
        f"Title: {title}\n"
        f"Assigned to: {assignee_team}\n"
        f"Priority: {priority}"
    )
    print(f"[ACTION: raise_ticket] {ticket_key} — {title}")
    return confirmation


def raise_it_ticket(description: str) -> str:
    return raise_ticket(
        title="Access request",
        description=description,
        assignee_team="IT Helpdesk",
        priority="medium",
    )
