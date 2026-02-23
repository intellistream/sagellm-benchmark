"""Tests for performance regression comparison script (#47)."""

from __future__ import annotations

import json
import subprocess
import sys


def test_compare_performance_baseline_script(tmp_path):
    baseline = {
        "kind": "e2e",
        "summary": {
            "avg_ttft_ms": 50.0,
            "avg_tbt_ms": 10.0,
            "avg_throughput_tps": 100.0,
        },
    }
    current = {
        "kind": "e2e",
        "summary": {
            "avg_ttft_ms": 51.0,
            "avg_tbt_ms": 10.2,
            "avg_throughput_tps": 98.0,
        },
    }

    baseline_path = tmp_path / "baseline.json"
    current_path = tmp_path / "current.json"
    summary_path = tmp_path / "summary.json"
    report_path = tmp_path / "report.md"

    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    current_path.write_text(json.dumps(current), encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/compare_performance_baseline.py",
        "--baseline",
        str(baseline_path),
        "--current",
        str(current_path),
        "--warning-threshold",
        "5",
        "--critical-threshold",
        "10",
        "--summary-json",
        str(summary_path),
        "--report-md",
        str(report_path),
    ]

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert result.returncode == 0

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["overall_status"] == "acceptable"
    assert report_path.exists()
