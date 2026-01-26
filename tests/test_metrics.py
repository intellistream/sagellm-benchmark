"""Tests for metrics collection."""

from __future__ import annotations


def test_metrics_structure(sample_metrics):
    """Test metrics have required structure."""
    required_fields = [
        "avg_ttft_ms",
        "avg_tbt_ms",
        "avg_tpot_ms",
        "avg_throughput_tps",
        "peak_mem_mb",
        "error_rate",
        "total_requests",
        "successful_requests",
        "failed_requests",
    ]

    for field in required_fields:
        assert field in sample_metrics, f"Missing required field: {field}"


def test_metrics_types(sample_metrics):
    """Test metrics have correct types."""
    assert isinstance(sample_metrics["avg_ttft_ms"], int | float)
    assert isinstance(sample_metrics["avg_tbt_ms"], int | float)
    assert isinstance(sample_metrics["total_requests"], int)
    assert isinstance(sample_metrics["successful_requests"], int)
    assert isinstance(sample_metrics["failed_requests"], int)


def test_metrics_values(sample_metrics):
    """Test metrics have valid values."""
    assert sample_metrics["avg_ttft_ms"] >= 0
    assert sample_metrics["avg_throughput_tps"] >= 0
    assert 0 <= sample_metrics["error_rate"] <= 1
    assert sample_metrics["total_requests"] >= 0
    assert sample_metrics["successful_requests"] >= 0
    assert sample_metrics["failed_requests"] >= 0
    assert (
        sample_metrics["total_requests"]
        == sample_metrics["successful_requests"] + sample_metrics["failed_requests"]
    )
