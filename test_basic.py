#!/usr/bin/env python3
"""Simple test script for sagellm-benchmark functionality."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for testing without install
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:

        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_workloads():
    """Test workload configuration."""
    print("\nTesting workload configuration...")

    try:
        from sagellm_benchmark import YEAR1_WORKLOADS, WorkloadType

        assert len(YEAR1_WORKLOADS) == 3, "Expected 3 workloads"

        workload_types = {w.workload_type for w in YEAR1_WORKLOADS}
        expected_types = {WorkloadType.SHORT, WorkloadType.LONG, WorkloadType.STRESS}
        assert workload_types == expected_types, f"Unexpected workload types: {workload_types}"

        print(f"✓ Found {len(YEAR1_WORKLOADS)} workloads:")
        for w in YEAR1_WORKLOADS:
            print(f"  - {w.name}: {w.workload_type.value} ({w.num_requests} requests)")

        return True
    except Exception as e:
        print(f"✗ Workload test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_metrics():
    """Test metrics collection."""
    print("\nTesting metrics collection...")

    try:
        from sagellm_benchmark import BenchmarkMetrics, MetricsCollector

        # Create empty metrics
        metrics = BenchmarkMetrics()
        assert metrics.total_requests == 0
        assert metrics.error_rate == 0.0

        # Test to_dict
        metrics_dict = metrics.to_dict()
        assert "avg_ttft_ms" in metrics_dict
        assert "throughput_samples" not in metrics_dict  # Should be excluded

        # Test collector
        collector = MetricsCollector()
        collector.start()
        collector.finish()

        print("✓ Metrics collection works")
        return True
    except Exception as e:
        print(f"✗ Metrics test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_import():
    """Test CLI module import."""
    print("\nTesting CLI import...")

    try:

        print("✓ CLI import successful")
        return True
    except Exception as e:
        print(f"✗ CLI import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("====================================")
    print("  sageLLM Benchmark - Self Test")
    print("====================================\n")

    tests = [
        test_imports,
        test_workloads,
        test_metrics,
        test_cli_import,
    ]

    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    print("\n====================================")
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
