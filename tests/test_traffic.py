"""测试流量控制模块 - Traffic Control Tests.

测试 ArrivalPattern, TrafficProfile, RequestGenerator, TrafficController 的功能。
"""

from __future__ import annotations

import pytest
from test_helpers import StubClient

from sagellm_benchmark.traffic import (
    ArrivalPattern,
    RequestGenerator,
    TrafficController,
    TrafficProfile,
)
from sagellm_benchmark.types import BenchmarkRequest

# ============================================================================
# Test ArrivalPattern Enum
# ============================================================================


def test_arrival_pattern_enum_values():
    """测试 ArrivalPattern 枚举值."""
    assert ArrivalPattern.INSTANT.value == "instant"
    assert ArrivalPattern.FIXED.value == "fixed"
    assert ArrivalPattern.POISSON.value == "poisson"
    assert ArrivalPattern.GAMMA.value == "gamma"


def test_arrival_pattern_enum_members():
    """测试 ArrivalPattern 枚举成员."""
    patterns = list(ArrivalPattern)
    assert len(patterns) == 4
    assert ArrivalPattern.INSTANT in patterns
    assert ArrivalPattern.FIXED in patterns
    assert ArrivalPattern.POISSON in patterns
    assert ArrivalPattern.GAMMA in patterns


# ============================================================================
# Test TrafficProfile
# ============================================================================


def test_traffic_profile_defaults():
    """测试 TrafficProfile 默认值."""
    profile = TrafficProfile()
    assert profile.pattern == ArrivalPattern.INSTANT
    assert profile.request_rate is None
    assert profile.burstiness == 1.0
    assert profile.duration_s is None
    assert profile.warmup_requests == 0
    assert profile.seed is None


def test_traffic_profile_custom_values():
    """测试 TrafficProfile 自定义值."""
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=10.0,
        burstiness=0.5,
        duration_s=60.0,
        warmup_requests=5,
        seed=42,
    )
    assert profile.pattern == ArrivalPattern.POISSON
    assert profile.request_rate == 10.0
    assert profile.burstiness == 0.5
    assert profile.duration_s == 60.0
    assert profile.warmup_requests == 5
    assert profile.seed == 42


# ============================================================================
# Test RequestGenerator
# ============================================================================


def _create_test_requests(count: int) -> list[BenchmarkRequest]:
    """创建测试请求列表."""
    return [
        BenchmarkRequest(
            prompt=f"Test prompt {i}",
            max_tokens=10,
            request_id=f"req-{i}",
            model="test-model",
            stream=False,
        )
        for i in range(count)
    ]


@pytest.mark.asyncio
async def test_request_generator_instant_mode():
    """测试 INSTANT 模式：所有 delay 应该为 0."""
    requests = _create_test_requests(5)
    profile = TrafficProfile(pattern=ArrivalPattern.INSTANT)
    generator = RequestGenerator(requests, profile)

    delays = []
    request_ids = []
    async for delay, request in generator:
        delays.append(delay)
        request_ids.append(request.request_id)

    assert len(delays) == 5
    assert all(d == 0.0 for d in delays), "INSTANT mode should have zero delays"
    assert request_ids == ["req-0", "req-1", "req-2", "req-3", "req-4"]


@pytest.mark.asyncio
async def test_request_generator_fixed_mode():
    """测试 FIXED 模式：固定间隔（第一个为 0，后续固定）."""
    requests = _create_test_requests(5)
    profile = TrafficProfile(
        pattern=ArrivalPattern.FIXED,
        request_rate=10.0,  # 10 QPS → 0.1s 间隔
        seed=42,
    )
    generator = RequestGenerator(requests, profile)

    delays = []
    async for delay, request in generator:
        delays.append(delay)

    assert len(delays) == 5
    assert delays[0] == 0.0, "First request should have zero delay"
    for d in delays[1:]:
        assert abs(d - 0.1) < 1e-9, f"Expected 0.1s interval, got {d}"


@pytest.mark.asyncio
async def test_request_generator_poisson_mode():
    """测试 POISSON 模式：延迟应该非零且随机."""
    requests = _create_test_requests(10)
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=10.0,  # 10 QPS → 平均 0.1s 间隔
        seed=42,
    )
    generator = RequestGenerator(requests, profile)

    delays = []
    async for delay, request in generator:
        delays.append(delay)

    assert len(delays) == 10
    # 泊松分布应该有非零延迟（几乎所有）
    non_zero_delays = [d for d in delays if d > 0]
    assert len(non_zero_delays) >= 8, "Most delays should be non-zero in POISSON mode"

    # 平均延迟应该接近 0.1s
    avg_delay = sum(delays) / len(delays)
    assert 0.05 < avg_delay < 0.15, f"Average delay {avg_delay} should be around 0.1s"


@pytest.mark.asyncio
async def test_request_generator_gamma_mode():
    """测试 GAMMA 模式：延迟应该非零且随机."""
    requests = _create_test_requests(10)
    profile = TrafficProfile(
        pattern=ArrivalPattern.GAMMA,
        request_rate=10.0,  # 10 QPS → 平均 0.1s 间隔
        burstiness=2.0,  # shape > 1 更均匀
        seed=42,
    )
    generator = RequestGenerator(requests, profile)

    delays = []
    async for delay, request in generator:
        delays.append(delay)

    assert len(delays) == 10
    # Gamma 分布应该有非零延迟
    non_zero_delays = [d for d in delays if d > 0]
    assert len(non_zero_delays) >= 8, "Most delays should be non-zero in GAMMA mode"

    # 平均延迟应该接近 0.1s
    avg_delay = sum(delays) / len(delays)
    assert 0.05 < avg_delay < 0.15, f"Average delay {avg_delay} should be around 0.1s"


