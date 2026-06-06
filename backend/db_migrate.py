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

logger = logging.getLogger(__name__)


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
        command.upgrade(config, "head")
        logger.info("Database migrations applied successfully")
    except Exception:
        logger.exception("Failed to run database migrations")
        raise
    finally:
        cur.execute("SELECT pg_advisory_unlock(87654321)")
        cur.close()
        conn.close()
