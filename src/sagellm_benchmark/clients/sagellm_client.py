"""Client for native sagellm engines.

This client directly uses sagellm-core's LLMEngine:
- LLMEngine (new vLLM v1 style, hardware-agnostic)
- BaseEngine (legacy, still supported)

Provides the most complete metrics since it's the native engine.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sagellm_benchmark.clients.base import BenchmarkClient

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class SageLLMClient(BenchmarkClient):
    """Client for native sagellm engines.

    Supports both new (LLMEngine) and legacy (BaseEngine) architectures.

    Attributes:
        engine: sagellm Engine instance.
        engine_type: Engine type.
    """

    def __init__(
        self,
        engine: Any,
        timeout: float = 60.0,
    ) -> None:
        """Initialize SageLLM client.

        Args:
            engine: sagellm LLMEngine instance.
            timeout: Request timeout (seconds).

        Raises:
            ImportError: If sagellm-core not installed.
        """
        super().__init__(name="sagellm", timeout=timeout)

        # Import from sagellm_core
        try:
            from sagellm_core import LLMEngine
        except ImportError:
            raise ImportError("sagellm-core not installed. Install with: pip install isagellm-core")

        # Verify engine type
        if isinstance(engine, LLMEngine):
            self.engine_type = "llm_engine"
            self.is_legacy = False
        else:
            raise TypeError(f"Expected LLMEngine, got {type(engine)}")

        self.engine = engine

        logger.info(f"SageLLM client initialized: engine_type={self.engine_type}")

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute request via sagellm engine.

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

            # Execute via engine (adapt to engine type)
            if self.is_legacy:
                # BaseEngine has execute() method
                response = await self.engine.execute(protocol_request)
            else:
                # LLMEngine has generate() method
                response = await self.engine.generate(
                    prompt=protocol_request.prompt,
                    max_tokens=protocol_request.max_tokens,
                    temperature=protocol_request.temperature,
                    top_p=protocol_request.top_p,
                    request_id=protocol_request.request_id,
                    trace_id=protocol_request.trace_id,
                )

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

            # metrics.timestamps 由 llm_engine 直接填充，无需从 response.timestamps 手动注入

            # Extract output (adapt field names)
            output_text = ""
            if hasattr(response, "output_text"):
                output_text = response.output_text
            elif hasattr(response, "text"):
                output_text = response.text

            output_tokens_count = 0
            if hasattr(response, "output_tokens") and response.output_tokens:
                output_tokens_count = (
                    len(response.output_tokens)
                    if isinstance(response.output_tokens, list)
                    else response.output_tokens
                )

            # 优先从 response.prompt_tokens 获取，若为 None 则用 request.prompt 词数估算
            prompt_tokens = 0
            if hasattr(response, "prompt_tokens") and response.prompt_tokens is not None:
                prompt_tokens = response.prompt_tokens
            elif request.prompt:
                prompt_tokens = len(request.prompt.split())

            # 从 metrics.timestamps 计算 e2e 延迟（ms）
            e2e_latency_ms = 0.0
            if metrics is not None and metrics.timestamps is not None:
                ts = metrics.timestamps
                if ts.queued_at > 0 and ts.completed_at > 0:
                    e2e_latency_ms = (ts.completed_at - ts.queued_at) * 1000.0

            return BenchmarkResult(
                request_id=request.request_id,
                success=True,
                error=None,
                metrics=metrics,
                output_text=output_text,
                output_tokens=output_tokens_count,
                prompt_tokens=prompt_tokens,
                e2e_latency_ms=e2e_latency_ms,
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
