"""Client for native sagellm-backend engines.

This client directly uses sagellm-backend's Engine classes:
- CPUEngine (for CPU/mock mode)
- CUDAEngine (for NVIDIA GPUs)
- AscendEngine (for Huawei Ascend NPUs)

Provides the most complete metrics since it's the native backend.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sagellm_benchmark.clients.base import BenchmarkClient

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class SageLLMClient(BenchmarkClient):
    """Client for native sagellm-backend engines.

    Attributes:
        engine: sagellm-backend Engine instance.
        engine_type: Engine type (cpu/cuda/ascend).
    """

    def __init__(
        self,
        engine: Any,
        timeout: float = 60.0,
    ) -> None:
        """Initialize SageLLM client.

        Args:
            engine: sagellm-backend Engine instance (already started).
            timeout: Request timeout (seconds).

        Raises:
            ImportError: If sagellm-backend not installed.
        """
        super().__init__(name="sagellm", timeout=timeout)

        try:
            from sagellm_backend import BaseEngine
        except ImportError:
            raise ImportError(
                "sagellm-backend not installed. Install with: pip install isagellm-backend"
            )

        if not isinstance(engine, BaseEngine):
            raise TypeError(f"Expected BaseEngine, got {type(engine)}")

        self.engine = engine
        self.engine_type = engine.__class__.__name__.lower().replace("engine", "")

        logger.info(f"SageLLM client initialized: engine_type={self.engine_type}")

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute request via sagellm-backend engine.

        Args:
            request: Benchmark request.

        Returns:
            Benchmark result with complete metrics.
        """
        from sagellm_benchmark.types import BenchmarkResult

        try:
            from sagellm_protocol import Metrics, Request
        except ImportError:
            logger.error("sagellm_protocol not installed")
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="sagellm_protocol not installed",
                metrics=None,
            )

        try:
            # Convert BenchmarkRequest to Protocol Request
            protocol_request = Request(
                request_id=request.request_id,
                trace_id=f"benchmark-{request.request_id}",
                model=request.model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                stream=request.stream,
            )

            # Execute via engine
            response = await self.engine.execute(protocol_request)

            # Extract metrics from response
            if hasattr(response, "metrics") and response.metrics:
                metrics = response.metrics
            else:
                # Fallback: create basic metrics
                logger.warning(f"No metrics in response for {request.request_id}")
                metrics = Metrics(
                    ttft_ms=0.0,
                    tbt_ms=0.0,
                    tpot_ms=0.0,
                    throughput_tps=0.0,
                    peak_mem_mb=0,
                    error_rate=0.0,
                    kv_used_tokens=0,
                    kv_used_bytes=0,
                    prefix_hit_rate=0.0,
                    evict_count=0,
                    evict_ms=0.0,
                    spec_accept_rate=0.0,
                )

            # Extract output
            output_text = response.text if hasattr(response, "text") else ""
            output_tokens = response.output_tokens if hasattr(response, "output_tokens") else 0
            prompt_tokens = response.prompt_tokens if hasattr(response, "prompt_tokens") else 0

            return BenchmarkResult(
                request_id=request.request_id,
                success=True,
                error=None,
                metrics=metrics,
                output_text=output_text,
                output_tokens=output_tokens,
                prompt_tokens=prompt_tokens,
            )

        except Exception as e:
            logger.error(f"SageLLM engine request failed: {e}", exc_info=True)
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def health_check(self) -> bool:
        """Check if engine is healthy.

        Returns:
            True if engine is running.
        """
        try:
            is_healthy = self.engine.is_running if hasattr(self.engine, "is_running") else True
            logger.info(f"SageLLM engine health check: {is_healthy}")
            return is_healthy
        except Exception as e:
            logger.error(f"SageLLM engine health check failed: {e}")
            return False

    async def close(self) -> None:
        """Close engine (does not stop it, just cleanup)."""
        logger.info("SageLLM client closed (engine remains running)")
