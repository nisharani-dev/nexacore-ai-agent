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
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

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

logger = logging.getLogger(__name__)

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
    Hindsight HTTP adapter for self-hosted Hindsight API.
    
    Expected environment:
    - HINDSIGHT_BASE_URL: URL of your Hindsight instance
    - HINDSIGHT_API_KEY: API key (optional for self-hosted)
    - HINDSIGHT_PROJECT: Bank ID (defaults to "ramp-onboarding-demo")
    
    Actual API endpoints (v1/default/banks/{bank_id}/memories/...):
    - /recall (search/query memories)
    - /retain (write/create memories)
    - /list (list/count memories)
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("HINDSIGHT_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
        self.bank_id = os.getenv("HINDSIGHT_PROJECT", "ramp-onboarding-demo")
        
        # Use v1 API with banks structure
        self.search_path = os.getenv(
            "HINDSIGHT_SEARCH_PATH",
            f"/v1/default/banks/{self.bank_id}/memories/recall"
        )
        self.write_path = os.getenv(
            "HINDSIGHT_WRITE_PATH",
            f"/v1/default/banks/{self.bank_id}/memories/retain"
        )
        self.list_path = os.getenv(
            "HINDSIGHT_LIST_PATH",
            f"/v1/default/banks/{self.bank_id}/memories/list"
        )
        self.namespaces_path = os.getenv(
            "HINDSIGHT_NAMESPACES_PATH",
            f"/v1/default/banks/{self.bank_id}/memories"
        )
        self.health_path = os.getenv("HINDSIGHT_HEALTH_PATH", "/health")
        
        if not self.base_url:
            raise EnvironmentError(
                "Hindsight HTTP backend selected but HINDSIGHT_BASE_URL is missing."
            )
        
        logger.info(
            "Hindsight HTTP client initialized | base_url=%s | bank_id=%s",
            self.base_url,
            self.bank_id
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4))
    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = requests.request(
            method,
            self.base_url + path,
            headers=self._headers(),
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )
        response.raise_for_status()
        return response

    def healthcheck(self) -> dict[str, Any]:
        """Check if the Hindsight API is reachable and responding."""
        try:
            response = self._request("GET", self.health_path, timeout=5)
            payload = response.json() if response.content else {"status": "ok"}
            return {"status": "ok", "backend": "http", "details": payload}
        except requests.exceptions.HTTPError as exc:
            # If health endpoint doesn't exist (404), try a simple search
            if exc.response is not None and exc.response.status_code == 404:
                try:
                    # Try minimal search instead
                    response = self._request("POST", self.search_path, json={
                        "tags": [],
                        "query": "",
                        "limit": 1
                    }, timeout=5)
                    return {"status": "ok", "backend": "http", "details": {"via": "search"}}
                except Exception as search_exc:
                    return {"status": "degraded", "backend": "http", "error": f"Health check failed: {exc}, Search also failed: {search_exc}"}
            return {"status": "degraded", "backend": "http", "error": str(exc)}
        except Exception as exc:
            return {"status": "degraded", "backend": "http", "error": str(exc)}

    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        response = self._request("GET", self.namespaces_path)
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
        self._request("POST", self.namespaces_path, json=payload)

    def write_record(self, record: StoredMemoryRecord) -> StoredMemoryRecord:
        """
        Write memory using Hindsight's /retain endpoint.
        
        Hindsight expects:
        POST /v1/default/banks/{bank_id}/memories/retain
        {
            "content": "...",
            "tags": [...],
            "metadata": {...}
        }
        """
        payload = {
            "content": record.content,
            "tags": record.tags,
            "metadata": {
                "namespace": record.namespace,
                "level": record.level,
                "source": record.source,
                "relevance_score": record.relevance_score,
            }
        }
        
        try:
            response = self._request("POST", self.write_path, json=payload)
            data = response.json()
            
            # Hindsight returns the created memory
            if isinstance(data, dict) and data:
                # Try to extract the memory from response
                memory = data.get("memory", data.get("record", data))
                if "id" in memory:
                    record.id = memory["id"]
                if "created_at" in memory:
                    record.created_at = memory["created_at"]
            
            return record
        except Exception as e:
            logger.warning("Hindsight write failed: %s", e)
            return record

    def search_records(
        self,
        *,
        tags: list[str],
        query: str = "",
        limit: int = 10,
        namespace: str | None = None,
    ) -> list[StoredMemoryRecord]:
        """
        Search memories using Hindsight's /recall endpoint.
        
        Hindsight expects:
        POST /v1/default/banks/{bank_id}/memories/recall
        {
            "query": "search text",
            "top_k": 10,
            "filters": {...}
        }
        """
        payload = {
            "query": query or "",
            "top_k": limit,
        }
        
        # Add filters if we have tags or namespace
        if tags or namespace:
            filters = {}
            if namespace:
                filters["namespace"] = namespace
            if tags:
                filters["tags"] = normalize_tags(tags)
            payload["filters"] = filters
        
        try:
            response = self._request("POST", self.search_path, json=payload)
            data = response.json()
            
            # Hindsight returns {"memories": [...]} or similar
            records = data.get("memories", data.get("records", data if isinstance(data, list) else []))
            
            # Convert to our StoredMemoryRecord format
            result = []
            for record in records:
                # Try to match our schema, with fallbacks
                try:
                    result.append(StoredMemoryRecord(**record))
                except Exception:
                    # Create a basic record if format doesn't match
                    result.append(StoredMemoryRecord(
                        id=record.get("id", str(uuid4())),
                        content=record.get("content", record.get("text", "")),
                        tags=normalize_tags(record.get("tags", [])),
                        namespace=record.get("namespace", namespace or "default"),
                        level=record.get("level", "company"),
                        source=record.get("source", "hindsight"),
                        relevance_score=record.get("score", record.get("relevance_score", 0.0)),
                        created_at=record.get("created_at", utc_now_iso()),
                        updated_at=record.get("updated_at", utc_now_iso()),
                    ))
            return result
        except Exception as e:
            logger.warning("Hindsight search failed: %s", e)
            return []

    def reset(self) -> None:
        reset_path = os.getenv("HINDSIGHT_RESET_PATH", "/records/reset")
        try:
            self._request("POST", reset_path)
        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                return
            raise

    def count_records(self) -> int:
        """
        Count total records using Hindsight's /list endpoint.
        
        Hindsight API:
        GET /v1/default/banks/{bank_id}/memories/list
        """
        try:
            response = self._request("GET", self.list_path, timeout=5)
            data = response.json()
            
            # Check various possible count fields
            if "total" in data:
                return int(data["total"])
            if "count" in data:
                return int(data["count"])
            
            # If response contains memories array, count them
            memories = data.get("memories", data.get("records", []))
            if isinstance(memories, list):
                return len(memories)
                
            return 0
        except Exception as e:
            logger.warning("Unable to count records from Hindsight API: %s", e)
            return 0

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        # API key is optional for self-hosted Hindsight
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class HindsightClient:
    def __init__(self, store_path: str | Path | None = None) -> None:
        self.project = os.getenv("HINDSIGHT_PROJECT", "ramp-onboarding-demo")
        self.backend_kind = hindsight_backend()
        
        # Force local backend if explicitly set
        if self.backend_kind == "local":
            logger.info("Using local Hindsight backend (file-based storage)")
            self._store = LocalJsonMemoryStore(store_path=store_path)
        elif self.backend_kind == "http":
            base_url = os.getenv("HINDSIGHT_BASE_URL", "").rstrip("/")
            api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
            
            if not base_url or not api_key:
                logger.warning(
                    "HINDSIGHT_BACKEND=http but HINDSIGHT_BASE_URL or HINDSIGHT_API_KEY "
                    "is missing; falling back to local store"
                )
                self.backend_kind = "local"
                self._store = LocalJsonMemoryStore(store_path=store_path)
            else:
                # Try to use official SDK if this looks like the cloud API
                if "api.hindsight.vectorize.io" in base_url:
                    try:
                        from backend.memory.hindsight_sdk_adapter import HindsightSDKStore
                        logger.info("Using official Hindsight SDK for cloud API")
                        self._store: BaseMemoryStore = HindsightSDKStore()
                        
                        # Test connectivity
                        health = self._store.healthcheck()
                        if health.get("status") != "ok":
                            logger.warning(
                                "Hindsight SDK health check failed: %s - falling back to local",
                                health
                            )
                            self.backend_kind = "local"
                            self._store = LocalJsonMemoryStore(store_path=store_path)
                    except ImportError:
                        logger.warning(
                            "hindsight-client package not installed, using HTTP adapter. "
                            "Install with: pip install hindsight-client"
                        )
                        self._store = self._create_http_store(base_url, api_key)
                    except Exception as e:
                        logger.warning(
                            "Failed to initialize Hindsight SDK: %s - falling back to local",
                            e
                        )
                        self.backend_kind = "local"
                        self._store = LocalJsonMemoryStore(store_path=store_path)
                else:
                    # Use HTTP adapter for self-hosted instances
                    logger.info("Using HTTP adapter for self-hosted Hindsight")
                    self._store = self._create_http_store(base_url, api_key)
        else:
            logger.warning("Unknown HINDSIGHT_BACKEND=%s, using local", self.backend_kind)
            self.backend_kind = "local"
            self._store = LocalJsonMemoryStore(store_path=store_path)
        
        self._db = AppDatabase.get()
    
    def _create_http_store(self, base_url: str, api_key: str) -> BaseMemoryStore:
        """Create HTTP store with health check and fallback."""
        try:
            store = HindsightHttpMemoryStore()
            health = store.healthcheck()
            if health.get("status") != "ok":
                logger.warning(
                    "Hindsight HTTP backend health check failed: %s - falling back to local",
                    health
                )
                self.backend_kind = "local"
                return LocalJsonMemoryStore()
            return store
        except Exception as e:
            logger.warning(
                "Failed to initialize Hindsight HTTP backend: %s - falling back to local",
                e
            )
            self.backend_kind = "local"
            return LocalJsonMemoryStore()

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
