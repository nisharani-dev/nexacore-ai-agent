"""
retriever.py
------------
Retrieves memories across all relevant Hindsight namespaces for a user's path.
"""

from __future__ import annotations

from backend.interfaces import MemoryItem
from backend.memory.hindsight_client import HindsightClient
from config.memory_schema import build_namespace_descriptors, normalize_tags


def fetch_memories(
    tags: list[str],
    query: str = "",
    *,
    limit: int = 16,
    per_namespace_limit: int = 6,
    client: HindsightClient | None = None,
) -> list[MemoryItem]:
    hindsight = client or HindsightClient()
    normalized_tags = normalize_tags(tags)
    descriptors = build_namespace_descriptors(normalized_tags)

    collected: list[MemoryItem] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    if not descriptors:
        return [
            record.to_memory_item()
            for record in hindsight.search(tags=normalized_tags, query=query, limit=limit)
        ]

    for descriptor in sorted(descriptors, key=lambda item: item.priority):
        records = hindsight.search(
            tags=[descriptor.tag],
            query=query,
            limit=per_namespace_limit,
        )
        for record in records:
            item = record.to_memory_item()
            fingerprint = (item.content, tuple(sorted(item.tags)))
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            item.relevance_score = _score_memory(
                item,
                normalized_tags,
                query,
                descriptor.priority,
                exact_namespace_match=(record.namespace == descriptor.namespace),
            )
            collected.append(item)

    collected.sort(key=lambda item: item.relevance_score, reverse=True)
    return collected[:limit]


def apply_demo_mode(memories: list[MemoryItem], demo_mode: str | None) -> list[MemoryItem]:
    if demo_mode == "person1":
        generic = [
            memory for memory in memories
            if memory.level in {"company", "division", "team"}
            and "known blocker" not in memory.content.lower()
            and "exception:" not in ",".join(memory.tags)
        ]
        if generic:
            return generic[:4]
        return memories[:2]
    return memories


def fetch_person1_demo_memories(client: HindsightClient | None = None) -> list[MemoryItem]:
    hindsight = client or HindsightClient()
    records = hindsight.search(tags=["org:company", "org:engineering"], query="", limit=12)
    memories = [record.to_memory_item() for record in records]
    generic = [
        memory for memory in memories
        if "known blocker" not in memory.content.lower()
        and not any(tag.startswith("exception:") for tag in memory.tags)
    ]
    return generic[:4]


def _score_memory(
    item: MemoryItem,
    request_tags: list[str],
    query: str,
    namespace_priority: int,
    exact_namespace_match: bool,
) -> float:
    tag_overlap = len(set(item.tags) & set(request_tags))
    score = item.relevance_score
    score += namespace_priority * 0.6
    score += tag_overlap * 1.5

    if query:
        query_terms = _tokenize(query)
        content_terms = _tokenize(item.content)
        score += len(query_terms & content_terms) * 0.75

    if "known blocker" in item.content.lower():
        score += 1.25
    if item.level == "exception":
        score += 0.5
    if exact_namespace_match:
        score += 0.4
    return score


def _tokenize(value: str) -> set[str]:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in value)
    return {token for token in cleaned.split() if len(token) > 2}
