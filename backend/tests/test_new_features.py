"""Tests for analytics, feedback, chat history, and integrations endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)


def test_integrations_status():
    response = client.get("/integrations/status")
    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert "label" in data


def test_analytics_summary():
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "database" in data
    assert "feedback" in data


def test_feedback_submission():
    response = client.post(
        "/feedback",
        json={
            "session_id": "sess-feedback-001",
            "helpful": True,
            "team": "platform",
            "query": "AWS access?",
            "comment": "Very helpful",
        },
    )
    assert response.status_code == 200
    assert response.json()["helpful"] is True


def test_session_messages_empty():
    create = client.post(
        "/sessions",
        json={"name": "Test", "team": "platform", "role": "SDE-1", "employee_type": "fte"},
    )
    session_id = create.json()["session_id"]
    response = client.get(f"/sessions/{session_id}/messages")
    assert response.status_code == 200
    assert response.json()["messages"] == []


def test_demo_reset():
    response = client.post("/demo/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "reset"
