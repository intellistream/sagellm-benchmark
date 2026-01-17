"""指标聚合器 - 将多个 BenchmarkResult 聚合为 AggregatedMetrics。

符合 INTERFACE_CONTRACT.md §4 定义。
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sagellm_benchmark.types import AggregatedMetrics, BenchmarkResult


class MetricsAggregator:
    """指标聚合器，将多个请求的结果聚合为统计指标。

    聚合规则：
    - 延迟类（ttft_ms, tbt_ms, tpot_ms）：取平均 + 百分位
    - 内存（peak_mem_mb）：取 max
    - KV Cache 计数（evict_count, kv_used_tokens）：取 sum
    - 比率类（prefix_hit_rate, spec_accept_rate）：取平均
    """

    @staticmethod
    def aggregate(results: list[BenchmarkResult]) -> AggregatedMetrics:
        """聚合多个 BenchmarkResult 为 AggregatedMetrics。

        Args:
            results: BenchmarkResult 列表。

        Returns:
            聚合后的 AggregatedMetrics。

        Note:
            - 如果所有请求都失败，返回空 AggregatedMetrics
            - 百分位使用排序后的索引法
        """
        from sagellm_benchmark.types import AggregatedMetrics

        # 初始化空指标
        aggregated = AggregatedMetrics()

        if not results:
            return aggregated

        # 统计总数
        aggregated.total_requests = len(results)
        successful = [r for r in results if r.success and r.metrics is not None]
        aggregated.successful_requests = len(successful)
        aggregated.failed_requests = aggregated.total_requests - aggregated.successful_requests
        aggregated.error_rate = (
            aggregated.failed_requests / aggregated.total_requests
            if aggregated.total_requests > 0
            else 0.0
        )

        # 如果全部失败，直接返回
        if not successful:
            return aggregated

        # 收集时间戳（从 timestamps 对象中获取）
        start_times = [
            r.metrics.timestamps.queued_at
            for r in successful
            if r.metrics.timestamps is not None and r.metrics.timestamps.queued_at > 0
        ]
        end_times = [
            r.metrics.timestamps.completed_at
            for r in successful
            if r.metrics.timestamps is not None and r.metrics.timestamps.completed_at > 0
        ]

        if start_times and end_times:
            aggregated.start_time = min(start_times)
            aggregated.end_time = max(end_times)
            aggregated.total_time_s = aggregated.end_time - aggregated.start_time

        # === 延迟指标 ===
        ttft_samples = [r.metrics.ttft_ms for r in successful if r.metrics.ttft_ms > 0]
        tbt_samples = [r.metrics.tbt_ms for r in successful if r.metrics.tbt_ms > 0]
        tpot_samples = [r.metrics.tpot_ms for r in successful if r.metrics.tpot_ms > 0]

        if ttft_samples:
            aggregated.avg_ttft_ms = statistics.mean(ttft_samples)
            aggregated.p50_ttft_ms = MetricsAggregator._percentile(ttft_samples, 0.50)
            aggregated.p95_ttft_ms = MetricsAggregator._percentile(ttft_samples, 0.95)
            aggregated.p99_ttft_ms = MetricsAggregator._percentile(ttft_samples, 0.99)

        if tbt_samples:
            aggregated.avg_tbt_ms = statistics.mean(tbt_samples)

        if tpot_samples:
            aggregated.avg_tpot_ms = statistics.mean(tpot_samples)

        # === 吞吐 ===
        throughput_samples = [
            r.metrics.throughput_tps for r in successful if r.metrics.throughput_tps > 0
        ]

        if throughput_samples:
            aggregated.avg_throughput_tps = statistics.mean(throughput_samples)
            # 总吞吐 = 总输出 tokens / 总时间
            total_output_tokens = sum(r.output_tokens for r in successful)
            if aggregated.total_time_s > 0:
                aggregated.total_throughput_tps = total_output_tokens / aggregated.total_time_s

        # === 内存（取 max）===
        mem_samples = [r.metrics.peak_mem_mb for r in successful if r.metrics.peak_mem_mb > 0]
        if mem_samples:
            aggregated.peak_mem_mb = max(mem_samples)

        # === KV Cache（取 sum/avg）===
        aggregated.total_kv_used_tokens = sum(r.metrics.kv_used_tokens for r in successful)
        aggregated.total_kv_used_bytes = sum(r.metrics.kv_used_bytes for r in successful)

        prefix_hit_samples = [
            r.metrics.prefix_hit_rate for r in successful if r.metrics.prefix_hit_rate >= 0
        ]
        if prefix_hit_samples:
            aggregated.avg_prefix_hit_rate = statistics.mean(prefix_hit_samples)

        aggregated.total_evict_count = sum(r.metrics.evict_count for r in successful)
        aggregated.total_evict_ms = sum(r.metrics.evict_ms for r in successful)

        # === Speculative（取 avg）===
        spec_samples = [
            r.metrics.spec_accept_rate for r in successful if r.metrics.spec_accept_rate >= 0
        ]
        if spec_samples:
            aggregated.avg_spec_accept_rate = statistics.mean(spec_samples)

        return aggregated

    @staticmethod
    def _percentile(samples: list[float], p: float) -> float:
        """计算百分位。

        Args:
            samples: 样本列表。
            p: 百分位（0-1）。

        Returns:
            百分位值。
        """
        if not samples:
            return 0.0

        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        index = int(n * p)

        # 边界保护
        if index >= n:
            index = n - 1

        return sorted_samples[index]
