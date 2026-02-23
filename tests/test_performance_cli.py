"""Tests for performance CLI commands."""

from __future__ import annotations

import json

from click.testing import CliRunner

from sagellm_benchmark.cli import main


def test_perf_help():
    runner = CliRunner()
    result = runner.invoke(main, ["perf", "--help"])
    assert result.exit_code == 0
    assert "--type" in result.output
    assert "operator" in result.output
    assert "e2e" in result.output
    assert "--plot" in result.output
    assert "--plot-format" in result.output


def test_perf_e2e_generates_files():
    runner = CliRunner()
    with runner.isolated_filesystem():
        json_path = "out/perf.json"
        md_path = "out/perf.md"
        result = runner.invoke(
            main,
            [
                "perf",
                "--type",
                "e2e",
                "--model",
                "Qwen/Qwen2-7B-Instruct",
                "--batch-size",
                "1",
                "--precision",
                "fp16",
                "--output-json",
                json_path,
                "--output-markdown",
                md_path,
            ],
        )
        assert result.exit_code == 0

        with open(json_path) as f:
            payload = json.load(f)
        assert payload["kind"] == "e2e"
        assert len(payload["rows"]) > 0
        assert "precision" in payload["rows"][0]


def test_report_accepts_perf_json():
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = "perf.json"
        with open(path, "w") as f:
            json.dump(
                {
                    "kind": "operator",
                    "device": "cpu",
                    "comparisons": [
                        {
                            "optimized_name": "CustomLinear",
                            "baseline_time_ms": 10.0,
                            "optimized_time_ms": 5.0,
                            "speedup": 2.0,
                            "time_saved_ms": 5.0,
                            "time_saved_pct": 50.0,
                        }
                    ],
                },
                f,
            )

        result = runner.invoke(main, ["report", "--input", path, "--format", "markdown"])
        assert result.exit_code == 0
        assert "Operator Benchmark Report" in result.output
