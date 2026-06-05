"""
writer.py
---------
Extracts durable memories from each interaction and writes them back to the
Hindsight layer with stable tags.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.interfaces import MemoryItem, TeamPath, UserProfile
from backend.memory.hindsight_client import HindsightClient


@dataclass
class InteractionMemoryResult:
    memories: list[MemoryItem]
    written_count: int


class MemoryWriter:
    def __init__(self, client: HindsightClient | None = None) -> None:
        self.client = client or HindsightClient()

    def write_interaction(
        self,
        *,
        user: UserProfile,
        team_path: TeamPath,
        user_query: str,
        assistant_response: str,
        suggested_actions: list[str] | None = None,
        session_id: str | None = None,
    ) -> InteractionMemoryResult:
        tags = self._build_tags(team_path, user.employment_type)
        memories = self.extract_memories(
            user=user,
            team_path=team_path,
            user_query=user_query,
            assistant_response=assistant_response,
            base_tags=tags,
            suggested_actions=suggested_actions or [],
        )
        if not memories:
            return InteractionMemoryResult(memories=[], written_count=0)

        metadata = {
            "user_name": user.name,
            "team_name": user.team_name,
            "employment_type": user.employment_type,
            "session_id": session_id or "",
        }
        self.client.write_many(memories, metadata=metadata)
        return InteractionMemoryResult(memories=memories, written_count=len(memories))

    def extract_memories(
        self,
        *,
        user: UserProfile,
        team_path: TeamPath,
        user_query: str,
        assistant_response: str,
        base_tags: list[str],
        suggested_actions: list[str],
    ) -> list[MemoryItem]:
        query_lower = user_query.lower()
        answer_lower = assistant_response.lower()
        combined = f"{user_query.strip()} {assistant_response.strip()}".strip()
        if not combined:
            return []

        candidates: list[MemoryItem] = []

        if _looks_like_blocker(query_lower, answer_lower):
            summary = _summarize_blocker(user_query, assistant_response)
            candidates.append(
                MemoryItem(
                    content=summary,
                    tags=base_tags,
                    level="exception" if user.employment_type != "fte" else "team",
                    source="interaction",
                    relevance_score=0.95,
                )
            )

        action_memory = _summarize_actions(suggested_actions)
        if action_memory:
            candidates.append(
                MemoryItem(
                    content=action_memory,
                    tags=base_tags,
                    level="team",
                    source="interaction",
                    relevance_score=0.7,
                )
            )

        if not candidates and _looks_like_reusable_guidance(query_lower, answer_lower):
            candidates.append(
                MemoryItem(
                    content=_summarize_guidance(user, team_path, assistant_response),
                    tags=base_tags,
                    level="team",
                    source="interaction",
                    relevance_score=0.6,
                )
            )

        return _dedupe_memories(candidates)

    @staticmethod
    def _build_tags(team_path: TeamPath, employment_type: str) -> list[str]:
        tags: list[str] = []
        for index, node_id in enumerate(team_path.ids):
            if node_id == "company":
                tags.append("org:company")
            elif index == 1:
                tags.append(f"org:{node_id}")
            else:
                tags.append(f"team:{node_id}")

        emp = employment_type.lower().strip()
        tags.append(f"exception:{emp}")
        tags.append("exception:all")
        return tags


def _looks_like_blocker(query_lower: str, answer_lower: str) -> bool:
    keywords = (
        "blocker",
        "stuck",
        "pending",
        "delayed",
        "cannot access",
        "can't access",
        "fix",
        "workaround",
        "escalat",
    )
    return any(keyword in query_lower or keyword in answer_lower for keyword in keywords)


def _looks_like_reusable_guidance(query_lower: str, answer_lower: str) -> bool:
    return any(
        phrase in query_lower or phrase in answer_lower
        for phrase in ("day 1", "first day", "onboarding", "request", "access", "training")
    )


def _summarize_blocker(user_query: str, assistant_response: str) -> str:
    blocker = _clean_sentence(user_query)
    resolution = _clean_sentence(assistant_response)
    return f"KNOWN BLOCKER: {blocker} | BEST NEXT STEP: {resolution}"


def _summarize_actions(actions: list[str]) -> str:
    if not actions:
        return ""
    joined = "; ".join(action.strip() for action in actions if action.strip())
    return f"ACTION PATTERN: When this issue appears, the agent used: {joined}"


def _summarize_guidance(user: UserProfile, team_path: TeamPath, assistant_response: str) -> str:
    team_name = team_path.names[-1] if team_path.names else user.team_name
    return (
        f"REUSABLE GUIDANCE for {team_name} ({user.employment_type}): "
        f"{_clean_sentence(assistant_response)}"
    )


def _clean_sentence(value: str, limit: int = 280) -> str:
    compact = " ".join(value.split())
    return compact[:limit].rstrip()


def _dedupe_memories(memories: list[MemoryItem]) -> list[MemoryItem]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    deduped: list[MemoryItem] = []
    for memory in memories:
        fingerprint = (memory.content, tuple(sorted(memory.tags)))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(memory)
    return deduped
