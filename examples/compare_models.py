"""Example: Compare performance across multiple models."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, "/home/shuhao/sagellm-backend/src")
sys.path.insert(0, "/home/shuhao/sagellm-protocol/src")


async def benchmark_model(model_path: str, output_subdir: str):
    """Benchmark a single model.
    
    Args:
        model_path: HuggingFace model identifier.
        output_subdir: Subdirectory name for results.
    """
    from sagellm_backend.engine.cpu import CPUEngineConfig, create_cpu_engine
    from sagellm_benchmark import run_year1_benchmark
    
    print(f"\n{'='*60}")
    print(f"🔥 Benchmarking: {model_path}")
    print(f"{'='*60}\n")
    
    # Create CPU engine
    config = CPUEngineConfig(
        engine_id=f"bench-{output_subdir}",
        model_path=model_path,
        device="cpu",
        max_new_tokens=64,
        num_threads=4,
    )
    
    engine = create_cpu_engine(config)
    
    # Run benchmark
    output_dir = Path(f"./benchmark_results/{output_subdir}")
    results = await run_year1_benchmark(engine=engine, output_dir=output_dir)
    
    # Stop engine
    await engine.stop()
    
    return results


async def main():
    """Run multi-model comparison."""
    models = [
        ("sshleifer/tiny-gpt2", "tiny-gpt2"),
        # Uncomment to test more models (requires download):
        # ("gpt2", "gpt2"),
        # ("distilgpt2", "distilgpt2"),
    ]
    
    print("🚀 Multi-Model Benchmark Suite")
    print(f"   Testing {len(models)} model(s)")
    print(f"   CPU threads: 4")
    print()
    
    all_results = {}
    
    for model_path, model_id in models:
        try:
            results = await benchmark_model(model_path, model_id)
            all_results[model_id] = results
        except Exception as e:
            print(f"❌ Failed to benchmark {model_path}: {e}")
            continue
    
    # Print comparison table
    print("\n" + "="*80)
    print("📊 MULTI-MODEL COMPARISON")
    print("="*80)
    print()
    print(f"{'Model':<20} {'TTFT (ms)':<15} {'Throughput':<20} {'Peak Mem (MB)':<15}")
    print("-"*80)
    
    for model_id, workload_results in all_results.items():
        # Use short_input workload for comparison
        metrics = workload_results.get("short_input")
        if metrics:
            print(f"{model_id:<20} {metrics.avg_ttft_ms:>7.2f} (P95: {metrics.p95_ttft_ms:>5.2f})  "
                  f"{metrics.avg_throughput_tps:>7.2f} tokens/sec  {metrics.peak_mem_mb:>7.2f}")
    
    print("="*80)
    print("✅ Results saved to: ./benchmark_results/<model>/")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
