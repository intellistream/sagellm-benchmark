from __future__ import annotations

import json

from sagellm_benchmark.baseline import BaselineManager
from sagellm_benchmark.regression import RegressionDetector, extract_metrics, render_markdown


def test_baseline_manager_update(tmp_path):
    baseline_path = tmp_path / "perf_baseline.json"
    manager = BaselineManager(baseline_path=baseline_path)

    payload = {
        "kind": "e2e",
        "summary": {
            "avg_ttft_ms": 50.0,
            "avg_tbt_ms": 10.0,
            "avg_throughput_tps": 100.0,
        },
    }

    manager.update(payload)
    saved = json.loads(baseline_path.read_text(encoding="utf-8"))

    assert saved["summary"]["avg_ttft_ms"] == 50.0
    assert "baseline_updated_at" in saved["metadata"]


def test_regression_detector_expected_change():
    baseline = {
        "summary": {
            "avg_ttft_ms": 50.0,
            "avg_tbt_ms": 10.0,
            "avg_throughput_tps": 100.0,
        }
    }
    current = {
        "summary": {
            "avg_ttft_ms": 58.0,
            "avg_tbt_ms": 10.6,
            "avg_throughput_tps": 96.0,
        }
    }

    detector = RegressionDetector(
        warning_threshold_pct=5.0,
        critical_threshold_pct=10.0,
        expected_changes={"avg_ttft_ms"},
    )
    summary = detector.compare(baseline, current)

    assert summary["metrics"]["avg_ttft_ms"]["status"] == "expected-change"
    assert summary["metrics"]["avg_tbt_ms"]["status"] == "warning"
    assert summary["overall_status"] == "warning"

    report = render_markdown(summary)
    assert "allowlisted" in report


def test_extract_metrics_from_rows():
    payload = {
        "rows": [
            {"ttft_ms": 10, "tbt_ms": 5, "throughput_tps": 20},
            {"ttft_ms": 30, "tbt_ms": 7, "throughput_tps": 10},
        ]
    }

    metrics = extract_metrics(payload)
    assert metrics["avg_ttft_ms"] == 20.0
    assert metrics["avg_tbt_ms"] == 6.0
    assert metrics["avg_throughput_tps"] == 15.0
