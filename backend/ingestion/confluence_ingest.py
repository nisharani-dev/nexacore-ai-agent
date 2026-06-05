"""
confluence_ingest.py  —  Person 4 (Ingestion + Actions)
---------------------------------------------------------
Reads mock Confluence pages from mock_data/confluence_pages.json
and writes each item into Hindsight memory via hindsight_client.

What is "ingestion"?
    Before any employee uses the agent, the agent needs some base knowledge
    to start from. This script "loads the library" — it reads our fake
    Confluence docs and stores each bullet point as a MemoryItem in Hindsight.
    
    After this runs, Person 2's retriever can fetch these memories when
    a new employee joins.

Tag format (agreed with P3's context_builder.py):
    org:company, org:engineering, team:platform, team:infra_security, etc.
    These match exactly what context_builder._build_tags() produces,
    so retrieval always finds what ingestion wrote.

Usage:
    python confluence_ingest.py
    python confluence_ingest.py --dry-run   # prints without writing
"""

import sys
import json
import argparse
from pathlib import Path

# Allow imports from backend/ root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interfaces import MemoryItem

# ── Path to mock data ─────────────────────────────────────────────────────────
MOCK_DATA_PATH = Path(__file__).resolve().parents[2] / "mock_data" / "confluence_pages.json"


# ── Hindsight client (stub until P2 ships hindsight_client.py) ────────────────

def _write_memory(item: MemoryItem, dry_run: bool = False):
    """
    Writes a single MemoryItem to Hindsight.

    When P2 ships memory/hindsight_client.py, replace the stub body with:
        from memory.hindsight_client import HindsightClient
        client = HindsightClient()
        client.write(item)

    The MemoryItem shape is defined in interfaces.py — we already match it.
    """
    if dry_run:
        print(f"  [DRY RUN] Would write → tags={item.tags} | {item.content[:80]}...")
        return

    # ── Real call goes here once P2 is ready ──────────────────────────────────
    try:
        from memory.hindsight_client import HindsightClient  # type: ignore
        client = HindsightClient()
        client.write(item)
    except ImportError:
        # P2 not ready yet — just print so we know it's working
        print(f"  [STUB WRITE] tags={item.tags} | {item.content[:80]}")


# ── Core ingestion logic ──────────────────────────────────────────────────────

def ingest_confluence(mock_path: Path = MOCK_DATA_PATH, dry_run: bool = False) -> list[MemoryItem]:
    """
    Reads confluence_pages.json and converts each item into a MemoryItem,
    then writes it to Hindsight.

    Returns the list of MemoryItems created (useful for testing).
    """
    if not mock_path.exists():
        raise FileNotFoundError(f"Mock data not found at: {mock_path}")

    with open(mock_path, "r") as f:
        pages = json.load(f)

    written: list[MemoryItem] = []

    for page in pages:
        print(f"\n[Confluence] Ingesting: '{page['title']}' (tag: {page['tag']})")

        for item_text in page["items"]:
            memory = MemoryItem(
                content=item_text,
                tags=[page["tag"], "org:company"],  # always include company tag too
                level=page["level"],
                source="confluence_ingestion",
                relevance_score=1.0,               # ingested data = high relevance baseline
            )
            _write_memory(memory, dry_run=dry_run)
            written.append(memory)

    print(f"\n✓ Confluence ingestion complete — {len(written)} memory items processed.")
    return written


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest mock Confluence pages into Hindsight")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing to Hindsight")
    args = parser.parse_args()

    ingest_confluence(dry_run=args.dry_run)