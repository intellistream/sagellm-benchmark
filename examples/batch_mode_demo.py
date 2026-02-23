"""Example: Using Batch Mode for Offline Throughput Testing.

This example demonstrates how to use the BATCH mode to measure offline throughput,
similar to vLLM/SGLang's offline throughput benchmark.

BATCH mode features:
1. All requests are submitted at once (concurrent execution)
2. Total time is measured from first request to last completion
3. Warmup requests are separated and not counted in statistics
4. Throughput metrics (request/s, input tok/s, output tok/s) are calculated
"""

from __future__ import annotations

import asyncio
import logging

from sagellm_benchmark.traffic import ArrivalPattern, TrafficController, TrafficProfile
from sagellm_benchmark.types import BenchmarkRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_batch_mode() -> None:
    """Demo: Batch mode for offline throughput testing."""
    logger.info("=" * 60)
    logger.info("Demo: BATCH Mode - Offline Throughput Testing")
    logger.info("=" * 60)

    # For this demo, we'll use a stub client
    # In production, replace with actual client (e.g., GatewayClient, VLLMClient)
    try:
        from test_helpers import StubClient
    except ImportError:
        logger.error("StubClient not available. This is a demo example.")
        logger.info("In production, use actual clients like GatewayClient or VLLMClient")
        return

    # Create a stub client with realistic latencies
    client = StubClient(
        ttft_ms=20.0,  # 20ms time to first token
        tbt_ms=10.0,   # 10ms between tokens
        name="demo-client"
    )

    # Configure BATCH mode with warmup
    profile = TrafficProfile(
        pattern=ArrivalPattern.BATCH,
        enable_batch_mode=True,
        warmup_requests=5,  # First 5 requests are warmup (not counted)
        seed=42,  # For reproducibility
    )

    logger.info(f"Traffic Profile: {profile.pattern.value}")
    logger.info(f"Warmup requests: {profile.warmup_requests}")

    # Create controller
    controller = TrafficController(client, profile)

    # Create test requests (15 total: 5 warmup + 10 benchmark)
    requests = [
        BenchmarkRequest(
            prompt=f"Explain the concept of {'machine learning' if i % 2 == 0 else 'quantum computing'} in detail.",
            max_tokens=100,
            request_id=f"batch-req-{i:03d}",
            model="test-model",
            stream=False,
            temperature=0.8,
        )
        for i in range(15)
    ]

    logger.info(f"Total requests: {len(requests)} (including warmup)")

    # Run benchmark
    logger.info("\nStarting batch benchmark...")
    results = await controller.run(requests)

    # Display results
    logger.info("\n" + "=" * 60)
    logger.info("BATCH Benchmark Results")
    logger.info("=" * 60)
    logger.info(f"Total results (excluding warmup): {len(results)}")
    logger.info(f"Successful: {sum(1 for r in results if r.success)}")
    logger.info(f"Failed: {sum(1 for r in results if not r.success)}")

    if results and hasattr(results[0], '_batch_total_time_s'):
        total_time = results[0]._batch_total_time_s
        logger.info(f"\nTotal execution time: {total_time:.3f}s")
        
        # Calculate throughput metrics (similar to vLLM/SGLang)
        total_input_tokens = sum(r.prompt_tokens for r in results if r.prompt_tokens > 0)
        total_output_tokens = sum(r.output_tokens for r in results if r.output_tokens > 0)
        
        request_throughput = len(results) / total_time
        input_throughput = total_input_tokens / total_time if total_input_tokens > 0 else 0
        output_throughput = total_output_tokens / total_time if total_output_tokens > 0 else 0
        total_throughput = (total_input_tokens + total_output_tokens) / total_time
        
        logger.info("\nThroughput Metrics:")
        logger.info(f"  Request throughput: {request_throughput:.2f} req/s")
        logger.info(f"  Input throughput:   {input_throughput:.2f} tokens/s")
        logger.info(f"  Output throughput:  {output_throughput:.2f} tokens/s")
        logger.info(f"  Total throughput:   {total_throughput:.2f} tokens/s")
        
        logger.info("\nToken Statistics:")
        logger.info(f"  Total input tokens:  {total_input_tokens}")
        logger.info(f"  Total output tokens: {total_output_tokens}")
        logger.info(f"  Total tokens:        {total_input_tokens + total_output_tokens}")

    logger.info("\n" + "=" * 60)


