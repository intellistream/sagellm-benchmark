"""测试 MetricsAggregator 和 ContractVerifier。"""

from __future__ import annotations

import pytest
from sagellm_protocol import Metrics, Timestamps

from sagellm_benchmark.metrics import ContractVerifier, MetricsAggregator
from sagellm_benchmark.types import BenchmarkResult, ContractVersion


@pytest.fixture
def sample_results() -> list[BenchmarkResult]:
    """创建 5 个示例 BenchmarkResult。"""
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


def test_aggregator_basic(sample_results: list[BenchmarkResult]) -> None:
    """测试基本聚合功能。"""
    aggregated = MetricsAggregator.aggregate(sample_results)

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


def test_contract_year1_pass(sample_results: list[BenchmarkResult]) -> None:
    """测试 Year1 Contract 通过。"""
    aggregated = MetricsAggregator.aggregate(sample_results)

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


# ==================== ITL/E2EL Aggregation Tests ====================


def _create_sample_metrics() -> Metrics:
    """创建示例 Metrics 用于测试。"""
    return Metrics(
        ttft_ms=10.0,
        tbt_ms=2.0,
        tpot_ms=2.5,
        throughput_tps=100.0,
        peak_mem_mb=1024,
        error_rate=0.0,
        kv_used_tokens=128,
        kv_used_bytes=128 * 16,
        prefix_hit_rate=0.8,
        evict_count=0,
        evict_ms=0.0,
        spec_accept_rate=0.7,
        timestamps=Timestamps(
            queued_at=1000.0,
            scheduled_at=1001.0,
            executed_at=1002.0,
            completed_at=1003.0,
        ),
    )


def test_itl_aggregation() -> None:
    """测试 ITL 聚合。"""
    results = [
        BenchmarkResult(
            request_id="r1",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[10.0, 12.0, 11.0, 15.0, 13.0],
            e2e_latency_ms=100.0,
            output_tokens=5,
        ),
        BenchmarkResult(
            request_id="r2",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[9.0, 11.0, 14.0, 12.0, 10.0],
            e2e_latency_ms=95.0,
            output_tokens=5,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)

    # ITL 应该是 10 个样本的统计（展平后）
    # 样本：[10.0, 12.0, 11.0, 15.0, 13.0, 9.0, 11.0, 14.0, 12.0, 10.0]
    assert aggregated.avg_itl_ms > 0
    assert aggregated.avg_itl_ms == pytest.approx(
        11.7, rel=0.01
    )  # (10+12+11+15+13+9+11+14+12+10)/10
    assert aggregated.p50_itl_ms > 0
    assert aggregated.p95_itl_ms >= aggregated.p50_itl_ms
    assert aggregated.p99_itl_ms >= aggregated.p95_itl_ms
    assert aggregated.std_itl_ms > 0

    # E2EL
    assert aggregated.avg_e2el_ms == pytest.approx(97.5, rel=0.01)
    assert aggregated.p50_e2el_ms > 0
    assert aggregated.p95_e2el_ms >= aggregated.p50_e2el_ms
    assert aggregated.std_e2el_ms > 0


def test_empty_itl_list() -> None:
    """测试空 ITL 列表不应导致异常。"""
    results = [
        BenchmarkResult(
            request_id="r1",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[],  # 空列表
            e2e_latency_ms=0.0,
            output_tokens=0,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)

    # 空 ITL 应返回 0.0，不抛异常
    assert aggregated.avg_itl_ms == 0.0
    assert aggregated.p50_itl_ms == 0.0
    assert aggregated.p95_itl_ms == 0.0
    assert aggregated.p99_itl_ms == 0.0
    assert aggregated.std_itl_ms == 0.0

    # E2EL 也为 0（过滤掉 <= 0 的样本）
    assert aggregated.avg_e2el_ms == 0.0


def test_single_itl_sample_no_std() -> None:
    """测试单样本时 std 应为 0。"""
    results = [
        BenchmarkResult(
            request_id="r1",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[10.0],  # 单样本
            e2e_latency_ms=100.0,
            output_tokens=1,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)

    # 单样本 std 应为 0.0
    assert aggregated.avg_itl_ms == 10.0
    assert aggregated.std_itl_ms == 0.0

    # E2EL 单样本 std 也应为 0.0
    assert aggregated.avg_e2el_ms == 100.0
    assert aggregated.std_e2el_ms == 0.0


def test_partial_itl_list() -> None:
    """测试部分请求有 ITL，部分没有。"""
    results = [
        BenchmarkResult(
            request_id="r1",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[10.0, 12.0, 11.0],
            e2e_latency_ms=100.0,
            output_tokens=3,
        ),
        BenchmarkResult(
            request_id="r2",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[],  # 空
            e2e_latency_ms=80.0,
            output_tokens=0,
        ),
        BenchmarkResult(
            request_id="r3",
            success=True,
            error=None,
            metrics=_create_sample_metrics(),
            itl_list=[9.0, 11.0],
            e2e_latency_ms=90.0,
            output_tokens=2,
        ),
    ]

    aggregated = MetricsAggregator.aggregate(results)

    # 只统计非空的 ITL：[10.0, 12.0, 11.0, 9.0, 11.0] = 5 样本
    assert aggregated.avg_itl_ms == pytest.approx(10.6, rel=0.01)
    assert aggregated.std_itl_ms > 0

    # E2EL 统计：[100.0, 80.0, 90.0] = 3 样本
    assert aggregated.avg_e2el_ms == pytest.approx(90.0, rel=0.01)
