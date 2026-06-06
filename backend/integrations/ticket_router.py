"""
integrations/ticket_router.py
-----------------------------
Route ticket creation to Jira or ServiceNow based on TICKET_BACKEND.
"""

from __future__ import annotations

import os
from typing import Any

from backend.integrations.jira import JiraClient
from backend.integrations.servicenow import ServiceNowClient


def ticket_backend() -> str:
    return os.getenv("TICKET_BACKEND", "jira").strip().lower()


def create_external_ticket(
    *,
    summary: str,
    description: str = "",
    issue_type: str = "Task",
    assignee: str | None = None,
    priority: str = "Medium",
    labels: list[str] | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    backend = ticket_backend()
    if backend == "servicenow":
        client = ServiceNowClient()
    else:
        client = JiraClient()
    return client.create_ticket(
        summary=summary,
        description=description,
        issue_type=issue_type,
        assignee=assignee,
        priority=priority,
        labels=labels,
        custom_fields=custom_fields,
    )
