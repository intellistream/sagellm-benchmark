"""Metrics 模块 - 聚合与 Contract 验证.

提供的功能：
- MetricsAggregator: 聚合多个 BenchmarkResult 为 AggregatedMetrics
- ContractVerifier: 验证 AggregatedMetrics 是否满足 Year1/2/3 Demo Contract
"""

from __future__ import annotations

from .aggregator import MetricsAggregator
from .contract import ContractVerifier

__all__ = [
    "MetricsAggregator",
    "ContractVerifier",
]
