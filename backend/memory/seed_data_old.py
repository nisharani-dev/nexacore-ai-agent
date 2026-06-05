"""
seed_data.py
------------
Seeds a substantial demo corpus so the product feels valuable immediately.

The dataset intentionally includes:
- company-wide onboarding guidance
- division-wide engineering and finance guidance
- team-specific operating notes
- exception memories for contractors and interns
- known blockers with actionable fixes
"""

from __future__ import annotations

from backend.interfaces import MemoryItem
from backend.memory.hindsight_client import HindsightClient


TEAM_DEFINITIONS = [
    {
        "id": "platform",
        "org": "engineering",
        "display": "Platform Engineering",
        "channels": "#platform-team, #deployments, #on-call",
        "systems": "Terraform Cloud, ArgoCD, PagerDuty",
        "blockers": [
            "Terraform Cloud access can stall if the primary platform lead is travelling; escalate to the backup lead after 2 business days.",
            "PagerDuty access should wait until the first shadow on-call week is scheduled.",
            "ArgoCD requests move faster when bundled with Terraform Cloud in one approval thread.",
        ],
    },
    {
        "id": "infra_security",
        "org": "engineering",
        "display": "Infra Security",
        "channels": "#security-onboarding, #security-alerts",
        "systems": "Vault, Snyk, AWS security audit role",
        "blockers": [
            "Vault access is blocked until compliance training is complete and the NDA is signed.",
            "Snyk access only appears after the infra_security Jira project membership is added.",
            "Security-runbooks access for contractors requires a redacted excerpt rather than full-space membership.",
        ],
    },
    {
        "id": "data_platform",
        "org": "engineering",
        "display": "Data Platform",
        "channels": "#data-platform, #data-alerts",
        "systems": "Snowflake, dbt Cloud, Airflow",
        "blockers": [
            "Snowflake write access can take 3 to 5 business days because manager approval is mandatory.",
            "dbt Cloud uses a shared non-SSO login that new joiners often miss in 1Password.",
            "Airflow access only works on VPN and fails silently if the laptop is not on the corporate network.",
        ],
    },
    {
        "id": "backend_api",
        "org": "engineering",
        "display": "Backend API",
        "channels": "#backend-api, #api-incidents",
        "systems": "Lambda, API Gateway, Postman Team",
        "blockers": [
            "Postman Team access is needed on Day 1 because internal API contracts are not mirrored elsewhere.",
            "Lambda deploy permissions depend on Platform-provisioned ArgoCD permissions; coordinate both together.",
            "API incident playbooks live in Confluence but are easy to miss because the space title differs from the Slack channel name.",
        ],
    },
    {
        "id": "fp_and_a",
        "org": "finance",
        "display": "FP&A",
        "channels": "#finance-team, #finance-ops",
        "systems": "SAP FP&A module, Adaptive Insights, Tableau",
        "blockers": [
            "Adaptive Insights SSO often fails on first login unless the direct URL is opened once beforehand.",
            "SAP tickets must go to Finance IT rather than the general helpdesk or they sit in the wrong queue.",
            "Tableau workspace approvals usually need a finance lead mention in the ticket comments to unblock faster.",
        ],
    },
    {
        "id": "product",
        "org": "product",
        "display": "Product",
        "channels": "#product, #product-design",
        "systems": "Jira Product workspace, Confluence Product, Figma, Amplitude",
        "blockers": [
            "Figma seats are limited and waiting to request one until Day 2 often delays onboarding by several days.",
            "Amplitude SSO only works once the Okta group is fully synced, which can lag by a day.",
            "Product review templates are scattered across multiple spaces and new PMs often need the curated onboarding index first.",
        ],
    },
]

COMPANY_GUIDANCE = [
    "Set up VPN before trying any internal tools because several onboarding systems fail silently without it.",
    "Badge pickup after 5 PM frequently fails; book reception pickup during business hours.",
    "Okta and email activation should be completed before submitting any access tickets.",
    "Collect the employee handbook link and HR portal details on Day 1 because those unblock several admin tasks.",
    "The general IT helpdesk is not always the fastest path; team-specific escalation contacts often matter more.",
    "Slack profile setup is worth doing early because many internal approvals are coordinated in chat rather than email.",
    "Save screenshots of ticket confirmations so onboarding buddies can escalate without re-requesting details.",
    "Use the onboarding agent as the first stop before filing duplicate tickets; several blockers already have known fixes.",
]

ORG_GUIDANCE = {
    "engineering": [
        "Request AWS baseline access on Day 1 because CloudOps queues are the single most common engineering blocker.",
        "GitHub org access only auto-provisions when the employee email matches the linked GitHub account.",
        "Engineering Jira and Confluence access should be requested together to avoid fragmented approvals.",
        "DataDog read access usually lands automatically but can lag if the Okta group sync is behind.",
        "1Password engineering vault access is required before several shared credentials are visible.",
    ],
    "finance": [
        "Finance system access often routes through Finance IT, not the main helpdesk.",
        "Concur and Netsuite tend to provision quickly, but SAP remains the long pole.",
        "Finance onboarding is smoother when expense tools and reporting tools are requested in one batch.",
        "Several finance dashboards are shared through Tableau workspace groups rather than direct invites.",
    ],
    "product": [
        "Product onboarding depends heavily on Jira Product and Confluence Product access being granted together.",
        "Figma and Amplitude are the two most commonly delayed tools for new product hires.",
        "Review templates and launch docs are spread across multiple product spaces, so the onboarding index matters.",
        "The fastest escalation for Figma seat issues is usually Design Ops rather than general IT.",
    ],
}

