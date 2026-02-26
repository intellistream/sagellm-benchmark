#!/usr/bin/env python3
"""Compare current performance result against baseline for CI regression checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sagellm_benchmark.regression import RegressionDetector, render_markdown


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare performance against baseline.")
    parser.add_argument("--baseline", required=True, help="Baseline perf JSON path")
    parser.add_argument("--current", required=True, help="Current perf JSON path")
    parser.add_argument(
        "--warning-threshold",
        type=float,
        default=5.0,
        help="Warning regression threshold in percent",
    )
    parser.add_argument(
        "--critical-threshold",
        type=float,
        default=10.0,
        help="Critical regression threshold in percent",
    )
    parser.add_argument("--summary-json", required=True, help="Output comparison summary JSON path")
    parser.add_argument("--report-md", required=True, help="Output markdown report path")
    parser.add_argument(
        "--expected-change",
        action="append",
        default=[],
        help="Metric names treated as expected changes (repeatable)",
    )
    parser.add_argument(
        "--github-output",
        default=None,
        help="GitHub output file path (e.g. $GITHUB_OUTPUT)",
    )
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    with open(path) as file:
        return json.load(file)


def write_outputs(summary: dict[str, Any], summary_path: str, report_md_path: str) -> None:
    summary_file = Path(summary_path)
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w") as file:
        json.dump(summary, file, indent=2)

    report_file = Path(report_md_path)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w") as file:
        file.write(render_markdown(summary) + "\n")


def write_github_output(summary: dict[str, Any], path: str | None) -> None:
    if not path:
        return
    with open(path, "a") as file:
        file.write(f"overall_status={summary['overall_status']}\n")
        file.write(f"warning_threshold={summary['warning_threshold_pct']}\n")
        file.write(f"critical_threshold={summary['critical_threshold_pct']}\n")


def main() -> int:
    args = parse_args()

    baseline_payload = load_json(args.baseline)
    current_payload = load_json(args.current)
    detector = RegressionDetector(
        warning_threshold_pct=args.warning_threshold,
        critical_threshold_pct=args.critical_threshold,
        expected_changes=set(args.expected_change),
    )
    summary = detector.compare(baseline_payload, current_payload)

    write_outputs(summary, args.summary_json, args.report_md)
    write_github_output(summary, args.github_output)

    if summary["overall_status"] == "critical":
        return 2
    if summary["overall_status"] == "warning":
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
