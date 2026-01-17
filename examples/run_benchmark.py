"""Example: Run Year 1 benchmark on CPU engine."""

import asyncio
import sys
from pathlib import Path

# Add paths for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/shuhao/sagellm-backend/src")
sys.path.insert(0, "/home/shuhao/sagellm-protocol/src")


async def main():
    """Run benchmark example."""
    from sagellm_backend.engine.cpu import CPUEngineConfig, create_cpu_engine

    from sagellm_benchmark import run_year1_benchmark

    # Create CPU engine
    config = CPUEngineConfig(
        engine_id="bench-cpu-001",
        model_path="sshleifer/tiny-gpt2",  # Lightweight model for testing
        device="cpu",
        max_new_tokens=64,  # Shorter for faster testing
        num_threads=4,  # Use 4 threads
    )

    engine = create_cpu_engine(config)

    print("🚀 Starting benchmark with CPU engine...")
    print(f"   Model: {config.model_path}")
    print(f"   Threads: {config.num_threads}")
    print()

    # Run benchmark
    results = await run_year1_benchmark(
        engine=engine,
        output_dir=Path("./benchmark_results"),
    )

    # Print summary
    print("\n" + "=" * 60)
    print("📊 BENCHMARK RESULTS")
    print("=" * 60)

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
    print("✅ Results saved to: ./benchmark_results/")
    print("=" * 60)

    # Stop engine
    await engine.stop()


if __name__ == "__main__":
    asyncio.run(main())