CONTRACTOR_NOTES = [
    "Contractors often receive the wrong Jira license and need the external license fix from IT.",
    "Contractor provisioning runs through a slower queue, so status checks should start earlier.",
    "Contractor NDA completion is mandatory before sensitive systems can be approved.",
    "Contractor Slack access expires at contract end date and renewals should be scheduled proactively.",
    "Restricted Confluence spaces often require redacted excerpts or manager-mediated screenshots instead of direct access.",
]

INTERN_NOTES = [
    "Interns use sandbox AWS accounts only and production access requests are auto-rejected.",
    "Intern PRs require a mentor co-reviewer until the internship ends.",
    "Intern onboarding is smoother when mentor office hours are scheduled in week one.",
    "Several repo permissions stay read-only until the week-two sign-off checkpoint.",
]


def build_seed_memories() -> list[MemoryItem]:
    memories: list[MemoryItem] = []

    for index, line in enumerate(COMPANY_GUIDANCE, start=1):
        memories.append(
            MemoryItem(
                content=f"COMPANY GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:all"],
                level="company",
                source="seed_data",
                relevance_score=0.72 + (index * 0.01),
            )
        )

    for org, lines in ORG_GUIDANCE.items():
        for index, line in enumerate(lines, start=1):
            memories.append(
                MemoryItem(
                    content=f"{org.upper()} GUIDANCE #{index}: {line}",
                    tags=["org:company", f"org:{org}", "exception:all"],
                    level="division",
                    source="seed_data",
                    relevance_score=0.76 + (index * 0.01),
                )
            )

    for team in TEAM_DEFINITIONS:
        team_tags = ["org:company", f"org:{team['org']}", f"team:{team['id']}"]

        memories.append(
            MemoryItem(
                content=f"{team['display']} channels to join early: {team['channels']}.",
                tags=team_tags,
                level="team",
                source="seed_data",
                relevance_score=0.81,
            )
        )
        memories.append(
            MemoryItem(
                content=f"{team['display']} core systems: {team['systems']}. Bundle those requests on Day 1 when possible.",
                tags=team_tags,
                level="team",
                source="seed_data",
                relevance_score=0.82,
            )
        )
        memories.append(
            MemoryItem(
                content=f"{team['display']} onboarding tip: ask your onboarding buddy for the most recent runbook index before opening separate questions in Slack.",
                tags=team_tags,
                level="team",
                source="seed_data",
                relevance_score=0.79,
            )
        )

        for index, blocker in enumerate(team["blockers"], start=1):
            memories.append(
                MemoryItem(
                    content=f"KNOWN BLOCKER [{team['display']} #{index}]: {blocker}",
                    tags=team_tags + ["exception:all"],
                    level="exception",
                    source="seed_data",
                    relevance_score=0.9 + (index * 0.01),
                )
            )

        for index, note in enumerate(CONTRACTOR_NOTES[:4], start=1):
            memories.append(
                MemoryItem(
                    content=f"CONTRACTOR NOTE [{team['display']} #{index}]: {note}",
                    tags=team_tags + ["exception:contractor", "exception:all"],
                    level="exception",
                    source="seed_data",
                    relevance_score=0.88 + (index * 0.01),
                )
            )

        for index, note in enumerate(INTERN_NOTES[:3], start=1):
            memories.append(
                MemoryItem(
                    content=f"INTERN NOTE [{team['display']} #{index}]: {note}",
                    tags=team_tags + ["exception:intern", "exception:all"],
                    level="exception",
                    source="seed_data",
                    relevance_score=0.84 + (index * 0.01),
                )
            )

    for index, line in enumerate(CONTRACTOR_NOTES, start=1):
        memories.append(
            MemoryItem(
                content=f"GLOBAL CONTRACTOR GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:contractor", "exception:all"],
                level="exception",
                source="seed_data",
                relevance_score=0.86 + (index * 0.01),
            )
        )

    for index, line in enumerate(INTERN_NOTES, start=1):
        memories.append(
            MemoryItem(
                content=f"GLOBAL INTERN GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:intern", "exception:all"],
                level="exception",
                source="seed_data",
                relevance_score=0.82 + (index * 0.01),
            )
        )

    return memories


SEED_MEMORIES = build_seed_memories()


def seed_demo_data(*, reset: bool = False, client: HindsightClient | None = None) -> list[MemoryItem]:
    hindsight = client or HindsightClient()
    if reset:
        hindsight.reset()
    hindsight.write_many(SEED_MEMORIES, metadata={"seed_batch": "demo"})
    return SEED_MEMORIES


def ensure_demo_data(client: HindsightClient | None = None) -> list[MemoryItem]:
    hindsight = client or HindsightClient()
    if hindsight.count_records() == 0:
        return seed_demo_data(reset=False, client=hindsight)
    seed_demo_data(reset=False, client=hindsight)
    return SEED_MEMORIES


if __name__ == "__main__":
    seeded = seed_demo_data(reset=True)
    print(f"Seeded {len(seeded)} memories into the Hindsight demo store.")