async def demo_batch_vs_traffic_mode() -> None:
    """Demo: Comparing BATCH mode vs TRAFFIC mode."""
    logger.info("=" * 60)
    logger.info("Demo: BATCH vs TRAFFIC Mode Comparison")
    logger.info("=" * 60)

    try:
        from test_helpers import StubClient
    except ImportError:
        logger.info("StubClient not available, skipping comparison demo")
        return

    # Create test requests
    num_requests = 10
    requests = [
        BenchmarkRequest(
            prompt=f"Test prompt {i}",
            max_tokens=50,
            request_id=f"req-{i:03d}",
            model="test-model",
        )
        for i in range(num_requests)
    ]

    # Test 1: BATCH mode (offline throughput)
    logger.info("\n--- Test 1: BATCH Mode ---")
    client_batch = StubClient(ttft_ms=10.0, tbt_ms=5.0, name="batch-client")
    profile_batch = TrafficProfile(
        pattern=ArrivalPattern.BATCH,
        enable_batch_mode=True,
    )
    controller_batch = TrafficController(client_batch, profile_batch)
    
    import time
    start = time.perf_counter()
    results_batch = await controller_batch.run(requests.copy())
    batch_time = time.perf_counter() - start
    
    logger.info(f"BATCH mode: {len(results_batch)} requests in {batch_time:.3f}s")
    logger.info(f"  Throughput: {len(results_batch) / batch_time:.2f} req/s")

    # Test 2: INSTANT mode (similar to batch but without timing)
    logger.info("\n--- Test 2: INSTANT Mode ---")
    client_instant = StubClient(ttft_ms=10.0, tbt_ms=5.0, name="instant-client")
    profile_instant = TrafficProfile(
        pattern=ArrivalPattern.INSTANT,
    )
    controller_instant = TrafficController(client_instant, profile_instant)
    
    start = time.perf_counter()
    results_instant = await controller_instant.run(requests.copy())
    instant_time = time.perf_counter() - start
    
    logger.info(f"INSTANT mode: {len(results_instant)} requests in {instant_time:.3f}s")
    logger.info(f"  Throughput: {len(results_instant) / instant_time:.2f} req/s")

    # Test 3: FIXED mode (traffic simulation)
    logger.info("\n--- Test 3: FIXED Mode (Traffic Simulation) ---")
    client_fixed = StubClient(ttft_ms=10.0, tbt_ms=5.0, name="fixed-client")
    profile_fixed = TrafficProfile(
        pattern=ArrivalPattern.FIXED,
        request_rate=5.0,  # 5 requests per second
    )
    controller_fixed = TrafficController(client_fixed, profile_fixed)
    
    start = time.perf_counter()
    results_fixed = await controller_fixed.run(requests.copy())
    fixed_time = time.perf_counter() - start
    
    logger.info(f"FIXED mode (5 QPS): {len(results_fixed)} requests in {fixed_time:.3f}s")
    logger.info(f"  Throughput: {len(results_fixed) / fixed_time:.2f} req/s")

    logger.info("\n" + "=" * 60)
    logger.info("Summary:")
    logger.info(f"  BATCH mode is for offline throughput (max capacity)")
    logger.info(f"  TRAFFIC modes are for realistic load simulation")
    logger.info("=" * 60)


async def main():
    """Run all demos."""
    await demo_batch_mode()
    print("\n\n")
    await demo_batch_vs_traffic_mode()


if __name__ == "__main__":
    asyncio.run(main())
