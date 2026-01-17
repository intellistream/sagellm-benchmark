"""测试 MetricsAggregator 和 ContractVerifier。"""

from __future__ import annotations

import pytest
from sagellm_protocol import Metrics, Timestamps

from sagellm_benchmark.metrics import ContractVerifier, MetricsAggregator
from sagellm_benchmark.types import BenchmarkResult, ContractVersion


@pytest.fixture
def mock_results() -> list[BenchmarkResult]:
    """创建 5 个 mock BenchmarkResult。"""
    results = []

    for i in range(5):
        timestamps = Timestamps(
            queued_at=1000.0 + i * 10.0,
            scheduled_at=1000.0 + i * 10.0 + 1.0,
            executed_at=1000.0 + i * 10.0 + 2.0,
            completed_at=1000.0 + i * 10.0 + 3.0,
        )

        metrics = Metrics(
            ttft_ms=10.0 + i * 5.0,  # 10, 15, 20, 25, 30
            tbt_ms=2.0 + i * 1.0,  # 2, 3, 4, 5, 6
            tpot_ms=2.5 + i * 0.5,  # 2.5, 3.0, 3.5, 4.0, 4.5
            throughput_tps=100.0 - i * 10.0,  # 100, 90, 80, 70, 60
            peak_mem_mb=1024 + i * 256,  # 1024, 1280, 1536, 1792, 2048
            error_rate=0.0,  # 添加必填字段
            kv_used_tokens=128 + i * 32,  # 128, 160, 192, 224, 256
            kv_used_bytes=(128 + i * 32) * 16,
            prefix_hit_rate=0.8 + i * 0.02,  # 0.8, 0.82, 0.84, 0.86, 0.88
            evict_count=i,  # 0, 1, 2, 3, 4
            evict_ms=0.5 * i,  # 0, 0.5, 1.0, 1.5, 2.0
            spec_accept_rate=0.7 + i * 0.01,  # 0.7, 0.71, 0.72, 0.73, 0.74
            timestamps=timestamps,
        )

        result = BenchmarkResult(
            request_id=f"req-{i}",
            success=True,
            error=None,
            metrics=metrics,
            output_text=f"Output {i}",
            output_tokens=50 + i * 10,  # 50, 60, 70, 80, 90
            prompt_tokens=100,
        )

        results.append(result)

    return results


def test_aggregator_basic(mock_results: list[BenchmarkResult]) -> None:
    """测试基本聚合功能。"""
    aggregated = MetricsAggregator.aggregate(mock_results)

    # 验证总数
    assert aggregated.total_requests == 5
    assert aggregated.successful_requests == 5
    assert aggregated.failed_requests == 0
    assert aggregated.error_rate == 0.0

    # 验证 TTFT（10, 15, 20, 25, 30）
    assert aggregated.avg_ttft_ms == pytest.approx(20.0, abs=0.1)  # (10+15+20+25+30)/5
    assert aggregated.p50_ttft_ms == 20.0  # 中位数
    assert aggregated.p95_ttft_ms == 30.0  # P95
    assert aggregated.p99_ttft_ms == 30.0  # P99

    # 验证 TBT（2, 3, 4, 5, 6）
    assert aggregated.avg_tbt_ms == pytest.approx(4.0, abs=0.1)

    # 验证内存（取 max）
    assert aggregated.peak_mem_mb == 2048

    # 验证 KV Cache（取 sum）
    assert aggregated.total_kv_used_tokens == 128 + 160 + 192 + 224 + 256  # 960
    assert aggregated.total_evict_count == 0 + 1 + 2 + 3 + 4  # 10


