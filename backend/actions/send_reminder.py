"""
send_reminder.py  —  Person 4 (Ingestion + Actions)
-----------------------------------------------------
LangChain tool: schedules a Day-N reminder for the new employee.

Why this matters for the demo:
    The agent knows from memory that AWS takes 3 days. So instead of
    just telling the user "request it Day 1", it can also SET A REMINDER:
    "I've scheduled a Day 3 reminder to follow up on your AWS ticket."
    That's a concrete action — it shows the agent doesn't just advise,
    it acts.

Mock behaviour:
    In production: integrate with Google Calendar API or Slack reminders.
    For the hackathon: store reminders in a local JSON log file and
    print them. Person 5's frontend can read this file to display
    "Upcoming reminders" in the UI sidebar — great demo moment.
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from langchain.tools import tool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Reminder log file — Person 5 can read this for the UI
REMINDER_LOG = Path(__file__).resolve().parents[2] / "reminder_log.json"


def _load_reminders() -> list:
    if REMINDER_LOG.exists():
        with open(REMINDER_LOG) as f:
            return json.load(f)
    return []


def _save_reminders(reminders: list):
    with open(REMINDER_LOG, "w") as f:
        json.dump(reminders, f, indent=2)


@tool
def send_reminder(day: int, message: str, employee_name: str = "New Employee") -> str:
    """
    Schedules a follow-up reminder for the employee on a specific onboarding day.

    Use this tool when something needs to be checked or followed up on a
    future day. Common cases:
    - Day 3: follow up on AWS access ticket (it takes 3 days)
    - Day 2: check if Terraform Cloud request has been actioned
    - Day 5: verify Snowflake write access was provisioned
    - Day 14: confirm PagerDuty on-call rotation has been added

    Inputs:
        day: which onboarding day to send the reminder (e.g. 3)
        message: what the reminder should say
        employee_name: the name of the new employee (optional)

    Returns: confirmation string that the reminder was scheduled.
    """
    reminder = {
        "employee": employee_name,
        "onboarding_day": day,
        "message": message,
        "created_at": datetime.now().isoformat(),
    }

    # Persist to log file (Person 5 reads this for the UI)
    reminders = _load_reminders()
    reminders.append(reminder)
    _save_reminders(reminders)

    confirmation = (
        f"⏰ Reminder scheduled for Day {day} of onboarding.\n"
        f"   For: {employee_name}\n"
        f"   Message: {message}"
    )
    print(f"[ACTION: send_reminder] Day {day} — {message}")
    return confirmation