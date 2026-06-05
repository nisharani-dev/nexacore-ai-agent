"""
observability.py
----------------
In-process metrics and distributed tracing suitable for Prometheus scraping and APM.

Metrics:
- Counters: request counts, errors, events
- Histograms: latency, sizes
- Gauges: active sessions, memory usage

All metrics are thread-safe and render as Prometheus exposition format.
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Dict, List, Tuple


class MetricsRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._lock = Lock()

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        """Increment a counter."""
        key = self._key(name, labels)
        with self._lock:
            self._counters[key] += amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        """Record a histogram observation."""
        key = self._key(name, labels)
        with self._lock:
            self._histograms[key].append(value)

    def gauge(self, name: str, value: float, **labels: str) -> None:
        """Set a gauge value."""
        key = self._key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def render_prometheus(self) -> str:
        """Render all metrics in Prometheus exposition format."""
        lines: List[str] = []
        
        with self._lock:
            # Counters
            for key, value in sorted(self._counters.items()):
                lines.append(f"{key} {value}")
            
            # Histograms - render quantiles and bucket stats
            for key, observations in sorted(self._histograms.items()):
                if observations:
                    sorted_obs = sorted(observations)
                    count = len(sorted_obs)
                    total = sum(sorted_obs)
                    
                    # Histogram buckets: 10ms, 50ms, 100ms, 500ms, 1000ms, +Inf
                    bucket_boundaries = [10, 50, 100, 500, 1000]
                    for boundary in bucket_boundaries:
                        bucket_count = sum(1 for v in sorted_obs if v <= boundary)
                        lines.append(f'{key}_bucket{{le="{boundary}"}} {bucket_count}')
                    lines.append(f'{key}_bucket{{le="+Inf"}} {count}')
                    
                    # Summary stats
                    lines.append(f"{key}_count {count}")
                    lines.append(f"{key}_sum {total}")
                    if count > 0:
                        lines.append(f"{key}_avg {total / count}")
            
            # Gauges
            for key, value in sorted(self._gauges.items()):
                lines.append(f"{key} {value}")
        
        return "\n".join(lines) + ("\n" if lines else "")

    def get_summary(self) -> dict:
        """Return a dict summary of all metrics for JSON responses."""
        with self._lock:
            summary = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
            }
            
            for key, observations in self._histograms.items():
                if observations:
                    sorted_obs = sorted(observations)
                    summary["histograms"][key] = {
                        "count": len(sorted_obs),
                        "sum": sum(sorted_obs),
                        "min": sorted_obs[0],
                        "max": sorted_obs[-1],
                        "p50": sorted_obs[len(sorted_obs) // 2],
                        "p95": sorted_obs[int(len(sorted_obs) * 0.95)],
                        "p99": sorted_obs[int(len(sorted_obs) * 0.99)],
                    }
            
            return summary

    @staticmethod
    def _key(name: str, labels: dict) -> str:
        """Build Prometheus metric key from name and labels."""
        if not labels:
            return name
        labels_block = ",".join(f'{label}="{value}"' for label, value in sorted(labels.items()))
        return f"{name}{{{labels_block}}}"


metrics = MetricsRegistry()

