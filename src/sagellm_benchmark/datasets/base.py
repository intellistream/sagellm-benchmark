"""Benchmark 数据集抽象基类。

提供统一的数据集接口，所有具体数据集（Random、ShareGPT 等）必须继承此基类。
遵循 Protocol-First 设计，仅使用协议层定义的类型。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from sagellm_benchmark.types import BenchmarkRequest, WorkloadSpec


class BenchmarkDataset(ABC):
    """Benchmark 数据集抽象基类。

    所有数据集实现必须继承此类并实现 sample() 方法。

    Example:
        >>> class MyDataset(BenchmarkDataset):
        ...     def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        ...         return [BenchmarkRequest(...)]
        >>> dataset = MyDataset()
        >>> requests = dataset.sample(spec)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """数据集名称，用于标识和日志记录。"""
        ...

    @abstractmethod
    def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        """根据 WorkloadSpec 生成请求列表。

        Args:
            spec: Workload 规格描述，包含 prompt_len、output_len、num_requests 等。

        Returns:
            符合规格的 BenchmarkRequest 列表，每个 request 包含唯一的 request_id。

        Raises:
            ValueError: 当规格参数无效时抛出。
        """
        ...

    def validate_spec(self, spec: WorkloadSpec) -> None:
        """验证 WorkloadSpec 参数有效性。

        Args:
            spec: 待验证的 Workload 规格。

        Raises:
            ValueError: 当参数无效时抛出明确错误。
        """
        if spec.prompt_len <= 0:
            raise ValueError(f"prompt_len must be positive, got {spec.prompt_len}")
        if spec.output_len <= 0:
            raise ValueError(f"output_len must be positive, got {spec.output_len}")
        if spec.num_requests <= 0:
            raise ValueError(f"num_requests must be positive, got {spec.num_requests}")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
