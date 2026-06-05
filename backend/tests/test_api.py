"""
test_api.py
-----------
Integration tests for FastAPI endpoints.
"""

import json

from fastapi.testclient import TestClient

from backend.server import app


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self):
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ready_endpoint(self):
        client = TestClient(app)
        response = client.get("/ready")
        assert response.status_code in [200, 503]  # OK or unavailable
        data = response.json()
        assert "database" in data
        assert "memory_backend" in data

    def test_health_detailed_endpoint(self):
        client = TestClient(app)
        response = client.get("/health-detailed")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "database_stats" in data


class TestMetricsEndpoints:
    """Tests for observability endpoints."""

    def test_metrics_prometheus_format(self):
        client = TestClient(app)
        response = client.get("/metrics")
        assert response.status_code == 200
        # Should be Prometheus text exposition format (metric lines)
        assert "http_requests_total" in response.text or "_bucket" in response.text

    def test_stats_json_endpoint(self):
        client = TestClient(app)
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "counters" in data or "histograms" in data

    def test_db_stats_endpoint(self):
        client = TestClient(app)
        response = client.get("/db-stats")
        assert response.status_code == 200
        data = response.json()
        assert "tables" in data


class TestSessionEndpoints:
    """Tests for session management."""

    def test_create_session(self):
        client = TestClient(app)
        payload = {
            "name": "Alice Johnson",
            "team": "platform",
            "role": "SDE-1",
            "employee_type": "fte",
        }
        response = client.post("/sessions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_get_session(self):
        client = TestClient(app)
        # First create a session
        create_payload = {
            "name": "Bob Smith",
            "team": "infra_security",
        }
        create_response = client.post("/sessions", json=create_payload)
        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]

        # Now retrieve it
        get_response = client.get(f"/sessions/{session_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == session_id
        assert data["user_name"] == "Bob Smith"

    def test_list_sessions(self):
        client = TestClient(app)
        response = client.get("/sessions?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data or isinstance(data, list)


class TestDataEndpoints:
    """Tests for data query endpoints."""

    def test_get_tickets(self):
        client = TestClient(app)
        response = client.get("/tickets")
        assert response.status_code == 200
        data = response.json()
        assert "tickets" in data or isinstance(data, list)

    def test_get_reminders(self):
        client = TestClient(app)
        response = client.get("/reminders")
        assert response.status_code == 200
        data = response.json()
        assert "reminders" in data or isinstance(data, list)

    def test_get_audit_events(self):
        client = TestClient(app)
        response = client.get("/audit")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data or isinstance(data, list)


class TestMemoryEndpoints:
    """Tests for memory retrieval."""

    def test_get_memories(self):
        client = TestClient(app)
        response = client.get("/memories", params={"team": "platform"})
        assert response.status_code == 200
        data = response.json()
        assert "memories" in data or isinstance(data, list)

    def test_get_memories_with_context(self):
        client = TestClient(app)
        params = {
            "team": "platform",
            "role": "SDE-1",
            "employee_type": "fte",
        }
        response = client.get("/memories", params=params)
        assert response.status_code == 200


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self):
        client = TestClient(app)
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_invalid_session_id(self):
        client = TestClient(app)
        response = client.get("/sessions/invalid-id-that-does-not-exist")
        assert response.status_code in [200, 404]  # Depends on implementation
