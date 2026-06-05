"""
seed_employees.py
-----------------
Generates 150 synthetic employee onboarding interaction records spanning
2022-06-01 through 2025-11-01. Each record simulates what that employee
learned/discovered during onboarding and writes it to Hindsight with
proper temporal tags so the "person #1 vs person #10" contrast is visible.

Run once:
    python -m backend.memory.seed_employees
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from backend.interfaces import MemoryItem
from backend.memory.hindsight_client import HindsightClient

TEAMS = [
    ("platform", "engineering", ["Terraform Cloud", "ArgoCD", "PagerDuty", "Kubernetes"]),
    ("infra_security", "engineering", ["Vault", "Snyk", "AWS IAM", "Cloudflare"]),
    ("data_platform", "engineering", ["Databricks", "Airflow", "dbt", "Looker"]),
    ("fp_and_a", "finance", ["Anaplan", "NetSuite", "Pigment", "Google Sheets"]),
    ("product", "product", ["Jira", "Confluence", "Amplitude", "Figma"]),
]

ROLES = [
    "SDE Intern",
    "SDE-1",
    "SDE-2",
    "Staff Engineer",
    "Engineering Manager",
    "Analyst",
    "Senior Analyst",
    "Product Manager",
]

EMP_TYPES = ["fte", "fte", "fte", "contractor", "intern"]

EARLY_BLOCKERS = [
    "No documented process for {tool} access — had to ask 3 people",
    "{tool} provisioning took 8 days due to missing approval chain",
    "Sandbox environment for {tool} not set up — blocked for first week",
    "VPN profile for contractors not configured by default — 2 day delay",
    "{tool} license pool exhausted — needed manager escalation",
]

LATER_LEARNINGS = [
    "{tool} access: request via Jira ITSD project, co-approve with team lead",
    "{tool} provisioning typically 2-3 days; ping #it-access if >3 days",
    "Sandbox for {tool} pre-provisioned from Day 1 — see #platform-team",
    "VPN for contractors: IT auto-provisions 1 day before start date now",
    "{tool} licenses auto-assigned when GitHub org invite is accepted",
]

RITUALS = [
    "Weekly sync every Monday 10am — join #{team}-team Slack",
    "On-call shadow rotation starts Week 2 for all engineers",
    "PR reviews expected within 1 business day per team norms",
    "Architecture decision records go in Confluence /{team}/ADRs",
    "Incident postmortems published in #incidents within 72h",
]


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def build_employee_memories(n: int = 150) -> list[MemoryItem]:
    random.seed(42)
    memories: list[MemoryItem] = []
    start_date = date(2022, 6, 1)
    end_date = date(2025, 11, 1)

    for i in range(n):
        team_id, org, tools = random.choice(TEAMS)
        role = random.choice(ROLES)
        emp_type = random.choice(EMP_TYPES)
        join_date = random_date(start_date, end_date)
        tool = random.choice(tools)
        name = f"Employee_{i+1:03d}"

        fraction = (join_date - start_date).days / (end_date - start_date).days

        if fraction < 0.3:
            template = random.choice(EARLY_BLOCKERS)
            level = "exception"
            mem_type = "blocker"
        elif fraction < 0.65:
            template = random.choice(EARLY_BLOCKERS + LATER_LEARNINGS)
            level = "team"
            mem_type = "access" if "request" in template or "provisioned" in template else "blocker"
        else:
            template = random.choice(LATER_LEARNINGS)
            level = "team"
            mem_type = "access"

        content = template.replace("{tool}", tool).replace("{team}", team_id)

        if random.random() < 0.25:
            ritual_content = random.choice(RITUALS).replace("{team}", team_id)
            memories.append(
                MemoryItem(
                    content=ritual_content,
                    tags=[
                        "seed:employees_v1",
                        f"org:{org}",
                        f"team:{team_id}",
                        "type:ritual",
                        f"join_date:{join_date.isoformat()}",
                        f"employee:{name}",
                    ],
                    level="team",
                    source="seed_employees",
                    relevance_score=round(0.70 + fraction * 0.15, 3),
                )
            )

        memories.append(
            MemoryItem(
                content=content,
                tags=[
                    "seed:employees_v1",
                    f"org:{org}",
                    f"team:{team_id}",
                    f"role:{role.lower().replace(' ', '_')}",
                    f"emp_type:{emp_type}",
                    f"type:{mem_type}",
                    f"tool:{tool.lower().replace(' ', '_')}",
                    f"join_date:{join_date.isoformat()}",
                    f"employee:{name}",
                ],
                level=level,
                source="seed_employees",
                relevance_score=round(0.65 + fraction * 0.25, 3),
            )
        )

    return memories


def seed_employees(*, reset: bool = False, client: HindsightClient | None = None) -> int:
    hindsight = client or HindsightClient()
    if reset:
        hindsight.reset()
    memories = build_employee_memories(150)
    hindsight.write_many(memories, metadata={"seed_batch": "employees_v1"})
    print(f"Seeded {len(memories)} employee memory records.")
    return len(memories)


def ensure_employee_data(client: HindsightClient | None = None) -> int:
    hindsight = client or HindsightClient()
    existing = hindsight.search(tags=["seed:employees_v1"], limit=1)
    if existing:
        return 0
    return seed_employees(client=hindsight)


if __name__ == "__main__":
    seed_employees()
