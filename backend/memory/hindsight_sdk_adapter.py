"""
hindsight_sdk_adapter.py
-------------------------
Adapter for the official Hindsight Python SDK.

Uses the hindsight-client package to interact with the cloud API at
https://api.hindsight.vectorize.io
"""

from __future__ import annotations

import logging
import os
from typing import Any
from uuid import uuid4

from hindsight_client import Hindsight
from hindsight_client.types import Memory

from backend.interfaces import MemoryItem
from config.memory_schema import StoredMemoryRecord, normalize_tags, utc_now_iso

logger = logging.getLogger(__name__)


class HindsightSDKStore:
    """
    Wrapper around the official Hindsight SDK.
    
    Environment variables:
    - HINDSIGHT_BASE_URL: API endpoint (defaults to https://api.hindsight.vectorize.io)
    - HINDSIGHT_API_KEY: Your API key
    - HINDSIGHT_PROJECT: Bank ID (defaults to "default")
    """
    
    def __init__(self) -> None:
        self.base_url = os.getenv(
            "HINDSIGHT_BASE_URL",
            "https://api.hindsight.vectorize.io"
        ).rstrip("/")
        self.api_key = os.getenv("HINDSIGHT_API_KEY", "").strip()
        self.bank_id = os.getenv("HINDSIGHT_PROJECT", "default")
        
        if not self.api_key:
            raise EnvironmentError(
                "HINDSIGHT_API_KEY environment variable is required for cloud Hindsight"
            )
        
        # Initialize the official SDK client
        self.client = Hindsight(
            base_url=self.base_url,
            api_key=self.api_key
        )
        
        logger.info(
            "Hindsight SDK initialized | base_url=%s | bank_id=%s",
            self.base_url,
            self.bank_id
        )
    
    def healthcheck(self) -> dict[str, Any]:
        """Check if Hindsight API is accessible."""
        try:
            # Try a simple recall to test connectivity (SDK doesn't support top_k yet)
            results = self.client.recall(bank_id=self.bank_id, query="test")
            return {"status": "ok", "backend": "hindsight-sdk"}
        except Exception as e:
            logger.warning("Hindsight SDK healthcheck failed: %s", e)
            return {"status": "degraded", "backend": "hindsight-sdk", "error": str(e)}
    
    def write_record(self, record: StoredMemoryRecord) -> StoredMemoryRecord:
        """
        Write a memory using Hindsight SDK's retain() method.
        
        Maps StoredMemoryRecord to Hindsight's Memory format.
        Note: SDK's retain() only accepts content parameter, not metadata.
        """
        try:
            # Use the SDK's retain method (only content parameter supported)
            memory = self.client.retain(
                bank_id=self.bank_id,
                content=record.content
            )
            
            # Update record with returned ID if available
            if hasattr(memory, 'id') and memory.id:
                record.id = str(memory.id)
            
            logger.info("Memory written via SDK | content_length=%d | id=%s", len(record.content), record.id)
            return record
            
        except Exception as e:
            logger.exception("Failed to write memory via SDK: %s", e)
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
        Search memories using Hindsight SDK's recall() method.
        
        Converts Hindsight's RecallResult objects back to StoredMemoryRecord.
        """
        try:
            # Use the SDK's recall method (note: SDK doesn't support top_k parameter)
            results = self.client.recall(
                bank_id=self.bank_id,
                query=query or "general information"  # SDK requires meaningful query
            )
            
            # Convert RecallResult objects to StoredMemoryRecord
            records = []
            for result in results[:limit]:  # Limit results client-side
                # RecallResult has: memory (Memory object) and score
                memory = result.memory if hasattr(result, 'memory') else result
                score = result.score if hasattr(result, 'score') else 0.0
                
                # Extract content - SDK uses 'text' not 'content'
                content = ""
                if hasattr(memory, 'text'):
                    content = memory.text
                elif hasattr(memory, 'content'):
                    content = memory.content
                else:
                    content = str(memory)
                
                # Get metadata if available
                metadata = memory.metadata if hasattr(memory, 'metadata') and memory.metadata else {}
                
                # Filter by tags if specified
                if tags:
                    memory_tags = metadata.get("tags", [])
                    if isinstance(memory_tags, str):
                        memory_tags = [memory_tags]
                    if not any(tag in memory_tags for tag in tags):
                        continue
                
                # Filter by namespace if specified
                if namespace:
                    memory_namespace = metadata.get("namespace", "")
                    if memory_namespace != namespace:
                        continue
                
                # Create StoredMemoryRecord
                record = StoredMemoryRecord(
                    id=str(memory.id) if hasattr(memory, 'id') and memory.id else str(uuid4()),
                    content=content,
                    tags=normalize_tags(metadata.get("tags", [])),
                    namespace=metadata.get("namespace", "default"),
                    level=metadata.get("level", "company"),
                    source=metadata.get("source", "hindsight"),
                    relevance_score=float(score),
                    created_at=str(memory.created_at) if hasattr(memory, 'created_at') else utc_now_iso(),
                    updated_at=utc_now_iso(),
                )
                records.append(record)
            
            logger.info("Memory search via SDK | query=%s | results=%d", query[:50], len(records))
            return records
            
        except Exception as e:
            logger.exception("Failed to search memories via SDK: %s", e)
            return []
    
    def count_records(self) -> int:
        """
        Count total memories (approximate via search).
        
        Note: SDK doesn't have a dedicated count method,
        so we do a broad search and count results.
        """
        try:
            # SDK doesn't support top_k parameter yet
            results = self.client.recall(
                bank_id=self.bank_id,
                query="*"
            )
            return len(results)
        except Exception as e:
            logger.warning("Failed to count memories via SDK: %s", e)
            return 0
    
    def list_namespaces(self) -> dict[str, dict[str, Any]]:
        """
        List namespaces (not directly supported by SDK).
        
        Returns empty dict as SDK doesn't expose namespace management.
        """
        logger.warning("list_namespaces not supported by Hindsight SDK")
        return {}
    
    def ensure_namespace(
        self,
        namespace: str,
        *,
        level: str,
        scope_id: str,
        tags: list[str] | None = None,
    ) -> None:
        """
        Ensure namespace exists (no-op for SDK).
        
        Hindsight SDK manages namespaces automatically via metadata.
        """
        pass
    
    def reset(self) -> None:
        """Reset all memories (not supported by SDK)."""
        logger.warning("reset not supported by Hindsight SDK")
    
    def backend_summary(self) -> dict[str, Any]:
        """Return summary of backend configuration."""
        return {
            "backend": "hindsight-sdk",
            "base_url": self.base_url,
            "bank_id": self.bank_id,
            "metadata": {
                "total": self.count_records()
            }
        }
