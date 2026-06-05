"""
analytics_summary.py
------------------
Aggregate operational metrics for the analytics dashboard endpoint.
"""

from __future__ import annotations

from collections import Counter

from backend.db import AppDatabase


def build_analytics_summary() -> dict:
    db = AppDatabase.get()
    stats = db.get_database_stats()
    feedback = db.feedback_summary()
    audit_events = db.list_audit_events(limit=500)

    event_counts = Counter(event["event_type"] for event in audit_events)
    team_counts = Counter()
    for event in audit_events:
        if event["event_type"] == "chat.requested":
            team = event.get("payload", {}).get("team")
            if team:
                team_counts[team] += 1

    top_teams = [
        {"team": team, "chat_requests": count}
        for team, count in team_counts.most_common(5)
    ]

    return {
        "database": stats,
        "feedback": feedback,
        "event_counts": dict(event_counts),
        "top_teams_by_chat": top_teams,
        "chat_requests_total": event_counts.get("chat.requested", 0),
        "chat_completions_total": event_counts.get("chat.completed", 0),
    }
