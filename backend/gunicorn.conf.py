"""
gunicorn.conf.py
----------------
Production WSGI config for Render and other container hosts.
Run Alembic once in the master process before workers fork.
"""

import os

from backend.db_migrate import run_migrations

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "1"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 180  # Increased for startup seed/warmup operations
graceful_timeout = 30
keepalive = 5
capture_output = True
loglevel = "info"


def on_starting(_server) -> None:
    """Master-only hook: migrate before any worker imports the app DB."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Gunicorn master starting, running migrations...")
    try:
        run_migrations()
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.exception("Migration failed: %s", e)
        raise
