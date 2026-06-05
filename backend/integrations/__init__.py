"""
integrations/jira.py
--------------------
Jira Cloud API integration for creating tickets.
Supports both mock (testing) and real Jira Cloud API modes.

Usage:
    from backend.integrations.jira import JiraClient
    client = JiraClient()
    ticket = client.create_ticket(
        summary="AWS access needed",
        description="New engineer onboarding",
        issue_type="Task",
        assignee="TEAM_LEAD"
    )
"""

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class JiraClient:
    """Jira Cloud API client. Supports mock and real modes."""

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        project_key: str | None = None,
        mock_mode: bool | None = None,
    ):
        """
        Initialize Jira client.

        Args:
            base_url: Jira instance URL (https://yourcompany.atlassian.net)
            api_token: API token for authentication (from Jira settings)
            project_key: Jira project key (e.g., "ONBOARD")
            mock_mode: Force mock mode. If None, auto-detect from env vars.
        """
        self.base_url = base_url or os.getenv("JIRA_BASE_URL", "https://dev.atlassian.net")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.project_key = project_key or os.getenv("JIRA_PROJECT_KEY", "ONBOARD")

        # Auto-detect mock mode: if no api token, use mock
        if mock_mode is None:
            self.mock_mode = not bool(self.api_token)
        else:
            self.mock_mode = mock_mode

        if self.mock_mode:
            logger.info("JiraClient initialized in MOCK mode (no credentials)")
        else:
            logger.info(f"JiraClient initialized for {self.base_url}")

    def create_ticket(
        self,
        *,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        assignee: str | None = None,
        priority: str = "Medium",
        labels: list[str] | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a Jira ticket (issue).

        Args:
            summary: Issue title
            description: Issue description/body
            issue_type: Type of issue (Task, Bug, Story, etc.)
            assignee: Assignee name or account ID
            priority: Priority level (Lowest, Low, Medium, High, Highest)
            labels: List of labels to apply
            custom_fields: Additional custom fields (field_id -> value)

        Returns:
            Dict with ticket_key and ticket_url, or mock_id in mock mode.
        """
        if self.mock_mode:
            return self._create_ticket_mock(
                summary=summary,
                description=description,
                issue_type=issue_type,
                assignee=assignee,
                priority=priority,
                labels=labels,
                custom_fields=custom_fields,
            )
        else:
            return self._create_ticket_real(
                summary=summary,
                description=description,
                issue_type=issue_type,
                assignee=assignee,
                priority=priority,
                labels=labels,
                custom_fields=custom_fields,
            )

    def _create_ticket_mock(
        self,
        *,
        summary: str,
        description: str,
        issue_type: str,
        assignee: str | None,
        priority: str,
        labels: list[str] | None,
        custom_fields: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Mock ticket creation (no API call)."""
        import hashlib
        from uuid import uuid4

        # Generate deterministic mock ticket ID
        ticket_seed = f"{summary}|{self.project_key}|{issue_type}"
        ticket_hash = hashlib.md5(ticket_seed.encode()).hexdigest()
        ticket_num = int(ticket_hash, 16) % 9000 + 1000
        ticket_key = f"{self.project_key}-{ticket_num}"

        payload = {
            "ticket_key": ticket_key,
            "ticket_url": f"{self.base_url}/browse/{ticket_key}",
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "assignee": assignee,
            "priority": priority,
            "labels": labels or [],
            "custom_fields": custom_fields or {},
            "created_at": None,  # Will be set when posted
            "backend": "mock",
        }

        logger.info(f"[MOCK] Would create ticket {ticket_key}: {summary}")
        return payload

    def _create_ticket_real(
        self,
        *,
        summary: str,
        description: str,
        issue_type: str,
        assignee: str | None,
        priority: str,
        labels: list[str] | None,
        custom_fields: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Create ticket using real Jira Cloud API."""
        url = f"{self.base_url}/rest/api/3/issues"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }

        # Build issue payload (Jira Cloud REST API v3 format)
        issue_payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self.project_key},
                "issuetype": {"name": issue_type},
                "summary": summary,
                "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
                "priority": {"name": priority},
            }
        }

        if labels:
            issue_payload["fields"]["labels"] = labels

        if assignee:
            issue_payload["fields"]["assignee"] = {"name": assignee}

        if custom_fields:
            issue_payload["fields"].update(custom_fields)

        try:
            response = requests.post(url, headers=headers, json=issue_payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            ticket_key = result.get("key", "UNKNOWN")
            return {
                "ticket_key": ticket_key,
                "ticket_url": f"{self.base_url}/browse/{ticket_key}",
                "ticket_id": result.get("id"),
                "summary": summary,
                "issue_type": issue_type,
                "created_at": None,
                "backend": "jira_cloud",
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create Jira ticket: {e}")
            raise

    def get_ticket(self, ticket_key: str) -> dict[str, Any]:
        """Fetch ticket details by key."""
        if self.mock_mode:
            logger.info(f"[MOCK] Fetching ticket {ticket_key}")
            return {"ticket_key": ticket_key, "found": False, "backend": "mock"}

        url = f"{self.base_url}/rest/api/3/issues/{ticket_key}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Jira ticket {ticket_key}: {e}")
            raise

    def update_ticket(
        self,
        ticket_key: str,
        **fields: Any,
    ) -> dict[str, Any]:
        """Update ticket fields."""
        if self.mock_mode:
            logger.info(f"[MOCK] Updating ticket {ticket_key} with {fields}")
            return {"ticket_key": ticket_key, "updated": True, "backend": "mock"}

        url = f"{self.base_url}/rest/api/3/issues/{ticket_key}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }

        payload = {"fields": fields}

        try:
            response = requests.put(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return {"ticket_key": ticket_key, "updated": True}
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update Jira ticket {ticket_key}: {e}")
            raise
