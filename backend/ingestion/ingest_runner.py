"""
ingest_runner.py  —  Person 4 (Ingestion + Actions)
-----------------------------------------------------
CLI entrypoint that runs ALL ingestion jobs in one shot.
This is the single command the team runs before a demo to
pre-populate Hindsight with all mock data.

What this does:
    1. Runs confluence_ingest  — loads fake Confluence pages
    2. Runs gdocs_ingest       — loads fake Google Docs pages
    3. Prints a summary of how many memories were written

Think of it like a database migration script — you run it
once to set up the initial state, and the agent's memory
layer starts from there.

Usage:
    python ingest_runner.py             # full run, writes to Hindsight
    python ingest_runner.py --dry-run   # preview only, no writes
    python ingest_runner.py --source confluence   # only run confluence
    python ingest_runner.py --source gdocs        # only run gdocs
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.confluence_ingest import ingest_confluence
from ingestion.gdocs_ingest import ingest_gdocs


def run_all(dry_run: bool = False, source: str = "all") -> dict:
    """
    Runs all (or selected) ingestion jobs.
    Returns a summary dict with counts per source.
    """
    summary = {}

    print("=" * 60)
    print("  RAMP — Ingestion Runner")
    print(f"  Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE (writing to Hindsight)'}")
    print("=" * 60)

    if source in ("all", "confluence"):
        print("\n── Confluence Ingestion ──────────────────────────────────")
        items = ingest_confluence(dry_run=dry_run)
        summary["confluence"] = len(items)

    if source in ("all", "gdocs"):
        print("\n── Google Docs Ingestion ─────────────────────────────────")
        items = ingest_gdocs(dry_run=dry_run)
        summary["gdocs"] = len(items)

    total = sum(summary.values())
    print("\n" + "=" * 60)
    print("  Ingestion Summary")
    print("=" * 60)
    for src, count in summary.items():
        print(f"  {src:<20} {count} memory items")
    print(f"  {'TOTAL':<20} {total} memory items")
    print("=" * 60)

    return summary


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run all Ramp ingestion jobs to pre-populate Hindsight memory"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be written, without writing to Hindsight"
    )
    parser.add_argument(
        "--source",
        choices=["all", "confluence", "gdocs"],
        default="all",
        help="Which source to ingest (default: all)"
    )
    args = parser.parse_args()

    run_all(dry_run=args.dry_run, source=args.source)