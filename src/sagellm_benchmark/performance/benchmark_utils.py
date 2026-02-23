"""Performance benchmarking utilities migrated from sagellm-core (#45)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Any


@dataclass
class BenchmarkResult:
    """Single benchmark result."""

    name: str
    mean_time_ms: float
    std_time_ms: float
    min_time_ms: float
    max_time_ms: float
    iterations: int
    memory_mb: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def speedup_vs(self, baseline: BenchmarkResult) -> float:
        if self.mean_time_ms <= 0:
            return 1.0
        return baseline.mean_time_ms / self.mean_time_ms


def benchmark_function(
    func: Callable[[], Any],
    *,
    warmup: int = 5,
    iterations: int = 50,
    name: str = "",
) -> BenchmarkResult:
    """Benchmark callable execution time."""
    if not name:
        name = getattr(func, "__name__", "anonymous")

    for _ in range(max(0, warmup)):
        func()

    times: list[float] = []
    for _ in range(max(1, iterations)):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append((end - start) * 1000)

    return BenchmarkResult(
        name=name,
        mean_time_ms=mean(times),
        std_time_ms=stdev(times) if len(times) > 1 else 0.0,
        min_time_ms=min(times),
        max_time_ms=max(times),
        iterations=len(times),
    )


def compare_benchmarks(
    baseline: BenchmarkResult, optimized: BenchmarkResult
) -> dict[str, float | str]:
    """Compare baseline and optimized benchmark results."""
    speedup = optimized.speedup_vs(baseline)
    time_saved_ms = baseline.mean_time_ms - optimized.mean_time_ms
    time_saved_pct = (
        (time_saved_ms / baseline.mean_time_ms * 100.0) if baseline.mean_time_ms > 0 else 0.0
    )

    return {
        "baseline_name": baseline.name,
        "optimized_name": optimized.name,
        "baseline_time_ms": baseline.mean_time_ms,
        "optimized_time_ms": optimized.mean_time_ms,
        "speedup": speedup,
        "time_saved_ms": time_saved_ms,
        "time_saved_pct": time_saved_pct,
        "baseline_memory_mb": baseline.memory_mb,
        "optimized_memory_mb": optimized.memory_mb,
    }


def format_comparison_table(comparisons: list[dict[str, float | str]]) -> str:
    """Format benchmark comparisons into markdown table."""
    lines = [
        "| Benchmark | Baseline (ms) | Optimized (ms) | Speedup | Time Saved |",
        "|-----------|---------------|----------------|---------|------------|",
    ]

    for item in comparisons:
        lines.append(
            "| "
            f"{item['optimized_name']} | {float(item['baseline_time_ms']):.3f} | "
            f"{float(item['optimized_time_ms']):.3f} | {float(item['speedup']):.2f}x | "
            f"{float(item['time_saved_ms']):.3f} ms ({float(item['time_saved_pct']):.1f}%) |"
        )

    return "\n".join(lines)
