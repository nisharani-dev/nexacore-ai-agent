"""
tools.py
─────────
Tool registry for the Ramp agent.

Person 1 (you) owns this file.
Person 4 implements the underlying action functions in backend/actions/*.
This file wraps those functions as LangChain tools so the LLM can call them.

Adding a new tool:
  1. Person 4 adds a function in backend/actions/
  2. You add a @tool-decorated wrapper here
  3. Add it to TOOL_REGISTRY at the bottom
"""

from langchain_core.tools import tool

# ── Action layer imports ───────────────────────────────────────────────────
# Lazy try/except keeps the agent loadable if an action module is missing.

try:
    from backend.actions.raise_ticket import raise_ticket as _raise_ticket_action
except ImportError:
    _raise_ticket_action = None  # type: ignore

try:
    from backend.actions.send_reminder import send_reminder as _send_reminder_action
except ImportError:
    _send_reminder_action = None  # type: ignore

try:
    from backend.actions.log_blocker import log_blocker as _log_blocker_action
except ImportError:
    _log_blocker_action = None  # type: ignore


# ─────────────────────────────────────────────
# Tool definitions
# ─────────────────────────────────────────────

@tool
def raise_ticket(
    title: str,
    description: str,
    assignee_team: str = "IT Helpdesk",
    priority: str = "medium",
) -> str:
    """
    Raises a support ticket for the new employee.
    Use this when the employee needs access to a system, tool, or resource
    that requires IT or team intervention.

    Args:
        title: Short summary of what is needed.
        description: Full details of the request.
        assignee_team: Which team should handle it (default: IT Helpdesk).
        priority: low | medium | high (default: medium).

    Returns:
        Confirmation string with ticket ID.
    """
    if _raise_ticket_action:
        return _raise_ticket_action(
            title=title,
            description=description,
            assignee_team=assignee_team,
            priority=priority,
        )
    # Stub response until Person 4 delivers the implementation
    return f"[STUB] Ticket raised: '{title}' → assigned to {assignee_team} (priority: {priority})"


@tool
def send_reminder(
    recipient: str,
    message: str,
    due_in_hours: int = 24,
) -> str:
    """
    Sends a reminder to a person or team about a pending onboarding task.
    Use this when an action is time-sensitive or has been waiting too long.

    Args:
        recipient: Name or email of who should receive the reminder.
        message: The reminder content.
        due_in_hours: Hours until the task is overdue (default: 24).

    Returns:
        Confirmation string.
    """
    if _send_reminder_action:
        return _send_reminder_action(
            recipient=recipient,
            message=message,
            due_in_hours=due_in_hours,
        )
    return f"[STUB] Reminder sent to {recipient}: '{message}' (due in {due_in_hours}h)"


@tool
def log_blocker(
    employee_name: str,
    blocker_description: str,
    severity: str = "medium",
) -> str:
    """
    Logs an onboarding blocker to the tracking system.
    Use this when the employee reports they are stuck and cannot proceed
    without help — e.g. missing access, unclear process, broken tool.

    Args:
        employee_name: Name of the affected employee.
        blocker_description: What is blocking them.
        severity: low | medium | high | critical (default: medium).

    Returns:
        Confirmation string with blocker log ID.
    """
    if _log_blocker_action:
        return _log_blocker_action(
            employee_name=employee_name,
            blocker_description=blocker_description,
            severity=severity,
        )
    return (
        f"[STUB] Blocker logged for {employee_name}: "
        f"'{blocker_description}' (severity: {severity})"
    )


# ─────────────────────────────────────────────
# Tool registry — the agent imports this list
# ─────────────────────────────────────────────

TOOL_REGISTRY: list = [
    raise_ticket,
    send_reminder,
    log_blocker,
]
