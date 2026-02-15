#!/usr/bin/env python3
"""Compare current performance result against baseline for CI regression checks."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MetricCheck:
    name: str
    baseline: float
    current: float
    regression_pct: float
    better_is_higher: bool

    @property
    def direction(self) -> str:
        return "higher-is-better" if self.better_is_higher else "lower-is-better"


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
        "--github-output",
        default=None,
        help="GitHub output file path (e.g. $GITHUB_OUTPUT)",
    )
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    with open(path) as file:
        return json.load(file)


def extract_metrics(payload: dict[str, Any]) -> dict[str, float]:
    summary = payload.get("summary")
    if isinstance(summary, dict):
        return {
            "avg_ttft_ms": float(summary.get("avg_ttft_ms", 0.0)),
            "avg_tbt_ms": float(summary.get("avg_tbt_ms", 0.0)),
            "avg_throughput_tps": float(summary.get("avg_throughput_tps", 0.0)),
        }

    rows = payload.get("rows", [])
    if not isinstance(rows, list) or not rows:
        raise ValueError("Cannot extract metrics: payload has no summary or rows.")

    avg_ttft = sum(float(row.get("ttft_ms", 0.0)) for row in rows) / len(rows)
    avg_tbt = sum(float(row.get("tbt_ms", 0.0)) for row in rows) / len(rows)
    avg_tps = sum(float(row.get("throughput_tps", 0.0)) for row in rows) / len(rows)
    return {
        "avg_ttft_ms": avg_ttft,
        "avg_tbt_ms": avg_tbt,
        "avg_throughput_tps": avg_tps,
    }


def compute_checks(baseline: dict[str, float], current: dict[str, float]) -> list[MetricCheck]:
    checks: list[MetricCheck] = []

    for metric in ["avg_ttft_ms", "avg_tbt_ms"]:
        base_value = baseline[metric]
        current_value = current[metric]
        regression = ((current_value - base_value) / base_value * 100.0) if base_value > 0 else 0.0
        checks.append(
            MetricCheck(
                name=metric,
                baseline=base_value,
                current=current_value,
                regression_pct=regression,
                better_is_higher=False,
            )
        )

    metric = "avg_throughput_tps"
    base_value = baseline[metric]
    current_value = current[metric]
    regression = ((base_value - current_value) / base_value * 100.0) if base_value > 0 else 0.0
    checks.append(
        MetricCheck(
            name=metric,
            baseline=base_value,
            current=current_value,
            regression_pct=regression,
            better_is_higher=True,
        )
    )

    return checks


def classify_status(regression_pct: float, warning: float, critical: float) -> str:
    if regression_pct > critical:
        return "critical"
    if regression_pct > warning:
        return "warning"
    return "acceptable"


def build_summary(
    checks: list[MetricCheck],
    warning_threshold: float,
    critical_threshold: float,
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    overall = "acceptable"

    for check in checks:
        status = classify_status(check.regression_pct, warning_threshold, critical_threshold)
        if status == "critical":
            overall = "critical"
        elif status == "warning" and overall != "critical":
            overall = "warning"

        metrics[check.name] = {
            "baseline": check.baseline,
            "current": check.current,
            "regression_pct": check.regression_pct,
            "status": status,
            "direction": check.direction,
        }

    return {
        "overall_status": overall,
        "warning_threshold_pct": warning_threshold,
        "critical_threshold_pct": critical_threshold,
        "metrics": metrics,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Performance Regression Report",
        "",
        f"- Overall Status: **{summary['overall_status'].upper()}**",
        f"- Warning Threshold: {summary['warning_threshold_pct']:.1f}%",
        f"- Critical Threshold: {summary['critical_threshold_pct']:.1f}%",
        "",
        "| Metric | Baseline | Current | Regression % | Status |",
        "|--------|----------|---------|--------------|--------|",
    ]

    for metric_name, metric in summary["metrics"].items():
        lines.append(
            f"| {metric_name} | {float(metric['baseline']):.4f} | {float(metric['current']):.4f} | "
            f"{float(metric['regression_pct']):.2f}% | {metric['status']} |"
        )

    return "\n".join(lines)


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

    baseline_metrics = extract_metrics(baseline_payload)
    current_metrics = extract_metrics(current_payload)

    checks = compute_checks(baseline_metrics, current_metrics)
    summary = build_summary(checks, args.warning_threshold, args.critical_threshold)

    write_outputs(summary, args.summary_json, args.report_md)
    write_github_output(summary, args.github_output)

    if summary["overall_status"] == "critical":
        return 2
    if summary["overall_status"] == "warning":
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
