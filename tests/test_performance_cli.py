"""Tests for performance CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

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


def test_compare_generates_files(monkeypatch):
    """Compare command should write per-target and summary artifacts."""

    def fake_run_e2e_model_benchmarks(**kwargs):
        backend_url = kwargs["backend_url"]
        if "8902" in backend_url:
            ttft = 10.0
            tbt = 2.0
            tps = 100.0
        else:
            ttft = 12.0
            tbt = 3.0
            tps = 90.0
        return [
            {
                "model": kwargs["models"][0],
                "precision": "live",
                "scenario": "short_b1",
                "batch_size": 1,
                "ttft_ms": ttft,
                "tbt_ms": tbt,
                "throughput_tps": tps,
                "latency_p50_ms": 20.0,
                "latency_p95_ms": 25.0,
                "latency_p99_ms": 30.0,
                "memory_mb": 0.0,
                "mode": "live",
            }
        ]

    monkeypatch.setattr(
        "sagellm_benchmark.performance.model_benchmarks.run_e2e_model_benchmarks",
        fake_run_e2e_model_benchmarks,
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_dir = Path("compare_out")
        result = runner.invoke(
            main,
            [
                "compare",
                "--target",
                "sagellm=http://127.0.0.1:8902/v1",
                "--target",
                "vllm=http://127.0.0.1:8901/v1",
                "--model",
                "Qwen/Qwen2.5-0.5B-Instruct",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "sagellm.json").exists()
        assert (output_dir / "vllm.json").exists()
        assert (output_dir / "comparison.json").exists()

        with open(output_dir / "comparison.json") as f:
            payload = json.load(f)
        assert payload["kind"] == "compare"
        assert payload["baseline"] == "sagellm"
        assert len(payload["targets"]) == 2


def test_vllm_compare_run_generates_files(monkeypatch):
    """vllm-compare run should write the same compare artifacts with semantic labels."""

    def fake_run_e2e_model_benchmarks(**kwargs):
        backend_url = kwargs["backend_url"]
        if "8901" in backend_url:
            ttft = 11.0
            tbt = 2.5
            tps = 80.0
        else:
            ttft = 9.0
            tbt = 1.5
            tps = 95.0
        return [
            {
                "model": kwargs["models"][0],
                "precision": "live",
                "scenario": "short_b1",
                "batch_size": 1,
                "ttft_ms": ttft,
                "tbt_ms": tbt,
                "throughput_tps": tps,
                "latency_p50_ms": 20.0,
                "latency_p95_ms": 25.0,
                "latency_p99_ms": 30.0,
                "memory_mb": 0.0,
                "mode": "live",
            }
        ]

    monkeypatch.setattr(
        "sagellm_benchmark.performance.model_benchmarks.run_e2e_model_benchmarks",
        fake_run_e2e_model_benchmarks,
    )

    runner = CliRunner()
    with runner.isolated_filesystem():
        output_dir = Path("compare_out")
        result = runner.invoke(
            main,
            [
                "vllm-compare",
                "run",
                "--sagellm-url",
                "http://127.0.0.1:8901/v1",
                "--vllm-url",
                "http://127.0.0.1:8000/v1",
                "--model",
                "Qwen/Qwen2.5-0.5B-Instruct",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "sagellm.json").exists()
        assert (output_dir / "vllm.json").exists()
        assert (output_dir / "comparison.json").exists()

        with open(output_dir / "comparison.json") as f:
            payload = json.load(f)
        assert payload["kind"] == "compare"
        assert payload["baseline"] == "sagellm"
        assert [target["label"] for target in payload["targets"]] == ["sagellm", "vllm"]
