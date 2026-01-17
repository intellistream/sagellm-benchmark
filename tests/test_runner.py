"""Tests for runner functionality."""

from __future__ import annotations


def test_runner_import():
    """Test runner module can be imported."""
    from sagellm_benchmark import runner

    assert hasattr(runner, "__name__")


def test_workloads_import():
    """Test workloads module can be imported."""
    from sagellm_benchmark import workloads

    assert hasattr(workloads, "__name__")
