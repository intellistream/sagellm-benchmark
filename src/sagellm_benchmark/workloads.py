"""Benchmark workloads and configurations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class WorkloadType(StrEnum):
    """Workload types for benchmarking."""

    QUERY = "query"  # TPCH/TPCC-style query workload
    SHORT = "short"  # Short prompt + short output
    LONG = "long"  # Long prompt + medium output
    STRESS = "stress"  # Concurrent requests, pressure test


class WorkloadQuery(StrEnum):
    """Query-style workload identifiers."""

    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    Q5 = "Q5"
    Q6 = "Q6"
    Q7 = "Q7"
    Q8 = "Q8"


@dataclass
class WorkloadConfig:
    """Configuration for a benchmark workload.

    Attributes:
        name: Workload identifier.
        workload_type: Type of workload (short/long/stress).
        prompt: Input prompt text.
        prompt_tokens: Expected prompt token count (approximate).
        max_tokens: Maximum tokens to generate.
        num_requests: Number of requests to run.
        concurrent: Whether to run requests concurrently.
        temperature: Sampling temperature (0.0 = greedy).
        top_p: Nucleus sampling parameter.
    """

    name: str
    workload_type: WorkloadType
    prompt: str
    prompt_tokens: int
    max_tokens: int
    num_requests: int = 1
    concurrent: bool = False
    temperature: float | None = None  # None = use model default (greedy)
    top_p: float = 1.0

    # Additional params
    extra_params: dict[str, Any] = field(default_factory=dict)


# Predefined workloads matching M1 Demo Contract
YEAR1_WORKLOADS = [
    WorkloadConfig(
        name="short_input",
        workload_type=WorkloadType.SHORT,
        prompt="Hello world, tell me a short story.",
        prompt_tokens=128,
        max_tokens=128,
        num_requests=5,
    ),
    WorkloadConfig(
        name="long_input",
        workload_type=WorkloadType.LONG,
        prompt=" ".join(["This is context about AI and technology."] * 20),  # ~200 tokens
        prompt_tokens=200,
        max_tokens=200,  # Reduced for tiny models
        num_requests=3,
    ),
    WorkloadConfig(
        name="stress_test",
        workload_type=WorkloadType.STRESS,
        prompt="Write a poem about AI.",
        prompt_tokens=256,
        max_tokens=256,
        num_requests=10,
        concurrent=True,
    ),
]

# Backward-compatible alias for M1 naming
M1_WORKLOADS = YEAR1_WORKLOADS


# TPCH/TPCC-style query workloads
TPCH_WORKLOADS = [
    WorkloadConfig(
        name=WorkloadQuery.Q1.value,
        workload_type=WorkloadType.QUERY,
        prompt="用一句话回答：什么是 Transformer？",
        prompt_tokens=32,
        max_tokens=64,
        num_requests=5,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q2.value,
        workload_type=WorkloadType.QUERY,
        prompt="\n".join(
            [
                "请阅读以下长上下文并做摘要：",
                " ".join(
                    [
                        "大型语言模型在推理系统中需要考虑吞吐、延迟、显存占用和可扩展性。"
                        "调度器需要平衡 prefilling 和 decoding，避免 head-of-line blocking。"
                    ]
                    * 12
                ),
            ]
        ),
        prompt_tokens=512,
        max_tokens=128,
        num_requests=3,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q3.value,
        workload_type=WorkloadType.QUERY,
        prompt="写一个 Python 函数，输入整数数组，返回前缀和数组，并给出时间复杂度。",
        prompt_tokens=128,
        max_tokens=256,
        num_requests=3,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q4.value,
        workload_type=WorkloadType.QUERY,
        prompt=(
            "你是一个技术助手。\n"
            "用户: 我在做 LLM 推理性能优化。\n"
            "助手: 你更关注延迟还是吞吐？\n"
            "用户: 两者都要兼顾，请给我一个分步骤方案。"
        ),
        prompt_tokens=256,
        max_tokens=256,
        num_requests=3,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q5.value,
        workload_type=WorkloadType.QUERY,
        prompt="请给我 3 条提升 API 稳定性的建议。",
        prompt_tokens=32,
        max_tokens=64,
        num_requests=10,
        concurrent=True,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q6.value,
        workload_type=WorkloadType.QUERY,
        prompt=" ".join(["分析分布式推理系统中的瓶颈与优化策略。"] * 24),
        prompt_tokens=512,
        max_tokens=256,
        num_requests=10,
        concurrent=True,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q7.value,
        workload_type=WorkloadType.QUERY,
        prompt="请逐步推理：比较同步和异步批处理在高并发场景下的优缺点。",
        prompt_tokens=256,
        max_tokens=512,
        num_requests=3,
    ),
    WorkloadConfig(
        name=WorkloadQuery.Q8.value,
        workload_type=WorkloadType.QUERY,
        prompt="综合任务：总结、分类并给出执行建议（兼顾准确性和时延）。",
        prompt_tokens=192,
        max_tokens=128,
        num_requests=4,
        concurrent=True,
    ),
]


def get_workloads_by_selector(selector: str) -> list[WorkloadConfig]:
    """Resolve workload selector to workload config list.

    Args:
        selector: Workload selector string from CLI.

    Returns:
        List of workload configs to run.
    """
    selected = selector.lower()

    if selected in {"all", "query"}:
        return TPCH_WORKLOADS
    if selected in {"m1", "year1"}:
        return M1_WORKLOADS
    if selected in {"short", "long", "stress"}:
        return [workload for workload in M1_WORKLOADS if workload.workload_type.value == selected]

    for workload in TPCH_WORKLOADS:
        if workload.name.lower() == selected:
            return [workload]

    raise ValueError(f"Unknown workload selector: {selector}")
