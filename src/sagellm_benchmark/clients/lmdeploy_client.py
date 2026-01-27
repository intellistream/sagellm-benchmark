"""Client for LMDeploy backend.

This client connects to LMDeploy's server or uses LMDeploy's
pipeline API directly for local inference.

Two modes:
1. Server mode: Connect to LMDeploy server via HTTP API
2. Local mode: Use LMDeploy pipeline directly (in-process)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from sagellm_benchmark.clients.base import BenchmarkClient

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class LMDeployClient(BenchmarkClient):
    """Client for LMDeploy backend.

    Attributes:
        mode: "server" (connect to server) or "local" (in-process pipeline).
        base_url: Server URL (server mode only).
        model_path: Model path (local mode only).
        pipeline: LMDeploy pipeline instance (local mode only).
    """

    def __init__(
        self,
        mode: str = "server",
        base_url: str = "http://localhost:23333",
        model_path: str | None = None,
        tp: int = 1,
        timeout: float = 60.0,
    ) -> None:
        """Initialize LMDeploy client.

        Args:
            mode: "server" or "local".
            base_url: LMDeploy server URL (server mode).
            model_path: Model path (local mode).
            tp: Tensor parallelism size (local mode).
            timeout: Request timeout (seconds).

        Raises:
            ImportError: If LMDeploy not installed.
            ValueError: If invalid mode.
        """
        super().__init__(name="lmdeploy", timeout=timeout)

        if mode not in ("server", "local"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'server' or 'local'.")

        self.mode = mode
        self.base_url = base_url
        self.model_path = model_path

        if mode == "server":
            # Use httpx for server mode
            try:
                import httpx
            except ImportError:
                raise ImportError(
                    "httpx package required for LMDeploy server mode. "
                    "Install with: pip install httpx"
                )
            self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
            logger.info(f"LMDeploy client (server mode): {base_url}")

        elif mode == "local":
            # Use LMDeploy pipeline for local mode
            if not model_path:
                raise ValueError("model_path required for LMDeploy local mode")

            try:
                from lmdeploy import GenerationConfig, pipeline
            except ImportError:
                raise ImportError(
                    "lmdeploy package required for local mode. Install with: pip install lmdeploy"
                )

            self.pipeline = pipeline(model_path, tp=tp)
            self.GenerationConfig = GenerationConfig
            logger.info(f"LMDeploy client (local mode): {model_path}, tp={tp}")

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute request via LMDeploy.

        Args:
            request: Benchmark request.

        Returns:
            Benchmark result with metrics.
        """
        if self.mode == "server":
            return await self._generate_server(request)
        else:
            return await self._generate_local(request)

    async def _generate_server(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute via LMDeploy server."""
        from sagellm_benchmark.types import BenchmarkResult

        try:
            from sagellm_protocol import Metrics
        except ImportError:
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="sagellm_protocol not installed",
                metrics=None,
            )

        start_time = time.perf_counter()

        try:
            # Build LMDeploy API request
            payload = {
                "prompt": request.prompt,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature if request.temperature is not None else 1.0,
                "top_p": request.top_p if request.top_p is not None else 1.0,
            }

            # LMDeploy uses /generate endpoint
            response = await self.client.post("/generate", json=payload)
            response.raise_for_status()
            result = response.json()

            end_time = time.perf_counter()

            # Extract output
            output_text = result.get("text", "")
            output_tokens = result.get("tokens", len(output_text.split()))

            # Calculate metrics
            total_time_s = end_time - start_time
            tpot_ms = (total_time_s * 1000 / output_tokens) if output_tokens > 0 else 0.0
            throughput_tps = output_tokens / total_time_s if total_time_s > 0 else 0.0

            metrics = Metrics(
                ttft_ms=0.0,  # Not available from server response
                tbt_ms=0.0,
                tpot_ms=tpot_ms,
                throughput_tps=throughput_tps,
                peak_mem_mb=0,
                error_rate=0.0,
                kv_used_tokens=0,
                kv_used_bytes=0,
                prefix_hit_rate=0.0,
                evict_count=0,
                evict_ms=0.0,
                spec_accept_rate=0.0,
            )

            return BenchmarkResult(
                request_id=request.request_id,
                success=True,
                error=None,
                metrics=metrics,
                output_text=output_text,
                output_tokens=output_tokens,
                prompt_tokens=len(request.prompt.split()),
            )

        except Exception as e:
            logger.error(f"LMDeploy server request failed: {e}", exc_info=True)
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def _generate_local(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute via LMDeploy pipeline (local in-process)."""
        import asyncio

        from sagellm_benchmark.types import BenchmarkResult

        try:
            from sagellm_protocol import Metrics
        except ImportError:
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="sagellm_protocol not installed",
                metrics=None,
            )

        try:
            start_time = time.perf_counter()

            # Create generation config
            gen_config = self.GenerationConfig(
                max_new_tokens=request.max_tokens,
                temperature=request.temperature if request.temperature is not None else 1.0,
                top_p=request.top_p if request.top_p is not None else 1.0,
            )

            # Run in thread pool (LMDeploy may be blocking)
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self.pipeline([request.prompt], gen_config=gen_config),
            )

            end_time = time.perf_counter()

            # Extract output
            output = outputs[0]
            output_text = output.text if hasattr(output, "text") else str(output)
            output_tokens = len(output_text.split())

            # Calculate metrics
            total_time_s = end_time - start_time
            tpot_ms = (total_time_s * 1000 / output_tokens) if output_tokens > 0 else 0.0
            throughput_tps = output_tokens / total_time_s if total_time_s > 0 else 0.0

            metrics = Metrics(
                ttft_ms=0.0,  # Not available in local mode
                tbt_ms=0.0,
                tpot_ms=tpot_ms,
                throughput_tps=throughput_tps,
                peak_mem_mb=0,
                error_rate=0.0,
                kv_used_tokens=0,
                kv_used_bytes=0,
                prefix_hit_rate=0.0,
                evict_count=0,
                evict_ms=0.0,
                spec_accept_rate=0.0,
            )

            return BenchmarkResult(
                request_id=request.request_id,
                success=True,
                error=None,
                metrics=metrics,
                output_text=output_text,
                output_tokens=output_tokens,
                prompt_tokens=len(request.prompt.split()),
            )

        except Exception as e:
            logger.error(f"LMDeploy local request failed: {e}", exc_info=True)
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def health_check(self) -> bool:
        """Check LMDeploy health.

        Returns:
            True if backend is healthy.
        """
        if self.mode == "server":
            try:
                response = await self.client.get("/health")
                response.raise_for_status()
                logger.info("LMDeploy server health check OK")
                return True
            except Exception as e:
                logger.error(f"LMDeploy server health check failed: {e}")
                return False
        else:
            # Local mode: assume healthy if pipeline loaded
            logger.info("LMDeploy local health check OK")
            return True

    async def close(self) -> None:
        """Close client."""
        if self.mode == "server":
            await self.client.aclose()
        logger.info("LMDeploy client closed")
