"""
integrations/servicenow.py
--------------------------
ServiceNow Table API integration for creating tickets.
Supports mock mode when credentials are absent or INTEGRATIONS_MODE=demo.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import requests

from backend.settings import integrations_mode

logger = logging.getLogger(__name__)


class ServiceNowClient:
    """ServiceNow incident/task client with mock and live modes."""

    def __init__(
        self,
        instance_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        table: str | None = None,
        mock_mode: bool | None = None,
    ):
        self.instance_url = (instance_url or os.getenv("SERVICENOW_INSTANCE_URL", "")).rstrip("/")
        self.username = username or os.getenv("SERVICENOW_USERNAME", "")
        self.password = password or os.getenv("SERVICENOW_PASSWORD", "")
        self.table = table or os.getenv("SERVICENOW_TABLE", "incident")

        if mock_mode is None:
            self.mock_mode = integrations_mode() == "demo" or not (
                self.instance_url and self.username and self.password
            )
        else:
            self.mock_mode = mock_mode

        if self.mock_mode:
            logger.info("ServiceNowClient initialized in MOCK mode")
        else:
            logger.info("ServiceNowClient initialized for %s", self.instance_url)

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
        if self.mock_mode:
            return self._create_ticket_mock(
                summary=summary,
                description=description,
                assignee=assignee,
                priority=priority,
            )

        payload: dict[str, Any] = {
            "short_description": summary,
            "description": description,
            "urgency": self._map_priority(priority),
            "assignment_group": assignee or "IT Helpdesk",
        }
        if custom_fields:
            payload.update(custom_fields)

        url = f"{self.instance_url}/api/now/table/{self.table}"
        try:
            response = requests.post(
                url,
                json=payload,
                auth=(self.username, self.password),
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=15,
            )
            response.raise_for_status()
            result = response.json().get("result", {})
            ticket_key = result.get("number", result.get("sys_id", "SN-UNKNOWN"))
            return {
                "ticket_key": ticket_key,
                "ticket_url": f"{self.instance_url}/nav_to.do?uri=/{self.table}.do?sys_id={result.get('sys_id', '')}",
                "summary": summary,
                "description": description,
                "backend": "servicenow",
            }
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to create ServiceNow ticket: %s", exc)
            raise

    def _create_ticket_mock(
        self,
        *,
        summary: str,
        description: str,
        assignee: str | None,
        priority: str,
    ) -> dict[str, Any]:
        seed = f"{summary}|{description}|{assignee}|{priority}"
        ticket_num = int(hashlib.md5(seed.encode()).hexdigest(), 16) % 9000 + 1000
        ticket_key = f"INC{ticket_num}"
        logger.info("[MOCK] Would create ServiceNow ticket %s: %s", ticket_key, summary)
        return {
            "ticket_key": ticket_key,
            "ticket_url": f"{self.instance_url or 'https://dev.service-now.com'}/nav_to.do?uri=/{self.table}.do?number={ticket_key}",
            "summary": summary,
            "description": description,
            "backend": "mock",
        }

    @staticmethod
    def _map_priority(priority: str) -> str:
        mapping = {
            "lowest": "4",
            "low": "3",
            "medium": "2",
            "high": "1",
            "highest": "1",
            "urgent": "1",
        }
        return mapping.get(priority.lower(), "2")
