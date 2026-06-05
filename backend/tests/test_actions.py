"""
test_actions.py
---------------
Unit tests for action handlers (raise_ticket, send_reminder).
"""

import tempfile
from pathlib import Path

import pytest

from backend.actions.raise_ticket import raise_ticket
from backend.actions.send_reminder import send_reminder
from backend.db import AppDatabase


@pytest.fixture
def test_db():
    """Create a test database for action tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    original_instance = AppDatabase._instance
    AppDatabase._instance = None

    db = AppDatabase(db_path)
    AppDatabase._instance = db
    yield db

    Path(db_path).unlink(missing_ok=True)
    AppDatabase._instance = original_instance


class TestRaiseTicketAction:
    """Tests for raise_ticket action."""

    def test_raise_ticket_creates_entry(self, test_db):
        """Test that raise_ticket creates database entry."""
        result = raise_ticket(
            title="AWS access needed",
            description="Onboarding access",
            assignee_team="IT",
            priority="high",
        )
        assert "raised successfully" in result.lower()
        # Verify database entry
        tickets = test_db.list_tickets()
        assert len(tickets) > 0

    def test_raise_ticket_with_different_priorities(self, test_db):
        """Test raise_ticket with different priorities."""
        for priority in ["low", "medium", "high", "urgent"]:
            result = raise_ticket(
                title=f"Test {priority}",
                description="Test",
                priority=priority,
            )
            assert "raised successfully" in result.lower()

    def test_raise_ticket_fallback_id(self, test_db):
        """Test that raise_ticket generates valid ID on failure."""
        result = raise_ticket(
            title="Test fallback",
            description="Testing fallback ID generation",
        )
        assert "IT-" in result or "raised" in result.lower()


class TestSendReminderAction:
    """Tests for send_reminder action."""

    def test_send_reminder_creates_entry(self, test_db):
        """Test that send_reminder creates database entry."""
        result = send_reminder(
            recipient="user@company.com",
            message="AWS access ready",
            due_in_hours=72,
        )
        assert "scheduled" in result.lower()
        # Verify database entry
        reminders = test_db.list_reminders()
        assert len(reminders) > 0

    def test_send_reminder_with_different_hours(self, test_db):
        """Test send_reminder with different time offsets."""
        for hours in [1, 6, 24, 72]:
            result = send_reminder(
                recipient=f"user{hours}@company.com",
                message="Test reminder",
                due_in_hours=hours,
            )
            assert "scheduled" in result.lower()

    def test_send_reminder_email_address(self, test_db):
        """Test that send_reminder handles email addresses."""
        result = send_reminder(
            recipient="alice.johnson@company.com",
            message="Welcome to the team!",
            due_in_hours=24,
        )
        assert "alice.johnson@company.com" in result
