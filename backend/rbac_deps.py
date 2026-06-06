"""
rbac_deps.py
------------
FastAPI dependencies for RBAC permission checks.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from backend.rbac import Permission, get_rbac
from backend.settings import auth_required, rbac_enforced


def _subject(request: Request) -> str:
    auth = getattr(request.state, "auth", None)
    if auth and getattr(auth, "subject", None):
        return auth.subject
    return "anonymous"


def require_permission(permission: Permission):
    async def _checker(request: Request) -> None:
        if not rbac_enforced():
            return
        subject = _subject(request)
        if subject in {"anonymous", "public"} and auth_required():
            raise HTTPException(status_code=401, detail="Authentication required")
        if not get_rbac().has_permission(subject, permission.value):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}",
            )

    return _checker
