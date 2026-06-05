"""
prompt_builder.py
──────────────────
Builds the system + human prompt sent to the LLM.
Uses the merged interfaces: ContextBlock, TeamPath, UserProfile, MemoryItem.
"""

from backend.interfaces import ContextBlock, MemoryItem


# ─────────────────────────────────────────────
# System prompt
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
- Pay attention to the employee's type (contractor / intern / fte) — different rules may apply.
- When the user needs something that requires a ticket, reminder, or blocker log, flag it clearly \
  with [ACTION NEEDED].
- Keep responses concise but complete. Use numbered lists for step-by-step guidance.
- Never fabricate system names, team names, or policy details.
"""


# ─────────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────────

def _format_memories(memories: list[MemoryItem]) -> str:
    if not memories:
        return "No relevant memories found for this query."
    lines = []
    for i, mem in enumerate(memories, 1):
        tags = f"  [tags: {', '.join(mem.tags)}]" if mem.tags else ""
        lines.append(f"{i}. [{mem.level.upper()}]{tags}\n   {mem.content}")
    return "\n".join(lines)


def _format_exceptions(ctx: ContextBlock) -> str:
    notes = ctx.exception_notes
    accesses = ctx.raw_accesses
    lines = []
    for note in notes:
        lines.append(f"⚠️  {note}")
    if accesses:
        lines.append(f"📋 Pre-granted accesses: {', '.join(accesses)}")
    return "\n".join(lines) if lines else "No special exceptions detected."


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────

def build_system_prompt() -> str:
    return SYSTEM_PROMPT


def build_human_prompt(ctx: ContextBlock, user_query: str) -> str:
    user = ctx.user
    hierarchy_str = str(ctx.team_path) if ctx.team_path.names else user.team_name
    memories_str = _format_memories(ctx.memories)
    exceptions_str = _format_exceptions(ctx)

    return f"""## Employee Profile
- Name: {user.name}
- Role: {user.role_title or 'Not specified'}
- Team: {user.team_name}
- Team Hierarchy: {hierarchy_str}
- Employment Type: {user.employment_type}

## Exception Flags
{exceptions_str}

## Retrieved Onboarding Memories
The following memories were retrieved from institutional knowledge relevant to this employee's hierarchy and role:

{memories_str}

## Employee's Question
{ctx.user.name} asks: {user_query}

## Your Task
Using the employee profile, exception flags, and retrieved memories above, provide personalized, \
accurate onboarding guidance. If a step requires raising a ticket, requesting access, or logging a blocker, \
clearly flag it with [ACTION NEEDED].
"""
