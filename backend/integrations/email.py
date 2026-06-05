"""
integrations/email.py
---------------------
Email integration for sending reminders and notifications.
Supports both mock (testing) and real SMTP modes.

Usage:
    from backend.integrations.email import EmailClient
    client = EmailClient()
    result = client.send_reminder(
        recipient="employee@company.com",
        message="Your AWS access request is ready",
        days_to_action=3
    )
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Any

from backend.settings import integrations_mode

logger = logging.getLogger(__name__)


class EmailClient:
    """Email client for sending reminders. Supports mock and real SMTP modes."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
        mock_mode: bool | None = None,
    ):
        """
        Initialize email client.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP port (usually 587 for TLS, 465 for SSL)
            smtp_user: SMTP username
            smtp_password: SMTP password
            from_email: From address for emails
            mock_mode: Force mock mode. If None, auto-detect from env vars.
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self.from_email = from_email or os.getenv("REMINDER_FROM_EMAIL", "onboarding@company.com")

        # Auto-detect mock mode: if no smtp credentials, use mock
        if mock_mode is None:
            self.mock_mode = integrations_mode() == "demo" or not bool(self.smtp_user and self.smtp_password)
        else:
            self.mock_mode = mock_mode

        if self.mock_mode:
            logger.info("EmailClient initialized in MOCK mode (no SMTP credentials)")
        else:
            logger.info(f"EmailClient initialized for {self.smtp_host}:{self.smtp_port}")

    def send_reminder(
        self,
        *,
        recipient: str,
        subject: str = "Onboarding Reminder",
        message: str,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a reminder email.

        Args:
            recipient: Email address of recipient
            subject: Email subject
            message: Plain text message body
            html_body: Optional HTML version of message

        Returns:
            Dict with send status and message_id.
        """
        if self.mock_mode:
            return self._send_email_mock(
                recipient=recipient,
                subject=subject,
                message=message,
                html_body=html_body,
            )
        else:
            return self._send_email_real(
                recipient=recipient,
                subject=subject,
                message=message,
                html_body=html_body,
            )

    def send_onboarding_checklist(
        self,
        *,
        recipient: str,
        name: str,
        team: str,
        role: str,
        checklist_items: list[str],
    ) -> dict[str, Any]:
        """Send personalized onboarding checklist email."""
        subject = f"Welcome to {team}, {name}!"
        message = f"""
Hi {name},

Welcome to the {team} team! Here's your onboarding checklist:

""" + "\n".join([f"- {item}" for item in checklist_items]) + f"""

If you have any questions, please reach out to your manager or the People team.

Best,
Onboarding Team
"""

        html_body = f"""
<html>
<body>
<p>Hi {name},</p>
<p>Welcome to the <strong>{team}</strong> team! Here's your onboarding checklist:</p>
<ul>
""" + "\n".join([f"<li>{item}</li>" for item in checklist_items]) + """
</ul>
<p>If you have any questions, please reach out to your manager or the People team.</p>
<p>Best,<br>Onboarding Team</p>
</body>
</html>
"""

        return self.send_reminder(
            recipient=recipient,
            subject=subject,
            message=message,
            html_body=html_body,
        )

    def _send_email_mock(
        self,
        *,
        recipient: str,
        subject: str,
        message: str,
        html_body: str | None,
    ) -> dict[str, Any]:
        """Mock email send (no actual SMTP)."""
        import uuid

        message_id = str(uuid.uuid4())
        logger.info(f"[MOCK] Would send email to {recipient}: {subject}")
        logger.debug(f"[MOCK] Message: {message[:100]}...")

        return {
            "message_id": message_id,
            "recipient": recipient,
            "subject": subject,
            "sent": True,
            "backend": "mock",
        }

    def _send_email_real(
        self,
        *,
        recipient: str,
        subject: str,
        message: str,
        html_body: str | None,
    ) -> dict[str, Any]:
        """Send email using real SMTP."""
        try:
            # Create MIME message
            msg = MIMEText(message, "plain" if not html_body else "html")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = recipient

            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()  # Upgrade to TLS
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipient}: {subject}")
            return {
                "message_id": msg["Message-ID"],
                "recipient": recipient,
                "subject": subject,
                "sent": True,
                "backend": "smtp",
            }
        except smtplib.SMTPException as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise

    def validate_recipient(self, email: str) -> bool:
        """Basic email validation."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None
