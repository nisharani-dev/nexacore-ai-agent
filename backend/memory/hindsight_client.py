"""
hindsight_client.py
-------------------
Pluggable memory backend facade.

Supported backends:
- `local`: file-backed store for reliable local/dev/demo usage
- `http`: scaffold for a future managed Hindsight cloud API
"""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import requests

from backend.db import AppDatabase
from backend.interfaces import MemoryItem
from backend.runtime_paths import hindsight_store_path
from backend.settings import hindsight_backend
from config.memory_schema import (
    COMPANY_NAMESPACE,
    NamespaceDescriptor,
    StoredMemoryRecord,
    build_namespace_descriptors,
    infer_primary_namespace,
    normalize_tags,
    utc_now_iso,
)


DEFAULT_STORE_PATH = hindsight_store_path()


class BaseMemoryStore(ABC):
    @abstractmethod
    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def ensure_namespace(
        self,
        namespace: str,
        *,
        level: str,
        scope_id: str,
        tags: list[str] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_record(self, record: StoredMemoryRecord) -> StoredMemoryRecord:
        raise NotImplementedError

    @abstractmethod
    def search_records(
        self,
        *,
        tags: list[str],
        query: str = "",
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[StoredMemoryRecord]:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def count_records(self) -> int:
        raise NotImplementedError


class LocalJsonMemoryStore(BaseMemoryStore):
    _lock = Lock()

    def __init__(self, store_path: str | Path | None = None) -> None:
        self.store_path = Path(store_path) if store_path else DEFAULT_STORE_PATH
        self.project = os.getenv("HINDSIGHT_PROJECT", "ramp-onboarding-demo")
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_store()

    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        return self._load_store()["namespaces"]

    def ensure_namespace(
        self,
        namespace: str,
        *,
        level: str,
        scope_id: str,
        tags: list[str] | None = None,
    ) -> None:
        store = self._load_store()
        namespaces = store["namespaces"]
        if namespace not in namespaces:
            namespaces[namespace] = {
                "level": level,
                "scope_id": scope_id,
                "tags": normalize_tags(tags or []),
                "project": self.project,
                "created_at": utc_now_iso(),
            }
            self._save_store(store)

    def write_record(self, record: StoredMemoryRecord) -> StoredMemoryRecord:
        store = self._load_store()
        existing = self._find_existing_record(store, record)
        if existing:
            existing["updated_at"] = utc_now_iso()
            existing["metadata"] = record.metadata
            existing["relevance_score"] = record.relevance_score
            self._save_store(store)
            return StoredMemoryRecord(**existing)

        store["records"].append(record.to_dict())
        self._save_store(store)
        return record

    def search_records(
        self,
        *,
        tags: list[str],
        query: str = "",
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[StoredMemoryRecord]:
        normalized_tags = set(normalize_tags(tags))
        query_terms = _tokenize(query)

        matches: list[tuple[float, StoredMemoryRecord]] = []
        for raw_record in self._load_store()["records"]:
            record = StoredMemoryRecord(**raw_record)
            if namespace and record.namespace != namespace:
                continue

            record_tags = set(record.tags)
            tag_overlap = len(normalized_tags & record_tags)
            if normalized_tags and tag_overlap == 0:
                continue

            score = float(tag_overlap * 4)
            if query_terms:
                content_terms = _tokenize(record.content)
                score += len(query_terms & content_terms) * 2

            score += record.relevance_score
            score += len(record.tags) * 0.05
            matches.append((score, record))

        matches.sort(key=lambda pair: pair[0], reverse=True)
        return [record for _, record in matches[:limit]]

    def reset(self) -> None:
        self._save_store({"namespaces": {}, "records": []})

    def count_records(self) -> int:
        return len(self._load_store()["records"])

    def _ensure_store(self) -> None:
        if self.store_path.exists():
            return
        self._save_store({"namespaces": {}, "records": []})

    def _load_store(self) -> dict[str, Any]:
        with self._lock:
            with self.store_path.open("r", encoding="utf-8") as handle:
                raw = handle.read().strip()
                if not raw:
                    return {"namespaces": {}, "records": []}
                return json.loads(raw)

    def _save_store(self, payload: dict[str, Any]) -> None:
        with self._lock:
            temp_path = self.store_path.with_name(f"{self.store_path.name}.{uuid4().hex}.tmp")
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=True)
            os.replace(temp_path, self.store_path)

    @staticmethod
    def _find_existing_record(store: dict[str, Any], record: StoredMemoryRecord) -> dict[str, Any] | None:
        for raw_record in store["records"]:
            if raw_record["content"] == record.content and raw_record["tags"] == record.tags:
                return raw_record
        return None


class HindsightHttpMemoryStore(BaseMemoryStore):
    """
    Generic HTTP adapter scaffold.

    Expected environment:
    - HINDSIGHT_BASE_URL
    - HINDSIGHT_API_KEY
    - optional endpoint paths:
      - HINDSIGHT_SEARCH_PATH
      - HINDSIGHT_WRITE_PATH
      - HINDSIGHT_NAMESPACES_PATH
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("HINDSIGHT_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
        self.search_path = os.getenv("HINDSIGHT_SEARCH_PATH", "/search")
        self.write_path = os.getenv("HINDSIGHT_WRITE_PATH", "/records")
        self.namespaces_path = os.getenv("HINDSIGHT_NAMESPACES_PATH", "/namespaces")
        if not self.base_url or not self.api_key:
            raise EnvironmentError(
                "Hindsight HTTP backend selected but HINDSIGHT_BASE_URL or HINDSIGHT_API_KEY is missing."
            )

    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        response = requests.get(self.base_url + self.namespaces_path, headers=self._headers(), timeout=30)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data.get("namespaces", data)
        return {}

    def ensure_namespace(
        self,
        namespace: str,
        *,
        level: str,
        scope_id: str,
        tags: list[str] | None = None,
    ) -> None:
        payload = {
            "namespace": namespace,
            "level": level,
            "scope_id": scope_id,
            "tags": normalize_tags(tags or []),
        }
        response = requests.post(
            self.base_url + self.namespaces_path,
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

    def write_record(self, record: StoredMemoryRecord) -> StoredMemoryRecord:
        response = requests.post(
            self.base_url + self.write_path,
            headers=self._headers(),
            json=record.to_dict(),
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload:
            return StoredMemoryRecord(**payload.get("record", payload))
        return record

    def search_records(
        self,
        *,
        tags: list[str],
        query: str = "",
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[StoredMemoryRecord]:
        payload = {
            "tags": normalize_tags(tags),
            "query": query,
            "limit": limit,
            "namespace": namespace,
        }
        response = requests.post(
            self.base_url + self.search_path,
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        records = data.get("records", data if isinstance(data, list) else [])
        return [StoredMemoryRecord(**record) for record in records]

    def reset(self) -> None:
        reset_path = os.getenv("HINDSIGHT_RESET_PATH", "/records/reset")
        response = requests.post(
            self.base_url + reset_path,
            headers=self._headers(),
            timeout=30,
        )
        if response.status_code in {200, 204, 404}:
            return
        response.raise_for_status()

    def count_records(self) -> int:
        response = requests.get(self.base_url + self.search_path, headers=self._headers(), timeout=30)
        response.raise_for_status()
        data = response.json()
        return int(data.get("count", 0))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


class HindsightClient:
    def __init__(self, store_path: str | Path | None = None) -> None:
        self.project = os.getenv("HINDSIGHT_PROJECT", "ramp-onboarding-demo")
        self.backend_kind = hindsight_backend()
        if self.backend_kind == "http":
            self._store: BaseMemoryStore = HindsightHttpMemoryStore()
        else:
            self.backend_kind = "local"
            self._store = LocalJsonMemoryStore(store_path=store_path)
        self._db = AppDatabase.get()

    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        return self._store.list_namespaces()

    def ensure_namespace(
        self,
        namespace: str,
        *,
        level: str,
        scope_id: str,
        tags: list[str] | None = None,
    ) -> None:
        self._store.ensure_namespace(namespace, level=level, scope_id=scope_id, tags=tags)

    def ensure_namespaces_for_tags(self, tags: list[str]) -> list[NamespaceDescriptor]:
        descriptors = build_namespace_descriptors(tags)
        if not descriptors:
            self.ensure_namespace(
                COMPANY_NAMESPACE,
                level="company",
                scope_id="company",
                tags=["org:company"],
            )
            return []

        for descriptor in descriptors:
            self.ensure_namespace(
                descriptor.namespace,
                level=descriptor.level,
                scope_id=descriptor.scope_id,
                tags=[descriptor.tag],
            )
        return descriptors

    def write(
        self,
        item: MemoryItem,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> StoredMemoryRecord:
        descriptors = self.ensure_namespaces_for_tags(item.tags)
        namespace = infer_primary_namespace(item.tags)
        record_metadata = dict(metadata or {})
        if descriptors:
            record_metadata["namespace_lineage"] = [descriptor.namespace for descriptor in descriptors]

        record = StoredMemoryRecord.from_memory_item(
            item,
            namespace=namespace,
            metadata=record_metadata,
        )
        persisted = self._store.write_record(record)
        self._db.upsert_memory_metadata(
            memory_id=persisted.id,
            namespace=persisted.namespace,
            content_hash=_content_hash(persisted.content, persisted.tags),
            level=persisted.level,
            source=persisted.source,
            tags=persisted.tags,
            metadata=persisted.metadata,
            backend_kind=self.backend_kind,
        )
        return persisted

    def write_many(
        self,
        items: list[MemoryItem],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[StoredMemoryRecord]:
        return [self.write(item, metadata=metadata) for item in items]

    def search(
        self,
        *,
        tags: list[str],
        query: str = "",
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[StoredMemoryRecord]:
        return self._store.search_records(
            tags=tags,
            query=query,
            limit=limit,
            namespace=namespace,
        )

    def reset(self) -> None:
        self._store.reset()

    def count_records(self) -> int:
        return self._store.count_records()

    def backend_summary(self) -> dict[str, Any]:
        return {
            "backend_kind": self.backend_kind,
            "project": self.project,
            "metadata": self._db.memory_metadata_summary(),
        }


def _content_hash(content: str, tags: list[str]) -> str:
    payload = content + "|" + "|".join(sorted(tags))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tokenize(value: str) -> set[str]:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in value)
    return {token for token in cleaned.split() if len(token) > 2}
