"""Test helpers and stub clients for unit testing.

This module provides stub implementations for testing without real backends.
"""

from __future__ import annotations

import asyncio
import random

from sagellm_protocol import Metrics, Timestamps

from sagellm_benchmark.clients.base import BenchmarkClient
from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult


class StubClient(BenchmarkClient):
    """Stub client for unit testing without real backend.

    This is a minimal implementation that simulates latency and errors
    for testing purposes only. Use real backends (CPU/vLLM/etc) for actual benchmarks.
    """

    def __init__(
        self,
        ttft_ms: float = 10.0,
        tbt_ms: float = 5.0,
        throughput_tps: float = 100.0,
        error_rate: float = 0.0,
        timeout: float = 60.0,
        simulate_full_itl: bool = False,
    ):
        """Initialize stub client.

        Args:
            ttft_ms: Simulated time to first token (ms)
            tbt_ms: Simulated time between tokens (ms)
            throughput_tps: Simulated throughput (tokens/sec)
            error_rate: Error rate (0.0-1.0)
            timeout: Timeout in seconds
            simulate_full_itl: Whether to simulate full ITL list
        """
        super().__init__(timeout=timeout)
        self.ttft_ms = ttft_ms
        self.tbt_ms = tbt_ms
        self.throughput_tps = throughput_tps
        self.error_rate = error_rate
        self.simulate_full_itl = simulate_full_itl

    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Generate stub response."""
        import time

        start_time = time.perf_counter()

        # Simulate error
        if random.random() < self.error_rate:
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="Simulated failure",
                output_text="",
                output_tokens=0,
                prompt_tokens=len(request.prompt.split()),
            )

        # Simulate timeout
        if self.ttft_ms / 1000 > self.timeout:
            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error="Timeout: TTFT exceeds timeout",
                output_text="",
                output_tokens=0,
                prompt_tokens=len(request.prompt.split()),
            )

        # Simulate TTFT delay
        await asyncio.sleep(self.ttft_ms / 1000)

        # Generate fake output
        num_tokens = request.max_tokens or 50
        output_text = f"Generated response for request {request.request_id}"

        # Simulate TBT delays
        itl_list: list[float] = []
        if self.simulate_full_itl:
            for i in range(num_tokens):
                await asyncio.sleep(self.tbt_ms / 1000)
                itl_list.append(self.tbt_ms)
        else:
            # Simulate aggregate delay
            await asyncio.sleep((self.tbt_ms * num_tokens) / 1000)
            itl_list = [self.ttft_ms] + [self.tbt_ms] * (num_tokens - 1)

        end_time = time.perf_counter()
        e2e_latency_s = end_time - start_time

        # Build metrics
        timestamps = Timestamps(
            queued_at=start_time,
            scheduled_at=start_time,
            executed_at=start_time,
            completed_at=end_time,
        )

        metrics = Metrics(
            ttft_ms=self.ttft_ms,
            tbt_ms=self.tbt_ms,
            tpot_ms=self.tbt_ms,
            throughput_tps=self.throughput_tps,
            peak_mem_mb=1024,
            error_rate=0.0,
            kv_used_tokens=100,
            kv_used_bytes=100 * 16,
            prefix_hit_rate=0.0,
            evict_count=0,
            evict_ms=0.0,
            spec_accept_rate=0.0,
            timestamps=timestamps,
            itl_list=itl_list,
        )

        return BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            output_text=output_text,
            output_tokens=num_tokens,
            prompt_tokens=len(request.prompt.split()),
            metrics=metrics,
            itl_list=itl_list,  # Also set at result level
            e2e_latency_ms=e2e_latency_s * 1000,  # Convert to ms
        )

    async def health_check(self) -> bool:
        """Always healthy for stub."""
        return True

    async def close(self) -> None:
        """No-op close."""
        pass
