"""
raise_ticket.py  —  Person 4 (Ingestion + Actions)
----------------------------------------------------
LangChain tool: raises an IT access ticket for the new employee.

What is a LangChain tool?
    The agent (Person 1) is built with LangChain. A "tool" is just a
    Python function with a @tool decorator and a docstring that explains
    WHEN the agent should call it. The agent reads the docstring and
    decides on its own: "the user needs AWS access — I should call raise_it_ticket."

    You don't tell the agent "call this tool now." It figures it out.

How Person 1 uses this:
    from actions.raise_ticket import raise_it_ticket
    # Then adds it to the agent's tools list

Mock behaviour:
    In a real product this would POST to Jira/ServiceNow API.
    For the hackathon we simulate it — generate a fake ticket ID,
    print it, and return a success string the agent can relay to the user.
"""

import sys
import hashlib
from pathlib import Path
from langchain.tools import tool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@tool
def raise_it_ticket(description: str) -> str:
    """
    Raises an IT support ticket for the new employee.

    Use this tool when the employee needs to request access to any system
    — for example: GitHub, AWS, Okta, Jira, Terraform Cloud, PagerDuty,
    Snowflake, Vault, Confluence spaces, or any other tool.

    Input: a plain-English description of what access is needed and why.
    Example: "Request AWS baseline access for new Platform Engineering hire"

    Returns: a confirmation string with the mock ticket ID.
    """
    # Generate a deterministic-looking fake ticket ID from the description
    # (so the same request always gets the same ID — looks more real in demo)
    ticket_num = int(hashlib.md5(description.encode()).hexdigest(), 16) % 9000 + 1000
    ticket_id = f"IT-{ticket_num}"

    # In production: POST to Jira/ServiceNow here
    # e.g. requests.post("https://acmecorp.atlassian.net/rest/api/2/issue", ...)

    confirmation = (
        f"✅ IT ticket {ticket_id} raised successfully.\n"
        f"   Request: {description}\n"
        f"   You will receive an email confirmation at your company address.\n"
        f"   Typical response time: 1–3 business days."
    )
    print(f"[ACTION: raise_it_ticket] {ticket_id} — {description}")
    return confirmation