"""
prompt_builder.py
──────────────────
Constructs the system + human prompt for the LLM.

Design principles:
  - System prompt sets the agent's persona and hard rules.
  - Human prompt injects all dynamic context (profile, memories, exceptions, query).
  - Keeps the LLM focused: no hallucinated policies, only retrieved memories.
"""

from backend.interfaces import AgentContext, MemoryItem


# ─────────────────────────────────────────────
# System prompt — static persona + guardrails
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are Ramp, an intelligent onboarding assistant for large organizations.
Your job is to help new employees navigate their first days using real institutional memory — \
knowledge collected from past employees who went through the same experience.

Guidelines:
- Always be warm, clear, and actionable. New employees are often anxious.
- Ground every piece of advice in the retrieved memories provided to you. Do not invent policies.
- If a memory directly answers the question, lead with it.
- If memories are partial, synthesize them into a coherent step-by-step answer.
- If no relevant memory exists, say so honestly and suggest who to contact.
- Pay attention to the employee's type (contractor / intern / full-time) — different rules may apply.
- When the user needs something that requires a ticket, reminder, or blocker log, mention it clearly \
  so the appropriate tool can be triggered.
- Keep responses concise but complete. Use numbered lists for step-by-step guidance.
- Never fabricate system names, team names, or policy details.
"""


# ─────────────────────────────────────────────
# Memory block formatter
# ─────────────────────────────────────────────

def _format_memories(memories: list[MemoryItem]) -> str:
    if not memories:
        return "No relevant memories found for this query."

    lines = []
    for i, mem in enumerate(memories, 1):
        tags = f"  [tags: {', '.join(mem.tags)}]" if mem.tags else ""
        lines.append(
            f"{i}. [{mem.source_level.upper()}]{tags}\n   {mem.content}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Exception block formatter
# ─────────────────────────────────────────────

def _format_exceptions(ctx: AgentContext) -> str:
    exc = ctx.exceptions
    flags = []

    if exc.is_contractor:
        flags.append("⚠️  CONTRACTOR: This employee uses a different Jira workflow and may have restricted tool access.")
    if exc.is_intern:
        flags.append("⚠️  INTERN: This employee has limited system access and requires a mentor assignment.")
    if exc.needs_vpn_exception:
        flags.append("⚠️  VPN EXCEPTION: Standard VPN setup may not apply. Check contractor/remote policy.")
    if exc.needs_special_jira_workflow:
        flags.append("⚠️  SPECIAL JIRA WORKFLOW: Use the non-standard Jira onboarding board.")

    for key, val in exc.custom_flags.items():
        flags.append(f"⚠️  {key.upper().replace('_', ' ')}: {val}")

    return "\n".join(flags) if flags else "No special exceptions detected."


# ─────────────────────────────────────────────
# Public API — called by agent.py
# ─────────────────────────────────────────────

def build_system_prompt() -> str:
    """Returns the static system prompt."""
    return SYSTEM_PROMPT


def build_human_prompt(ctx: AgentContext) -> str:
    """
    Builds the human-turn message with all dynamic context injected.
    This is what gets sent alongside the system prompt to the LLM.
    """
    user = ctx.user
    hierarchy_str = " → ".join(user.team_hierarchy) if user.team_hierarchy else user.team
    memories_str = _format_memories(ctx.memories)
    exceptions_str = _format_exceptions(ctx)

    prompt = f"""## Employee Profile
- Name: {user.name}
- Role: {user.role}
- Team: {user.team}
- Team Hierarchy: {hierarchy_str}
- Employment Type: {user.employee_type}

## Exception Flags
{exceptions_str}

## Retrieved Onboarding Memories
The following memories were retrieved from institutional knowledge relevant to this employee's hierarchy and role:

{memories_str}

## Employee's Question
{ctx.query}

## Your Task
Using the employee profile, exception flags, and retrieved memories above, provide personalized, \
accurate onboarding guidance. If a step requires raising a ticket, requesting access, or logging a blocker, \
clearly flag it with [ACTION NEEDED].
"""
    return prompt
