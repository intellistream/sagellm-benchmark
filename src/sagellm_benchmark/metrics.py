"""Metrics collection and aggregation."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BenchmarkMetrics:
    """Aggregated metrics from benchmark run.

    Follows Demo Contract metrics format (§5).
    """

    # Core metrics
    avg_ttft_ms: float = 0.0
    p50_ttft_ms: float = 0.0
    p95_ttft_ms: float = 0.0
    p99_ttft_ms: float = 0.0

    avg_tbt_ms: float = 0.0
    avg_tpot_ms: float = 0.0
    avg_throughput_tps: float = 0.0

    peak_mem_mb: int = 0
    avg_mem_mb: float = 0.0

    error_rate: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0

    # KV cache metrics
    kv_used_tokens: int = 0
    kv_used_bytes: int = 0
    prefix_hit_rate: float = 0.0
    evict_count: int = 0
    evict_ms: float = 0.0

    # Compression metrics
    spec_accept_rate: float = 0.0

    # Timing
    total_time_s: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0

    # Per-request details (for percentile calculation)
    ttft_samples: list[float] = field(default_factory=list)
    tbt_samples: list[float] = field(default_factory=list)
    throughput_samples: list[float] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict (exclude sample lists for cleaner JSON)."""
        d = asdict(self)
        # Remove internal fields
        d.pop("ttft_samples", None)
        d.pop("tbt_samples", None)
        d.pop("throughput_samples", None)
        return d

    def to_json(self, path: Path | str | None = None) -> str:
        """Export metrics as JSON.

        Args:
            path: Optional file path to write JSON.

        Returns:
            JSON string.
        """
        json_str = json.dumps(self.to_dict(), indent=2)

        if path:
            Path(path).write_text(json_str)

        return json_str

    @classmethod
    def aggregate(cls, responses: list[Any]) -> BenchmarkMetrics:
        """Aggregate metrics from multiple responses.

        Args:
            responses: List of Response objects with .metrics attribute.

        Returns:
            Aggregated BenchmarkMetrics.
        """
        metrics = cls()

        if not responses:
            return metrics

        metrics.total_requests = len(responses)
        metrics.successful_requests = sum(1 for r in responses if r.error is None)
        metrics.failed_requests = metrics.total_requests - metrics.successful_requests
        metrics.error_rate = (
            metrics.failed_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0
        )

        # Collect samples
        successful = [r for r in responses if r.error is None]
        if not successful:
            return metrics

        metrics.ttft_samples = [r.metrics.ttft_ms for r in successful]
        metrics.tbt_samples = [r.metrics.tbt_ms for r in successful if r.metrics.tbt_ms > 0]
        metrics.throughput_samples = [r.metrics.throughput_tps for r in successful]

        # Compute percentiles
        metrics.avg_ttft_ms = sum(metrics.ttft_samples) / len(metrics.ttft_samples)
        sorted_ttft = sorted(metrics.ttft_samples)
        metrics.p50_ttft_ms = sorted_ttft[len(sorted_ttft) // 2]
        metrics.p95_ttft_ms = sorted_ttft[int(len(sorted_ttft) * 0.95)]
        metrics.p99_ttft_ms = sorted_ttft[int(len(sorted_ttft) * 0.99)]

        # Averages
        if metrics.tbt_samples:
            metrics.avg_tbt_ms = sum(metrics.tbt_samples) / len(metrics.tbt_samples)

        metrics.avg_tpot_ms = sum(r.metrics.tpot_ms for r in successful) / len(successful)
        metrics.avg_throughput_tps = sum(metrics.throughput_samples) / len(
            metrics.throughput_samples
        )

        # Memory (take max)
        metrics.peak_mem_mb = max(r.metrics.peak_mem_mb for r in successful)
        metrics.avg_mem_mb = sum(r.metrics.peak_mem_mb for r in successful) / len(successful)

        # KV cache (sum)
        metrics.kv_used_tokens = sum(r.metrics.kv_used_tokens for r in successful)
        metrics.kv_used_bytes = sum(r.metrics.kv_used_bytes for r in successful)
        metrics.prefix_hit_rate = sum(r.metrics.prefix_hit_rate for r in successful) / len(
            successful
        )
        metrics.evict_count = sum(r.metrics.evict_count for r in successful)
        metrics.evict_ms = sum(r.metrics.evict_ms for r in successful)

        # Compression
        metrics.spec_accept_rate = sum(r.metrics.spec_accept_rate for r in successful) / len(
            successful
        )

        return metrics


class MetricsCollector:
    """Real-time metrics collection during benchmark."""

    def __init__(self) -> None:
        """Initialize collector."""
        self.responses: list[Any] = []
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def start(self) -> None:
        """Mark benchmark start."""
        self.start_time = time.perf_counter()

    def record(self, response: Any) -> None:
        """Record a response."""
        self.responses.append(response)

    def finish(self) -> BenchmarkMetrics:
        """Finish collection and compute metrics."""
        self.end_time = time.perf_counter()

        metrics = BenchmarkMetrics.aggregate(self.responses)
        metrics.start_time = self.start_time
        metrics.end_time = self.end_time
        metrics.total_time_s = self.end_time - self.start_time

        return metrics
