"""Postgres integration smoke tests (skipped without DATABASE_URL)."""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set",
)


@pytest.fixture
def postgres_db():
    from backend.db_migrate import run_migrations
    from backend.db_postgres import AppDatabasePostgres

    run_migrations()
    AppDatabasePostgres._instance = None
    AppDatabasePostgres._pool = None
    db = AppDatabasePostgres()
    yield db
    AppDatabasePostgres._instance = None
    AppDatabasePostgres._pool = None


def test_postgres_healthcheck(postgres_db):
    assert postgres_db.healthcheck()["status"] == "ok"
    assert postgres_db.healthcheck()["backend"] == "postgresql"


def test_postgres_ticket_roundtrip(postgres_db):
    ticket = postgres_db.upsert_ticket(
        ticket_id="PG-TEST-001",
        title="Postgres smoke test",
        description="verify ticket persistence",
        assignee_team="IT Helpdesk",
        priority="medium",
    )
    assert ticket["ticket_id"] == "PG-TEST-001"
    listed = postgres_db.list_tickets(limit=5)
    assert any(row["id"] == "PG-TEST-001" for row in listed)


def test_postgres_session_and_chat_messages(postgres_db):
    session_id = "pg-session-smoke"
    postgres_db.upsert_session(
        session_id=session_id,
        user_name="Smoke Tester",
        team_name="platform",
        role_title="SDE-1",
        employment_type="fte",
    )
    postgres_db.insert_chat_message(
        session_id=session_id,
        role="user",
        content="hello postgres",
    )
    messages = postgres_db.list_chat_messages(session_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "hello postgres"
