"""
seed_data_expanded.py
---------------------
Expanded demo corpus with 150+ realistic onboarding scenarios covering:
- Company-wide policies and best practices
- Division and team-specific guidance
- Tool-specific onboarding flows  
- Common blockers and resolutions
- Employment type exceptions (contractor, intern)
- Tool integration patterns
- Time-based dependencies
- Escalation paths
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
        "systems": "Terraform Cloud, ArgoCD, PagerDuty, Kubernetes, Helm",
        "tools": [
            ("Terraform Cloud", "Day 0", "Apply to lead@company.com, co-approve with backup", "medium", "Cloud IaC management"),
            ("ArgoCD", "Day 1", "Bundled with Terraform, GitOps platform", "high", "Deployment automation"),
            ("PagerDuty", "Day 3", "Schedule shadow week first, then provision", "high", "Incident response"),
            ("Kubernetes", "Day 1", "Sandbox cluster access auto-provisioned via GitHub", "high", "Container orchestration"),
        ],
        "blockers": [
            "Terraform Cloud access can stall if the primary platform lead is travelling; escalate to the backup lead after 2 business days.",
            "PagerDuty access should wait until the first shadow on-call week is scheduled.",
            "ArgoCD requests move faster when bundled with Terraform Cloud in one approval thread.",
            "Kubernetes RBAC changes require a PR review; don't request manually in Jira.",
            "Helm chart deployments need linting via our internal CI before approval.",
        ],
    },
    {
        "id": "infra_security",
        "org": "engineering",
        "display": "Infra Security",
        "channels": "#security-onboarding, #security-alerts, #vault-access",
        "systems": "Vault, Snyk, AWS IAM, Cloudflare, Qualys",
        "tools": [
            ("Vault", "Day 2", "After NDA and compliance training signed", "critical", "Secrets management"),
            ("Snyk", "Day 1", "Auto-provisioned once GitHub repo sync completes", "high", "Vulnerability scanning"),
            ("AWS IAM", "Day 0", "Base sandbox role auto-provided, prod roles by mgr approval", "critical", "Cloud permissions"),
            ("Cloudflare", "Day 3", "Read-only first week, write after security review", "medium", "CDN and WAF"),
        ],
        "blockers": [
            "Vault access is blocked until compliance training is complete and the NDA is signed.",
            "Snyk access only appears after the infra_security Jira project membership is added.",
            "Security-runbooks access for contractors requires a redacted excerpt rather than full-space membership.",
            "AWS MFA setup is required before any prod access is granted.",
            "Qualys scanner access needs infrastructure team to whitelist your IP range first.",
        ],
    },
    {
        "id": "data_platform",
        "org": "engineering",
        "display": "Data Platform",
        "channels": "#data-platform, #data-alerts, #dbt-users",
        "systems": "Snowflake, dbt Cloud, Airflow, Great Expectations, Tableau",
        "tools": [
            ("Snowflake", "Day 2", "Manager approval required, 3-5 days typical", "critical", "Data warehouse"),
            ("dbt Cloud", "Day 1", "Shared non-SSO login in 1Password vault, auto-provisioned", "high", "Data transformation"),
            ("Airflow", "Day 1", "VPN-only access, check laptop network config", "high", "Workflow orchestration"),
            ("Great Expectations", "Day 3", "Self-service role provisioning in Airflow UI", "medium", "Data validation"),
        ],
        "blockers": [
            "Snowflake write access can take 3 to 5 business days because manager approval is mandatory.",
            "dbt Cloud uses a shared non-SSO login that new joiners often miss in 1Password.",
            "Airflow access only works on VPN and fails silently if the laptop is not on the corporate network.",
            "Snowflake cold storage queries fail silently; check query editor for warning messages.",
            "dbt Cloud CI/CD requires GitHub PR integration; self-service GitHub Actions setup in docs.",
        ],
    },
    {
        "id": "backend_api",
        "org": "engineering",
        "display": "Backend API",
        "channels": "#backend-api, #api-incidents, #api-design",
        "systems": "Lambda, API Gateway, RDS, ElastiCache, Postman",
        "tools": [
            ("Postman Team", "Day 0", "Mandatory on Day 1, all API contracts live here", "critical", "API collaboration"),
            ("Lambda", "Day 2", "Via ArgoCD + Terraform Cloud provisioning", "critical", "Serverless compute"),
            ("API Gateway", "Day 1", "Auto-provisioned with Lambda deployment role", "critical", "API gateway"),
            ("RDS", "Day 3", "Manager approval, read-only first week standard", "high", "Relational database"),
        ],
        "blockers": [
            "Postman Team access is needed on Day 1 because internal API contracts are not mirrored elsewhere.",
            "Lambda deploy permissions depend on Platform-provisioned ArgoCD permissions; coordinate both together.",
            "API incident playbooks live in Confluence but are easy to miss because the space title differs from the Slack channel name.",
            "RDS connection strings are in Vault, not GitHub secrets; check Vault first.",
            "API throttling rate limits are per-team, not per-user; coordinate with team lead before load testing.",
        ],
    },
    {
        "id": "frontend",
        "org": "engineering",
        "display": "Frontend Engineering",
        "channels": "#frontend, #design-handoff, #web-perf",
        "systems": "GitHub, Storybook, Figma, Datadog RUM, Lighthouse CI",
        "tools": [
            ("Figma", "Day 1", "Limited seats; request ASAP, can take 3-4 days", "high", "Design collaboration"),
            ("GitHub", "Day 0", "Auto-provisioned via email domain match", "critical", "Code repository"),
            ("Storybook", "Day 1", "Self-hosted, accessible once GitHub access is granted", "medium", "Component library"),
            ("Datadog RUM", "Day 2", "Auto-provisioned, check browser console for RUM agent", "medium", "Frontend monitoring"),
        ],
        "blockers": [
            "Figma seats are limited and waiting to request one until Day 2 often delays onboarding by several days.",
            "GitHub org access fails silently if email domain is not recognized; check Okta sync status.",
            "Storybook access requires VPN in some regions; test via tunnel first.",
            "CSS-in-JS builds can break if PostCSS config references an old bundler; check webpack config version.",
        ],
    },
    {
        "id": "fp_and_a",
        "org": "finance",
        "display": "FP&A",
        "channels": "#finance-team, #finance-ops, #budget-planning",
        "systems": "SAP FP&A module, Adaptive Insights, Tableau, Concur, Netsuite",
        "tools": [
            ("Adaptive Insights", "Day 2", "SSO sync can lag; open direct URL once beforehand", "critical", "Planning platform"),
            ("SAP", "Day 3", "Route through Finance IT, not main helpdesk", "critical", "ERP system"),
            ("Tableau", "Day 1", "Via finance workspace group, request manager approval", "high", "Analytics dashboard"),
            ("Concur", "Day 1", "Fast provisioning, auto-linked to payroll", "high", "Expense management"),
        ],
        "blockers": [
            "Adaptive Insights SSO often fails on first login unless the direct URL is opened once beforehand.",
            "SAP tickets must go to Finance IT rather than the general helpdesk or they sit in the wrong queue.",
            "Tableau workspace approvals usually need a finance lead mention in the ticket comments to unblock faster.",
            "SAP password reset doesn't sync with corporate Okta; use SAP-specific reset portal.",
            "Concur mileage reimbursement rules vary by region; check Finance wiki for your location.",
        ],
    },
    {
        "id": "product",
        "org": "product",
        "display": "Product",
        "channels": "#product, #product-design, #roadmap",
        "systems": "Jira Product workspace, Confluence Product, Figma, Amplitude, Mixpanel",
        "tools": [
            ("Figma", "Day 0", "Limited seats, fast-track request to Design Ops", "high", "Design collaboration"),
            ("Amplitude", "Day 2", "Okta sync lag common; wait for email confirmation", "high", "Product analytics"),
            ("Jira Product", "Day 1", "Auto-provisioned once GitHub email is recognized", "critical", "Issue tracking"),
            ("Confluence Product", "Day 1", "Bundled with Jira Product access", "critical", "Docs and specs"),
        ],
        "blockers": [
            "Figma seats are limited and waiting to request one until Day 2 often delays onboarding by several days.",
            "Amplitude SSO only works once the Okta group is fully synced, which can lag by a day.",
            "Product review templates are scattered across multiple spaces and new PMs often need the curated onboarding index first.",
            "Mixpanel API keys for product are in Vault, not 1Password; check Vault browser plugin.",
            "Jira Product board filters can break if archived projects aren't cleaned up; refresh board view.",
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
    "Okta MFA setup is non-optional; complete it before the first day ends to avoid access lockouts.",
    "Check the internal knowledge base before asking in public Slack channels; answers are usually already documented.",
    "Calendar invites should include Zoom links; defaults to video first, email as backup.",
    "All recurring 1:1s and standup meetings are recorded; check Slack threads for async updates.",
    "GitHub SSH keys are required on Day 1 for repo access; generate and upload before trying to clone.",
    "Password managers (1Password) access is mandatory; check IT wiki for vault setup instructions.",
    "Team budgets and expense policies vary by department; ask your manager for the finance wiki link.",
    "On-call rotations start on Monday mornings; ensure you're not scheduled on your first week.",
    "Performance review cycles run twice yearly; mark calendar in Jan and July for self-evaluation reminders.",
    "All-hands meetings are bi-weekly on Thursdays at 10 AM PT; recordings available next business day.",
    "Equity grants vest over 4 years with 1-year cliff; equity page in HR portal has detailed schedule.",
    "Internal promotion windows open in March and September; check HR notifications for application deadlines.",
]

ORG_GUIDANCE = {
    "engineering": [
        "Request AWS baseline access on Day 1 because CloudOps queues are the single most common engineering blocker.",
        "GitHub org access only auto-provisions when the employee email matches the linked GitHub account.",
        "Engineering Jira and Confluence access should be requested together to avoid fragmented approvals.",
        "DataDog read access usually lands automatically but can lag if the Okta group sync is behind.",
        "1Password engineering vault access is required before several shared credentials are visible.",
        "Code review SLAs are 24 hours for standard PRs, 4 hours for critical infrastructure changes.",
        "Deploy approvals require both an engineering owner and a platform engineer co-sign.",
        "Staging environment credentials are in Vault, not committed to repositories; never check secrets into Git.",
        "Load testing requires advance notice on #platform-team; unannounced tests trigger incident response.",
        "Database schema changes need migration scripts; raw SQL in deploy hooks will be rejected.",
        "Kubernetes namespace provisioning takes 2-3 hours; request early in the day for same-day setup.",
        "Helm values overrides are per-environment; dev/staging use different image registries than prod.",
        "Docker builds must use internal registry; external DockerHub pulls are rate-limited after 100 pulls/hour.",
        "Terraform state files are backed up nightly; manually request point-in-time recovery through Platform team.",
        "All CI/CD pipelines use GitHub Actions; GitLab CI is not supported for new projects.",
    ],
    "finance": [
        "Finance system access often routes through Finance IT, not the main helpdesk.",
        "Concur and Netsuite tend to provision quickly, but SAP remains the long pole.",
        "Finance onboarding is smoother when expense tools and reporting tools are requested in one batch.",
        "Several finance dashboards are shared through Tableau workspace groups rather than direct invites.",
        "Budget allocation cycles run quarterly; Q1 planning starts in December of prior year.",
        "Reimbursement processing takes 5-7 business days from approval; Concur shows weekly processing schedule.",
        "Headcount planning is annual in September; budget impacts are discussed in summer planning.",
        "Audit logs for financial transactions are archived quarterly; requests older than 2 years need restoration.",
        "Equity grant documents are confidential; access is one-time during grant issuance.",
        "401k plan elections must be made within 30 days of employment start; deadline enforced by payroll.",
        "W-4 tax form updates take one payroll cycle (bi-weekly) to apply; submit ASAP if changes needed.",
        "Bonus structures differ by level and department; Finance wiki has level-specific bonus multipliers.",
        "Expense report approval authority is hierarchical; L3+ reports need department head approval.",
        "Travel policy limits change by role; check HR portal for your specific authorization level.",
    ],
    "product": [
        "Product onboarding depends heavily on Jira Product and Confluence Product access being granted together.",
        "Figma and Amplitude are the two most commonly delayed tools for new product hires.",
        "Review templates and launch docs are spread across multiple product spaces, so the onboarding index matters.",
        "The fastest escalation for Figma seat issues is usually Design Ops rather than general IT.",
        "Product metrics dashboard refreshes daily at 6 AM UTC; yesterday's data is always available by 9 AM.",
        "Feature flags are controlled via LaunchDarkly; product controls rollout percentages without code deploy.",
        "A/B test results require 2-week minimum for statistical significance; early termination not recommended.",
        "User feedback channels: support tickets in Jira, in-app surveys via Apptentive, community via Slack.",
        "Roadmap planning happens quarterly; feature scoping deadline is 3 weeks before quarter start.",
        "Product PRDs require design mockups before engineering starts; review early to avoid rework.",
        "Release notes are auto-generated from Jira tickets; use standard labels for inclusion in notes.",
        "Post-launch monitoring dashboard is in Datadog; set up custom metrics before launch day.",
        "Customer success hands off new accounts at Day 7; coordinate onboarding resources with CS team.",
        "Beta programs run 2-4 weeks; beta feedback requires documented consent from participants.",
    ],
}

ADDITIONAL_BLOCKERS = [
    ("AWS", "Account provisioning can take 1-2 days; check CloudOps queue status before escalating"),
    ("GitHub", "SSH key uploads fail silently on first attempt; wait 60 seconds and retry"),
    ("Jira", "Custom field permissions are role-based; some fields are read-only for new users"),
    ("Confluence", "Space permissions sync hourly; changes are not instant"),
    ("Slack", "App installations require security review; pre-installed apps are in #apps channel"),
    ("1Password", "Vault sharing requires manager approval; shared vaults appear after next sync"),
    ("Okta", "Group membership changes require SSO cache clear; browser cache reset may be needed"),
    ("VPN", "Certificate renewal happens automatically; expired certs can cause silent auth failures"),
    ("Datadog", "Agent installation requires CloudFormation update; manual setup not supported"),
    ("PagerDuty", "Escalation policy changes take 30 minutes to propagate; test after waiting"),
    ("Terraform Cloud", "API token rotation required every 90 days; set calendar reminder at 60 days"),
    ("Postman", "API key shares expire after 90 days; collection owner must refresh"),
    ("Figma", "File permissions are separate from seat licensing; both must be granted"),
    ("Tableau", "Workbook extracts refresh on schedule; manual refresh requires publisher role"),
    ("Amplitude", "Custom events backfill does not work; events from Day 1 only available from deployment day"),
]

CONTRACTOR_NOTES = [
    "Contractors often receive the wrong Jira license and need the external license fix from IT.",
    "Contractor provisioning runs through a slower queue, so status checks should start earlier.",
    "Contractor NDA completion is mandatory before sensitive systems can be approved.",
    "Contractor Slack access expires at contract end date and renewals should be scheduled proactively.",
    "Restricted Confluence spaces often require redacted excerpts or manager-mediated screenshots instead of direct access.",
    "Contractor GitHub access is limited to specific repos; broad org access is not available.",
    "Contractor AWS IAM roles lack several permissions; check IAM policy document before troubleshooting access errors.",
    "Contractor 1Password vaults are read-only by default; write access requires manager co-sign.",
    "Contractor VPN certificates expire monthly; monthly renewal is required (vs. annual for FTEs).",
    "Contractor expense approvals route through Finance IT, not standard Concur workflow.",
    "Contractor Okta groups are managed separately; group membership changes take 48 hours.",
    "Contractor security trainings are shorter but must be renewed every 6 months.",
    "Contractor laptop provisioning can take 2-3 weeks; IT should order on contract start date.",
    "Contractor DataDog dashboards have limited data retention; real-time queries only.",
    "Contractor email forwarding is disabled; all mail sent to @contractor domain, not corporate domain.",
]

INTERN_NOTES = [
    "Interns use sandbox AWS accounts only and production access requests are auto-rejected.",
    "Intern PRs require a mentor co-reviewer until the internship ends.",
    "Intern onboarding is smoother when mentor office hours are scheduled in week one.",
    "Several repo permissions stay read-only until the week-two sign-off checkpoint.",
    "Interns cannot access production databases; sandbox Postgres is set up for learning.",
    "Intern Slack channels are separate from team channels; chat in #interns first.",
    "Intern badge access is limited to common areas; lab and datacenter access requires mentor approval.",
    "Intern performance feedback is weekly, not monthly; real-time coaching is standard.",
    "Interns cannot attend executive meetings or strategic planning sessions.",
    "Intern laptops are loaner devices; personal device use requires InfoSec exception.",
    "Internship extension deadlines are 4 weeks before end date; announce intent early.",
    "Interns receive stipend, not full salary; tax forms are 1099, not W-4.",
    "Intern mentors get quarterly bonus; make sure your mentor is aware of bonus timing.",
    "Intern open source contributions are OK but require IP clearance for commercial projects.",
    "Interns network with peer group; quarterly happy hours are mandatory social events.",
]

TOOL_INTEGRATION_PATTERNS = [
    ("GitHub + Jira", "Sync is automatic; mention issue keys in commit messages for auto-linking"),
    ("Jira + Slack", "Notifications go to channel after ticket creation; customize per-project"),
    ("Confluence + Jira", "Space permissions must match Jira project; request together"),
    ("Figma + Slack", "Embed preview via Slack integration; click to open full design"),
    ("DataDog + Slack", "Alert routing is channel-specific; configure in monitor settings"),
    ("Amplitude + Jira", "Feature flag export to CSV, then import segments into Jira filters"),
    ("Tableau + Slack", "Schedule automated reports to post to channel daily/weekly"),
    ("GitHub + CloudFormation", "Infrastructure as code is version-controlled; PRs require approval"),
    ("PagerDuty + VictorOps", "Incident escalation spans both platforms; configure bridge"),
    ("Snyk + GitHub", "PR checks fail if vulnerabilities found; bypass requires security approval"),
    ("dbt + Airflow", "DAG is auto-generated from dbt project; keep manifest.json in sync"),
    ("RDS + DataDog", "Database metrics stream automatically; custom metrics require IAM policy"),
    ("Lambda + Postman", "Integration tests use AWS credentials from 1Password; refresh before test"),
    ("Kubernetes + ArgoCD", "Manifest repo is source of truth; cluster changes are auto-reverted"),
    ("Terraform + GitHub", "HCL linting happens in PR checks; format with 'terraform fmt'"),
]

TIME_BASED_DEPENDENCIES = [
    ("Week 1", "VPN setup, Okta, email, badge pickup - these must complete before anything else"),
    ("Week 1", "GitHub SSH keys - needed before first repo clone"),
    ("Week 2", "AWS baseline access - required for most engineering tasks"),
    ("Week 2", "Team-specific system access - varies by team, coordinate with team lead"),
    ("Week 3", "Production access - review and approval after 2 weeks observation"),
    ("Week 4", "On-call rotation - shadow an on-call engineer before taking rotations"),
    ("Month 2", "Security training completion - required before sensitive data access"),
    ("Month 3", "First performance review - feedback from manager and team members"),
    ("Month 6", "Probation period end - formal confirmation and compensation review"),
    ("Year 1", "First full review cycle - complete self-evaluation and peer feedback"),
]

ESCALATION_PATHS = [
    ("Tool Access", "Level 1: Team lead -> Level 2: Tool admin -> Level 3: IT Security"),
    ("Budget", "Level 1: Manager -> Level 2: Department head -> Level 3: CFO"),
    ("Performance", "Level 1: Manager -> Level 2: HR -> Level 3: Executive coach"),
    ("Salary/Equity", "Level 1: HR -> Level 2: Finance -> Level 3: CEO"),
    ("Policy Exception", "Level 1: Manager -> Level 2: HR policy -> Level 3: Legal"),
    ("Security Incident", "Level 1: Team lead -> Level 2: InfoSec -> Level 3: CISO"),
    ("Infrastructure", "Level 1: Team lead -> Level 2: Platform lead -> Level 3: Director of Engineering"),
]


def build_seed_memories() -> list[MemoryItem]:
    memories: list[MemoryItem] = []

    # Company guidance
    for index, line in enumerate(COMPANY_GUIDANCE, start=1):
        memories.append(
            MemoryItem(
                content=f"COMPANY GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:all"],
                level="company",
                source="seed_data",
                relevance_score=0.72 + (index * 0.002),
            )
        )

    # Org guidance
    for org, lines in ORG_GUIDANCE.items():
        for index, line in enumerate(lines, start=1):
            memories.append(
                MemoryItem(
                    content=f"{org.upper()} GUIDANCE #{index}: {line}",
                    tags=["org:company", f"org:{org}", "exception:all"],
                    level="division",
                    source="seed_data",
                    relevance_score=0.76 + (index * 0.002),
                )
            )

    # Team definitions with expanded details
    for team in TEAM_DEFINITIONS:
        team_tags = ["org:company", f"org:{team['org']}", f"team:{team['id']}"]

        # Channels and systems
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

        # Tool-specific guidance
        for tool_name, day, description, priority, purpose in team.get("tools", []):
            memories.append(
                MemoryItem(
                    content=f"{team['display']} tool '{tool_name}' (requested: {day}, priority: {priority}): {description}. Purpose: {purpose}.",
                    tags=team_tags + ["type:tool"],
                    level="team",
                    source="seed_data",
                    relevance_score=0.85,
                )
            )

        # Team tips
        memories.append(
            MemoryItem(
                content=f"{team['display']} onboarding tip: ask your onboarding buddy for the most recent runbook index before opening separate questions in Slack.",
                tags=team_tags,
                level="team",
                source="seed_data",
                relevance_score=0.79,
            )
        )

        # Team blockers
        for index, blocker in enumerate(team.get("blockers", []), start=1):
            memories.append(
                MemoryItem(
                    content=f"KNOWN BLOCKER [{team['display']} #{index}]: {blocker}",
                    tags=team_tags + ["exception:all"],
                    level="exception",
                    source="seed_data",
                    relevance_score=0.9 + (index * 0.01),
                )
            )

        # Contractor notes for team
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

        # Intern notes for team
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

    # Global contractor guidance
    for index, line in enumerate(CONTRACTOR_NOTES, start=1):
        memories.append(
            MemoryItem(
                content=f"GLOBAL CONTRACTOR GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:contractor", "exception:all"],
                level="exception",
                source="seed_data",
                relevance_score=0.86 + (index * 0.002),
            )
        )

    # Global intern guidance
    for index, line in enumerate(INTERN_NOTES, start=1):
        memories.append(
            MemoryItem(
                content=f"GLOBAL INTERN GUIDANCE #{index}: {line}",
                tags=["org:company", "exception:intern", "exception:all"],
                level="exception",
                source="seed_data",
                relevance_score=0.82 + (index * 0.002),
            )
        )

    # Additional blockers
    for index, (tool, blocker) in enumerate(ADDITIONAL_BLOCKERS, start=1):
        memories.append(
            MemoryItem(
                content=f"{tool} BLOCKER #{index}: {blocker}",
                tags=["org:company", "type:tool", f"tool:{tool.lower()}"],
                level="exception",
                source="seed_data",
                relevance_score=0.87 + (index * 0.001),
            )
        )

    # Tool integration patterns
    for index, (integration, description) in enumerate(TOOL_INTEGRATION_PATTERNS, start=1):
        memories.append(
            MemoryItem(
                content=f"TOOL INTEGRATION #{index} ({integration}): {description}",
                tags=["org:company", "type:integration"],
                level="company",
                source="seed_data",
                relevance_score=0.75 + (index * 0.001),
            )
        )

    # Time-based dependencies
    for index, (timeframe, task) in enumerate(TIME_BASED_DEPENDENCIES, start=1):
        memories.append(
            MemoryItem(
                content=f"TIMELINE DEPENDENCY [{timeframe}]: {task}",
                tags=["org:company", "type:timeline"],
                level="company",
                source="seed_data",
                relevance_score=0.80 + (index * 0.001),
            )
        )

    # Escalation paths
    for index, (area, path) in enumerate(ESCALATION_PATHS, start=1):
        memories.append(
            MemoryItem(
                content=f"ESCALATION PATH [{area}]: {path}",
                tags=["org:company", "type:escalation"],
                level="company",
                source="seed_data",
                relevance_score=0.78 + (index * 0.001),
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
