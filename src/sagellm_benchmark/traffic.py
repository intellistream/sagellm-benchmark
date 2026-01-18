"""流量控制模块 - Traffic Control Layer.

此模块提供多种请求到达模式和流量控制功能：
- ArrivalPattern: 请求到达模式枚举（INSTANT/FIXED/POISSON/GAMMA）
- TrafficProfile: 流量配置数据类
- RequestGenerator: 请求发生器（生成带延迟的请求序列）
- TrafficController: 流量控制器（封装完整压测流程）

参考 vLLM 的请求发生器设计，但保持简洁独立。
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sagellm_benchmark.clients.base import BenchmarkClient
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class ArrivalPattern(str, Enum):
    """请求到达模式枚举.

    Attributes:
        INSTANT: 立即发送所有请求（现有行为，兼容旧代码）
        FIXED: 固定间隔发送
        POISSON: 泊松分布（指数间隔）
        GAMMA: Gamma 分布（支持突发流量控制）
    """

    INSTANT = "instant"
    FIXED = "fixed"
    POISSON = "poisson"
    GAMMA = "gamma"


@dataclass
class TrafficProfile:
    """流量配置数据类.

    Attributes:
        pattern: 到达模式，默认 INSTANT（兼容现有行为）。
        request_rate: 请求速率（请求/秒），None 表示不限速。
        burstiness: Gamma 分布形状参数，1.0 = 泊松，<1 更突发，>1 更均匀。
        duration_s: 持续时间（秒），None 表示发完所有请求即停止。
        warmup_requests: 预热请求数（不计入统计）。
        seed: 随机种子（用于可复现测试）。

    Example:
        >>> # 泊松分布，10 QPS，5 个预热请求
        >>> profile = TrafficProfile(
        ...     pattern=ArrivalPattern.POISSON,
        ...     request_rate=10.0,
        ...     warmup_requests=5,
        ...     seed=42,
        ... )
        >>> # 固定间隔，20 QPS
        >>> profile = TrafficProfile(
        ...     pattern=ArrivalPattern.FIXED,
        ...     request_rate=20.0,
        ... )
    """

    pattern: ArrivalPattern = ArrivalPattern.INSTANT
    request_rate: float | None = None
    burstiness: float = 1.0
    duration_s: float | None = None
    warmup_requests: int = 0
    seed: int | None = None


class RequestGenerator:
    """请求发生器 - 根据 TrafficProfile 控制请求发射节奏.

    根据配置的流量模式生成带延迟的请求序列。支持：
    - INSTANT: 所有请求延迟为 0（并发执行）
    - FIXED: 固定间隔
    - POISSON: 泊松分布（指数间隔）
    - GAMMA: Gamma 分布（可控突发）

    Example:
        >>> profile = TrafficProfile(
        ...     pattern=ArrivalPattern.POISSON,
        ...     request_rate=10.0,
        ...     seed=42,
        ... )
        >>> generator = RequestGenerator(requests, profile)
        >>> async for delay, request in generator:
        ...     await asyncio.sleep(delay)
        ...     result = await client.generate(request)
    """

    def __init__(
        self,
        requests: list[BenchmarkRequest],
        profile: TrafficProfile,
    ) -> None:
        """初始化请求发生器.

        Args:
            requests: 要发送的请求列表。
            profile: 流量配置。
        """
        self.requests = requests
        self.profile = profile
        self._rng = random.Random(profile.seed)
        logger.debug(
            f"RequestGenerator initialized: pattern={profile.pattern.value}, "
            f"rate={profile.request_rate}, requests={len(requests)}"
        )

    def __aiter__(self) -> AsyncIterator[tuple[float, BenchmarkRequest]]:
        """返回异步迭代器."""
        return self._generate()

    async def _generate(self) -> AsyncIterator[tuple[float, BenchmarkRequest]]:
        """生成 (delay_seconds, request) 序列.

        Yields:
            tuple[float, BenchmarkRequest]: (延迟秒数, 请求对象)
        """
        for i, request in enumerate(self.requests):
            delay = self._compute_delay(i)
            yield delay, request

    def _compute_delay(self, index: int) -> float:
        """根据模式计算下一个请求的延迟.

        Args:
            index: 请求序号（从 0 开始）。

        Returns:
            延迟秒数（>= 0）。

        Note:
            - INSTANT 模式：所有延迟为 0
            - FIXED 模式：第一个请求延迟 0，后续请求固定间隔
            - POISSON 模式：使用指数分布
            - GAMMA 模式：使用 Gamma 分布
        """
        # INSTANT 模式：无延迟
        if self.profile.pattern == ArrivalPattern.INSTANT:
            return 0.0

        # 未设置速率：无延迟
        if self.profile.request_rate is None or self.profile.request_rate <= 0:
            return 0.0

        mean_interval = 1.0 / self.profile.request_rate

        # FIXED 模式：固定间隔（第一个请求无延迟）
        if self.profile.pattern == ArrivalPattern.FIXED:
            return mean_interval if index > 0 else 0.0

        # POISSON 模式：指数分布
        elif self.profile.pattern == ArrivalPattern.POISSON:
            return self._rng.expovariate(self.profile.request_rate)

        # GAMMA 模式：Gamma 分布
        elif self.profile.pattern == ArrivalPattern.GAMMA:
            shape = self.profile.burstiness
            scale = mean_interval / shape
            return self._rng.gammavariate(shape, scale)

        # 未知模式：无延迟
        return 0.0


class TrafficController:
    """流量控制器 - 封装完整的压测流程.

    封装 warmup → 正式测试 → 结果收集 的完整流程。
    支持所有 ArrivalPattern 模式和 warmup 机制。

    Attributes:
        client: BenchmarkClient 实例。
        profile: TrafficProfile 配置。

    Example:
        >>> profile = TrafficProfile(
        ...     pattern=ArrivalPattern.POISSON,
        ...     request_rate=10.0,
        ...     warmup_requests=5,
        ... )
        >>> controller = TrafficController(client, profile)
        >>> results = await controller.run(requests)
        >>> # results 不包含 warmup 请求的结果
    """

    def __init__(
        self,
        client: BenchmarkClient,
        profile: TrafficProfile,
    ) -> None:
        """初始化流量控制器.

        Args:
            client: BenchmarkClient 实例。
            profile: TrafficProfile 配置。
        """
        self.client = client
        self.profile = profile
        logger.info(
            f"TrafficController initialized: client={client.name}, "
            f"pattern={profile.pattern.value}, warmup={profile.warmup_requests}"
        )

    async def run(
        self,
        requests: list[BenchmarkRequest],
    ) -> list[BenchmarkResult]:
        """执行压测流程.

        流程：
        1. 如果配置了 warmup_requests，先执行预热（结果丢弃）
        2. 执行正式测试
        3. 返回正式测试结果

        Args:
            requests: 要执行的请求列表（包含 warmup + 正式测试）。

        Returns:
            正式测试的结果列表（不含 warmup 结果）。

        Note:
            - warmup 请求从 requests 前部提取
            - 正式测试请求为剩余请求
            - 如果 requests 数量少于 warmup_requests，则全部用于 warmup，正式测试返回空列表
        """
        all_requests = requests.copy()

        # Warmup 阶段
        warmup_count = self.profile.warmup_requests
        if warmup_count > 0 and len(all_requests) > 0:
            # 提取 warmup 请求
            actual_warmup_count = min(warmup_count, len(all_requests))
            warmup_reqs = all_requests[:actual_warmup_count]
            all_requests = all_requests[actual_warmup_count:]

            logger.info(f"Starting warmup phase: {len(warmup_reqs)} requests")
            await self._run_requests(warmup_reqs, is_warmup=True)
            logger.info("Warmup phase completed")

        # 正式测试
        if not all_requests:
            logger.warning("No requests left for actual testing after warmup")
            return []

        logger.info(f"Starting actual test phase: {len(all_requests)} requests")
        results = await self._run_requests(all_requests, is_warmup=False)
        logger.info(f"Test phase completed: {len(results)} results")

        return results

    async def _run_requests(
        self,
        requests: list[BenchmarkRequest],
        is_warmup: bool,
    ) -> list[BenchmarkResult]:
        """按 profile 发射请求并收集结果.

        Args:
            requests: 要执行的请求列表。
            is_warmup: 是否为 warmup 阶段（仅用于日志）。

        Returns:
            结果列表（与 requests 顺序一致）。

        Note:
            - INSTANT 模式：使用 asyncio.gather 并发执行
            - 其他模式：按延迟顺序执行（流式）
        """
        results: list[BenchmarkResult] = []
        generator = RequestGenerator(requests, self.profile)

        # INSTANT 模式：并发执行
        if self.profile.pattern == ArrivalPattern.INSTANT:
            tasks = []
            async for delay, request in generator:
                # INSTANT 模式下 delay 应该为 0，但仍然尊重返回值
                if delay > 0:
                    await asyncio.sleep(delay)
                tasks.append(asyncio.create_task(self.client.generate(request)))

            # 等待所有任务完成
            if tasks:
                logger.debug(f"Running {len(tasks)} requests concurrently")
                results = await asyncio.gather(*tasks, return_exceptions=False)
                results = list(results)

        # 其他模式：流式执行
        else:
            async for delay, request in generator:
                if delay > 0:
                    await asyncio.sleep(delay)
                result = await self.client.generate(request)
                results.append(result)

        return results
