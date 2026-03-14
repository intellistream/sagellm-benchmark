"""Tests for canonical artifact to leaderboard export."""

from __future__ import annotations

import json
from pathlib import Path

from sagellm_benchmark.exporters import LeaderboardExporter


def _canonical_execution_result(
    *,
    workload_name: str = "Q1",
    engine: str = "sagellm",
    engine_version: str = "0.6.0.0",
    hardware_family: str = "cuda",
    chip_count: int = 1,
    node_count: int = 1,
    precision: str = "FP16",
) -> dict:
    artifact = {
        "schema_version": "canonical-benchmark-result/v1",
        "artifact_kind": "execution_result",
        "artifact_id": "11111111-1111-1111-1111-111111111111",
        "producer": {"name": "sagellm-benchmark", "command": "compare"},
        "provenance": {
            "captured_at": "2026-03-14T12:00:00+00:00",
            "endpoint_url": "http://127.0.0.1:8901/v1",
            "output_dir": "benchmark_results/compare_test",
        },
        "hardware": {
            "family": hardware_family,
            "vendor": "NVIDIA" if hardware_family == "cuda" else "Huawei",
            "chip_model": "A100" if hardware_family == "cuda" else "Ascend 910B",
            "chip_count": chip_count,
            "chips_per_node": max(1, chip_count // node_count),
            "node_count": node_count,
            "interconnect": "NVLink" if hardware_family == "cuda" else "HCCS",
        },
        "engine": {
            "name": engine,
            "version": engine_version,
            "backend": hardware_family,
            "precision": precision,
            "model": "Qwen/Qwen2.5-0.5B-Instruct",
        },
        "model": {
            "name": "Qwen/Qwen2.5-0.5B-Instruct",
            "precision": precision,
        },
        "versions": {
            "benchmark": "0.6.0.0",
            "sagellm": "0.6.0.0",
            "vllm": "0.8.2",
        },
        "workload": {
            "name": workload_name,
            "precision": precision,
            "dataset": "default",
            "batch_size": 1,
            "concurrency": 1,
        },
        "metrics": {
            "avg_ttft_ms": 10.0,
            "avg_tbt_ms": 2.0,
            "avg_tpot_ms": 3.0,
            "avg_throughput_tps": 80.0,
            "output_throughput_tps": 120.0,
            "peak_mem_mb": 1024,
            "error_rate": 0.0,
            "avg_prefix_hit_rate": 0.1,
            "total_kv_used_tokens": 1024,
            "total_kv_used_bytes": 4096,
            "total_evict_count": 0,
            "total_evict_ms": 0.0,
            "avg_spec_accept_rate": 0.0,
        },
        "measurements": {"rows": [{"precision": precision, "batch_size": 1}]},
        "telemetry": {},
        "validation": {"publishable_to_leaderboard": True},
        "artifacts": {},
        "relations": [],
    }
    if node_count > 1:
        artifact["cluster"] = {
            "node_count": node_count,
            "comm_backend": "nccl" if hardware_family == "cuda" else "hccl",
            "topology_type": "multi_node",
            "parallelism": {
                "tensor_parallel": chip_count,
                "pipeline_parallel": 1,
                "data_parallel": 1,
            },
        }
    return artifact


def test_leaderboard_entry_from_canonical_q_workload() -> None:
    entry = LeaderboardExporter.leaderboard_entry_from_canonical_artifact(
        _canonical_execution_result(workload_name="Q3")
    )

    assert entry["workload"]["name"] == "Q3"
    assert entry["workload"]["input_length"] == 128
    assert entry["workload"]["output_length"] == 256
    assert entry["engine"] == "sagellm"
    assert entry["model"]["precision"] == "FP16"
    assert entry["metadata"]["idempotency_key"]
    assert entry["canonical_path"].endswith("_leaderboard.json")


def test_leaderboard_entry_from_canonical_multi_node_compare() -> None:
    entry = LeaderboardExporter.leaderboard_entry_from_canonical_artifact(
        _canonical_execution_result(
            workload_name="compare-live",
            engine="vllm-ascend",
            engine_version="0.11.0",
            hardware_family="ascend",
            chip_count=16,
            node_count=2,
            precision="BF16",
        )
    )

    assert entry["engine"] == "vllm-ascend"
    assert entry["engine_version"] == "0.11.0"
    assert entry["config_type"] == "multi_node"
    assert entry["cluster"]["node_count"] == 2
    assert entry["hardware"]["chip_count"] == 16
    assert entry["model"]["precision"] == "BF16"
    assert entry["metadata"]["hardware_family"] == "ascend"


def test_collect_entries_from_directory_prefers_canonical(tmp_path: Path) -> None:
    compare_dir = tmp_path / "compare"
    compare_dir.mkdir()
    canonical_path = compare_dir / "sagellm.canonical.json"
    canonical_path.write_text(
        json.dumps(_canonical_execution_result(workload_name="Q5"), indent=2),
        encoding="utf-8",
    )
    leaderboard_path = compare_dir / "sagellm_leaderboard.json"
    entry = LeaderboardExporter.export_canonical_artifact(
        _canonical_execution_result(workload_name="Q5"),
        leaderboard_path,
    )
    LeaderboardExporter.register_exported_entry(
        output_dir=compare_dir,
        entry=entry,
        leaderboard_path=leaderboard_path,
        canonical_artifact_path=canonical_path,
    )

    entries, errors = LeaderboardExporter.collect_entries_from_directory(compare_dir)

    assert errors == []
    assert len(entries) == 1
    assert entries[0]["workload"]["name"] == "Q5"
    assert entries[0]["metadata"]["manifest_source"].endswith("leaderboard_manifest.json")


def test_export_canonical_artifact_end_to_end(tmp_path: Path) -> None:
    artifact = _canonical_execution_result(workload_name="Q8", engine="vllm")
    output_path = tmp_path / "vllm_leaderboard.json"

    entry = LeaderboardExporter.export_canonical_artifact(artifact, output_path)

    assert output_path.exists()
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["entry_id"] == entry["entry_id"]
    assert saved["workload"]["name"] == "Q8"
    assert saved["workload"]["input_length"] == 192
    assert saved["workload"]["output_length"] == 128
    assert saved["engine"] == "vllm"
    assert saved["metadata"]["idempotency_key"] == entry["metadata"]["idempotency_key"]


def test_collect_entries_requires_manifest(tmp_path: Path) -> None:
    artifact = _canonical_execution_result(workload_name="Q2")
    (tmp_path / "Q2_leaderboard.json").write_text(json.dumps(artifact), encoding="utf-8")

    entries, errors = LeaderboardExporter.collect_entries_from_directory(tmp_path)

    assert entries == []
    assert errors
    assert "leaderboard_manifest.json" in errors[0]
