"""sagellm-benchmark: Benchmark Suite & E2E Testing for sageLLM."""

from __future__ import annotations

from sagellm_benchmark.metrics import BenchmarkMetrics, MetricsCollector
from sagellm_benchmark.runner import BenchmarkConfig, BenchmarkRunner, run_year1_benchmark
from sagellm_benchmark.workloads import YEAR1_WORKLOADS, WorkloadConfig, WorkloadType

__version__ = "0.1.0.1"

__all__ = [
    "__version__",
    # Metrics
    "BenchmarkMetrics",
    "MetricsCollector",
    # Runner
    "BenchmarkRunner",
    "BenchmarkConfig",
    "run_year1_benchmark",
    # Workloads
    "WorkloadConfig",
    "WorkloadType",
    "YEAR1_WORKLOADS",
]
