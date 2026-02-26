"""Tests for MultiEngineRunner and EngineType (#4, #12)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sagellm_benchmark.clients import EngineInfo, EngineType, MultiEngineRunner
from sagellm_benchmark.clients.base import BenchmarkClient
from sagellm_benchmark.types import AggregatedMetrics, BenchmarkRequest, BenchmarkResult

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Minimal simulated client for testing
# ---------------------------------------------------------------------------


class SimulatedBenchmarkClient(BenchmarkClient):
    """Simulated client that returns synthetic results."""

    def __init__(self, latency_ms: float = 20.0, fail: bool = False) -> None:
        super().__init__(name="simulated")
        self.latency_ms = latency_ms
        self.fail = fail
        self.call_count = 0

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        self.call_count += 1
        if self.fail:
            raise RuntimeError("Simulated backend failure")
        from sagellm_protocol import Metrics

        tbt_ms = self.latency_ms / 5
        output_tokens = request.max_tokens or 16
        total_time_s = (self.latency_ms + tbt_ms * output_tokens) / 1000
        metrics = Metrics(
            ttft_ms=self.latency_ms,
            tbt_ms=tbt_ms,
            tpot_ms=tbt_ms,
            throughput_tps=output_tokens / total_time_s if total_time_s > 0 else 0.0,
            peak_mem_mb=256,
            error_rate=0.0,
        )
        return BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            output_text="simulated output",
            output_tokens=output_tokens,
            prompt_tokens=32,
            metrics=metrics,
        )


def _make_requests(n: int = 3) -> list[BenchmarkRequest]:
    from uuid import uuid4

    return [
        BenchmarkRequest(
            prompt="Test prompt",
            max_tokens=16,
            request_id=str(uuid4()),
            model="simulated",
        )
        for _ in range(n)
    ]


def _make_workload():
    from sagellm_benchmark.workloads import WorkloadConfig, WorkloadType

    return WorkloadConfig(
        name="test_wl",
        workload_type=WorkloadType.SHORT,
        prompt="Test",
        prompt_tokens=8,
        max_tokens=16,
        num_requests=3,
        warmup_rounds=0,
    )


# ---------------------------------------------------------------------------
# EngineType enum tests
# ---------------------------------------------------------------------------


def test_engine_type_values() -> None:
    assert EngineType.SAGELLM == "sagellm"
    assert EngineType.OPENAI == "openai"
    assert EngineType.VLLM == "vllm"
    assert EngineType.LMDEPLOY == "lmdeploy"
    assert EngineType.ASCEND == "ascend"
    assert EngineType.SIMULATED == "simulated"


def test_engine_type_is_str_enum() -> None:
    assert isinstance(EngineType.SAGELLM, str)


# ---------------------------------------------------------------------------
# EngineInfo tests
# ---------------------------------------------------------------------------


def test_engine_info_default_label() -> None:
    client = SimulatedBenchmarkClient()
    info = EngineInfo(engine_type=EngineType.SIMULATED, client=client)
    assert info.label == "simulated"


def test_engine_info_custom_label() -> None:
    client = SimulatedBenchmarkClient()
    info = EngineInfo(engine_type=EngineType.SAGELLM, client=client, label="SageLLM-CPU")
    assert info.label == "SageLLM-CPU"


def test_engine_info_tags() -> None:
    client = SimulatedBenchmarkClient()
    info = EngineInfo(
        engine_type=EngineType.SIMULATED,
        client=client,
        tags={"model": "Qwen2-7B", "hardware": "CPU"},
    )
    assert info.tags["model"] == "Qwen2-7B"


# ---------------------------------------------------------------------------
# MultiEngineRunner tests
# ---------------------------------------------------------------------------


def test_multi_engine_runner_requires_engines() -> None:
    with pytest.raises(ValueError, match="At least one engine"):
        MultiEngineRunner(engines=[])


def test_multi_engine_runner_init() -> None:
    client = SimulatedBenchmarkClient()
    engine = EngineInfo(engine_type=EngineType.SIMULATED, client=client, label="simulated-1")
    runner = MultiEngineRunner(engines=[engine])
    assert len(runner.engines) == 1


@pytest.mark.asyncio
async def test_multi_engine_runner_single_engine() -> None:
    client = SimulatedBenchmarkClient(latency_ms=15.0)
    engine = EngineInfo(engine_type=EngineType.SIMULATED, client=client, label="simulated-fast")
    runner = MultiEngineRunner(engines=[engine])

    workload = _make_workload()
    requests = _make_requests(2)

    results = await runner.run_workload(workload, requests)

    assert len(results) == 1
    assert results[0].engine_label == "simulated-fast"
    assert results[0].success
    assert results[0].error is None
    assert isinstance(results[0].metrics, AggregatedMetrics)


@pytest.mark.asyncio
async def test_multi_engine_runner_two_engines() -> None:
    e1 = EngineInfo(
        engine_type=EngineType.SAGELLM,
        client=SimulatedBenchmarkClient(latency_ms=10.0),
        label="fast",
    )
    e2 = EngineInfo(
        engine_type=EngineType.SIMULATED,
        client=SimulatedBenchmarkClient(latency_ms=30.0),
        label="slow",
    )
    runner = MultiEngineRunner(engines=[e1, e2])

    workload = _make_workload()
    requests = _make_requests(2)

    results = await runner.run_workload(workload, requests)

    assert len(results) == 2
    labels = [r.engine_label for r in results]
    assert "fast" in labels
    assert "slow" in labels
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_multi_engine_runner_failed_engine() -> None:
    """Failed engine should return error result, not raise."""
    e1 = EngineInfo(
        engine_type=EngineType.SIMULATED,
        client=SimulatedBenchmarkClient(fail=True),
        label="bad-engine",
    )
    runner = MultiEngineRunner(engines=[e1])
    workload = _make_workload()
    requests = _make_requests(1)

    results = await runner.run_workload(workload, requests)

    assert len(results) == 1
    assert not results[0].success
    assert results[0].error is not None


def test_multi_engine_exported_from_clients() -> None:
    from sagellm_benchmark.clients import (
        EngineInfo,  # noqa: F401
        EngineType,  # noqa: F401
        MultiEngineRunner,  # noqa: F401
    )

    assert EngineType.SAGELLM == "sagellm"
    assert EngineInfo is not None
    assert MultiEngineRunner is not None
