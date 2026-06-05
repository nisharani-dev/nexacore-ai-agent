"""
test_db.py
----------
Unit tests for database layer (SQLite).
"""

import json
import tempfile
from pathlib import Path

import pytest

from backend.db import AppDatabase


@pytest.fixture
def sqlite_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    original_instance = AppDatabase._instance
    AppDatabase._instance = None

    db = AppDatabase(db_path)
    AppDatabase._instance = db
    yield db

    Path(db_path).unlink(missing_ok=True)
    AppDatabase._instance = original_instance


class TestDatabaseInitialization:
    """Tests for database initialization."""

    def test_create_instance(self, sqlite_db):
        """Test creating database instance."""
        assert sqlite_db is not None
        assert sqlite_db.healthcheck()["status"] == "ok"

    def test_singleton_pattern(self, sqlite_db):
        """Test singleton pattern."""
        db1 = AppDatabase.get()
        db2 = AppDatabase.get()
        assert db1 is db2


class TestTickets:
    """Tests for ticket operations."""

    def test_upsert_ticket(self, sqlite_db):
        """Test creating a ticket."""
        result = sqlite_db.upsert_ticket(
            ticket_id="IT-001",
            title="AWS access",
            description="Onboarding access",
            assignee_team="IT",
            priority="high",
            status="open",
        )
        assert result["ticket_id"] == "IT-001"
        assert result["title"] == "AWS access"

    def test_get_ticket(self, sqlite_db):
        """Test retrieving a ticket."""
        # Create
        sqlite_db.upsert_ticket(
            ticket_id="IT-002",
            title="GitHub SSH key",
            description="Setup SSH",
            assignee_team="Engineering",
            priority="medium",
        )
        # Retrieve
        ticket = sqlite_db.get_ticket("IT-002")
        assert ticket is not None
        assert ticket["title"] == "GitHub SSH key"

    def test_list_tickets(self, sqlite_db):
        """Test listing tickets."""
        # Create multiple tickets
        for i in range(3):
            sqlite_db.upsert_ticket(
                ticket_id=f"IT-{i}",
                title=f"Task {i}",
                description=f"Description {i}",
                assignee_team="IT",
                priority="low",
            )
        # List
        tickets = sqlite_db.list_tickets(limit=10)
        assert len(tickets) == 3

    def test_update_ticket_status(self, sqlite_db):
        """Test updating ticket status."""
        sqlite_db.upsert_ticket(
            ticket_id="IT-003",
            title="Update test",
            description="Test",
            assignee_team="IT",
            priority="low",
        )
        sqlite_db.update_ticket_status("IT-003", "closed")
        ticket = sqlite_db.get_ticket("IT-003")
        assert ticket["status"] == "closed"


class TestReminders:
    """Tests for reminder operations."""

    def test_create_reminder(self, sqlite_db):
        """Test creating a reminder."""
        result = sqlite_db.create_reminder(
            recipient="user@company.com",
            message="Follow up on AWS",
            due_in_hours=72,
            scheduled_for="2026-06-08T10:00:00Z",
        )
        assert result["recipient"] == "user@company.com"
        assert result["status"] == "scheduled"

    def test_get_reminder(self, sqlite_db):
        """Test retrieving a reminder."""
        result = sqlite_db.create_reminder(
            recipient="user@company.com",
            message="Test reminder",
            due_in_hours=24,
            scheduled_for="2026-06-06T10:00:00Z",
        )
        reminder_id = result["id"]

        reminder = sqlite_db.get_reminder(reminder_id)
        assert reminder is not None
        assert reminder["recipient"] == "user@company.com"

    def test_list_reminders(self, sqlite_db):
        """Test listing reminders."""
        for i in range(3):
            sqlite_db.create_reminder(
                recipient=f"user{i}@company.com",
                message=f"Reminder {i}",
                due_in_hours=24,
                scheduled_for="2026-06-06T10:00:00Z",
            )
        reminders = sqlite_db.list_reminders(limit=10)
        assert len(reminders) == 3


