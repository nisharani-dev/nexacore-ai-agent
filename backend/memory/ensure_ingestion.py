"""
ensure_ingestion.py
-------------------
Idempotent startup hook for Confluence/GDocs mock ingestion.
"""

from __future__ import annotations

from backend.memory.hindsight_client import HindsightClient


def ensure_ingestion_data(*, dry_run: bool = False) -> dict[str, int]:
    hindsight = HindsightClient()
    has_confluence = bool(hindsight.search(tags=["seed:confluence"], limit=1))
    has_gdocs = bool(hindsight.search(tags=["seed:gdocs"], limit=1))
    if has_confluence and has_gdocs:
        return {"confluence": 0, "gdocs": 0}

    from backend.ingestion.confluence_ingest import ingest_confluence
    from backend.ingestion.gdocs_ingest import ingest_gdocs

    summary: dict[str, int] = {"confluence": 0, "gdocs": 0}
    if not has_confluence:
        summary["confluence"] = len(ingest_confluence(dry_run=dry_run))
    if not has_gdocs:
        summary["gdocs"] = len(ingest_gdocs(dry_run=dry_run))
    return summary
