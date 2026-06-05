"""
auth.py
-------
Optional production auth/session helpers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import HTTPException, Request

from backend.db import AppDatabase


@dataclass
class AuthContext:
    subject: str
    auth_type: str
    session_id: str | None = None


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "false").strip().lower() == "true"


def app_api_key() -> str:
    return os.getenv("APP_API_KEY", "").strip()


def authenticate_request(request: Request) -> AuthContext:
    if request.url.path in {"/health", "/ready", "/metrics"}:
        return AuthContext(subject="public", auth_type="public", session_id=None)

    auth_header = request.headers.get("authorization", "").strip()
    api_key_header = request.headers.get("x-api-key", "").strip()
    session_id = request.headers.get("x-session-id", "").strip() or None

    expected_api_key = app_api_key()
    if expected_api_key:
        if api_key_header == expected_api_key:
            return AuthContext(subject="api-key-client", auth_type="api_key", session_id=session_id)
        if auth_header.startswith("Bearer ") and auth_header.removeprefix("Bearer ").strip() == expected_api_key:
            return AuthContext(subject="bearer-api-key-client", auth_type="bearer_api_key", session_id=session_id)

    if auth_required():
        raise HTTPException(status_code=401, detail="Authentication required")

    return AuthContext(subject="anonymous", auth_type="anonymous", session_id=session_id)


def create_session(
    *,
    user_name: str,
    team_name: str,
    role_title: str,
    employment_type: str,
    metadata: dict | None = None,
) -> dict:
    from uuid import uuid4

    session_id = str(uuid4())
    AppDatabase.get().upsert_session(
        session_id=session_id,
        user_name=user_name,
        team_name=team_name,
        role_title=role_title,
        employment_type=employment_type,
        auth_subject="anonymous",
        metadata=metadata or {},
    )
    return {"session_id": session_id}
