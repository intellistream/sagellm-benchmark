"""Benchmark workloads and configurations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkloadType(str, Enum):
    """Workload types for benchmarking."""
    
    SHORT = "short"  # Short prompt + short output
    LONG = "long"  # Long prompt + medium output  
    STRESS = "stress"  # Concurrent requests, pressure test


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


# Predefined workloads matching Year 1 Demo Contract
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
