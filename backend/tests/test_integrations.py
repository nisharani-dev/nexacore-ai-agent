"""
test_integrations.py
--------------------
Unit tests for Jira and Email integrations.
"""

import pytest

from backend.integrations.email import EmailClient
from backend.integrations.jira import JiraClient
from backend.integrations.ticket_router import create_external_ticket


class TestJiraClient:
    """Tests for Jira integration."""

    def test_jira_mock_mode_no_credentials(self):
        """Test Jira client in mock mode (no credentials)."""
        client = JiraClient(mock_mode=True)
        assert client.mock_mode is True

    def test_jira_create_ticket_mock(self):
        """Test creating a ticket in mock mode."""
        client = JiraClient(mock_mode=True)
        result = client.create_ticket(
            summary="Test ticket",
            description="Test description",
            issue_type="Task",
            assignee="user@company.com",
            priority="Medium",
        )
        assert "ticket_key" in result
        assert "ticket_url" in result
        assert result["backend"] == "mock"
        assert "ONBOARD" in result["ticket_key"]

    def test_jira_get_ticket_mock(self):
        """Test fetching a ticket in mock mode."""
        client = JiraClient(mock_mode=True)
        result = client.get_ticket("ONBOARD-001")
        assert result["backend"] == "mock"

    def test_jira_update_ticket_mock(self):
        """Test updating a ticket in mock mode."""
        client = JiraClient(mock_mode=True)
        result = client.update_ticket(
            "ONBOARD-001",
            status="Done",
            assignee="new_user@company.com",
        )
        assert result["updated"] is True
        assert result["backend"] == "mock"

    def test_jira_auto_detect_mock_mode(self):
        """Test auto-detection of mock mode."""
        # No api_token set, should be mock
        client = JiraClient(api_token="")
        assert client.mock_mode is True


class TestEmailClient:
    """Tests for Email integration."""

    def test_email_mock_mode_no_credentials(self):
        """Test Email client in mock mode (no credentials)."""
        client = EmailClient(mock_mode=True)
        assert client.mock_mode is True

    def test_email_send_reminder_mock(self):
        """Test sending a reminder in mock mode."""
        client = EmailClient(mock_mode=True)
        result = client.send_reminder(
            recipient="user@company.com",
            subject="Test reminder",
            message="This is a test message",
        )
        assert result["sent"] is True
        assert result["recipient"] == "user@company.com"
        assert result["backend"] == "mock"

    def test_email_send_checklist_mock(self):
        """Test sending onboarding checklist in mock mode."""
        client = EmailClient(mock_mode=True)
        result = client.send_onboarding_checklist(
            recipient="alice@company.com",
            name="Alice Johnson",
            team="Platform Engineering",
            role="SDE-1",
            checklist_items=["Set up laptop", "Get AWS access", "Read onboarding docs"],
        )
        assert result["sent"] is True
        assert "welcome" in result["subject"].lower()

    def test_email_validate_recipient(self):
        """Test email validation."""
        client = EmailClient()
        assert client.validate_recipient("user@company.com") is True
        assert client.validate_recipient("user@example.org") is True
        assert client.validate_recipient("invalid-email") is False
        assert client.validate_recipient("@company.com") is False

    def test_email_auto_detect_mock_mode(self):
        """Test auto-detection of mock mode."""
        # No SMTP credentials set, should be mock
        client = EmailClient(smtp_user="", smtp_password="")
        assert client.mock_mode is True


def test_ticket_router_defaults_to_jira_mock():
    result = create_external_ticket(
        summary="Router smoke test",
        description="ticket router",
        assignee="IT Helpdesk",
        priority="Medium",
    )
    assert "ticket_key" in result
