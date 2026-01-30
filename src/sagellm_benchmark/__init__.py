"""sagellm-benchmark: Benchmark Suite & E2E Testing for sageLLM."""

from __future__ import annotations

# Clients - Task B 客户端
from sagellm_benchmark.clients import (
    BenchmarkClient,
)

# Traffic - 流量控制
from sagellm_benchmark.traffic import (
    ArrivalPattern,
    RequestGenerator,
    TrafficController,
    TrafficProfile,
)

# Types - 公共数据类型（契约定义）
from sagellm_benchmark.types import (
    AggregatedMetrics,
    BenchmarkRequest,
    BenchmarkResult,
    ContractResult,
    ContractVersion,
    WorkloadSpec,
    WorkloadType,
)

__version__ = "0.4.0.3"

__all__ = [
    "__version__",
    # Types (契约定义)
    "BenchmarkRequest",
    "BenchmarkResult",
    "WorkloadSpec",
    "WorkloadType",
    "AggregatedMetrics",
    "ContractResult",
    "ContractVersion",
    # Clients
    "BenchmarkClient",
    # Traffic
    "ArrivalPattern",
    "TrafficProfile",
    "RequestGenerator",
    "TrafficController",
]
