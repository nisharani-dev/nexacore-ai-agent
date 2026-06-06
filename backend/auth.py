"""
auth.py
-------
Optional production auth/session helpers with API-key and OIDC JWT support.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from fastapi import HTTPException, Request

from backend.db import AppDatabase


@dataclass
class AuthContext:
    subject: str
    auth_type: str
    session_id: str | None = None
    email: str | None = None
    groups: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)


PUBLIC_PATHS = {
    "/health",
    "/ready",
    "/metrics",
    "/auth/oidc/info",
    "/auth/oidc/login",
    "/docs",
    "/redoc",
    "/openapi.json",
}


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "false").strip().lower() == "true"


def app_api_key() -> str:
    return os.getenv("APP_API_KEY", "").strip()


def _verify_oidc_token(token: str):
    from backend.auth_oidc import OIDCFactory

    provider = OIDCFactory.create_from_env()
    if not provider:
        return None
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, provider.verify_token(token)).result()
        return asyncio.run(provider.verify_token(token))
    except Exception:
        return None


def authenticate_request(request: Request) -> AuthContext:
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/auth/oidc/"):
        return AuthContext(subject="public", auth_type="public", session_id=None)

    auth_header = request.headers.get("authorization", "").strip()
    api_key_header = request.headers.get("x-api-key", "").strip()
    session_id = request.headers.get("x-session-id", "").strip() or None

    expected_api_key = app_api_key()
    if expected_api_key:
        if api_key_header == expected_api_key:
            return AuthContext(
                subject="api-key-client",
                auth_type="api_key",
                session_id=session_id,
                roles=["admin"],
            )
        if auth_header.startswith("Bearer "):
            bearer = auth_header.removeprefix("Bearer ").strip()
            if bearer == expected_api_key:
                return AuthContext(
                    subject="bearer-api-key-client",
                    auth_type="bearer_api_key",
                    session_id=session_id,
                    roles=["admin"],
                )
            user_info = _verify_oidc_token(bearer)
            if user_info:
                from backend.rbac import get_rbac

                subject = user_info.email or user_info.sub
                rbac = get_rbac()
                rbac.sync_oidc_roles(
                    subject,
                    groups=user_info.groups or [],
                    roles=user_info.roles or [],
                )
                return AuthContext(
                    subject=subject,
                    auth_type="oidc",
                    session_id=session_id,
                    email=user_info.email,
                    groups=list(user_info.groups or []),
                    roles=list(user_info.roles or []),
                )

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
    auth_subject: str = "anonymous",
) -> dict:
    from uuid import uuid4

    session_id = str(uuid4())
    AppDatabase.get().upsert_session(
        session_id=session_id,
        user_name=user_name,
        team_name=team_name,
        role_title=role_title,
        employment_type=employment_type,
        auth_subject=auth_subject,
        metadata=metadata or {},
    )
    return {"session_id": session_id}
