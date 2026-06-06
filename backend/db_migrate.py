"""
db_migrate.py
-------------
Run Alembic migrations when DATABASE_URL points at Postgres.
Called once from gunicorn master (on_starting) before workers fork.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alembic.config import Config

logger = logging.getLogger(__name__)

CORE_TABLES = ("tickets", "reminders", "sessions", "audit_events", "memory_metadata")
EXTRA_TABLES = ("chat_messages", "feedback")
INITIAL_REVISION = "0a45e4524ff5"


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
    return cursor.fetchone()[0] is not None


def _current_alembic_version(cursor) -> str | None:
    if not _table_exists(cursor, "alembic_version"):
        return None
    cursor.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cursor.fetchone()
    return row[0] if row else None


def _stamp_revision_for_existing_schema(cursor, config: "Config") -> None:
    """
    Recover when tables were created outside Alembic (e.g. failed deploys with
    _initialize()) but alembic_version was never stamped.
    """
    from alembic import command

    if _current_alembic_version(cursor) is not None:
        return

    existing_core = [name for name in CORE_TABLES if _table_exists(cursor, name)]
    if not existing_core:
        return

    if len(existing_core) != len(CORE_TABLES):
        missing = [name for name in CORE_TABLES if name not in existing_core]
        raise RuntimeError(
            "Partial Postgres schema without alembic_version "
            f"(found: {existing_core}, missing: {missing}). "
            "Reset the database, then redeploy:\n"
            "  DROP SCHEMA public CASCADE;\n"
            "  CREATE SCHEMA public;\n"
            "  GRANT ALL ON SCHEMA public TO public;"
        )

    extra_ok = all(_table_exists(cursor, name) for name in EXTRA_TABLES)
    target = "head" if extra_ok else INITIAL_REVISION
    logger.warning(
        "Core tables exist without alembic_version; stamping %s before upgrade",
        target,
    )
    command.stamp(config, target)


def run_migrations() -> None:
    """Apply pending Alembic migrations for Postgres deployments."""
    db_url = os.getenv("DATABASE_URL", "").strip()
    if not db_url:
        return

    import psycopg2

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT pg_advisory_lock(87654321)")
    try:
        from alembic import command
        from alembic.config import Config

        alembic_ini = Path(__file__).resolve().parent / "alembic.ini"
        config = Config(str(alembic_ini))
        _stamp_revision_for_existing_schema(cur, config)
        command.upgrade(config, "head")
        logger.info("Database migrations applied successfully")
    except Exception:
        logger.exception("Failed to run database migrations")
        raise
    finally:
        cur.execute("SELECT pg_advisory_unlock(87654321)")
        cur.close()
        conn.close()
