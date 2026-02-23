"""Tests for performance plotting input validation paths."""

from __future__ import annotations

import pytest

from sagellm_benchmark.performance.plotting import generate_perf_charts


def test_generate_perf_charts_rejects_unknown_kind(tmp_path):
    with pytest.raises(ValueError):
        generate_perf_charts({"kind": "unknown"}, output_dir=tmp_path, formats=["png"])


def test_generate_perf_charts_rejects_bad_format(tmp_path):
    payload = {
        "kind": "operator",
        "comparisons": [{"optimized_name": "x", "speedup": 1.1}],
    }
    with pytest.raises(ValueError):
        generate_perf_charts(payload, output_dir=tmp_path, formats=["svg"])
