"""Standalone Example: Batch Mode Demonstration.

This example shows how to use BATCH mode for offline throughput testing,
without requiring test helpers or running services.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from sagellm_benchmark.traffic import ArrivalPattern, TrafficController, TrafficProfile
from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MockMetrics:
    """Mock metrics for demonstration."""
    ttft_ms: float = 0.0
    tbt_ms: float = 0.0
    e2e_latency_ms: float = 0.0


class DemoClient:
    """Simple demo client for illustration (no real backend needed)."""
    
    def __init__(self, name: str = "demo"):
        self.name = name
        self.request_count = 0
    
    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Simulate request processing."""
        self.request_count += 1
        
        # Simulate some processing time
        await asyncio.sleep(0.05)  # 50ms latency
        
        # Create mock result
        result = BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            metrics=MockMetrics(ttft_ms=20.0, tbt_ms=10.0, e2e_latency_ms=50.0),
            output_text=f"Response to: {request.prompt[:30]}...",
            output_tokens=50,  # Simulate 50 output tokens
            prompt_tokens=len(request.prompt.split()),  # Rough estimate
        )
        
        return result


async def demo_batch_mode():
    """Demonstrate BATCH mode for offline throughput testing."""
    logger.info("=" * 70)
    logger.info("BATCH Mode Demo: Offline Throughput Testing")
    logger.info("=" * 70)
    
    # Create demo client
    client = DemoClient(name="demo-client")
    
    # Configure BATCH mode with warmup
    profile = TrafficProfile(
        pattern=ArrivalPattern.BATCH,
        enable_batch_mode=True,
        warmup_requests=5,  # First 5 requests are warmup
        seed=42,
    )
    
    logger.info(f"\nConfiguration:")
    logger.info(f"  Pattern: {profile.pattern.value}")
    logger.info(f"  Warmup requests: {profile.warmup_requests}")
    
    # Create controller
    controller = TrafficController(client, profile)
    
    # Create test requests (15 total: 5 warmup + 10 benchmark)
    num_requests = 15
    requests = [
        BenchmarkRequest(
            prompt=f"Explain the concept of machine learning in simple terms. Request {i}",
            max_tokens=100,
            request_id=f"batch-{i:03d}",
            model="demo-model",
            stream=False,
        )
        for i in range(num_requests)
    ]
    
    logger.info(f"  Total requests: {num_requests} (including warmup)")
    
    # Run batch benchmark
    logger.info("\n" + "-" * 70)
    logger.info("Running batch benchmark...")
    logger.info("-" * 70)
    
    start = time.perf_counter()
    results = await controller.run(requests)
    end = time.perf_counter()
    
    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("Results")
    logger.info("=" * 70)
    
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    
    logger.info(f"\nExecution Summary:")
    logger.info(f"  Total results (after warmup): {len(results)}")
    logger.info(f"  Successful: {successful}")
    logger.info(f"  Failed: {failed}")
    logger.info(f"  Client request count: {client.request_count}")
    
    # Calculate throughput metrics
    if results and hasattr(results[0], '_batch_total_time_s'):
        batch_total_time = results[0]._batch_total_time_s
        
        total_input_tokens = sum(r.prompt_tokens for r in results)
        total_output_tokens = sum(r.output_tokens for r in results)
        total_tokens = total_input_tokens + total_output_tokens
        
        request_throughput = len(results) / batch_total_time
        input_throughput = total_input_tokens / batch_total_time
        output_throughput = total_output_tokens / batch_total_time
        total_throughput = total_tokens / batch_total_time
        
        logger.info(f"\nTiming:")
        logger.info(f"  Batch total time: {batch_total_time:.3f}s")
        logger.info(f"  Measured time: {end - start:.3f}s")
        
        logger.info(f"\nThroughput Metrics (like vLLM/SGLang):")
        logger.info(f"  Request throughput: {request_throughput:>8.2f} req/s")
        logger.info(f"  Input throughput:   {input_throughput:>8.2f} tokens/s")
        logger.info(f"  Output throughput:  {output_throughput:>8.2f} tokens/s")
        logger.info(f"  Total throughput:   {total_throughput:>8.2f} tokens/s")
        
        logger.info(f"\nToken Statistics:")
        logger.info(f"  Total input tokens:  {total_input_tokens:>6}")
        logger.info(f"  Total output tokens: {total_output_tokens:>6}")
        logger.info(f"  Total tokens:        {total_tokens:>6}")
        logger.info(f"  Avg tokens/request:  {total_tokens / len(results):>6.1f}")
    
    logger.info("\n" + "=" * 70)


async def compare_modes():
    """Compare BATCH vs other traffic modes."""
    logger.info("\n\n" + "=" * 70)
    logger.info("Mode Comparison: BATCH vs INSTANT vs FIXED")
    logger.info("=" * 70)
    
    num_requests = 10
    requests = [
        BenchmarkRequest(
            prompt=f"Test request {i}",
            max_tokens=50,
            request_id=f"req-{i:03d}",
            model="demo",
        )
        for i in range(num_requests)
    ]
    
    modes = [
        ("BATCH", TrafficProfile(pattern=ArrivalPattern.BATCH, enable_batch_mode=True)),
        ("INSTANT", TrafficProfile(pattern=ArrivalPattern.INSTANT)),
        ("FIXED 10 QPS", TrafficProfile(pattern=ArrivalPattern.FIXED, request_rate=10.0)),
    ]
    
    results_summary = []
    
    for mode_name, profile in modes:
        client = DemoClient(name=f"{mode_name.lower()}-client")
        controller = TrafficController(client, profile)
        
        start = time.perf_counter()
        results = await controller.run(requests.copy())
        elapsed = time.perf_counter() - start
        
        throughput = len(results) / elapsed if elapsed > 0 else 0
        
        results_summary.append({
            "mode": mode_name,
            "requests": len(results),
            "time": elapsed,
            "throughput": throughput,
        })
        
        logger.info(f"\n{mode_name}:")
        logger.info(f"  Requests: {len(results)}")
        logger.info(f"  Time: {elapsed:.3f}s")
        logger.info(f"  Throughput: {throughput:.2f} req/s")
    
    logger.info("\n" + "-" * 70)
    logger.info("Summary:")
    logger.info("  BATCH mode = max capacity test (offline throughput)")
    logger.info("  INSTANT mode = concurrent execution (no rate limiting)")
    logger.info("  FIXED mode = realistic load simulation (controlled QPS)")
    logger.info("=" * 70)


async def main():
    """Run all demos."""
    await demo_batch_mode()
    await compare_modes()


if __name__ == "__main__":
    asyncio.run(main())
