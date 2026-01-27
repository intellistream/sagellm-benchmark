"""Client for vLLM backend.

This client connects to vLLM's OpenAI-compatible server or uses vLLM's
LLM class directly for local inference.

Two modes:
1. Server mode: Connect to vLLM server via OpenAI API
2. Local mode: Use vLLM.LLM class directly (in-process)
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from sagellm_benchmark.clients.base import BenchmarkClient

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class VLLMClient(BenchmarkClient):
    """Client for vLLM backend.

    Attributes:
        mode: "server" (connect to vLLM server) or "local" (in-process LLM).
        base_url: Server URL (server mode only).
        model_path: Model path (local mode only).
        llm: vLLM LLM instance (local mode only).
    """

    def __init__(
        self,
        mode: str = "server",
        base_url: str = "http://localhost:8000/v1",
        model_path: str | None = None,
        gpu_memory_utilization: float = 0.9,
        timeout: float = 60.0,
    ) -> None:
        """Initialize vLLM client.

        Args:
            mode: "server" or "local".
            base_url: vLLM server URL (server mode).
            model_path: Model path (local mode).
            gpu_memory_utilization: GPU memory fraction (local mode).
            timeout: Request timeout (seconds).

        Raises:
            ImportError: If vLLM not installed.
            ValueError: If invalid mode.
        """
        super().__init__(name="vllm", timeout=timeout)

        if mode not in ("server", "local"):
            raise ValueError(f"Invalid mode: {mode}. Must be 'server' or 'local'.")

        self.mode = mode
        self.base_url = base_url
        self.model_path = model_path

        if mode == "server":
            # Use OpenAI client for server mode
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise ImportError(
                    "openai package required for vLLM server mode. Install with: pip install openai"
                )
            self.client = AsyncOpenAI(base_url=base_url, api_key="vllm-benchmark")
            logger.info(f"vLLM client (server mode): {base_url}")

        elif mode == "local":
            # Use vLLM LLM class for local mode
            if not model_path:
                raise ValueError("model_path required for vLLM local mode")

            try:
                from vllm import LLM, SamplingParams
            except ImportError:
                raise ImportError(
                    "vllm package required for local mode. Install with: pip install vllm"
                )

            self.llm = LLM(
                model=model_path,
                gpu_memory_utilization=gpu_memory_utilization,
            )
            self.SamplingParams = SamplingParams
            logger.info(f"vLLM client (local mode): {model_path}")

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute request via vLLM.

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
        """Execute via vLLM server (OpenAI API)."""
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
        first_token_time = None
        tokens_received = 0
        token_times: list[float] = []

        try:
            api_kwargs: dict[str, Any] = {
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "stream": True,
            }

            if request.temperature is not None:
                api_kwargs["temperature"] = request.temperature
            if request.top_p is not None:
                api_kwargs["top_p"] = request.top_p

            output_text = ""
            async for chunk in await self.client.chat.completions.create(**api_kwargs):
                current_time = time.perf_counter()

                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    output_text += content
                    tokens_received += 1

                    if first_token_time is None:
                        first_token_time = current_time
                    else:
                        token_times.append(current_time)

            end_time = time.perf_counter()

            # Calculate metrics
            total_time_s = end_time - start_time
            ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else 0.0

            if len(token_times) > 1:
                tbt_intervals = [
                    (token_times[i] - token_times[i - 1]) * 1000 for i in range(1, len(token_times))
                ]
                tbt_ms = sum(tbt_intervals) / len(tbt_intervals)
            else:
                tbt_ms = 0.0

            tpot_ms = (total_time_s * 1000 / tokens_received) if tokens_received > 0 else 0.0
            throughput_tps = tokens_received / total_time_s if total_time_s > 0 else 0.0

            metrics = Metrics(
                ttft_ms=ttft_ms,
                tbt_ms=tbt_ms,
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
                output_tokens=tokens_received,
                prompt_tokens=len(request.prompt.split()),
            )

        except Exception as e:
            logger.error(f"vLLM server request failed: {e}", exc_info=True)
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def _generate_local(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute via vLLM LLM class (local in-process)."""
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

            # Create sampling params
            sampling_params = self.SamplingParams(
                max_tokens=request.max_tokens,
                temperature=request.temperature if request.temperature is not None else 1.0,
                top_p=request.top_p if request.top_p is not None else 1.0,
            )

            # Run in thread pool (vLLM is blocking)
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self.llm.generate([request.prompt], sampling_params),
            )

            end_time = time.perf_counter()

            # Extract output
            output = outputs[0]
            output_text = output.outputs[0].text
            output_tokens = len(output.outputs[0].token_ids)

            # Calculate metrics (local mode has limited metrics)
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
            logger.error(f"vLLM local request failed: {e}", exc_info=True)
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def health_check(self) -> bool:
        """Check vLLM health.

        Returns:
            True if backend is healthy.
        """
        if self.mode == "server":
            try:
                _ = await self.client.models.list()  # Just check if we can connect
                logger.info("vLLM server health check OK")
                return True
            except Exception as e:
                logger.error(f"vLLM server health check failed: {e}")
                return False
        else:
            # Local mode: assume healthy if LLM loaded
            logger.info("vLLM local health check OK")
            return True

    async def close(self) -> None:
        """Close client."""
        if self.mode == "server":
            await self.client.close()
        logger.info("vLLM client closed")
