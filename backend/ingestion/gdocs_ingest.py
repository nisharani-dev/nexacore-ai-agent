"""
gdocs_ingest.py  —  Person 4 (Ingestion + Actions)
----------------------------------------------------
Reads mock Google Docs pages from mock_data/gdocs_pages.json
and writes each item into Hindsight memory via hindsight_client.

Identical pattern to confluence_ingest.py — same tag format,
same MemoryItem shape, same Hindsight write call.
We keep them as separate files so in a real product you'd swap
each one independently (Confluence API vs Google Docs API).

Usage:
    python gdocs_ingest.py
    python gdocs_ingest.py --dry-run
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interfaces import MemoryItem

MOCK_DATA_PATH = Path(__file__).resolve().parents[2] / "mock_data" / "gdocs_pages.json"


# ── Hindsight writer (same stub pattern as confluence_ingest) ─────────────────

def _write_memory(item: MemoryItem, dry_run: bool = False):
    """Same stub as confluence_ingest — swap body once P2 ships hindsight_client."""
    if dry_run:
        print(f"  [DRY RUN] Would write → tags={item.tags} | {item.content[:80]}...")
        return

    try:
        from memory.hindsight_client import HindsightClient  # type: ignore
        client = HindsightClient()
        client.write(item)
    except ImportError:
        print(f"  [STUB WRITE] tags={item.tags} | {item.content[:80]}")


# ── Core ingestion logic ──────────────────────────────────────────────────────

def ingest_gdocs(mock_path: Path = MOCK_DATA_PATH, dry_run: bool = False) -> list[MemoryItem]:
    """
    Reads gdocs_pages.json and converts each item into a MemoryItem,
    then writes it to Hindsight.

    Returns the list of MemoryItems created (useful for testing).
    """
    if not mock_path.exists():
        raise FileNotFoundError(f"Mock data not found at: {mock_path}")

    with open(mock_path, "r") as f:
        pages = json.load(f)

    written: list[MemoryItem] = []

    for page in pages:
        print(f"\n[GDocs] Ingesting: '{page['title']}' (tag: {page['tag']})")

        for item_text in page["items"]:
            memory = MemoryItem(
                content=item_text,
                tags=[page["tag"], "org:company"],
                level=page["level"],
                source="gdocs_ingestion",
                relevance_score=1.0,
            )
            _write_memory(memory, dry_run=dry_run)
            written.append(memory)

    print(f"\n✓ GDocs ingestion complete — {len(written)} memory items processed.")
    return written


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest mock GDocs pages into Hindsight")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing to Hindsight")
    args = parser.parse_args()

    ingest_gdocs(dry_run=args.dry_run)