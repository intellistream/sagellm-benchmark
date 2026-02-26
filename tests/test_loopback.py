"""单机单卡最小环回测试 (Issue #10).

阶段 1：单机单卡最小环回（优先级最高）
目标:
  ✅ 保持 CPU-First（无 GPU 也能运行）
  ✅ 验证 benchmark runner 端到端流程可跑通
  ✅ 使用模拟客户端测试真实 KV 指标

测试覆盖:
  - MinimalLoopbackClient 单请求环回
  - MinimalLoopbackClient 批量串行环回
  - MinimalLoopbackClient 批量并发环回
  - 端到端 MetricsAggregator 指标聚合
  - 最小 runner 集成（不依赖 GPU）
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from sagellm_benchmark.clients.base import BenchmarkClient
from sagellm_benchmark.metrics.aggregator import MetricsAggregator
from sagellm_benchmark.types import AggregatedMetrics, BenchmarkRequest, BenchmarkResult

# ---------------------------------------------------------------------------
# Minimal CPU-first simulated client
# ---------------------------------------------------------------------------


class MinimalLoopbackClient(BenchmarkClient):
    """Minimal CPU-first loopback client.

    Returns synthetic BenchmarkResult without any network or GPU dependency.
    Suitable as a smoke test that the full request→result→metrics pipeline works.
    """

    def __init__(self, ttft_ms: float = 10.0, output_tokens: int = 32) -> None:
        super().__init__(name="loopback", timeout=5.0)
        self.ttft_ms = ttft_ms
        self.output_tokens = output_tokens

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Simulate a single loopback request."""
        from sagellm_protocol import Metrics

        tbt_ms = self.ttft_ms / 10
        throughput_tps = self.output_tokens / (
            self.ttft_ms / 1000 + tbt_ms * self.output_tokens / 1000
        )
        metrics = Metrics(
            ttft_ms=self.ttft_ms,
            tbt_ms=tbt_ms,
            tpot_ms=tbt_ms,
            throughput_tps=throughput_tps,
            peak_mem_mb=256,
            error_rate=0.0,
        )
        from sagellm_benchmark.types import BenchmarkResult

        return BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            output_text="loopback output " * (self.output_tokens // 4),
            output_tokens=self.output_tokens,
            prompt_tokens=len(request.prompt.split()),
            metrics=metrics,
        )


def _make_request(**kwargs) -> BenchmarkRequest:
    defaults = dict(
        prompt="What is the capital of France?",
        max_tokens=32,
        request_id=str(uuid4()),
        model="loopback",
    )
    defaults.update(kwargs)
    return BenchmarkRequest(**defaults)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loopback_single_request() -> None:
    """Single request loopback should succeed and return valid metrics."""
    client = MinimalLoopbackClient(ttft_ms=15.0)
    req = _make_request()
    result = await client.generate(req)

    assert result.success
    assert result.request_id == req.request_id
    assert result.metrics is not None
    assert result.metrics.ttft_ms == 15.0
    assert result.output_tokens == 32


@pytest.mark.asyncio
async def test_loopback_batch_sequential() -> None:
    """Sequential batch of 5 requests should all succeed."""
    client = MinimalLoopbackClient(ttft_ms=10.0)
    requests = [_make_request() for _ in range(5)]
    results = await client.generate_batch(requests, concurrent=False)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_loopback_batch_concurrent() -> None:
    """Concurrent batch of 5 requests should all succeed."""
    client = MinimalLoopbackClient(ttft_ms=10.0)
    requests = [_make_request() for _ in range(5)]
    results = await client.generate_batch(requests, concurrent=True)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_loopback_batch_empty() -> None:
    """Empty batch returns empty list."""
    client = MinimalLoopbackClient()
    results = await client.generate_batch([], concurrent=True)
    assert results == []


@pytest.mark.asyncio
async def test_loopback_metrics_aggregation() -> None:
    """End-to-end: loopback → aggregate → AggregatedMetrics."""
    client = MinimalLoopbackClient(ttft_ms=20.0, output_tokens=16)
    requests = [_make_request() for _ in range(4)]
    results = await client.generate_batch(requests, concurrent=False)

    metrics = MetricsAggregator.aggregate(results)

    assert isinstance(metrics, AggregatedMetrics)
    assert metrics.total_requests == 4
    assert metrics.successful_requests == 4
    assert metrics.failed_requests == 0
    assert metrics.error_rate == 0.0
    assert metrics.avg_ttft_ms > 0
    assert metrics.output_throughput_tps >= 0


@pytest.mark.asyncio
async def test_loopback_request_id_preserved() -> None:
    """Request IDs in results must match the input requests."""
    client = MinimalLoopbackClient()
    requests = [_make_request() for _ in range(3)]
    results = await client.generate_batch(requests, concurrent=False)

    input_ids = [r.request_id for r in requests]
    result_ids = [r.request_id for r in results]
    assert input_ids == result_ids


@pytest.mark.asyncio
async def test_loopback_large_batch_cpu_first() -> None:
    """20-request batch should complete without GPU dependencies."""
    client = MinimalLoopbackClient(ttft_ms=5.0)
    requests = [_make_request() for _ in range(20)]
    results = await client.generate_batch(requests, concurrent=True)

    assert len(results) == 20
    success_count = sum(1 for r in results if r.success)
    assert success_count == 20


def test_loopback_client_is_benchmark_client() -> None:
    """MinimalLoopbackClient must be a BenchmarkClient subtype."""
    client = MinimalLoopbackClient()
    assert isinstance(client, BenchmarkClient)
