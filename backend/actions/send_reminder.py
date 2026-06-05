"""
send_reminder.py  —  Person 4 (Ingestion + Actions)
-----------------------------------------------------
LangChain tool: schedules and sends a reminder for the new employee.

Implementation:
    Sends reminder via email (SMTP). Falls back to local mock if not configured.
    Also persists to local database for audit trail and frontend display.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import AppDatabase
from backend.integrations.email import EmailClient


def send_reminder(recipient: str, message: str, due_in_hours: int = 24) -> str:
    """
    Schedules and sends a reminder email, persists to local database.
    """
    scheduled_for = (datetime.now(timezone.utc) + timedelta(hours=due_in_hours)).isoformat()

    # Persist to database first (audit trail)
    AppDatabase.get().create_reminder(
        recipient=recipient,
        message=message,
        due_in_hours=due_in_hours,
        scheduled_for=scheduled_for,
    )

    # Send email
    email_client = EmailClient()
    try:
        email_result = email_client.send_reminder(
            recipient=recipient,
            subject=f"Onboarding Reminder ({due_in_hours}h from now)",
            message=message,
        )
        email_status = "sent" if email_result.get("sent") else "queued"
    except Exception as e:
        email_status = "error"
        print(f"[WARNING] Failed to send reminder email: {e}")

    confirmation = (
        f"Reminder scheduled and {email_status}.\n"
        f"For: {recipient}\n"
        f"Due in: {due_in_hours} hours\n"
        f"Message: {message}"
    )
    print(f"[ACTION: send_reminder] {recipient} in {due_in_hours}h — {message} ({email_status})")
    return confirmation

