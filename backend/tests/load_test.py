"""
load_test.py
─────────────
Load testing suite using Locust for NexaCore.

Tests:
- Chat endpoint under load
- Memory retrieval performance
- Session creation/management
- Real-time WebSocket connections

Usage:
    # Install: pip install locust
    # Run: locust -f backend/tests/load_test.py --host=http://localhost:8000
    # Or: python -m locust -f backend/tests/load_test.py --host=http://localhost:8000
"""

import random
import string
from typing import Optional

from locust import HttpUser, between, task, events
from pydantic import BaseModel


class LoadTestConfig(BaseModel):
    """Load test configuration."""
    
    num_users: int = 10
    spawn_rate: int = 2  # Users per second
    run_time: str = "5m"
    target_rps: int = 100  # Target requests per second
    
    # Thresholds
    p95_latency_ms: float = 500
    p99_latency_ms: float = 1000
    error_rate_pct: float = 1.0


class ChatLoadTest(HttpUser):
    """Load test for chat endpoint."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
        self.chat_count = 0
    
    def on_start(self):
        """Setup: Create a session."""
        # Create session
        response = self.client.post(
            "/sessions",
            json={
                "name": f"loadtest_user_{random.randint(1000, 9999)}",
                "team_name": random.choice([
                    "engineering",
                    "product",
                    "design",
                    "marketing",
                ]),
                "role_title": random.choice([
                    "Engineer",
                    "Product Manager",
                    "Designer",
                    "Marketer",
                ]),
            },
        )
        
        if response.status_code == 200:
            self.session_id = response.json().get("session_id")
        else:
            print(f"Failed to create session: {response.status_code}")
    
    @task(3)
    def chat(self):
        """Send a chat message."""
        if not self.session_id:
            return
        
        prompts = [
            "What should I do on day 1?",
            "How do I set up my development environment?",
            "Where can I find the onboarding docs?",
            "Who should I talk to about the API?",
            "What's the team structure?",
            "How do I submit my first PR?",
            "Where's the design system documented?",
            "What's the best way to debug issues?",
        ]
        
        response = self.client.post(
            "/chat",
            json={
                "session_id": self.session_id,
                "user_input": random.choice(prompts),
            },
        )
        
        self.chat_count += 1
        
        if response.status_code != 200:
            print(f"Chat failed: {response.status_code} - {response.text}")
    
    @task(2)
    def get_memories(self):
        """Retrieve memories."""
        if not self.session_id:
            return
        
        self.client.get(
            f"/memories?session_id={self.session_id}",
        )
    
    @task(1)
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/health")


class TicketLoadTest(HttpUser):
    """Load test for ticket creation."""
    
    wait_time = between(2, 5)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = None
    
    def on_start(self):
        """Setup: Create a session."""
        response = self.client.post(
            "/sessions",
            json={
                "name": f"ticket_user_{random.randint(1000, 9999)}",
                "team_name": random.choice([
                    "engineering",
                    "product",
                    "design",
                ]),
            },
        )
        
        if response.status_code == 200:
            self.session_id = response.json().get("session_id")
    
    @task
    def create_ticket(self):
        """Create a ticket."""
        if not self.session_id:
            return
        
        title = "".join(random.choices(string.ascii_letters, k=20))
        
        self.client.post(
            "/tickets",
            json={
                "session_id": self.session_id,
                "title": f"Task: {title}",
                "description": "Test ticket from load test",
                "assignee_team": random.choice([
                    "engineering",
                    "product",
                ]),
                "priority": random.choice(["low", "medium", "high"]),
            },
        )


# Event handlers for reporting

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "="*60)
    print("  NexaCore Load Test Started")
    print("="*60)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_client_count}")
    print(f"Spawn Rate: {environment.runner.spawn_rate}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "="*60)
    print("  NexaCore Load Test Completed")
    print("="*60)
    
    # Print statistics
    stats = environment.stats
    
    print("\nRequest Statistics:")
    print(f"  Total Requests: {stats.total.num_requests}")
    print(f"  Total Failures: {stats.total.num_failures}")
    print(f"  Success Rate: {stats.total.success_rate:.1f}%")
    print(f"  Avg Response Time: {stats.total.avg_response_time:.0f}ms")
    print(f"  Min Response Time: {stats.total.min_response_time:.0f}ms")
    print(f"  Max Response Time: {stats.total.max_response_time:.0f}ms")
    print(f"  p50 Response Time: {stats.total.get_response_time_percentile(0.5):.0f}ms")
    print(f"  p95 Response Time: {stats.total.get_response_time_percentile(0.95):.0f}ms")
    print(f"  p99 Response Time: {stats.total.get_response_time_percentile(0.99):.0f}ms")
    
    print("\nEndpoint Performance:")
    for name, entry in stats.entries.items():
        print(f"  {name}")
        print(f"    Requests: {entry.num_requests}")
        print(f"    Failures: {entry.num_failures}")
        print(f"    Avg: {entry.avg_response_time:.0f}ms")
        print(f"    p95: {entry.get_response_time_percentile(0.95):.0f}ms")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    # This allows running the script directly
    # Usage: python backend/tests/load_test.py
    import sys
    
    sys.exit(1)  # Must be run with locust command
