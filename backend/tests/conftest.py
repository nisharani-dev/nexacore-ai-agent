"""
conftest.py
-----------
Pytest configuration and shared fixtures for all tests.
"""

import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from backend.server import app


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_ticket() -> dict:
    """Sample ticket data for tests."""
    return {
        "ticket_id": "IT-1234",
        "title": "AWS access needed",
        "description": "New engineer onboarding",
        "assignee_team": "IT Helpdesk",
        "priority": "medium",
        "status": "open",
    }


@pytest.fixture
def sample_session() -> dict:
    """Sample session data for tests."""
    return {
        "session_id": "sess-test-001",
        "user_name": "Alice Johnson",
        "team_name": "platform",
        "role_title": "SDE-1",
        "employment_type": "fte",
        "auth_subject": "alice@company.com",
        "metadata": {"onboarded_at": "2026-06-05T10:00:00Z"},
    }


@pytest.fixture
def sample_reminder() -> dict:
    """Sample reminder data for tests."""
    return {
        "recipient": "alice@company.com",
        "message": "Your AWS access has been provisioned",
        "due_in_hours": 72,
        "scheduled_for": "2026-06-08T10:00:00Z",
    }