def test_aggregator_with_failures() -> None:
    """测试包含失败请求的情况。"""
    results = [
        BenchmarkResult(
            request_id="req-1",
            success=True,
            error=None,
            metrics=Metrics(
                ttft_ms=10.0,
                tbt_ms=2.0,
                tpot_ms=2.5,
                throughput_tps=100.0,
                peak_mem_mb=1024,
                error_rate=0.0,
                timestamps=Timestamps(
                    queued_at=1000.0,
                    scheduled_at=1001.0,
                    executed_at=1002.0,
                    completed_at=1003.0,
                ),
            ),
            output_tokens=50,
        ),
        BenchmarkResult(
            request_id="req-2",
            success=False,
            error="Timeout",
            metrics=None,
        ),
        BenchmarkResult(
            request_id="req-3",
            success=True,
            error=None,
            metrics=Metrics(
                ttft_ms=20.0,
                tbt_ms=4.0,
                tpot_ms=4.5,
                throughput_tps=80.0,
                peak_mem_mb=2048,
                error_rate=0.0,
                timestamps=Timestamps(
                    queued_at=1010.0,
                    scheduled_at=1011.0,
                    executed_at=1012.0,
                    completed_at=1013.0,
                ),
            ),
            output_tokens=70,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)

    assert aggregated.total_requests == 3
    assert aggregated.successful_requests == 2
    assert aggregated.failed_requests == 1
    assert aggregated.error_rate == pytest.approx(1 / 3, abs=0.01)


def test_contract_year1_pass(mock_results: list[BenchmarkResult]) -> None:
    """测试 Year1 Contract 通过。"""
    aggregated = MetricsAggregator.aggregate(mock_results)

    # Year1 阈值: ttft<100ms, tbt<20ms, tpot<20ms, throughput>50, error_rate<0.05
    result = ContractVerifier.verify(aggregated, ContractVersion.YEAR1)

    assert result.passed is True
    assert result.version == ContractVersion.YEAR1
    assert "ttft_ms" in result.checks
    assert result.checks["ttft_ms"] is True  # 20ms < 100ms


def test_contract_year2_fail() -> None:
    """测试 Year2 Contract 失败（prefix_hit_rate 不足）。"""
    results = [
        BenchmarkResult(
            request_id="req-1",
            success=True,
            error=None,
            metrics=Metrics(
                ttft_ms=40.0,  # < 50ms (Year2)
                tbt_ms=8.0,  # < 10ms
                tpot_ms=8.0,  # < 10ms
                throughput_tps=120.0,  # > 100
                peak_mem_mb=20000,  # < 24576
                error_rate=0.0,
                prefix_hit_rate=0.5,  # < 0.7 (Year2 要求) - 不满足
                timestamps=Timestamps(
                    queued_at=1000.0,
                    scheduled_at=1001.0,
                    executed_at=1002.0,
                    completed_at=1003.0,
                ),
            ),
            output_tokens=50,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)
    result = ContractVerifier.verify(aggregated, ContractVersion.YEAR2)

    assert result.passed is False
    assert "prefix_hit_rate" in result.checks
    assert result.checks["prefix_hit_rate"] is False


def test_contract_year3_all_checks() -> None:
    """测试 Year3 Contract 所有检查项。"""
    results = [
        BenchmarkResult(
            request_id="req-1",
            success=True,
            error=None,
            metrics=Metrics(
                ttft_ms=25.0,  # < 30ms ✅
                tbt_ms=4.0,  # < 5ms ✅
                tpot_ms=4.0,  # < 5ms ✅
                throughput_tps=220.0,  # > 200 ✅
                peak_mem_mb=15000,  # < 16384 ✅
                error_rate=0.0,
                prefix_hit_rate=0.9,  # > 0.85 ✅
                spec_accept_rate=0.7,  # > 0.6 ✅
                timestamps=Timestamps(
                    queued_at=1000.0,
                    scheduled_at=1001.0,
                    executed_at=1002.0,
                    completed_at=1003.0,
                ),
            ),
            output_tokens=50,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)
    result = ContractVerifier.verify(aggregated, ContractVersion.YEAR3)

    assert result.passed is True
    assert all(result.checks.values())
    assert "spec_accept_rate" in result.checks