@pytest.mark.asyncio
async def test_request_generator_no_rate_limit():
    """测试无速率限制：delay 应该为 0."""
    requests = _create_test_requests(5)
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=None,  # 无速率限制
    )
    generator = RequestGenerator(requests, profile)

    delays = []
    async for delay, request in generator:
        delays.append(delay)

    assert all(d == 0.0 for d in delays), "No rate limit should result in zero delays"


@pytest.mark.asyncio
async def test_request_generator_zero_rate():
    """测试零速率：delay 应该为 0."""
    requests = _create_test_requests(5)
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=0.0,  # 零速率
    )
    generator = RequestGenerator(requests, profile)

    delays = []
    async for delay, request in generator:
        delays.append(delay)

    assert all(d == 0.0 for d in delays), "Zero rate should result in zero delays"


@pytest.mark.asyncio
async def test_request_generator_reproducibility():
    """测试随机种子可复现性."""
    requests = _create_test_requests(5)

    # 第一次运行
    profile1 = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=10.0,
        seed=42,
    )
    generator1 = RequestGenerator(requests, profile1)
    delays1 = [delay async for delay, _ in generator1]

    # 第二次运行（相同种子）
    profile2 = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=10.0,
        seed=42,
    )
    generator2 = RequestGenerator(requests, profile2)
    delays2 = [delay async for delay, _ in generator2]

    # 应该完全相同
    assert delays1 == delays2, "Same seed should produce same delays"


# ============================================================================
# Test TrafficController
# ============================================================================


@pytest.mark.asyncio
async def test_traffic_controller_instant_mode():
    """测试 TrafficController INSTANT 模式."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(pattern=ArrivalPattern.INSTANT)
    controller = TrafficController(client, profile)

    requests = _create_test_requests(5)
    results = await controller.run(requests)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_traffic_controller_fixed_mode():
    """测试 TrafficController FIXED 模式."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.FIXED,
        request_rate=100.0,  # 100 QPS → 0.01s 间隔（快速测试）
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(3)
    results = await controller.run(requests)

    assert len(results) == 3
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_traffic_controller_warmup():
    """测试 TrafficController warmup 机制."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.INSTANT,
        warmup_requests=3,
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(10)  # 10 个请求
    results = await controller.run(requests)

    # 前 3 个是 warmup，应该返回剩余 7 个结果
    assert len(results) == 7
    assert all(r.success for r in results)
    # 验证返回的是后 7 个请求
    expected_ids = [f"req-{i}" for i in range(3, 10)]
    actual_ids = [r.request_id for r in results]
    assert actual_ids == expected_ids


@pytest.mark.asyncio
async def test_traffic_controller_warmup_exceeds_requests():
    """测试 warmup 数量超过请求总数."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.INSTANT,
        warmup_requests=10,  # warmup 10 个
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(5)  # 只有 5 个请求
    results = await controller.run(requests)

    # 所有请求都用于 warmup，正式测试应该返回空列表
    assert len(results) == 0


@pytest.mark.asyncio
async def test_traffic_controller_no_warmup():
    """测试 TrafficController 无 warmup."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.INSTANT,
        warmup_requests=0,
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(5)
    results = await controller.run(requests)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_traffic_controller_poisson_mode():
    """测试 TrafficController POISSON 模式."""
    client = StubClient(ttft_ms=5.0, tbt_ms=2.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=50.0,  # 50 QPS（快速测试）
        seed=42,
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(5)
    results = await controller.run(requests)

    assert len(results) == 5
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_traffic_controller_empty_requests():
    """测试 TrafficController 空请求列表."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)
    profile = TrafficProfile(pattern=ArrivalPattern.INSTANT)
    controller = TrafficController(client, profile)

    results = await controller.run([])

    assert len(results) == 0


@pytest.mark.asyncio
async def test_traffic_controller_gamma_mode():
    """测试 TrafficController GAMMA 模式."""
    client = StubClient(ttft_ms=5.0, tbt_ms=2.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.GAMMA,
        request_rate=50.0,  # 50 QPS
        burstiness=1.5,
        seed=42,
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(5)
    results = await controller.run(requests)

    assert len(results) == 5
    assert all(r.success for r in results)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_traffic_controller_integration():
    """集成测试：完整流程."""
    client = StubClient(ttft_ms=10.0, tbt_ms=5.0)

    # 配置：POISSON 模式，10 QPS，2 个 warmup
    profile = TrafficProfile(
        pattern=ArrivalPattern.POISSON,
        request_rate=100.0,  # 快速测试
        warmup_requests=2,
        seed=42,
    )

    controller = TrafficController(client, profile)
    requests = _create_test_requests(10)

    results = await controller.run(requests)

    # 验证结果
    assert len(results) == 8, "Should have 8 results (10 - 2 warmup)"
    assert all(r.success for r in results), "All requests should succeed"

    # 验证请求 ID
    expected_ids = [f"req-{i}" for i in range(2, 10)]
    actual_ids = [r.request_id for r in results]
    assert actual_ids == expected_ids


@pytest.mark.asyncio
async def test_request_order_preserved():
    """测试请求顺序保持一致."""
    client = StubClient(ttft_ms=5.0, tbt_ms=2.0)
    profile = TrafficProfile(
        pattern=ArrivalPattern.FIXED,
        request_rate=100.0,
    )
    controller = TrafficController(client, profile)

    requests = _create_test_requests(10)
    results = await controller.run(requests)

    # 验证顺序
    expected_ids = [f"req-{i}" for i in range(10)]
    actual_ids = [r.request_id for r in results]
    assert actual_ids == expected_ids, "Request order should be preserved"
