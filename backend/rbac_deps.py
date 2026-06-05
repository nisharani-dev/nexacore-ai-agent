"""
rbac_deps.py
------------
FastAPI dependencies for RBAC permission checks.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from backend.rbac import Permission, RBAC
from backend.settings import app_env

_rbac = RBAC()


def _subject(request: Request) -> str:
    auth = getattr(request.state, "auth", None)
    if auth and getattr(auth, "subject", None):
        return auth.subject
    return "anonymous"


def require_permission(permission: Permission):
    async def _checker(request: Request) -> None:
        if app_env() == "development":
            return
        subject = _subject(request)
        if not _rbac.has_permission(subject, permission.value):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}",
            )

    return _checker
