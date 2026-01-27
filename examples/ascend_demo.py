"""Example: Run Year 1 benchmark on Ascend engine (MVP).

This demo shows how to configure and run benchmarks with the Ascend backend.
Note: Real hardware execution is not required for MVP (CPU fallback available).

Usage:
    python examples/ascend_demo.py

Environment:
    - If torch_npu is available, will attempt to use real Ascend device
    - Otherwise, falls back to CPU for demonstration purposes
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add paths for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/shuhao/sagellm-core/src")
sys.path.insert(0, "/home/shuhao/sagellm-backend/src")
sys.path.insert(0, "/home/shuhao/sagellm-protocol/src")


async def main():
    """Run benchmark example with Ascend engine."""
    from sagellm_core.engines.ascend import AscendEngineConfig, create_ascend_engine

    from sagellm_benchmark import run_year1_benchmark

    # Create Ascend engine config
    config = AscendEngineConfig(
        engine_id="bench-ascend-001",
        model_path="sshleifer/tiny-gpt2",  # Lightweight model for testing
        device="ascend:0",  # Primary Ascend device
        max_new_tokens=64,  # Shorter for faster testing
        # Ascend-specific settings (if needed)
        # precision="fp16",  # FP16 precision for Ascend
        # max_batch_size=8,  # Batch size for throughput
    )

    # Check if Ascend is available
    try:
        engine = create_ascend_engine(config)
        print("🚀 Starting benchmark with Ascend engine...")
        print(f"   Device: {config.device}")
        backend_available = True
    except Exception as e:
        print(f"⚠️  Ascend backend not available: {e}")
        print("   Falling back to CPU for demo purposes...")

        # Fallback to CPU
        from sagellm_backend.engine.cpu import CPUEngineConfig, create_cpu_engine

        cpu_config = CPUEngineConfig(
            engine_id="bench-ascend-fallback-cpu",
            model_path="sshleifer/tiny-gpt2",
            device="cpu",
            max_new_tokens=64,
            num_threads=4,
        )
        engine = create_cpu_engine(cpu_config)
        backend_available = False

    print(f"   Model: {config.model_path}")
    print()

    # Run benchmark
    results = await run_year1_benchmark(
        engine=engine,
        output_dir=Path("./benchmark_results_ascend"),
    )

    # Print summary
    print("\n" + "=" * 60)
    print("📊 BENCHMARK RESULTS (Ascend MVP Demo)")
    print("=" * 60)
    if not backend_available:
        print("⚠️  Note: Results from CPU fallback (Ascend not available)")
    print()

    for workload_name, metrics in results.items():
        print(f"\n{workload_name.upper()}:")
        print(f"  Total Requests:     {metrics.total_requests}")
        print(f"  Successful:         {metrics.successful_requests}")
        print(f"  Failed:             {metrics.failed_requests}")
        print(f"  Error Rate:         {metrics.error_rate:.2%}")
        print("  ")
        print("  TTFT (ms):")
        print(f"    Avg:              {metrics.avg_ttft_ms:.2f}")
        print(f"    P50:              {metrics.p50_ttft_ms:.2f}")
        print(f"    P95:              {metrics.p95_ttft_ms:.2f}")
        print(f"    P99:              {metrics.p99_ttft_ms:.2f}")
        print("  ")
        print(f"  Throughput:         {metrics.avg_throughput_tps:.2f} tokens/sec")
        print(f"  Peak Memory:        {metrics.peak_mem_mb:.2f} MB")
        print(f"  Total Time:         {metrics.total_time_s:.2f} seconds")

    print("\n" + "=" * 60)
    print("✅ Results saved to: ./benchmark_results_ascend/")
    print("=" * 60)

    # Stop engine
    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
