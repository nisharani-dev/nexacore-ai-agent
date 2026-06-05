"""
actions/__init__.py  —  Person 4 (Ingestion + Actions)
-------------------------------------------------------
Exports ALL_TOOLS — the single import Person 1 needs.

Person 1 does:
    from actions import ALL_TOOLS
    agent = initialize_agent(ALL_TOOLS, llm, ...)

That's it. Person 1 doesn't need to know which file each tool lives in.
"""

try:
    from .raise_ticket import raise_it_ticket, raise_ticket
    from .send_reminder import send_reminder
    from .log_blocker import log_blocker, log_resolved_blocker
except ImportError:
    from actions.raise_ticket import raise_it_ticket, raise_ticket  # type: ignore
    from actions.send_reminder import send_reminder  # type: ignore
    from actions.log_blocker import log_blocker, log_resolved_blocker  # type: ignore

ALL_TOOLS = [raise_it_ticket, raise_ticket, send_reminder, log_blocker, log_resolved_blocker]
