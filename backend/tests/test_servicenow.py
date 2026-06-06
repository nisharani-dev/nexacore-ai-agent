"""Tests for ServiceNow integration."""

from backend.integrations.servicenow import ServiceNowClient


class TestServiceNowClient:
    def test_mock_mode(self):
        client = ServiceNowClient(mock_mode=True)
        assert client.mock_mode is True

    def test_create_ticket_mock(self):
        client = ServiceNowClient(mock_mode=True)
        result = client.create_ticket(
            summary="Laptop provisioning",
            description="New hire onboarding",
            assignee="IT Helpdesk",
            priority="Medium",
        )
        assert result["backend"] == "mock"
        assert result["ticket_key"].startswith("INC")
