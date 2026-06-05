"""
memory_schema.py
----------------
Shared schema helpers for the Hindsight-backed memory layer.

Person 2 owns this contract. The rest of the backend can treat these helpers as
the single source of truth for:
  - namespace conventions
  - tag normalisation
  - stored memory record shape
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.interfaces import MemoryItem


COMPANY_NAMESPACE = "company/global"
KNOWN_DIVISION_IDS = {"engineering", "finance", "product"}
LEVEL_PRIORITY = {
    "company": 1,
    "division": 2,
    "org": 2,
    "team": 3,
    "sub_team": 4,
    "exception": 5,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_identifier(value: str) -> str:
    return (
        value.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )


def normalize_tags(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        clean = normalize_identifier(tag.replace(":", "_")).replace("_", ":", 1)
        if clean not in seen:
            seen.add(clean)
            normalized.append(clean)
    return normalized


@dataclass(frozen=True)
class NamespaceDescriptor:
    level: str
    scope_id: str
    tag: str
    namespace: str
    priority: int


@dataclass
class StoredMemoryRecord:
    id: str
    namespace: str
    content: str
    tags: list[str]
    level: str
    source: str
    relevance_score: float
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_memory_item(
        cls,
        item: MemoryItem,
        *,
        namespace: str,
        metadata: dict[str, Any] | None = None,
    ) -> "StoredMemoryRecord":
        return cls(
            id=str(uuid4()),
            namespace=namespace,
            content=item.content.strip(),
            tags=normalize_tags(item.tags),
            level=item.level or infer_level_from_tags(item.tags),
            source=item.source or "interaction",
            relevance_score=item.relevance_score or 0.5,
            metadata=metadata or {},
        )

    def to_memory_item(self) -> MemoryItem:
        return MemoryItem(
            content=self.content,
            tags=list(self.tags),
            level=self.level,
            source=self.source,
            relevance_score=self.relevance_score,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_level_from_tags(tags: list[str]) -> str:
    descriptors = build_namespace_descriptors(tags)
    if not descriptors:
        return "company"
    return max(descriptors, key=lambda descriptor: descriptor.priority).level


def infer_primary_namespace(tags: list[str]) -> str:
    descriptors = build_namespace_descriptors(tags)
    if not descriptors:
        return COMPANY_NAMESPACE
    return max(descriptors, key=lambda descriptor: descriptor.priority).namespace


def build_namespace_descriptors(tags: list[str]) -> list[NamespaceDescriptor]:
    descriptors: list[NamespaceDescriptor] = []
    for raw_tag in normalize_tags(tags):
        if ":" not in raw_tag:
            continue
        prefix, value = raw_tag.split(":", 1)
        if prefix == "org" and value == "company":
            descriptors.append(
                NamespaceDescriptor(
                    level="company",
                    scope_id="company",
                    tag=raw_tag,
                    namespace=COMPANY_NAMESPACE,
                    priority=LEVEL_PRIORITY["company"],
                )
            )
        elif prefix == "org":
            descriptors.append(
                NamespaceDescriptor(
                    level="division",
                    scope_id=value,
                    tag=raw_tag,
                    namespace=f"org/{value}",
                    priority=LEVEL_PRIORITY["division"],
                )
            )
        elif prefix == "team":
            level = "team" if value not in KNOWN_DIVISION_IDS else "division"
            descriptors.append(
                NamespaceDescriptor(
                    level=level,
                    scope_id=value,
                    tag=raw_tag,
                    namespace=f"team/{value}",
                    priority=LEVEL_PRIORITY[level],
                )
            )
        elif prefix == "subteam":
            descriptors.append(
                NamespaceDescriptor(
                    level="sub_team",
                    scope_id=value,
                    tag=raw_tag,
                    namespace=f"team/{value}",
                    priority=LEVEL_PRIORITY["sub_team"],
                )
            )
        elif prefix == "exception":
            descriptors.append(
                NamespaceDescriptor(
                    level="exception",
                    scope_id=value,
                    tag=raw_tag,
                    namespace=f"exception/{value}",
                    priority=LEVEL_PRIORITY["exception"],
                )
            )
    return descriptors