class TestSessions:
    """Tests for session operations."""

    def test_upsert_session(self, sqlite_db):
        """Test creating a session."""
        result = sqlite_db.upsert_session(
            session_id="sess-001",
            user_name="Alice Johnson",
            team_name="platform",
            role_title="SDE-1",
            employment_type="fte",
        )
        assert result["session_id"] == "sess-001"
        assert result["user_name"] == "Alice Johnson"

    def test_get_session(self, sqlite_db):
        """Test retrieving a session."""
        sqlite_db.upsert_session(
            session_id="sess-002",
            user_name="Bob Smith",
            team_name="infra",
            metadata={"onboarded_date": "2026-06-05"},
        )
        session = sqlite_db.get_session("sess-002")
        assert session is not None
        assert session["user_name"] == "Bob Smith"
        assert session["metadata"]["onboarded_date"] == "2026-06-05"

    def test_list_sessions(self, sqlite_db):
        """Test listing sessions."""
        for i in range(3):
            sqlite_db.upsert_session(
                session_id=f"sess-{i}",
                user_name=f"User {i}",
                team_name="engineering",
            )
        sessions = sqlite_db.list_sessions(limit=10)
        assert len(sessions) == 3


class TestAuditEvents:
    """Tests for audit event operations."""

    def test_insert_audit_event(self, sqlite_db):
        """Test creating an audit event."""
        result = sqlite_db.insert_audit_event(
            event_type="session_created",
            actor="alice@company.com",
            session_id="sess-001",
            payload={"team": "platform"},
        )
        assert result["event_type"] == "session_created"
        assert result["actor"] == "alice@company.com"

    def test_list_audit_events(self, sqlite_db):
        """Test listing audit events."""
        for i in range(3):
            sqlite_db.insert_audit_event(
                event_type=f"event_type_{i}",
                actor=f"user{i}@company.com",
                payload={"index": i},
            )
        events = sqlite_db.list_audit_events(limit=10)
        assert len(events) == 3


class TestMemoryMetadata:
    """Tests for memory metadata operations."""

    def test_upsert_memory_metadata(self, sqlite_db):
        """Test upserting memory metadata."""
        sqlite_db.upsert_memory_metadata(
            memory_id="mem-001",
            namespace="company",
            content_hash="hash-abc123",
            level="company",
            source="seed",
            tags=["vpn", "onboarding"],
            metadata={"category": "infrastructure"},
            backend_kind="local",
        )
        summary = sqlite_db.memory_metadata_summary()
        assert summary["total"] >= 1

    def test_memory_metadata_summary(self, sqlite_db):
        """Test memory metadata summary."""
        # Create multiple memory records
        for i in range(5):
            sqlite_db.upsert_memory_metadata(
                memory_id=f"mem-{i}",
                namespace="test",
                content_hash=f"hash-{i}",
                level="team",
                source="test",
                tags=["test"],
                metadata={},
                backend_kind="local",
            )
        summary = sqlite_db.memory_metadata_summary()
        assert summary["total"] == 5


class TestDatabaseStats:
    """Tests for database statistics."""

    def test_get_database_stats(self, sqlite_db):
        """Test getting database statistics."""
        # Create some data
        sqlite_db.upsert_ticket(
            ticket_id="IT-stat-001",
            title="Stat test",
            description="Test",
            assignee_team="IT",
            priority="low",
        )
        sqlite_db.create_reminder(
            recipient="user@company.com",
            message="Stat test",
            due_in_hours=24,
            scheduled_for="2026-06-06T10:00:00Z",
        )
        sqlite_db.upsert_session(
            session_id="sess-stat-001",
            user_name="Stat User",
        )

        stats = sqlite_db.get_database_stats()
        assert "tables" in stats
        assert stats["tables"]["tickets"] >= 1
        assert stats["tables"]["reminders"] >= 1
        assert stats["tables"]["sessions"] >= 1
