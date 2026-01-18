"""Mock client for CI and testing.

This client simulates a real backend without requiring GPU or actual model.
It generates:
- Configurable TTFT, TBT, throughput
- Complete Protocol Metrics
- Fake output text

Used for:
- CI/CD testing without GPU
- Development testing
- Interface validation
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from sagellm_benchmark.clients.base import BenchmarkClient

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class MockClient(BenchmarkClient):
    """Mock client that simulates backend behavior.

    Generates realistic metrics without actual model inference.

    Attributes:
        ttft_ms: Simulated time to first token (ms).
        tbt_ms: Simulated time between tokens (ms).
        throughput_tps: Simulated throughput (tokens/s).
        error_rate: Probability of request failure (0.0-1.0).
        mock_full_itl: Whether to simulate full ITL (slower but realistic).
    """

    def __init__(
        self,
        ttft_ms: float = 50.0,
        tbt_ms: float = 15.0,
        throughput_tps: float = 80.0,
        error_rate: float = 0.0,
        timeout: float = 60.0,
        mock_full_itl: bool = False,
    ) -> None:
        """Initialize mock client.

        Args:
            ttft_ms: Time to first token (ms).
            tbt_ms: Time between tokens (ms).
            throughput_tps: Throughput (tokens/s).
            error_rate: Probability of failure (0.0-1.0).
            timeout: Request timeout (seconds).
            mock_full_itl: If True, simulate each token delay individually (slower).
                          If False, use batch delay but still generate ITL list.
        """
        super().__init__(name="mock", timeout=timeout)
        self.ttft_ms = ttft_ms
        self.tbt_ms = tbt_ms
        self.throughput_tps = throughput_tps
        self.error_rate = error_rate
        self.mock_full_itl = mock_full_itl

        logger.info(
            f"MockClient initialized: TTFT={ttft_ms}ms, TBT={tbt_ms}ms, "
            f"Throughput={throughput_tps}tps, ErrorRate={error_rate}, "
            f"FullITL={mock_full_itl}"
        )

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Simulate request execution.

        Args:
            request: Benchmark request.

        Returns:
            Benchmark result with simulated metrics.
        """
        import random
        import time

        from sagellm_benchmark.types import BenchmarkResult

        # Record start time for E2E latency
        start_time = time.perf_counter()

        # Simulate random failure
        if random.random() < self.error_rate:
            logger.warning(f"Mock request {request.request_id} failed (simulated)")
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="Simulated failure",
                metrics=None,
            )

        output_tokens = request.max_tokens
        prompt_tokens = len(request.prompt.split())  # Rough estimate
        itl_list: list[float] = []

        try:
            # Simulate TTFT delay with timeout
            await asyncio.wait_for(asyncio.sleep(self.ttft_ms / 1000.0), timeout=self.timeout)
            first_token_time = time.perf_counter()

            if self.mock_full_itl:
                # Full ITL simulation: delay each token individually
                last_token_time = first_token_time
                for _ in range(output_tokens):
                    # Add random jitter (0.8x - 1.2x)
                    jitter = random.uniform(0.8, 1.2)
                    token_delay = (self.tbt_ms / 1000.0) * jitter
                    await asyncio.wait_for(asyncio.sleep(token_delay), timeout=self.timeout)

                    current_time = time.perf_counter()
                    itl_ms = (current_time - last_token_time) * 1000.0
                    itl_list.append(itl_ms)
                    last_token_time = current_time
            else:
                # Fast mode: batch delay but generate synthetic ITL list
                total_generation_time = self.tbt_ms * output_tokens / 1000.0
                await asyncio.wait_for(asyncio.sleep(total_generation_time), timeout=self.timeout)

                # Generate synthetic ITL list with jitter
                for _ in range(output_tokens):
                    jitter = random.uniform(0.8, 1.2)
                    itl_list.append(self.tbt_ms * jitter)

        except asyncio.TimeoutError:
            logger.warning(f"Mock request {request.request_id} timed out after {self.timeout}s")
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=f"Timeout: Request exceeded {self.timeout}s limit",
                metrics=None,
            )

        # Calculate E2E latency
        end_time = time.perf_counter()
        e2e_latency_ms = (end_time - start_time) * 1000.0

        # Generate mock output
        output_text = f"[Mock output for {request.request_id}] " + " ".join(
            [f"token{i}" for i in range(min(output_tokens, 10))]
        )
        if output_tokens > 10:
            output_text += f" ... ({output_tokens} tokens total)"

        # Create Protocol Metrics
        try:
            from sagellm_protocol import Metrics
        except ImportError:
            logger.error("sagellm_protocol not installed. Cannot create Metrics.")
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="sagellm_protocol not installed",
                metrics=None,
            )

        metrics = Metrics(
            # Latency metrics
            ttft_ms=self.ttft_ms,
            tbt_ms=self.tbt_ms,
            tpot_ms=self.tbt_ms,  # Same as TBT for mock
            # Throughput
            throughput_tps=self.throughput_tps,
            # Memory (mock values)
            peak_mem_mb=1024,
            # Error rate
            error_rate=0.0,
            # KV Cache (mock values)
            kv_used_tokens=prompt_tokens + output_tokens,
            kv_used_bytes=4 * 1024 * 1024,  # 4MB
            prefix_hit_rate=0.85,
            evict_count=0,
            evict_ms=0.0,
            # Speculative (mock values)
            spec_accept_rate=0.0,
            # ITL list for protocol metrics
            itl_list=itl_list,
        )

        return BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            metrics=metrics,
            output_text=output_text,
            output_tokens=output_tokens,
            prompt_tokens=prompt_tokens,
            itl_list=itl_list,
            e2e_latency_ms=e2e_latency_ms,
        )

    async def health_check(self) -> bool:
        """Mock health check always succeeds.

        Returns:
            True.
        """
        logger.info("Mock health check: OK")
        return True
