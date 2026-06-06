"""Tests for RBAC role mapping and permissions."""

from backend.rbac import Permission, reset_rbac


def test_default_user_permissions():
    rbac = reset_rbac()
    assert rbac.has_permission("alice", Permission.VIEW_TICKET.value)
    assert not rbac.has_permission("alice", Permission.SYSTEM_ADMIN.value)


def test_sync_oidc_roles_from_groups():
    rbac = reset_rbac()
    roles = rbac.sync_oidc_roles("admin@company.com", groups=["ramp-admins"], roles=[])
    assert "admin" in roles
    assert rbac.has_permission("admin@company.com", Permission.SYSTEM_ADMIN.value)


def test_sync_oidc_roles_from_oidc_role_mapping():
    rbac = reset_rbac()
    roles = rbac.sync_oidc_roles("manager@company.com", groups=[], roles=["manager"])
    assert "manager" in roles
    assert rbac.has_permission("manager@company.com", Permission.VIEW_AUDIT_LOG.value)
