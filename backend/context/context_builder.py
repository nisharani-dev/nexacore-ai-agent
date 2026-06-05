"""
context_builder.py  —  Person 3 (Context Builder)
---------------------------------------------------
The main entry point for P3's module.

Given a UserProfile, this module:
1. Resolves the full team path (via TeamResolver)
2. Fetches memories from all ancestor levels (calls P2's retriever stub)
3. Tags exceptions (via ExceptionTagger)
4. Merges all accesses from the team hierarchy
5. Returns a ContextBlock ready for P1's prompt_builder

Integration notes for P1:
    from context.context_builder import ContextBuilder
    from interfaces import UserProfile

    builder = ContextBuilder()
    ctx = builder.build(UserProfile(
        name="Priya",
        team_name="infra security",
        employment_type="contractor",
    ))
    # ctx is a ContextBlock — pass to prompt_builder.assemble(ctx, user_query)

Integration notes for P2:
    This module calls retriever.fetch_memories(tags: list[str]) → list[MemoryItem]
    P2 needs to implement that function signature in memory/retriever.py.
    Until P2 is ready, the stub below is used automatically.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interfaces import UserProfile, TeamPath, MemoryItem, ContextBlock
from context.team_resolver import TeamResolver, _TeamNode
from context.exception_tagger import ExceptionTagger


# ── Stub for P2's retriever (used until memory/ module is ready) ──────────────

def _stub_fetch_memories(tags: list[str]) -> list[MemoryItem]:
    """
    STUB — replace with real Hindsight call once P2 ships retriever.py.

    P2: your retriever.py should expose:
        def fetch_memories(tags: list[str]) -> list[MemoryItem]

    This stub returns empty list so the rest of the pipeline works immediately.
    """
    return []


# ── Try to import P2's real retriever; fall back to stub ─────────────────────

try:
    from memory.retriever import fetch_memories as _fetch_memories  # type: ignore
except ImportError:
    _fetch_memories = _stub_fetch_memories


# ── Context Builder ───────────────────────────────────────────────────────────

class ContextBuilder:
    """
    Assembles a full ContextBlock for a given UserProfile.
    This is the only class P1 needs to import from P3's module.
    """

    def __init__(self):
        self._resolver = TeamResolver()
        self._tagger = ExceptionTagger()

    def build(self, user: UserProfile) -> ContextBlock:
        """
        Main entry point. Returns a ContextBlock.

        Steps:
          1. Resolve team path
          2. Build Hindsight tags from path + exception type
          3. Fetch memories (calls P2)
          4. Tag exception profile
          5. Merge accesses across all levels
          6. Return assembled ContextBlock
        """
        # 1. Resolve team path
        team_path, nodes = self._resolve_path(user.team_name)

        # 2. Build memory tags
        tags = self._build_tags(team_path, user.employment_type)

        # 3. Fetch memories from Hindsight (P2's domain)
        memories = _fetch_memories(tags)

        # 4. Exception profile
        exception_profile = self._tagger.tag(user.employment_type)
        exception_notes = exception_profile.summary_lines()

        # 5. Merge all access lists (company → leaf)
        raw_accesses = self._merge_accesses(nodes, exception_profile)

        return ContextBlock(
            user=user,
            team_path=team_path,
            memories=memories,
            exception_notes=exception_notes,
            raw_accesses=raw_accesses,
        )

    def get_tags_for_user(self, user: UserProfile) -> list[str]:
        """
        Returns just the tags for a user — useful for P2 to call directly
        when deciding what to write back to Hindsight after an interaction.
        """
        team_path, _ = self._resolve_path(user.team_name)
        return self._build_tags(team_path, user.employment_type)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_path(self, team_name: str) -> tuple[TeamPath, list[_TeamNode]]:
        nodes = self._resolver.resolve_with_nodes(team_name)
        path = TeamPath(
            ids=[n.id for n in nodes],
            names=[n.name for n in nodes],
        )
        return path, nodes

    @staticmethod
    def _build_tags(path: TeamPath, employment_type: str) -> list[str]:
        """
        Build Hindsight retrieval tags from the resolved team path.

        Tag format convention (agreed with P2):
          org:company           — always included
          org:<division_id>     — for division-level nodes
          team:<team_id>        — for team-level nodes
          subteam:<id>          — for sub_team nodes
          exception:<emp_type>  — for employment type exceptions
          exception:all         — always included (catches generic exception memories)

        P2 uses these same tags when *writing* memories, so reads always match writes.
        """
        tags = []
        for node_id in path.ids:
            if node_id == "company":
                tags.append("org:company")
            elif node_id in ("engineering", "finance", "product"):
                tags.append(f"org:{node_id}")
            else:
                # Heuristic: leaf nodes that appear after a division are teams/sub_teams
                tags.append(f"team:{node_id}")

        # Exception tags
        emp = employment_type.lower().strip()
        tags.append(f"exception:{emp}")
        tags.append("exception:all")

        return tags

    @staticmethod
    def _merge_accesses(nodes: list[_TeamNode], exception_profile) -> list[str]:
        """
        Concatenate all access requirements from company → leaf team.
        Prefix each entry with its level name for clarity in the prompt.
        Prepend any exception-specific constraints.
        """
        merged = []

        for node in nodes:
            if node.accesses:
                merged.append(f"[{node.name}]")
                for access in node.accesses:
                    merged.append(f"  • {access}")

        # Append exception-specific access adjustments
        if exception_profile.has_restrictions():
            merged.append(f"[{exception_profile.employment_type.upper()} — Access Differences]")
            merged.append(f"  • Jira: {exception_profile.jira_license}")
            merged.append(f"  • GitHub team: {exception_profile.github_org_team}")
            merged.append(f"  • AWS account: {exception_profile.aws_account}")
            for step in exception_profile.extra_steps:
                merged.append(f"  ⚠ {step}")

        return merged


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from interfaces import UserProfile

    # Example: contractor joining Infra Security
    user = UserProfile(
        name="Priya",
        team_name=sys.argv[1] if len(sys.argv) > 1 else "infra security",
        employment_type=sys.argv[2] if len(sys.argv) > 2 else "contractor",
        role_title="Software Engineer",
    )

    print(f"\nBuilding context for: {user.name} → {user.team_name} ({user.employment_type})")
    print("─" * 60)

    builder = ContextBuilder()
    ctx = builder.build(user)

    print(f"\nTeam path:  {ctx.team_path}")
    print(f"\nMemory tags fetched: {builder.get_tags_for_user(user)}")
    print(f"Memories retrieved: {len(ctx.memories)} (stub returns 0 until P2 is ready)")

    print(f"\nException notes ({len(ctx.exception_notes)} lines):")
    for line in ctx.exception_notes:
        print(f"  {line}")

    print(f"\nMerged access list ({len(ctx.raw_accesses)} entries):")
    for line in ctx.raw_accesses:
        print(f"  {line}")