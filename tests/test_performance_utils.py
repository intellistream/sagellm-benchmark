"""Tests for performance benchmark utilities."""

from __future__ import annotations

from sagellm_benchmark.performance.benchmark_utils import (
    BenchmarkResult,
    compare_benchmarks,
    format_comparison_table,
)
from sagellm_benchmark.performance.model_benchmarks import (
    run_e2e_model_benchmarks,
    summarize_e2e_rows,
)


def test_compare_benchmarks():
    baseline = BenchmarkResult(
        name="baseline",
        mean_time_ms=10.0,
        std_time_ms=1.0,
        min_time_ms=8.0,
        max_time_ms=12.0,
        iterations=10,
    )
    optimized = BenchmarkResult(
        name="optimized",
        mean_time_ms=5.0,
        std_time_ms=0.5,
        min_time_ms=4.0,
        max_time_ms=6.0,
        iterations=10,
    )

    result = compare_benchmarks(baseline, optimized)
    assert result["speedup"] == 2.0
    assert result["time_saved_ms"] == 5.0


def test_format_comparison_table():
    table = format_comparison_table(
        [
            {
                "optimized_name": "CustomLinear",
                "baseline_time_ms": 10.0,
                "optimized_time_ms": 5.0,
                "speedup": 2.0,
                "time_saved_ms": 5.0,
                "time_saved_pct": 50.0,
            }
        ]
    )
    assert "| Benchmark |" in table
    assert "CustomLinear" in table
    assert "2.00x" in table


def test_run_e2e_model_benchmarks_simulated():
    rows = run_e2e_model_benchmarks(
        models=["Qwen/Qwen2-7B-Instruct"],
        batch_sizes=[1, 4],
        precisions=["fp16", "int8"],
        simulate=True,
    )
    assert len(rows) == 8
    assert all("ttft_ms" in row for row in rows)
    assert all("precision" in row for row in rows)

    summary = summarize_e2e_rows(rows)
    assert summary["total_rows"] == 8
    assert summary["avg_ttft_ms"] > 0
