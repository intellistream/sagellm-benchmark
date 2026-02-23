"""Performance benchmark modules for sagellm-benchmark."""

from __future__ import annotations

from sagellm_benchmark.performance.benchmark_utils import (
    BenchmarkResult,
    benchmark_function,
    compare_benchmarks,
    format_comparison_table,
)
from sagellm_benchmark.performance.model_benchmarks import run_e2e_model_benchmarks
from sagellm_benchmark.performance.operator_benchmarks import run_operator_benchmarks
from sagellm_benchmark.performance.plotting import generate_perf_charts

__all__ = [
    "BenchmarkResult",
    "benchmark_function",
    "compare_benchmarks",
    "format_comparison_table",
    "run_operator_benchmarks",
    "run_e2e_model_benchmarks",
    "generate_perf_charts",
]
