"""
performance_baseline.py
────────────────────────
Establish performance baselines for NexaCore.

This script runs a series of tests to measure:
- API latency (p95, p99)
- Database query performance
- Memory retrieval speed
- Agent response time

Results are saved to metrics/baselines.json for tracking
improvements over time.

Usage:
    python -m backend.tests.performance_baseline
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from backend.db import AppDatabase
from backend.logging_config import get_logger
from backend.memory.retriever import MemoryRetriever

logger = get_logger(__name__)


class PerformanceBaseline:
    """Measure and record performance baselines."""
    
    def __init__(self, api_host: str = "http://localhost:8000"):
        self.api_host = api_host
        self.db = AppDatabase.get()
        self.retriever = MemoryRetriever()
        self.results: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "api_host": api_host,
            "tests": {},
        }
    
    async def run_all(self) -> dict[str, Any]:
        """Run all baseline tests."""
        logger.info("Starting performance baseline tests...")
        
        await self.test_api_latency()
        await self.test_db_query_speed()
        await self.test_memory_retrieval()
        
        self.save_results()
        return self.results
    
    async def test_api_latency(self) -> None:
        """Test API endpoint latencies."""
        logger.info("Testing API latencies...")
        
        endpoints = [
            ("GET", "/health"),
            ("GET", "/metrics"),
        ]
        
        latencies = {endpoint: [] for method, endpoint in endpoints}
        
        async with httpx.AsyncClient() as client:
            for method, endpoint in endpoints:
                for _ in range(10):
                    start = time.perf_counter()
                    
                    try:
                        if method == "GET":
                            response = await client.get(f"{self.api_host}{endpoint}")
                        else:
                            response = await client.post(f"{self.api_host}{endpoint}")
                        
                        latency = (time.perf_counter() - start) * 1000
                        
                        if response.status_code == 200:
                            latencies[endpoint].append(latency)
                    except Exception as e:
                        logger.warning(f"API test failed: {e}")
        
        # Calculate statistics
        api_stats = {}
        for endpoint, times in latencies.items():
            if times:
                api_stats[endpoint] = {
                    "avg_ms": sum(times) / len(times),
                    "min_ms": min(times),
                    "max_ms": max(times),
                    "p95_ms": sorted(times)[int(len(times) * 0.95)],
                    "count": len(times),
                }
        
        self.results["tests"]["api_latency"] = api_stats
        logger.info(f"API latencies: {api_stats}")
    
    async def test_db_query_speed(self) -> None:
        """Test database query performance."""
        logger.info("Testing database query speed...")
        
        times = {}
        
        # Test table scans
        with self.db.connect() as connection:
            for table in ["tickets", "reminders", "sessions", "audit_events"]:
                start = time.perf_counter()
                connection.execute(f"SELECT COUNT(*) FROM {table}")
                times[f"{table}_count"] = (time.perf_counter() - start) * 1000
                
                start = time.perf_counter()
                connection.execute(f"SELECT * FROM {table} LIMIT 100")
                times[f"{table}_scan"] = (time.perf_counter() - start) * 1000
        
        self.results["tests"]["db_query_speed"] = {
            k: f"{v:.2f}ms" for k, v in times.items()
        }
        logger.info(f"Database query speeds: {times}")
    
    async def test_memory_retrieval(self) -> None:
        """Test memory retrieval speed."""
        logger.info("Testing memory retrieval...")
        
        queries = [
            {"team": "engineering"},
            {"level": "onboarding"},
            {"tags": ["org:company", "team:engineering"]},
        ]
        
        times = []
        
        for query in queries:
            start = time.perf_counter()
            results = await self.retriever.search(**query, limit=10)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)
        
        if times:
            self.results["tests"]["memory_retrieval"] = {
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "queries": len(times),
            }
            logger.info(f"Memory retrieval times: {times}")
    
    def save_results(self) -> None:
        """Save results to file."""
        metrics_dir = Path("./metrics")
        metrics_dir.mkdir(exist_ok=True)
        
        output_file = metrics_dir / "baselines.json"
        
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Baseline results saved to {output_file}")
        print(json.dumps(self.results, indent=2))


async def main():
    """Run baseline tests."""
    baseline = PerformanceBaseline()
    await baseline.run_all()


if __name__ == "__main__":
    asyncio.run(main())
