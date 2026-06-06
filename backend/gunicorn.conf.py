"""
gunicorn.conf.py
----------------
Run Alembic once in the master process before workers fork.
"""

from backend.db_migrate import run_migrations


def on_starting(_server) -> None:
    """Master-only hook: migrate before any worker imports the app DB."""
    run_migrations()
