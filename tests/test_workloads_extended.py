"""Tests for extended workload coverage (#1, #12).

Covers: new WorkloadType variants, WorkloadConfig new fields,
WorkloadLoader (JSON/YAML), WorkloadTemplateGenerator, and
get_workloads_by_selector for new selectors.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sagellm_benchmark.workloads import (
    BATCH_INFERENCE_WORKLOADS,
    MIXED_WORKLOADS,
    STREAMING_WORKLOADS,
    WorkloadConfig,
    WorkloadLoader,
    WorkloadTemplateGenerator,
    WorkloadType,
    get_workloads_by_selector,
)

# ---------------------------------------------------------------------------
# New WorkloadType values
# ---------------------------------------------------------------------------


def test_workload_type_streaming_exists() -> None:
    assert WorkloadType.STREAMING == "streaming"


def test_workload_type_batch_inference_exists() -> None:
    assert WorkloadType.BATCH_INFERENCE == "batch_inference"


def test_workload_type_mixed_exists() -> None:
    assert WorkloadType.MIXED == "mixed"


# ---------------------------------------------------------------------------
# New WorkloadConfig fields
# ---------------------------------------------------------------------------


def test_workload_config_new_fields_defaults() -> None:
    w = WorkloadConfig(
        name="test",
        workload_type=WorkloadType.SHORT,
        prompt="hello",
        prompt_tokens=8,
        max_tokens=16,
    )
    assert w.top_k is None
    assert w.repetition_penalty == 1.0
    assert w.stream is False
    assert w.warmup_rounds == 0
    assert w.concurrency is None


def test_workload_config_new_fields_set() -> None:
    w = WorkloadConfig(
        name="custom",
        workload_type=WorkloadType.STREAMING,
        prompt="hi",
        prompt_tokens=4,
        max_tokens=32,
        top_k=50,
        repetition_penalty=1.1,
        stream=True,
        warmup_rounds=2,
        concurrency=4,
    )
    assert w.top_k == 50
    assert w.repetition_penalty == 1.1
    assert w.stream is True
    assert w.warmup_rounds == 2
    assert w.concurrency == 4


# ---------------------------------------------------------------------------
# Predefined workload lists
# ---------------------------------------------------------------------------


def test_streaming_workloads_non_empty() -> None:
    assert len(STREAMING_WORKLOADS) >= 3


def test_streaming_workloads_use_stream_flag() -> None:
    assert all(w.stream for w in STREAMING_WORKLOADS)


def test_streaming_workloads_type() -> None:
    assert all(w.workload_type == WorkloadType.STREAMING for w in STREAMING_WORKLOADS)


def test_batch_inference_workloads_non_empty() -> None:
    assert len(BATCH_INFERENCE_WORKLOADS) >= 3


def test_batch_inference_workloads_type() -> None:
    assert all(w.workload_type == WorkloadType.BATCH_INFERENCE for w in BATCH_INFERENCE_WORKLOADS)


def test_batch_inference_workloads_concurrent() -> None:
    assert all(w.concurrent for w in BATCH_INFERENCE_WORKLOADS)


def test_mixed_workloads_non_empty() -> None:
    assert len(MIXED_WORKLOADS) >= 3


def test_mixed_workloads_type() -> None:
    assert all(w.workload_type == WorkloadType.MIXED for w in MIXED_WORKLOADS)


# ---------------------------------------------------------------------------
# get_workloads_by_selector — new selectors
# ---------------------------------------------------------------------------


def test_selector_streaming() -> None:
    result = get_workloads_by_selector("streaming")
    assert result is STREAMING_WORKLOADS


def test_selector_batch() -> None:
    result = get_workloads_by_selector("batch")
    assert result is BATCH_INFERENCE_WORKLOADS


def test_selector_batch_inference() -> None:
    result = get_workloads_by_selector("batch_inference")
    assert result is BATCH_INFERENCE_WORKLOADS


def test_selector_mixed() -> None:
    result = get_workloads_by_selector("mixed")
    assert result is MIXED_WORKLOADS


# ---------------------------------------------------------------------------
# WorkloadLoader — JSON
# ---------------------------------------------------------------------------


def test_loader_load_json() -> None:
    data = {
        "workloads": [
            {
                "name": "my_custom",
                "workload_type": "short",
                "prompt": "Hello there",
                "prompt_tokens": 8,
                "max_tokens": 32,
                "num_requests": 3,
                "temperature": 0.7,
                "top_k": 40,
                "warmup_rounds": 1,
            }
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        tmp = Path(f.name)

    try:
        workloads = WorkloadLoader.load(tmp)
        assert len(workloads) == 1
        w = workloads[0]
        assert w.name == "my_custom"
        assert w.workload_type == WorkloadType.SHORT
        assert w.prompt == "Hello there"
        assert w.top_k == 40
        assert w.warmup_rounds == 1
    finally:
        tmp.unlink()


def test_loader_load_json_list_format() -> None:
    """Flat list format (no 'workloads' key)."""
    data = [
        {
            "name": "flat_workload",
            "workload_type": "streaming",
            "prompt": "Test prompt",
            "prompt_tokens": 16,
            "max_tokens": 64,
        }
    ]
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        tmp = Path(f.name)

    try:
        workloads = WorkloadLoader.load(tmp)
        assert len(workloads) == 1
        assert workloads[0].workload_type == WorkloadType.STREAMING
    finally:
        tmp.unlink()


def test_loader_file_not_found() -> None:
    with pytest.raises(FileNotFoundError):
        WorkloadLoader.load("/nonexistent/path/workloads.json")


def test_loader_unsupported_format() -> None:
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        f.write(b"<workloads/>")
        tmp = Path(f.name)
    try:
        with pytest.raises(ValueError, match="Unsupported workload config format"):
            WorkloadLoader.load(tmp)
    finally:
        tmp.unlink()


def test_loader_unknown_workload_type_raises() -> None:
    data = {
        "workloads": [
            {
                "name": "bad",
                "workload_type": "invalid_type",
                "prompt": "test",
                "prompt_tokens": 8,
                "max_tokens": 16,
            }
        ]
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(data, f)
        tmp = Path(f.name)
    try:
        with pytest.raises(ValueError, match="Unknown workload_type"):
            WorkloadLoader.load(tmp)
    finally:
        tmp.unlink()


# ---------------------------------------------------------------------------
# WorkloadTemplateGenerator — JSON
# ---------------------------------------------------------------------------


def test_template_generator_json() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = Path(f.name)
    try:
        content = WorkloadTemplateGenerator.generate_json(tmp)
        assert tmp.exists()
        data = json.loads(content)
        assert "workloads" in data
        assert len(data["workloads"]) >= 1
        # Each template workload must have required keys
        for w in data["workloads"]:
            assert "name" in w
            assert "workload_type" in w
            assert "prompt" in w
    finally:
        tmp.unlink()


def test_template_generator_json_loadable() -> None:
    """Templates generated by generator must be loadable by WorkloadLoader."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp = Path(f.name)
    try:
        WorkloadTemplateGenerator.generate_json(tmp)
        loaded = WorkloadLoader.load(tmp)
        assert len(loaded) >= 1
    finally:
        tmp.unlink()
