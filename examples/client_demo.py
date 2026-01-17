"""Example: Using different benchmark clients.

This example demonstrates how to use various benchmark clients:
1. MockClient - For testing without real backend
2. OpenAIClient - For OpenAI-compatible APIs (sagellm-gateway)
3. VLLMClient - For vLLM backend
4. LMDeployClient - For LMDeploy backend
5. SageLLMClient - For native sagellm-backend engines
"""

from __future__ import annotations

import asyncio
import logging

from sagellm_benchmark.clients import MockClient
from sagellm_benchmark.types import BenchmarkRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demo_mock_client() -> None:
    """Demo: MockClient for testing."""
    logger.info("=" * 60)
    logger.info("Demo 1: MockClient")
    logger.info("=" * 60)

    # Create mock client
    client = MockClient(
        ttft_ms=50.0,
        tbt_ms=15.0,
        throughput_tps=80.0,
        timeout=60.0,
    )

    # Single request
    request = BenchmarkRequest(
        prompt="What is the capital of France?",
        max_tokens=100,
        request_id="mock-001",
        model="mock-model",
        temperature=0.7,
    )

    result = await client.generate(request)

    logger.info(f"Success: {result.success}")
    logger.info(f"Output: {result.output_text[:100]}")
    logger.info(f"TTFT: {result.metrics.ttft_ms}ms" if result.metrics else "No metrics")
    logger.info(
        f"Throughput: {result.metrics.throughput_tps}tps" if result.metrics else "No metrics"
    )

    await client.close()


async def demo_openai_client() -> None:
    """Demo: OpenAIClient for sagellm-gateway or OpenAI API."""
    logger.info("=" * 60)
    logger.info("Demo 2: OpenAIClient (requires running gateway)")
    logger.info("=" * 60)

    try:
        from sagellm_benchmark.clients.openai_client import OpenAIClient
    except ImportError:
        logger.error("openai package not installed. Install with: pip install openai")
        return

    # Connect to local gateway
    client = OpenAIClient(
        base_url="http://localhost:8000/v1",
        api_key="benchmark",
        timeout=60.0,
    )

    # Health check
    is_healthy = await client.health_check()
    if not is_healthy:
        logger.warning("Gateway not available, skipping demo")
        await client.close()
        return

    # Create request
    request = BenchmarkRequest(
        prompt="Explain quantum computing in simple terms.",
        max_tokens=200,
        request_id="openai-001",
        model="default",
        temperature=0.8,
    )

    # Execute
    result = await client.generate(request)

    logger.info(f"Success: {result.success}")
    if result.success:
        logger.info(f"Output length: {result.output_tokens} tokens")
        logger.info(f"TTFT: {result.metrics.ttft_ms:.2f}ms" if result.metrics else "No metrics")
    else:
        logger.error(f"Error: {result.error}")

    await client.close()


async def demo_vllm_client() -> None:
    """Demo: VLLMClient for vLLM backend."""
    logger.info("=" * 60)
    logger.info("Demo 3: VLLMClient (server mode)")
    logger.info("=" * 60)

    try:
        from sagellm_benchmark.clients.vllm_client import VLLMClient
    except ImportError:
        logger.error("Required packages not installed")
        return

    # Connect to vLLM server
    client = VLLMClient(
        mode="server",
        base_url="http://localhost:8000/v1",
        timeout=60.0,
    )

    # Health check
    is_healthy = await client.health_check()
    if not is_healthy:
        logger.warning("vLLM server not available, skipping demo")
        await client.close()
        return

    # Create request
    request = BenchmarkRequest(
        prompt="Write a Python function to calculate fibonacci numbers.",
        max_tokens=150,
        request_id="vllm-001",
        model="default",
    )

    # Execute
    result = await client.generate(request)

    logger.info(f"Success: {result.success}")
    if result.success:
        logger.info(f"Output: {result.output_text[:200]}")
        logger.info(
            f"Throughput: {result.metrics.throughput_tps:.2f}tps"
            if result.metrics
            else "No metrics"
        )
    else:
        logger.error(f"Error: {result.error}")

    await client.close()


async def demo_batch_execution() -> None:
    """Demo: Batch execution with concurrent mode."""
    logger.info("=" * 60)
    logger.info("Demo 4: Batch Execution (concurrent vs sequential)")
    logger.info("=" * 60)

    client = MockClient(ttft_ms=30.0, tbt_ms=10.0)

    # Create batch
    requests = [
        BenchmarkRequest(
            prompt=f"Question {i}: What is {i} + {i}?",
            max_tokens=20,
            request_id=f"batch-{i:03d}",
            model="mock-model",
        )
        for i in range(5)
    ]

    # Sequential execution
    logger.info("Running SEQUENTIAL batch...")
    import time

    start = time.perf_counter()
    seq_results = await client.generate_batch(requests, concurrent=False)
    seq_time = time.perf_counter() - start
    logger.info(f"Sequential: {len(seq_results)} requests in {seq_time:.2f}s")

    # Concurrent execution
    logger.info("Running CONCURRENT batch...")
    start = time.perf_counter()
    conc_results = await client.generate_batch(requests, concurrent=True)
    conc_time = time.perf_counter() - start
    logger.info(f"Concurrent: {len(conc_results)} requests in {conc_time:.2f}s")
    logger.info(f"Speedup: {seq_time / conc_time:.2f}x")

    # Verify order preservation
    for i, result in enumerate(conc_results):
        assert result.request_id == f"batch-{i:03d}"
    logger.info("✓ Order preserved in concurrent mode")

    await client.close()


async def demo_error_handling() -> None:
    """Demo: Error handling and timeout."""
    logger.info("=" * 60)
    logger.info("Demo 5: Error Handling & Timeout")
    logger.info("=" * 60)

    # Test error simulation
    error_client = MockClient(error_rate=0.5)  # 50% failure rate

    requests = [
        BenchmarkRequest(
            prompt=f"Request {i}",
            max_tokens=10,
            request_id=f"error-{i:03d}",
        )
        for i in range(10)
    ]

    results = await error_client.generate_batch(requests, concurrent=True)

    successes = sum(1 for r in results if r.success)
    failures = sum(1 for r in results if not r.success)

    logger.info(f"Total: {len(results)}, Success: {successes}, Failures: {failures}")
    logger.info(f"Error rate: {failures / len(results) * 100:.1f}%")

    # Test timeout
    logger.info("\nTesting timeout...")
    timeout_client = MockClient(ttft_ms=5000.0, timeout=1.0)  # 5s TTFT, 1s timeout

    request = BenchmarkRequest(
        prompt="Long request",
        max_tokens=100,
        request_id="timeout-001",
    )

    result = await timeout_client.generate(request)

    assert not result.success
    assert "Timeout" in result.error
    logger.info(f"✓ Timeout correctly handled: {result.error}")

    await error_client.close()
    await timeout_client.close()


async def main() -> None:
    """Run all demos."""
    await demo_mock_client()
    print()

    await demo_batch_execution()
    print()

    await demo_error_handling()
    print()

    # Optional: uncomment if you have services running
    # await demo_openai_client()
    # await demo_vllm_client()

    logger.info("=" * 60)
    logger.info("All demos completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
