"""Tests for package imports and version."""

from __future__ import annotations


def test_import_package():
    """Test package can be imported."""
    import sagellm_benchmark

    assert hasattr(sagellm_benchmark, "__version__")


def test_version():
    """Test version string format."""
    from sagellm_benchmark import __version__

    assert isinstance(__version__, str)
    parts = __version__.split(".")
    assert len(parts) >= 3, "Version should be at least X.Y.Z"


def test_import_cli():
    """Test CLI module can be imported."""
    from sagellm_benchmark.cli import main

    assert callable(main)


def test_import_metrics():
    """Test metrics module can be imported."""
    from sagellm_benchmark import metrics

    assert hasattr(metrics, "__name__")
