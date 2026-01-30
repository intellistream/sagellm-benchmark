"""CLI for sagellm-benchmark."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def normalize_model_name(model_path: str) -> str:
    """Normalize model path to directory name.
    
    Args:
        model_path: Model path or HuggingFace repo ID
        
    Returns:
        Normalized model name for directory
        
    Examples:
        sshleifer/tiny-gpt2 → tiny-gpt2
        Qwen/Qwen2-7B-Instruct → Qwen2-7B-Instruct
        /path/to/model → model
    """
    # Remove leading/trailing slashes
    model_path = model_path.strip("/")
    
    # If it's a HuggingFace repo (contains /), take the last part
    if "/" in model_path:
        model_path = model_path.split("/")[-1]
    
    # If it's a local path, take basename
    if model_path.startswith("/") or model_path.startswith("./"):
        model_path = Path(model_path).name
    
    # Replace special characters
    model_path = model_path.replace(" ", "-").replace("_", "-")
    
    return model_path


def create_output_directory(
    backend: str,
    model: str,
    workload: str,
    custom_path: str | None = None,
) -> tuple[Path, dict]:
    """Create hierarchical output directory.
    
    Directory structure: outputs/<backend>/<model>/<workload_YYYYMMDD_NNN>/
    
    Args:
        backend: Backend name (cpu, cuda, vllm, etc.)
        model: Model name/path
        workload: Workload type (m1, short, long, stress)
        custom_path: User-specified output path (optional)
        
    Returns:
        Tuple of (output_path, metadata_dict)
    """
    if custom_path:
        # User specified path - use as-is
        output_dir = Path(custom_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir, {"custom_output": True}
    
    # Standard hierarchical structure
    outputs_root = Path("outputs")
    model_name = normalize_model_name(model)
    
    # Create backend/model directory
    backend_model_dir = outputs_root / backend / model_name
    backend_model_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next sequence number for today
    today = datetime.now().strftime("%Y%m%d")
    existing_runs = list(backend_model_dir.glob(f"{workload}_{today}_*"))
    seq_num = len(existing_runs) + 1
    
    # Create run directory: workload_YYYYMMDD_NNN
    run_id = f"{workload}_{today}_{seq_num:03d}"
    output_dir = backend_model_dir / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create/update 'latest' symlink in backend/model directory
    latest_link = backend_model_dir / "latest"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    
    try:
        # Create relative symlink
        latest_link.symlink_to(run_id)
    except OSError:
        # Windows may not support symlinks
        pass
    
    metadata = {
        "run_id": run_id,
        "backend": backend,
        "model": model_name,
        "workload": workload,
        "date": today,
        "sequence": seq_num,
    }
    
    return output_dir, metadata


def save_run_config(
    output_dir: Path,
    backend: str,
    model: str,
    workload: str,
    dataset: str,
    num_samples: int,
    metadata: dict,
) -> None:
    """Save run configuration to config.json.
    
    Args:
        output_dir: Output directory path
        backend: Backend name
        model: Model name/path
        workload: Workload type
        dataset: Dataset name
        num_samples: Number of samples
        metadata: Additional metadata from create_output_directory
    """
    try:
        import importlib.metadata
        versions = {
            "sagellm_benchmark": importlib.metadata.version("isagellm-benchmark"),
            "sagellm_core": importlib.metadata.version("isagellm-core"),
            "sagellm_backend": importlib.metadata.version("isagellm-backend"),
        }
    except Exception:
        versions = {}
    
    config = {
        **metadata,
        "timestamp": datetime.now().isoformat(),
        "model_path": model,  # Original model path
        "dataset": dataset,
        "num_samples": num_samples,
        "versions": versions,
    }
    
    config_file = output_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    console.print(f"[dim]Saved config: {config_file}[/dim]")


@click.group()
@click.version_option(version="0.1.0", prog_name="sagellm-benchmark")
def main() -> None:
    """sageLLM Benchmark Suite - M1 Demo Contract Validation."""
    pass


@main.command()
@click.option(
    "--workload",
    type=click.Choice(["m1", "short", "long", "stress"]),
    default="m1",
    help="Workload type to run.",
)
@click.option(
    "--backend",
    type=click.Choice(["cpu", "lmdeploy", "vllm"]),
    default="cpu",
    help="Backend engine to use.",
)
@click.option(
    "--model",
    type=str,
    default="sshleifer/tiny-gpt2",
    help="Model path (for CPU backend).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output directory (default: outputs/<backend>/<model>/<workload_date_seq>/).",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging.",
)
@click.option(
    "--dataset",
    type=click.Choice(["default", "sharegpt", "synthetic"]),
    default="default",
    help="Dataset to use for prompts (default: hardcoded prompts, sharegpt: HuggingFace ShareGPT).",
)
@click.option(
    "--num-samples",
    type=int,
    default=5,
    help="Number of samples to use from dataset (ignored for 'default').",
)
def run(
    workload: str,
    backend: str,
    model: str | None,
    output: str,
    verbose: bool,
    dataset: str,
    num_samples: int,
) -> None:
    """Run benchmark workloads."""
    console.print("[bold cyan]sageLLM Benchmark[/bold cyan]")
    console.print(f"Workload: {workload}")
    console.print(f"Backend: {backend}")
    console.print(f"Model: {model}")
    console.print(f"Dataset: {dataset}")
    
    # Create hierarchical output directory
    output_dir, metadata = create_output_directory(backend, model or "default", workload, output)
    console.print(f"[bold green]Output:[/bold green] {output_dir}\n")

    # Import LLMEngine
    try:
        from sagellm_core import LLMEngine, LLMEngineConfig
    except ImportError:
        console.print("[bold red]Error:[/bold red] isagellm-core not installed.")
        console.print("Install with: pip install isagellm-core")
        sys.exit(1)

    # Determine workloads to run
    from sagellm_benchmark.workloads import M1_WORKLOADS, WorkloadType

    # Load dataset if needed
    dataset_instance = None
    if dataset == "sharegpt":
        console.print("Loading ShareGPT dataset from HuggingFace...")
        from sagellm_benchmark.datasets import ShareGPTDataset
        try:
            dataset_instance = ShareGPTDataset.from_huggingface(
                repo_id="anon8231489123/ShareGPT_Vicuna_unfiltered",
                split="train[:1000]",  # Load first 1000 for speed
                min_prompt_len=50,
                max_prompt_len=5000,
                seed=42,
            )
            console.print(f"✓ Loaded {len(dataset_instance)} prompts from ShareGPT")
        except Exception as e:
            console.print(f"[bold red]Error loading ShareGPT:[/bold red] {e}")
            console.print("Falling back to default prompts")
            dataset_instance = None
    elif dataset == "synthetic":
        console.print("Using synthetic ShareGPT-style prompts...")
        from sagellm_benchmark.datasets import SyntheticShareGPTDataset
        dataset_instance = SyntheticShareGPTDataset(seed=42)
        console.print("✓ Synthetic dataset ready")

    if workload == "m1":
        workloads = M1_WORKLOADS
    elif workload == "short":
        workloads = [w for w in M1_WORKLOADS if w.workload_type == WorkloadType.SHORT]
    elif workload == "long":
        workloads = [w for w in M1_WORKLOADS if w.workload_type == WorkloadType.LONG]
    elif workload == "stress":
        workloads = [w for w in M1_WORKLOADS if w.workload_type == WorkloadType.STRESS]
    else:
        console.print(f"[bold red]Unknown workload:[/bold red] {workload}")
        sys.exit(1)
    
    # Override num_requests if using dataset
    if dataset_instance is not None:
        for w in workloads:
            w.num_requests = num_samples

    # Create engine using LLMEngine
    if backend == "cpu":
        try:
            from sagellm_core import LLMEngine, LLMEngineConfig
        except ImportError:
            console.print("[bold red]Error:[/bold red] isagellm-core not installed.")
            console.print("Install with: pip install isagellm-core")
            sys.exit(1)

        # Create LLMEngine config
        engine_config = LLMEngineConfig(
            model_path=model,
            backend_type="cpu",  # Use CPU backend
            comm_type="gloo",  # Not used in single-device mode
            max_batch_size=32,
            max_model_len=4096,
            max_new_tokens=128,
            trust_remote_code=True,
        )
        
        # Create engine
        engine = LLMEngine(engine_config)
        
        # Start engine
        console.print(f"[dim]Starting engine with model: {model}[/dim]")
        asyncio.run(engine.start())
        console.print("[green]✓[/green] Engine started\n")

    elif backend in ["lmdeploy", "vllm"]:
        console.print(f"[bold red]Backend not yet implemented:[/bold red] {backend}")
        console.print("Available: cpu")
        console.print("[dim]lmdeploy and vllm support coming soon[/dim]")
        sys.exit(1)
    else:
        console.print(f"[bold red]Unknown backend:[/bold red] {backend}")
        console.print("Available: cpu")
        sys.exit(1)

    # Run benchmark
    from sagellm_benchmark.runner import BenchmarkConfig, BenchmarkRunner

    bench_config = BenchmarkConfig(
        engine=engine,
        workloads=workloads,
        output_dir=output_dir,
        verbose=verbose,
        dataset=dataset_instance,  # Pass dataset to runner
    )
    
    # Save run configuration
    save_run_config(
        output_dir, backend, model or "default", workload, dataset, num_samples, metadata
    )

    runner = BenchmarkRunner(bench_config)

    console.print("\n[bold green]Starting benchmark...[/bold green]")
    console.print(f"Workloads: {len(workloads)}\n")

    try:
        results = asyncio.run(runner.run())

        # Display summary
        console.print("\n[bold green]✓ Benchmark completed![/bold green]\n")
        _display_results(results)

        console.print(f"\n[bold]Results saved to:[/bold] {output_dir}")
        
        # Show latest link if not custom output
        if not metadata.get("custom_output"):
            latest_path = output_dir.parent / "latest"
            console.print(f"[dim]Latest results: {latest_path}[/dim]")

    except Exception as e:
        console.print(f"\n[bold red]✗ Benchmark failed:[/bold red] {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True),
    default="./benchmark_results/benchmark_summary.json",
    help="Input summary JSON file.",
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "markdown"]),
    default="table",
    help="Output format.",
)
def report(input: str, format: str) -> None:
    """Generate report from benchmark results."""
    try:
        with open(input) as f:
            data = json.load(f)
    except FileNotFoundError:
        console.print(f"[bold red]Error:[/bold red] File not found: {input}")
        console.print("Run benchmark first with: sagellm-benchmark run")
        sys.exit(1)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] Invalid JSON file: {input}")
        sys.exit(1)

    if format == "table":
        _display_summary_table(data)
    elif format == "json":
        console.print(json.dumps(data, indent=2))
    elif format == "markdown":
        _display_markdown(data)


def _display_results(results: dict) -> None:
    """Display benchmark results in table format."""
    table = Table(title="Benchmark Results")

    table.add_column("Workload", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Avg TTFT (ms)", justify="right")
    table.add_column("Avg TBT (ms)", justify="right")
    table.add_column("Throughput (tok/s)", justify="right")
    table.add_column("Peak Mem (MB)", justify="right")

    for name, metrics in results.items():
        table.add_row(
            name,
            str(metrics.total_requests),
            str(metrics.failed_requests),
            f"{metrics.avg_ttft_ms:.2f}",
            f"{metrics.avg_tbt_ms:.2f}",
            f"{metrics.avg_throughput_tps:.2f}",
            str(metrics.peak_mem_mb),
        )

    console.print(table)


def _display_summary_table(data: dict) -> None:
    """Display summary in table format."""
    console.print("\n[bold cyan]Benchmark Summary[/bold cyan]\n")

    # Overall stats
    overall = data["overall"]
    console.print(f"Total workloads: {overall['total_workloads']}")
    console.print(f"Total requests: {overall['total_requests']}")
    console.print(f"Successful: {overall['successful_requests']}")
    console.print(f"Failed: {overall['failed_requests']}")

    # Per-workload table
    table = Table(title="\nWorkload Details")

    table.add_column("Workload", style="cyan")
    table.add_column("Requests", justify="right")
    table.add_column("Errors", justify="right", style="red")
    table.add_column("Avg TTFT (ms)", justify="right")
    table.add_column("Throughput (tok/s)", justify="right")

    for name, metrics in data["workloads"].items():
        table.add_row(
            name,
            str(metrics["total_requests"]),
            str(metrics["failed_requests"]),
            f"{metrics['avg_ttft_ms']:.2f}",
            f"{metrics['avg_throughput_tps']:.2f}",
        )

    console.print(table)


def _display_markdown(data: dict) -> None:
    """Display summary in markdown format."""
    console.print("# Benchmark Results\n")

    overall = data["overall"]
    console.print("## Overall Statistics\n")
    console.print(f"- **Total Workloads**: {overall['total_workloads']}")
    console.print(f"- **Total Requests**: {overall['total_requests']}")
    console.print(f"- **Successful**: {overall['successful_requests']}")
    console.print(f"- **Failed**: {overall['failed_requests']}\n")

    console.print("## Workload Details\n")
    console.print("| Workload | Requests | Errors | Avg TTFT (ms) | Throughput (tok/s) |")
    console.print("|----------|----------|--------|---------------|---------------------|")

    for name, metrics in data["workloads"].items():
        console.print(
            f"| {name} | {metrics['total_requests']} | {metrics['failed_requests']} | "
            f"{metrics['avg_ttft_ms']:.2f} | {metrics['avg_throughput_tps']:.2f} |"
        )


@main.command()
def aggregate():
    """聚合本地 benchmark 结果并准备上传到 Hugging Face.
    
    工作流程:
    1. 从 HF 下载最新的公开数据（无需 token）
    2. 扫描本地 outputs/ 目录的新结果
    3. 智能合并（去重，选性能更好的）
    4. 保存到 hf_data/ 目录
    
    之后用户可以:
        git add hf_data/
        git commit -m "feat: add benchmark results"
        git push
    """
    import subprocess
    from pathlib import Path
    
    # 找到 aggregate_for_hf.py 脚本
    script_dir = Path(__file__).parent.parent.parent.parent / "scripts"
    aggregate_script = script_dir / "aggregate_for_hf.py"
    
    if not aggregate_script.exists():
        console.print(f"[red]❌ 未找到聚合脚本: {aggregate_script}[/red]")
        console.print("[yellow]💡 请确保在 sagellm-benchmark 仓库根目录运行[/yellow]")
        sys.exit(1)
    
    # 运行聚合脚本
    try:
        subprocess.run(
            [sys.executable, str(aggregate_script)],
            check=True
        )
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ 聚合失败: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
