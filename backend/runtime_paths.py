"""
runtime_paths.py
----------------
Centralized runtime file locations so local dev and cloud deployments can use
the same code with different writable volumes.
"""

from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    configured = os.getenv("DATA_DIR", "").strip()
    path = Path(configured) if configured else ROOT_DIR / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hindsight_store_path() -> Path:
    configured = os.getenv("HINDSIGHT_STORE_PATH", "").strip()
    if configured:
        path = Path(configured)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return data_dir() / "hindsight_store.json"


def reminder_store_path() -> Path:
    configured = os.getenv("REMINDER_STORE_PATH", "").strip()
    if configured:
        path = Path(configured)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return data_dir() / "reminder_log.json"


def ticket_store_path() -> Path:
    configured = os.getenv("TICKET_STORE_PATH", "").strip()
    if configured:
        path = Path(configured)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return data_dir() / "ticket_log.json"


def database_path() -> Path:
    configured = os.getenv("APP_DB_PATH", "").strip()
    if configured:
        path = Path(configured)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    return data_dir() / "app.db"
