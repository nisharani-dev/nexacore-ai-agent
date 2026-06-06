"""
db_postgres.py
--------------
PostgreSQL-backed operational store for production deployments.
Implements the same interface as db.py (SQLite) for compatibility.

Uses psycopg2 for database access.
Requires DATABASE_URL environment variable (postgresql://user:pass@host:port/db)
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator
from uuid import uuid4

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppDatabasePostgres:
    """PostgreSQL implementation of application database."""

    _instance: "AppDatabasePostgres | None" = None
    _pool: SimpleConnectionPool | None = None

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize connection pool. database_url should be postgresql://..."""
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL environment variable must be set for PostgreSQL backend")

        self.database_url = url
        # Create connection pool (min 1, max 5 connections)
        self._pool = SimpleConnectionPool(1, 5, url)
        self._initialize()

    @classmethod
    def get(cls) -> "AppDatabasePostgres":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @contextmanager
    def connect(self) -> Iterator[psycopg2.extensions.connection]:
        """Get connection from pool, auto-commit on success."""
        connection = self._pool.getconn()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            self._pool.putconn(connection)

    def _initialize(self) -> None:
        """Create tables and indexes on startup."""
        statements = [
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                assignee_team TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                due_in_hours INTEGER NOT NULL,
                scheduled_for TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_name TEXT,
                team_name TEXT,
                role_title TEXT,
                employment_type TEXT,
                auth_subject TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor TEXT,
                session_id TEXT,
                request_id TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS memory_metadata (
                id TEXT PRIMARY KEY,
                namespace TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                level TEXT NOT NULL,
                source TEXT NOT NULL,
                tags_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                backend_kind TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(content_hash, namespace)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                helpful INTEGER NOT NULL,
                comment TEXT,
                team_name TEXT,
                query_text TEXT,
                created_at TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_tickets_team ON tickets(assignee_team)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
            "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_recipient ON reminders(recipient)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status)",
            "CREATE INDEX IF NOT EXISTS idx_reminders_created_at ON reminders(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_team_name ON sessions(team_name)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_employment_type ON sessions(employment_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_session_id ON audit_events(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_metadata(namespace)",
            "CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_metadata(level)",
            "CREATE INDEX IF NOT EXISTS idx_memory_source ON memory_metadata(source)",
            "CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_metadata(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_messages(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id)",
        ]
        with self.connect() as connection:
            cursor = connection.cursor()
            # Advisory lock prevents race between gunicorn workers on startup
            cursor.execute("SELECT pg_advisory_lock(12345678)")
            try:
                for statement in statements:
                    cursor.execute(statement)
            finally:
                cursor.execute("SELECT pg_advisory_unlock(12345678)")
            cursor.close()

    def healthcheck(self) -> dict[str, Any]:
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
        return {"status": "ok", "backend": "postgresql"}

    def upsert_ticket(
        self,
        *,
        ticket_id: str,
        title: str,
        description: str,
        assignee_team: str,
        priority: str,
        status: str = "open",
    ) -> dict[str, Any]:
        now = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO tickets (id, title, description, assignee_team, priority, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                  title = EXCLUDED.title,
                  description = EXCLUDED.description,
                  assignee_team = EXCLUDED.assignee_team,
                  priority = EXCLUDED.priority,
                  status = EXCLUDED.status,
                  updated_at = EXCLUDED.updated_at
                """,
                (ticket_id, title, description, assignee_team, priority, status, now, now),
            )
            cursor.close()
        return {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "assignee_team": assignee_team,
            "priority": priority,
            "status": status,
            "updated_at": now,
        }

    def list_tickets(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            cursor.close()
        return [dict(row) for row in rows]

    def create_reminder(
        self,
        *,
        recipient: str,
        message: str,
        due_in_hours: int,
        scheduled_for: str,
    ) -> dict[str, Any]:
        reminder_id = str(uuid4())
        created_at = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO reminders (id, recipient, message, due_in_hours, scheduled_for, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (reminder_id, recipient, message, due_in_hours, scheduled_for, "scheduled", created_at),
            )
            cursor.close()
        return {
            "id": reminder_id,
            "recipient": recipient,
            "message": message,
            "due_in_hours": due_in_hours,
            "scheduled_for": scheduled_for,
            "status": "scheduled",
            "created_at": created_at,
        }

    def list_reminders(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM reminders ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            cursor.close()
        return [dict(row) for row in rows]

    def upsert_session(
        self,
        *,
        session_id: str,
        user_name: str = "",
        team_name: str = "",
        role_title: str = "",
        employment_type: str = "",
        auth_subject: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        metadata_json = json.dumps(metadata or {}, ensure_ascii=True)
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (id, user_name, team_name, role_title, employment_type, auth_subject, created_at, last_seen_at, metadata_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(id) DO UPDATE SET
                  user_name = EXCLUDED.user_name,
                  team_name = EXCLUDED.team_name,
                  role_title = EXCLUDED.role_title,
                  employment_type = EXCLUDED.employment_type,
                  auth_subject = EXCLUDED.auth_subject,
                  last_seen_at = EXCLUDED.last_seen_at,
                  metadata_json = EXCLUDED.metadata_json
                """,
                (
                    session_id,
                    user_name,
                    team_name,
                    role_title,
                    employment_type,
                    auth_subject,
                    now,
                    now,
                    metadata_json,
                ),
            )
            cursor.close()
        return {
            "session_id": session_id,
            "user_name": user_name,
            "team_name": team_name,
            "role_title": role_title,
            "employment_type": employment_type,
            "auth_subject": auth_subject,
            "last_seen_at": now,
        }

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
            row = cursor.fetchone()
            cursor.close()
        if row is None:
            return None
        payload = dict(row)
        payload["metadata"] = json.loads(payload.pop("metadata_json"))
        return payload

    def insert_audit_event(
        self,
        *,
        event_type: str,
        actor: str = "",
        session_id: str = "",
        request_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event_id = str(uuid4())
        created_at = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO audit_events (id, event_type, actor, session_id, request_id, payload_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    event_id,
                    event_type,
                    actor,
                    session_id,
                    request_id,
                    json.dumps(payload or {}, ensure_ascii=True),
                    created_at,
                ),
            )
            cursor.close()
        return {
            "id": event_id,
            "event_type": event_type,
            "actor": actor,
            "session_id": session_id,
            "request_id": request_id,
            "created_at": created_at,
        }

    def list_audit_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            cursor.close()
        events: list[dict[str, Any]] = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event.pop("payload_json"))
            events.append(event)
        return events

    def upsert_memory_metadata(
        self,
        *,
        memory_id: str,
        namespace: str,
        content_hash: str,
        level: str,
        source: str,
        tags: list[str],
        metadata: dict[str, Any],
        backend_kind: str,
    ) -> None:
        now = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO memory_metadata (
                    id, namespace, content_hash, level, source, tags_json, metadata_json, backend_kind, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(content_hash, namespace) DO UPDATE SET
                  level = EXCLUDED.level,
                  source = EXCLUDED.source,
                  tags_json = EXCLUDED.tags_json,
                  metadata_json = EXCLUDED.metadata_json,
                  backend_kind = EXCLUDED.backend_kind,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    memory_id,
                    namespace,
                    content_hash,
                    level,
                    source,
                    json.dumps(tags, ensure_ascii=True),
                    json.dumps(metadata, ensure_ascii=True),
                    backend_kind,
                    now,
                    now,
                ),
            )
            cursor.close()

    def memory_metadata_summary(self) -> dict[str, Any]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT COUNT(*) as total FROM memory_metadata")
            total = cursor.fetchone()["total"]
            cursor.execute("SELECT backend_kind, COUNT(*) as count FROM memory_metadata GROUP BY backend_kind")
            by_backend_rows = cursor.fetchall()
            cursor.close()
        return {
            "total": total,
            "by_backend": {row["backend_kind"]: row["count"] for row in by_backend_rows},
        }

    def get_database_stats(self) -> dict[str, Any]:
        """Return operational statistics for monitoring."""
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT COUNT(*) as count FROM tickets")
            ticket_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM reminders")
            reminder_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM sessions")
            session_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM audit_events")
            audit_count = cursor.fetchone()["count"]
            cursor.execute("SELECT COUNT(*) as count FROM memory_metadata")
            memory_count = cursor.fetchone()["count"]

            # Status distributions
            cursor.execute("SELECT status, COUNT(*) as count FROM tickets GROUP BY status")
            ticket_by_status = cursor.fetchall()
            cursor.execute("SELECT status, COUNT(*) as count FROM reminders GROUP BY status")
            reminder_by_status = cursor.fetchall()

            # Time-based stats
            cursor.execute(
                "SELECT COUNT(*) as count FROM sessions WHERE created_at > NOW() - INTERVAL '1 day'"
            )
            session_today = cursor.fetchone()["count"]
            cursor.execute(
                "SELECT COUNT(*) as count FROM audit_events WHERE created_at > NOW() - INTERVAL '1 day'"
            )
            audit_today = cursor.fetchone()["count"]
            cursor.close()

        return {
            "tables": {
                "tickets": ticket_count,
                "reminders": reminder_count,
                "sessions": session_count,
                "audit_events": audit_count,
                "memory_metadata": memory_count,
            },
            "ticket_status_distribution": {row["status"]: row["count"] for row in ticket_by_status},
            "reminder_status_distribution": {row["status"]: row["count"] for row in reminder_by_status},
            "today": {"sessions_created": session_today, "audit_events": audit_today},
        }

    def list_sessions(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """List recent sessions."""
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                "SELECT id, user_name, team_name, role_title, employment_type, created_at, last_seen_at FROM sessions ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cursor.fetchall()
            cursor.close()
        return [dict(row) for row in rows]

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Get a single ticket by ID."""
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,))
            row = cursor.fetchone()
            cursor.close()
        return dict(row) if row else None

    def get_reminder(self, reminder_id: str) -> dict[str, Any] | None:
        """Get a single reminder by ID."""
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT * FROM reminders WHERE id = %s", (reminder_id,))
            row = cursor.fetchone()
            cursor.close()
        return dict(row) if row else None

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        """Update a ticket's status."""
        now = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE tickets SET status = %s, updated_at = %s WHERE id = %s",
                (status, now, ticket_id),
            )
            cursor.close()

    def insert_chat_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid4())
        created_at = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, metadata_json, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    json.dumps(metadata or {}, ensure_ascii=True),
                    created_at,
                ),
            )
            cursor.close()
        return {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
            "created_at": created_at,
        }

    def list_chat_messages(self, session_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()
            cursor.close()
        messages: list[dict[str, Any]] = []
        for row in rows:
            message = dict(row)
            message["metadata"] = json.loads(message.pop("metadata_json"))
            messages.append(message)
        return messages

    def insert_feedback(
        self,
        *,
        session_id: str = "",
        helpful: bool,
        comment: str = "",
        team_name: str = "",
        query_text: str = "",
    ) -> dict[str, Any]:
        feedback_id = str(uuid4())
        created_at = utc_now_iso()
        with self.connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO feedback (id, session_id, helpful, comment, team_name, query_text, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    feedback_id,
                    session_id,
                    1 if helpful else 0,
                    comment,
                    team_name,
                    query_text,
                    created_at,
                ),
            )
            cursor.close()
        return {
            "id": feedback_id,
            "session_id": session_id,
            "helpful": helpful,
            "comment": comment,
            "team_name": team_name,
            "query_text": query_text,
            "created_at": created_at,
        }

    def feedback_summary(self) -> dict[str, Any]:
        with self.connect() as connection:
            cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute("SELECT COUNT(*) as total FROM feedback")
            total = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) as helpful FROM feedback WHERE helpful = 1")
            helpful = cursor.fetchone()["helpful"]
            cursor.close()
        return {
            "total": total,
            "helpful": helpful,
            "not_helpful": total - helpful,
            "helpful_rate": round(helpful / total, 3) if total else 0.0,
        }
