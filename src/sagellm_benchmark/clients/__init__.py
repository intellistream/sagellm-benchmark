"""Benchmark clients for different backends.

This module provides a unified interface for benchmarking various LLM backends:
- GatewayClient: For OpenAI-protocol HTTP APIs (sagellm-gateway)
- VLLMClient: For vLLM backend
- LMDeployClient: For LMDeploy backend
- SageLLMClient: For native sagellm-backend engines (no HTTP)
- EngineType / EngineInfo / MultiEngineRunner: Cross-engine comparison harness
"""

from __future__ import annotations

from sagellm_benchmark.clients.base import BenchmarkClient
from sagellm_benchmark.clients.multi_engine import EngineInfo, EngineType, MultiEngineRunner

__all__ = [
    "BenchmarkClient",
    "EngineType",
    "EngineInfo",
    "MultiEngineRunner",
]

# Optional clients (imported on demand)
try:
    from sagellm_benchmark.clients.openai_client import GatewayClient  # noqa: F401

    __all__.append("GatewayClient")
except ImportError:
    pass

try:
    from sagellm_benchmark.clients.vllm_client import VLLMClient  # noqa: F401

    __all__.append("VLLMClient")
except ImportError:
    pass

try:
    from sagellm_benchmark.clients.lmdeploy_client import LMDeployClient  # noqa: F401

    __all__.append("LMDeployClient")
except ImportError:
    pass

try:
    from sagellm_benchmark.clients.sagellm_client import SageLLMClient  # noqa: F401

    __all__.append("SageLLMClient")
except ImportError:
    pass
