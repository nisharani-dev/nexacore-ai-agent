"""
db.py
-----
Database abstraction layer for operational store.
Supports both SQLite and PostgreSQL backends.

Auto-detects based on DATABASE_URL environment variable:
- If DATABASE_URL set → PostgreSQL (db_postgres.AppDatabasePostgres)
- Otherwise → SQLite (AppDatabase)
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Iterator
from uuid import uuid4

from backend.runtime_paths import database_path

DB_PATH = database_path()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppDatabase:
    _instance: "AppDatabase | None" = None
    _instance_lock = Lock()

    def __new__(cls, db_path: str | Path | None = None) -> "AppDatabase":
        """Factory: Return PostgreSQL or SQLite instance based on DATABASE_URL."""
        if os.getenv("DATABASE_URL"):
            # Use PostgreSQL backend
            from backend.db_postgres import AppDatabasePostgres
            return AppDatabasePostgres()  # type: ignore
        # Fall back to SQLite
        return super().__new__(cls)

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    @classmethod
    def get(cls) -> "AppDatabase":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            try:
                yield connection
                connection.commit()
            finally:
                connection.close()

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA synchronous=NORMAL;
                PRAGMA cache_size=10000;

                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    assignee_team TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tickets_team ON tickets(assignee_team);
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
                CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC);

                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    recipient TEXT NOT NULL,
                    message TEXT NOT NULL,
                    due_in_hours INTEGER NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_reminders_recipient ON reminders(recipient);
                CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status);
                CREATE INDEX IF NOT EXISTS idx_reminders_created_at ON reminders(created_at DESC);

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
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_team_name ON sessions(team_name);
                CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_employment_type ON sessions(employment_type);

                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    session_id TEXT,
                    request_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
                CREATE INDEX IF NOT EXISTS idx_audit_session_id ON audit_events(session_id);
                CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events(created_at DESC);

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
                );

                CREATE INDEX IF NOT EXISTS idx_memory_namespace ON memory_metadata(namespace);
                CREATE INDEX IF NOT EXISTS idx_memory_level ON memory_metadata(level);
                CREATE INDEX IF NOT EXISTS idx_memory_source ON memory_metadata(source);
                CREATE INDEX IF NOT EXISTS idx_memory_created_at ON memory_metadata(created_at DESC);

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages(created_at DESC);

                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    helpful INTEGER NOT NULL,
                    comment TEXT,
                    team_name TEXT,
                    query_text TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_feedback_session ON feedback(session_id);
                """
            )

    def healthcheck(self) -> dict[str, Any]:
        with self.connect() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok", "db_path": str(self.db_path)}

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
            connection.execute(
                """
                INSERT INTO tickets (id, title, description, assignee_team, priority, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  title = excluded.title,
                  description = excluded.description,
                  assignee_team = excluded.assignee_team,
                  priority = excluded.priority,
                  status = excluded.status,
                  updated_at = excluded.updated_at
                """,
                (ticket_id, title, description, assignee_team, priority, status, now, now),
            )
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
            rows = connection.execute(
                "SELECT * FROM tickets ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
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
            connection.execute(
                """
                INSERT INTO reminders (id, recipient, message, due_in_hours, scheduled_for, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (reminder_id, recipient, message, due_in_hours, scheduled_for, "scheduled", created_at),
            )
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
            rows = connection.execute(
                "SELECT * FROM reminders ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
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
            connection.execute(
                """
                INSERT INTO sessions (id, user_name, team_name, role_title, employment_type, auth_subject, created_at, last_seen_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  user_name = excluded.user_name,
                  team_name = excluded.team_name,
                  role_title = excluded.role_title,
                  employment_type = excluded.employment_type,
                  auth_subject = excluded.auth_subject,
                  last_seen_at = excluded.last_seen_at,
                  metadata_json = excluded.metadata_json
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
            row = connection.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
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
            connection.execute(
                """
                INSERT INTO audit_events (id, event_type, actor, session_id, request_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
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
            connection.execute(
                """
                INSERT INTO memory_metadata (
                    id, namespace, content_hash, level, source, tags_json, metadata_json, backend_kind, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash, namespace) DO UPDATE SET
                  level = excluded.level,
                  source = excluded.source,
                  tags_json = excluded.tags_json,
                  metadata_json = excluded.metadata_json,
                  backend_kind = excluded.backend_kind,
                  updated_at = excluded.updated_at
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

    def memory_metadata_summary(self) -> dict[str, Any]:
        with self.connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM memory_metadata").fetchone()[0]
            by_backend = connection.execute(
                "SELECT backend_kind, COUNT(*) as count FROM memory_metadata GROUP BY backend_kind"
            ).fetchall()
        return {
            "total": total,
            "by_backend": {row["backend_kind"]: row["count"] for row in by_backend},
        }

    def get_database_stats(self) -> dict[str, Any]:
        """Return operational statistics for monitoring."""
        with self.connect() as connection:
            ticket_count = connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
            reminder_count = connection.execute("SELECT COUNT(*) FROM reminders").fetchone()[0]
            session_count = connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            audit_count = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            memory_count = connection.execute("SELECT COUNT(*) FROM memory_metadata").fetchone()[0]

            # Status distributions
            ticket_by_status = connection.execute(
                "SELECT status, COUNT(*) as count FROM tickets GROUP BY status"
            ).fetchall()
            reminder_by_status = connection.execute(
                "SELECT status, COUNT(*) as count FROM reminders GROUP BY status"
            ).fetchall()

            # Time-based stats
            session_today = connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE created_at > datetime('now', '-1 day')"
            ).fetchone()[0]
            audit_today = connection.execute(
                "SELECT COUNT(*) FROM audit_events WHERE created_at > datetime('now', '-1 day')"
            ).fetchone()[0]

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
            rows = connection.execute(
                "SELECT id, user_name, team_name, role_title, employment_type, created_at, last_seen_at FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Get a single ticket by ID."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM tickets WHERE id = ?",
                (ticket_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_reminder(self, reminder_id: str) -> dict[str, Any] | None:
        """Get a single reminder by ID."""
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM reminders WHERE id = ?",
                (reminder_id,),
            ).fetchone()
        return dict(row) if row else None

    def update_ticket_status(self, ticket_id: str, status: str) -> None:
        """Update a ticket's status."""
        now = utc_now_iso()
        with self.connect() as connection:
            connection.execute(
                "UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, ticket_id),
            )

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
            connection.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
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
            rows = connection.execute(
                """
                SELECT * FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
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
            connection.execute(
                """
                INSERT INTO feedback (id, session_id, helpful, comment, team_name, query_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
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
            total = connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            helpful = connection.execute(
                "SELECT COUNT(*) FROM feedback WHERE helpful = 1"
            ).fetchone()[0]
        return {
            "total": total,
            "helpful": helpful,
            "not_helpful": total - helpful,
            "helpful_rate": round(helpful / total, 3) if total else 0.0,
        }
