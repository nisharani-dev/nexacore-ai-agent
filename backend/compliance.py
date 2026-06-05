"""
compliance.py
──────────────
GDPR and data privacy compliance handlers.

Supports:
- User data export (GDPR Article 15)
- User data deletion (GDPR Article 17 - Right to be Forgotten)
- Consent management
- Data retention policies
- Audit logging

Usage:
    from backend.compliance import ComplianceManager
    
    compliance = ComplianceManager()
    
    # Export user data
    export = compliance.export_user_data(user_id)
    
    # Delete user data
    compliance.delete_user_data(user_id)
    
    # Check consent
    if compliance.has_consent(user_id, "analytics"):
        track_event(user_id)
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

from backend.db import AppDatabase
from backend.logging_config import get_logger

logger = get_logger(__name__)


class ConsentRecord(BaseModel):
    """Record of user consent."""
    
    user_id: str
    category: str  # analytics, marketing, cookies, etc
    granted: bool
    timestamp: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class DataExport(BaseModel):
    """User data export package."""
    
    user_id: str
    export_date: str
    sessions: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []
    reminders: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    consent_records: list[dict[str, Any]] = []
    personal_data: dict[str, Any] = {}


class ComplianceManager:
    """GDPR and privacy compliance manager."""
    
    def __init__(self, db: Optional[AppDatabase] = None):
        """Initialize compliance manager."""
        self.db = db or AppDatabase.get()
        self.consent_store: dict[str, dict[str, ConsentRecord]] = {}  # user_id -> category -> record
        self.retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
        
        logger.info(
            "Compliance manager initialized",
            extra={"retention_days": self.retention_days}
        )
    
    def set_consent(
        self,
        user_id: str,
        category: str,
        granted: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ConsentRecord:
        """
        Record user consent decision.
        
        Args:
            user_id: User identifier
            category: Consent category (analytics, marketing, cookies)
            granted: Whether consent was granted
            ip_address: Client IP for audit trail
            user_agent: Client User-Agent for audit trail
            
        Returns:
            ConsentRecord
        """
        record = ConsentRecord(
            user_id=user_id,
            category=category,
            granted=granted,
            timestamp=datetime.now(timezone.utc).isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        if user_id not in self.consent_store:
            self.consent_store[user_id] = {}
        
        self.consent_store[user_id][category] = record
        
        logger.info(
            "Consent recorded",
            extra={
                "user_id": user_id,
                "category": category,
                "granted": granted,
            }
        )
        
        return record
    
    def has_consent(self, user_id: str, category: str) -> bool:
        """Check if user has granted consent for a category."""
        if user_id not in self.consent_store:
            return False
        
        record = self.consent_store[user_id].get(category)
        return record.granted if record else False
    
    def get_consent(self, user_id: str, category: str) -> Optional[ConsentRecord]:
        """Get consent record for user and category."""
        if user_id not in self.consent_store:
            return None
        
        return self.consent_store[user_id].get(category)
    
    def get_all_consents(self, user_id: str) -> dict[str, bool]:
        """Get all consent decisions for a user."""
        if user_id not in self.consent_store:
            return {}
        
        return {
            category: record.granted
            for category, record in self.consent_store[user_id].items()
        }
    
    def export_user_data(self, user_id: str) -> DataExport:
        """
        Export all user data (GDPR Article 15 - Right of Access).
        
        Args:
            user_id: User to export data for
            
        Returns:
            DataExport with all user data
        """
        export = DataExport(
            user_id=user_id,
            export_date=datetime.now(timezone.utc).isoformat(),
        )
        
        # Export sessions
        with self.db.connect() as connection:
            sessions = connection.execute(
                "SELECT * FROM sessions WHERE user_name = ? OR id = ?",
                (user_id, user_id),
            ).fetchall()
            export.sessions = [dict(row) for row in sessions]
            
            # Export tickets
            tickets = connection.execute(
                "SELECT * FROM tickets WHERE assignee_team IN (SELECT team_name FROM sessions WHERE user_name = ?)",
                (user_id,),
            ).fetchall()
            export.tickets = [dict(row) for row in tickets]
            
            # Export reminders
            reminders = connection.execute(
                "SELECT * FROM reminders WHERE recipient = ?",
                (user_id,),
            ).fetchall()
            export.reminders = [dict(row) for row in reminders]
            
            # Export audit events
            audit_events = connection.execute(
                "SELECT * FROM audit_events WHERE actor = ? OR session_id IN (SELECT id FROM sessions WHERE user_name = ?)",
                (user_id, user_id),
            ).fetchall()
            export.audit_events = [dict(row) for row in audit_events]
        
        # Export consent records
        export.consent_records = [
            record.dict()
            for record in (self.consent_store.get(user_id, {}).values())
        ]
        
        # Export personal data
        export.personal_data = {
            "user_id": user_id,
            "export_date": export.export_date,
            "all_consents": self.get_all_consents(user_id),
        }
        
        logger.info(
            "User data exported",
            extra={
                "user_id": user_id,
                "sessions": len(export.sessions),
                "tickets": len(export.tickets),
                "reminders": len(export.reminders),
                "audit_events": len(export.audit_events),
            }
        )
        
        return export
    
    def export_data_as_json(self, user_id: str) -> str:
        """Export user data as JSON string."""
        export = self.export_user_data(user_id)
        return json.dumps(export.dict(), indent=2, default=str)
    
    def export_data_as_file(self, user_id: str, directory: Optional[Path] = None) -> Path:
        """
        Export user data as JSON file.
        
        Returns:
            Path to exported file
        """
        if directory is None:
            directory = Path("./exports")
        
        directory.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = directory / f"{user_id}_export_{timestamp}.json"
        
        with open(filename, "w") as f:
            f.write(self.export_data_as_json(user_id))
        
        logger.info(
            "User data exported to file",
            extra={
                "user_id": user_id,
                "file": str(filename),
            }
        )
        
        return filename
    
    def delete_user_data(
        self,
        user_id: str,
        export_before_delete: bool = True,
    ) -> bool:
        """
        Delete all user data (GDPR Article 17 - Right to be Forgotten).
        
        Args:
            user_id: User to delete
            export_before_delete: Export data before deletion
            
        Returns:
            True if deletion successful
        """
        try:
            # Export data before deletion if requested
            if export_before_delete:
                self.export_data_as_file(user_id)
            
            with self.db.connect() as connection:
                # Delete reminders
                connection.execute(
                    "DELETE FROM reminders WHERE recipient = ?",
                    (user_id,),
                )
                
                # Delete/anonymize sessions
                connection.execute(
                    "UPDATE sessions SET user_name = NULL WHERE user_name = ?",
                    (user_id,),
                )
                
                # Delete/anonymize audit events
                connection.execute(
                    "UPDATE audit_events SET actor = NULL WHERE actor = ?",
                    (user_id,),
                )
            
            # Clear consent records
            self.consent_store.pop(user_id, None)
            
            logger.info(
                "User data deleted",
                extra={
                    "user_id": user_id,
                    "exported_first": export_before_delete,
                }
            )
            
            return True
        
        except Exception as e:
            logger.error(
                "Failed to delete user data",
                extra={
                    "user_id": user_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False
    
    def cleanup_old_audit_logs(self, days: Optional[int] = None) -> int:
        """
        Delete audit logs older than retention period.
        
        Args:
            days: Days to retain (uses default if not specified)
            
        Returns:
            Number of records deleted
        """
        if days is None:
            days = self.retention_days
        
        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(days=days)
        ).isoformat()
        
        try:
            with self.db.connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM audit_events WHERE created_at < ?",
                    (cutoff_date,),
                )
                deleted = cursor.rowcount
            
            logger.info(
                "Old audit logs cleaned up",
                extra={
                    "days": days,
                    "deleted": deleted,
                }
            )
            
            return deleted
        
        except Exception as e:
            logger.error(
                "Failed to cleanup audit logs",
                extra={
                    "error": str(e),
                },
                exc_info=True,
            )
            return 0
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """
        Delete sessions older than specified hours.
        
        Args:
            hours: Hours to retain
            
        Returns:
            Number of sessions deleted
        """
        cutoff_date = (
            datetime.now(timezone.utc) - timedelta(hours=hours)
        ).isoformat()
        
        try:
            with self.db.connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM sessions WHERE last_seen_at < ?",
                    (cutoff_date,),
                )
                deleted = cursor.rowcount
            
            logger.info(
                "Old sessions cleaned up",
                extra={
                    "hours": hours,
                    "deleted": deleted,
                }
            )
            
            return deleted
        
        except Exception as e:
            logger.error(
                "Failed to cleanup sessions",
                extra={
                    "error": str(e),
                },
                exc_info=True,
            )
            return 0
    
    def get_compliance_report(self) -> dict[str, Any]:
        """Get compliance and data protection report."""
        with self.db.connect() as connection:
            total_sessions = connection.execute(
                "SELECT COUNT(*) FROM sessions"
            ).fetchone()[0]
            total_audit_logs = connection.execute(
                "SELECT COUNT(*) FROM audit_events"
            ).fetchone()[0]
            total_reminders = connection.execute(
                "SELECT COUNT(*) FROM reminders"
            ).fetchone()[0]
            total_tickets = connection.execute(
                "SELECT COUNT(*) FROM tickets"
            ).fetchone()[0]
        
        return {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "data_retention_days": self.retention_days,
            "statistics": {
                "total_sessions": total_sessions,
                "total_audit_logs": total_audit_logs,
                "total_reminders": total_reminders,
                "total_tickets": total_tickets,
            },
            "consent_categories": list(set(
                cat for user_consents in self.consent_store.values()
                for cat in user_consents.keys()
            )),
        }


# Global compliance manager instance
_compliance_manager: Optional[ComplianceManager] = None


def get_compliance() -> ComplianceManager:
    """Get or create global compliance manager."""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager()
    return _compliance_manager
