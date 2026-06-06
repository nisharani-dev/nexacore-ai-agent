"""
rbac.py
────────
Role-Based Access Control (RBAC) for NexaCore.

Supports:
- Role definitions (admin, manager, user, etc)
- Permission checks
- Group-based access
- Resource-level permissions

Usage:
    from backend.rbac import RBAC, Role
    
    rbac = RBAC()
    
    # Check if user has role
    if rbac.has_role(user_id, "admin"):
        # Grant access
    
    # Check permission
    if rbac.has_permission(user_id, "create_ticket"):
        # Grant access
    
    # Get user roles
    roles = rbac.get_roles(user_id)
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Set

import yaml
from pydantic import BaseModel, ConfigDict, Field

from backend.logging_config import get_logger

logger = get_logger(__name__)


class Permission(str, Enum):
    """Standard permissions in NexaCore."""
    
    # Ticket permissions
    CREATE_TICKET = "create_ticket"
    EDIT_TICKET = "edit_ticket"
    DELETE_TICKET = "delete_ticket"
    VIEW_TICKET = "view_ticket"
    
    # Reminder permissions
    CREATE_REMINDER = "create_reminder"
    EDIT_REMINDER = "edit_reminder"
    DELETE_REMINDER = "delete_reminder"
    VIEW_REMINDER = "view_reminder"
    
    # User management
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    VIEW_AUDIT_LOG = "view_audit_log"
    
    # System
    SYSTEM_ADMIN = "system_admin"
    VIEW_METRICS = "view_metrics"


class Role(BaseModel):
    """Role definition."""

    model_config = ConfigDict(extra="allow")

    name: str
    description: Optional[str] = None
    permissions: Set[str] = set()


class RoleConfig(BaseModel):
    """Configuration for roles and permissions."""

    model_config = ConfigDict(extra="allow")

    default_role: str = "user"
    roles: dict[str, Role] = {}
    group_role_mapping: dict[str, str] = Field(default_factory=dict)
    oidc_role_mapping: dict[str, str] = Field(default_factory=dict)


class RBAC:
    """Role-Based Access Control manager."""
    
    # Default role definitions
    DEFAULT_ROLES = {
        "admin": Role(
            name="admin",
            description="System administrator with full access",
            permissions={
                "system_admin",
                "manage_users",
                "manage_roles",
                "view_audit_log",
                "view_metrics",
                "create_ticket",
                "edit_ticket",
                "delete_ticket",
                "view_ticket",
                "create_reminder",
                "edit_reminder",
                "delete_reminder",
                "view_reminder",
            }
        ),
        "manager": Role(
            name="manager",
            description="Team manager with moderator access",
            permissions={
                "create_ticket",
                "edit_ticket",
                "delete_ticket",
                "view_ticket",
                "create_reminder",
                "edit_reminder",
                "delete_reminder",
                "view_reminder",
                "view_audit_log",
            }
        ),
        "user": Role(
            name="user",
            description="Standard user access",
            permissions={
                "create_ticket",
                "view_ticket",
                "create_reminder",
                "view_reminder",
            }
        ),
        "guest": Role(
            name="guest",
            description="Limited guest access",
            permissions={
                "view_ticket",
                "view_reminder",
            }
        ),
    }
    
    def __init__(self, config: Optional[RoleConfig] = None):
        """
        Initialize RBAC.
        
        Args:
            config: Role configuration (loaded from file or defaults)
        """
        if config:
            self.config = config
        else:
            # Load from environment or use defaults
            self.config = self._load_config()
        
        self.user_roles: dict[str, Set[str]] = {}  # user_id -> set of role names
        self.user_groups: dict[str, Set[str]] = {}  # user_id -> set of group names
        
        logger.info(
            "RBAC initialized",
            extra={
                "roles": list(self.config.roles.keys()),
                "default_role": self.config.default_role,
            }
        )
    
    def _load_config(self) -> RoleConfig:
        """Load role configuration from file or environment."""
        config_file = os.getenv("RBAC_CONFIG_FILE")
        if not config_file:
            default_path = Path(__file__).resolve().parents[1] / "config" / "rbac.yaml"
            if default_path.exists():
                config_file = str(default_path)

        if config_file and os.path.exists(config_file):
            logger.info("Loading RBAC config", extra={"file": config_file})
            with open(config_file) as handle:
                config_data = yaml.safe_load(handle) or {}
            roles_data = config_data.get("roles", {})
            roles = {
                name: Role(
                    name=data.get("name", name),
                    description=data.get("description"),
                    permissions=set(data.get("permissions", [])),
                )
                for name, data in roles_data.items()
            }
            if not roles:
                roles = self.DEFAULT_ROLES
            return RoleConfig(
                default_role=config_data.get("default_role", "user"),
                roles=roles,
                group_role_mapping=config_data.get("group_role_mapping", {}),
                oidc_role_mapping=config_data.get("oidc_role_mapping", {}),
            )

        return RoleConfig(
            default_role="user",
            roles=self.DEFAULT_ROLES,
        )

    def sync_oidc_roles(
        self,
        user_id: str,
        *,
        groups: list[str] | None = None,
        roles: list[str] | None = None,
    ) -> Set[str]:
        """Map OIDC groups/roles to RBAC roles for a user."""
        assigned: Set[str] = set()
        for group in groups or []:
            mapped = self.config.group_role_mapping.get(group)
            if mapped:
                assigned.add(mapped)
        for role in roles or []:
            mapped = self.config.oidc_role_mapping.get(role)
            if mapped:
                assigned.add(mapped)
            elif role in self.config.roles:
                assigned.add(role)
        if not assigned:
            assigned.add(self.config.default_role)
        self.user_roles[user_id] = assigned
        return assigned
    
    def get_roles(self, user_id: str) -> Set[str]:
        """Get roles assigned to user."""
        return self.user_roles.get(user_id, {self.config.default_role})
    
    def get_groups(self, user_id: str) -> Set[str]:
        """Get groups assigned to user."""
        return self.user_groups.get(user_id, set())
    
    def set_roles(self, user_id: str, roles: Set[str]) -> None:
        """Set roles for user."""
        self.user_roles[user_id] = roles
        logger.info(
            "User roles updated",
            extra={
                "user_id": user_id,
                "roles": list(roles),
            }
        )
    
    def add_role(self, user_id: str, role: str) -> None:
        """Add role to user."""
        if role not in self.config.roles:
            logger.warning(
                "Role not defined",
                extra={
                    "role": role,
                    "user_id": user_id,
                }
            )
            return
        
        roles = self.get_roles(user_id)
        roles.add(role)
        self.user_roles[user_id] = roles
    
    def remove_role(self, user_id: str, role: str) -> None:
        """Remove role from user."""
        roles = self.get_roles(user_id)
        roles.discard(role)
        if roles:
            self.user_roles[user_id] = roles
        else:
            self.user_roles.pop(user_id, None)
    
    def has_role(self, user_id: str, role: str) -> bool:
        """Check if user has role."""
        return role in self.get_roles(user_id)
    
    def has_any_role(self, user_id: str, roles: Set[str]) -> bool:
        """Check if user has any of the roles."""
        return bool(self.get_roles(user_id) & roles)
    
    def has_all_roles(self, user_id: str, roles: Set[str]) -> bool:
        """Check if user has all of the roles."""
        user_roles = self.get_roles(user_id)
        return roles.issubset(user_roles)
    
    def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has permission (via their roles)."""
        user_roles = self.get_roles(user_id)
        
        for role_name in user_roles:
            role = self.config.roles.get(role_name)
            if role and permission in role.permissions:
                return True
        
        return False
    
    def has_any_permission(self, user_id: str, permissions: Set[str]) -> bool:
        """Check if user has any of the permissions."""
        for permission in permissions:
            if self.has_permission(user_id, permission):
                return True
        return False
    
    def has_all_permissions(self, user_id: str, permissions: Set[str]) -> bool:
        """Check if user has all of the permissions."""
        for permission in permissions:
            if not self.has_permission(user_id, permission):
                return False
        return True
    
    def get_permissions(self, user_id: str) -> Set[str]:
        """Get all permissions for user (via their roles)."""
        permissions: Set[str] = set()
        
        for role_name in self.get_roles(user_id):
            role = self.config.roles.get(role_name)
            if role:
                permissions.update(role.permissions)
        
        return permissions
    
    def require_permission(
        self,
        user_id: str,
        permission: str,
    ) -> None:
        """
        Check permission and raise exception if not granted.
        
        Raises:
            PermissionError: If user lacks permission
        """
        if not self.has_permission(user_id, permission):
            logger.warning(
                "Permission denied",
                extra={
                    "user_id": user_id,
                    "permission": permission,
                }
            )
            raise PermissionError(f"Permission denied: {permission}")
    
    def require_role(
        self,
        user_id: str,
        role: str,
    ) -> None:
        """
        Check role and raise exception if not assigned.
        
        Raises:
            PermissionError: If user lacks role
        """
        if not self.has_role(user_id, role):
            logger.warning(
                "Role required",
                extra={
                    "user_id": user_id,
                    "role": role,
                }
            )
            raise PermissionError(f"Role required: {role}")
    
    def require_any_role(
        self,
        user_id: str,
        roles: Set[str],
    ) -> None:
        """Check that user has at least one of the roles."""
        if not self.has_any_role(user_id, roles):
            raise PermissionError(f"One of these roles required: {roles}")
    
    def require_all_roles(
        self,
        user_id: str,
        roles: Set[str],
    ) -> None:
        """Check that user has all of the roles."""
        if not self.has_all_roles(user_id, roles):
            raise PermissionError(f"All of these roles required: {roles}")
    
    def list_roles(self) -> list[Role]:
        """Get all available roles."""
        return list(self.config.roles.values())
    
    def get_role_details(self, role_name: str) -> Optional[Role]:
        """Get details for a specific role."""
        return self.config.roles.get(role_name)
    
    def to_dict(self) -> dict[str, Any]:
        """Export current RBAC state."""
        return {
            "config": self.config.model_dump(),
            "user_roles": {k: list(v) for k, v in self.user_roles.items()},
            "user_groups": {k: list(v) for k, v in self.user_groups.items()},
        }


# Global RBAC instance
_rbac_instance: Optional[RBAC] = None


def get_rbac() -> RBAC:
    """Get global RBAC instance."""
    global _rbac_instance
    if _rbac_instance is None:
        _rbac_instance = RBAC()
    return _rbac_instance


def reset_rbac(config: Optional[RoleConfig] = None) -> RBAC:
    """Reset global RBAC instance (mainly for testing)."""
    global _rbac_instance
    _rbac_instance = RBAC(config)
    return _rbac_instance
