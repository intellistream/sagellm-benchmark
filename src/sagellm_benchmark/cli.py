"""CLI for sagellm-benchmark."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
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
    versions = collect_installed_versions()

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


def collect_installed_versions() -> dict[str, str]:
    """Collect installed sageLLM component versions from Python environment.

    Returns:
        Mapping of internal component keys to installed package versions.
    """
    try:
        import importlib.metadata
    except Exception:
        return {}

    package_map = {
        "sagellm": "isagellm",
        "sagellm_benchmark": "isagellm-benchmark",
        "sagellm_protocol": "isagellm-protocol",
        "sagellm_backend": "isagellm-backend",
        "sagellm_core": "isagellm-core",
        "sagellm_kv_cache": "isagellm-kv-cache",
        "sagellm_control_plane": "isagellm-control-plane",
        "sagellm_gateway": "isagellm-gateway",
        "sagellm_comm": "isagellm-comm",
        "sagellm_compression": "isagellm-compression",
    }

    versions: dict[str, str] = {}
    for key, package_name in package_map.items():
        try:
            versions[key] = importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            continue
        except Exception:
            continue

    return versions


@click.group()
@click.version_option(version="0.1.0", prog_name="sagellm-benchmark")
def main() -> None:
    """sageLLM Benchmark Suite - M1 Demo Contract Validation."""
    pass


@main.command()
@click.option(
    "--workload",
    type=click.Choice(
        [
            "all",
            "query",
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "Q5",
            "Q6",
            "Q7",
            "Q8",
            "streaming",
            "batch",
            "mixed",
        ],
        case_sensitive=False,
    ),
    default="all",
    help="Workload type to run (Q1-Q8 query workloads, or 'all' for full suite).",
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
    "--mode",
    type=click.Choice(["batch", "traffic"]),
    default="traffic",
    help="Benchmark mode: 'batch' for offline throughput (all requests at once), 'traffic' for arrival pattern simulation.",
)
@click.option(
    "--output-json",
    type=click.Path(),
    default=None,
    help="Path to save JSON output (in addition to default location).",
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
    mode: str,
    output_json: str | None,
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
    console.print(f"Mode: {mode}")

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
    from sagellm_benchmark.workloads import get_workloads_by_selector

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

    try:
        workloads = get_workloads_by_selector(workload)
    except ValueError:
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
        mode=mode,  # Pass benchmark mode
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

        # Save to custom JSON output if specified
        if output_json:
            import json

            output_json_path = Path(output_json)
            output_json_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert results to serializable format
            json_results = {}
            for name, metrics in results.items():
                from dataclasses import asdict

                json_results[name] = asdict(metrics)

            with open(output_json_path, "w") as f:
                json.dump(json_results, f, indent=2)

            console.print(f"[bold]Additional JSON output:[/bold] {output_json_path}")

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
    "--type",
    "benchmark_type",
    type=click.Choice(["operator", "e2e"]),
    default="operator",
    help="Performance benchmark type.",
)
@click.option(
    "--device",
    type=str,
    default="cpu",
    help="Execution device for operator benchmark (e.g., cpu, cuda).",
)
@click.option(
    "--iterations",
    type=int,
    default=20,
    help="Benchmark iterations for operator benchmark.",
)
@click.option(
    "--warmup",
    type=int,
    default=5,
    help="Warmup iterations for operator benchmark.",
)
@click.option(
    "--model",
    "models",
    multiple=True,
    default=("Qwen/Qwen2-7B-Instruct",),
    help="Model(s) for e2e benchmarks. Repeat for multiple models.",
)
@click.option(
    "--batch-size",
    "batch_sizes",
    multiple=True,
    type=int,
    default=(1, 4, 8),
    help="Batch sizes for e2e benchmark. Repeat for multiple values.",
)
@click.option(
    "--precision",
    "precisions",
    multiple=True,
    default=("fp16", "int8"),
    help="Precisions for e2e benchmark. Repeat for multiple values.",
)
@click.option(
    "--simulate/--live",
    default=True,
    help="Run e2e benchmark in deterministic simulation mode (default) or live mode.",
)
@click.option(
    "--backend-url",
    type=str,
    default="http://localhost:8000/v1",
    show_default=True,
    help="API base URL for live e2e benchmark mode (OpenAI-compatible endpoint).",
)
@click.option(
    "--api-key",
    type=str,
    default="sagellm-benchmark",
    show_default=True,
    help="API key for live e2e benchmark mode.",
)
@click.option(
    "--request-timeout",
    type=float,
    default=120.0,
    show_default=True,
    help="Per-request timeout in seconds for live e2e mode.",
)
@click.option(
    "--server-wait",
    "server_wait_s",
    type=float,
    default=30.0,
    show_default=True,
    help="Max seconds to wait for the API server to become ready in live mode.",
)
@click.option(
    "--max-seq-len",
    "max_seq_len",
    type=int,
    default=None,
    help=(
        "Maximum sequence length (prompt + output tokens) the model supports. "
        "Auto-detected if not set. Used in live mode to clamp prompts so they "
        "never exceed the model's context window."
    ),
)
@click.option(
    "--max-output-tokens",
    "max_output_tokens",
    type=int,
    default=None,
    help=(
        "Hard cap on output tokens per request in live e2e mode. "
        "Use this for CPU/slow models where the full scenario output length would "
        "exceed the request timeout. E.g. '--max-output-tokens 16' for tiny CPU models."
    ),
)
@click.option(
    "--output-json",
    type=click.Path(),
    default="./benchmark_results/perf_results.json",
    help="Path to save performance JSON result.",
)
@click.option(
    "--output-markdown",
    type=click.Path(),
    default="./benchmark_results/perf_report.md",
    help="Path to save performance markdown report.",
)
@click.option(
    "--plot/--no-plot",
    default=False,
    help="Generate performance charts.",
)
@click.option(
    "--plot-format",
    "plot_formats",
    multiple=True,
    type=click.Choice(["png", "pdf"]),
    default=("png",),
    help="Plot output format(s). Repeat for multiple formats.",
)
@click.option(
    "--theme",
    type=click.Choice(["light", "dark"]),
    default="light",
    help="Chart theme.",
)
@click.option(
    "--dpi",
    type=int,
    default=300,
    help="Chart output DPI.",
)
def perf(
    benchmark_type: str,
    device: str,
    iterations: int,
    warmup: int,
    models: tuple[str, ...],
    batch_sizes: tuple[int, ...],
    precisions: tuple[str, ...],
    simulate: bool,
    backend_url: str,
    api_key: str,
    request_timeout: float,
    server_wait_s: float,
    max_seq_len: int | None,
    max_output_tokens: int | None,
    output_json: str,
    output_markdown: str,
    plot: bool,
    plot_formats: tuple[str, ...],
    theme: str,
    dpi: int,
) -> None:
    """Run performance benchmarks (operator/e2e) migrated from sagellm-core."""
    console.print("[bold cyan]sageLLM Performance Benchmark[/bold cyan]")
    console.print(f"Type: {benchmark_type}")

    if benchmark_type == "operator":
        from sagellm_benchmark.performance.benchmark_utils import format_comparison_table
        from sagellm_benchmark.performance.operator_benchmarks import run_operator_benchmarks

        comparisons = run_operator_benchmarks(device=device, iterations=iterations, warmup=warmup)
        markdown = "# Operator Benchmark Report\n\n" + format_comparison_table(comparisons)
        result_data = {
            "kind": "operator",
            "device": device,
            "iterations": iterations,
            "warmup": warmup,
            "comparisons": comparisons,
        }
        console.print("\n" + format_comparison_table(comparisons))
    else:
        from sagellm_benchmark.performance.model_benchmarks import (
            run_e2e_model_benchmarks,
            summarize_e2e_rows,
        )

        if simulate:
            console.print("[dim]Mode: simulate (deterministic)[/dim]")
        else:
            import logging as _logging

            # Enable INFO logging for live mode so server wait/discovery messages are visible
            _logging.basicConfig(
                level=_logging.INFO,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
            console.print(
                f"[bold yellow]Mode: live — sending real requests to {backend_url}[/bold yellow]"
            )
            console.print(
                f"[dim]Models: {', '.join(models)} | "
                f"batch sizes: {', '.join(str(b) for b in batch_sizes)} | "
                f"timeout: {request_timeout:.0f}s/req[/dim]"
            )

        rows = run_e2e_model_benchmarks(
            models=list(models),
            batch_sizes=list(batch_sizes),
            precisions=list(precisions),
            simulate=simulate,
            backend_url=backend_url,
            api_key=api_key,
            request_timeout=request_timeout,
            server_wait_s=server_wait_s,
            max_seq_len=max_seq_len,
            max_output_tokens=max_output_tokens,
        )
        summary = summarize_e2e_rows(rows)
        result_data = {
            "kind": "e2e",
            "simulate": simulate,
            "models": list(models),
            "batch_sizes": list(batch_sizes),
            "precisions": list(precisions),
            "summary": summary,
            "rows": rows,
        }
        markdown = _format_e2e_markdown(result_data)
        _display_perf_e2e_table(result_data)

    if plot:
        from sagellm_benchmark.performance.plotting import generate_perf_charts

        plot_output_dir = Path(output_markdown).parent / "plots"
        plot_paths = generate_perf_charts(
            result_data,
            output_dir=plot_output_dir,
            formats=list(plot_formats),
            theme=theme,
            dpi=dpi,
        )
        result_data["plots"] = plot_paths
        console.print("\n[bold]Generated plots:[/bold]")
        for path in plot_paths:
            console.print(f"- {path}")

    output_json_path = Path(output_json)
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json_path, "w") as f:
        json.dump(result_data, f, indent=2)

    output_md_path = Path(output_markdown)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_md_path, "w") as f:
        f.write(markdown + "\n")

    console.print("\n[bold green]✓ Performance benchmark completed[/bold green]")
    console.print(f"JSON: {output_json_path}")
    console.print(f"Markdown: {output_md_path}")


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
@click.option(
    "--plot/--no-plot",
    default=False,
    help="Generate charts when input is a perf JSON.",
)
@click.option(
    "--plot-format",
    "plot_formats",
    multiple=True,
    type=click.Choice(["png", "pdf"]),
    default=("png",),
    help="Plot output format(s). Repeat for multiple formats.",
)
@click.option(
    "--theme",
    type=click.Choice(["light", "dark"]),
    default="light",
    help="Chart theme.",
)
@click.option(
    "--dpi",
    type=int,
    default=300,
    help="Chart output DPI.",
)
def report(
    input: str,
    format: str,
    plot: bool,
    plot_formats: tuple[str, ...],
    theme: str,
    dpi: int,
) -> None:
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

    if data.get("kind") == "operator":
        if plot:
            _generate_plots_for_report(input, data, plot_formats, theme, dpi)
        _display_perf_operator_report(data, format)
        return
    if data.get("kind") == "e2e":
        if plot:
            _generate_plots_for_report(input, data, plot_formats, theme, dpi)
        _display_perf_e2e_report(data, format)
        return

    if format == "table":
        _display_summary_table(data)
    elif format == "json":
        console.print(json.dumps(data, indent=2))
    elif format == "markdown":
        _display_markdown(data)


def _display_perf_operator_report(data: dict, format: str) -> None:
    from sagellm_benchmark.performance.benchmark_utils import format_comparison_table

    if format == "json":
        console.print(json.dumps(data, indent=2))
        return

    markdown = "# Operator Benchmark Report\n\n" + format_comparison_table(data["comparisons"])
    if format == "markdown":
        console.print(markdown)
        return

    console.print("[bold cyan]Operator Benchmark Summary[/bold cyan]")
    console.print(f"Device: {data.get('device', 'unknown')}")
    console.print(format_comparison_table(data["comparisons"]))


def _display_perf_e2e_report(data: dict, format: str) -> None:
    if format == "json":
        console.print(json.dumps(data, indent=2))
        return
    if format == "markdown":
        console.print(_format_e2e_markdown(data))
        return
    _display_perf_e2e_table(data)


def _display_perf_e2e_table(data: dict) -> None:
    summary = data.get("summary", {})
    console.print("[bold cyan]E2E Benchmark Summary[/bold cyan]")
    console.print(f"Rows: {summary.get('total_rows', 0)}")
    console.print(f"Avg TTFT (ms): {summary.get('avg_ttft_ms', 0.0):.2f}")
    console.print(f"Avg TBT (ms): {summary.get('avg_tbt_ms', 0.0):.2f}")
    console.print(f"Avg Throughput (tok/s): {summary.get('avg_throughput_tps', 0.0):.2f}\n")

    table = Table(title="E2E Scenario Results")
    table.add_column("Model", style="cyan")
    table.add_column("Scenario")
    table.add_column("Precision")
    table.add_column("Batch", justify="right")
    table.add_column("TTFT(ms)", justify="right")
    table.add_column("TBT(ms)", justify="right")
    table.add_column("TPS", justify="right")
    table.add_column("P95(ms)", justify="right")

    for row in data.get("rows", []):
        table.add_row(
            str(row.get("model", "")),
            str(row.get("scenario", "")),
            str(row.get("precision", "default")),
            str(row.get("batch_size", "")),
            f"{float(row.get('ttft_ms', 0.0)):.2f}",
            f"{float(row.get('tbt_ms', 0.0)):.2f}",
            f"{float(row.get('throughput_tps', 0.0)):.2f}",
            f"{float(row.get('latency_p95_ms', 0.0)):.2f}",
        )
    console.print(table)


def _format_e2e_markdown(data: dict) -> str:
    summary = data.get("summary", {})
    lines = [
        "# E2E Benchmark Report",
        "",
        "## Summary",
        f"- Rows: {summary.get('total_rows', 0)}",
        f"- Avg TTFT (ms): {summary.get('avg_ttft_ms', 0.0):.2f}",
        f"- Avg TBT (ms): {summary.get('avg_tbt_ms', 0.0):.2f}",
        f"- Avg Throughput (tok/s): {summary.get('avg_throughput_tps', 0.0):.2f}",
        "",
        "## Results",
        "",
        "| Model | Scenario | Precision | Batch | TTFT(ms) | TBT(ms) | TPS | P95(ms) |",
        "|-------|----------|-----------|-------|----------|---------|-----|---------|",
    ]
    for row in data.get("rows", []):
        lines.append(
            f"| {row.get('model', '')} | {row.get('scenario', '')} | {row.get('precision', 'default')} | "
            f"{row.get('batch_size', '')} | "
            f"{float(row.get('ttft_ms', 0.0)):.2f} | {float(row.get('tbt_ms', 0.0)):.2f} | "
            f"{float(row.get('throughput_tps', 0.0)):.2f} | {float(row.get('latency_p95_ms', 0.0)):.2f} |"
        )
    return "\n".join(lines)


def _generate_plots_for_report(
    input_path: str,
    data: dict,
    plot_formats: tuple[str, ...],
    theme: str,
    dpi: int,
) -> None:
    from sagellm_benchmark.performance.plotting import generate_perf_charts

    output_dir = Path(input_path).parent / "plots"
    paths = generate_perf_charts(
        data,
        output_dir=output_dir,
        formats=list(plot_formats),
        theme=theme,
        dpi=dpi,
    )
    console.print("\n[bold]Generated plots:[/bold]")
    for path in paths:
        console.print(f"- {path}")


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

    # Display throughput benchmark metrics (aligned with vLLM/SGLang)
    console.print("\n[bold cyan]Throughput Metrics (vLLM/SGLang Compatible)[/bold cyan]")

    for name, metrics in results.items():
        console.print(f"\n[bold]{name}:[/bold]")
        console.print(f"  Request Throughput:  {metrics.request_throughput_rps:>8.2f} req/s")
        console.print(f"  Input Throughput:    {metrics.input_throughput_tps:>8.2f} tokens/s")
        console.print(f"  Output Throughput:   {metrics.output_throughput_tps:>8.2f} tokens/s")
        console.print(f"  Total Throughput:    {metrics.total_throughput_tps:>8.2f} tokens/s")
        console.print(f"  Total Input Tokens:  {metrics.total_input_tokens:>8d}")
        console.print(f"  Total Output Tokens: {metrics.total_output_tokens:>8d}")


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


def _normalize_key_part(value: str | int | None) -> str:
    """Normalize one idempotency key part."""
    raw = str(value or "unknown").strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", raw)
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "unknown"


def _extract_workload_for_key(entry: dict) -> str:
    """Extract workload name for idempotency key construction."""
    direct = (
        entry.get("workload", {}).get("name")
        or entry.get("workload_name")
        or entry.get("metadata", {}).get("workload")
    )
    if isinstance(direct, str) and direct.strip():
        return direct.strip().upper()

    notes = str(entry.get("metadata", {}).get("notes") or "")
    q_match = re.search(r"\bQ([1-8])\b", notes, flags=re.IGNORECASE)
    if q_match:
        return f"Q{q_match.group(1)}"

    return "LEGACY"


def build_idempotency_key(entry: dict) -> str:
    """Build idempotency key for one leaderboard entry.

    Key dimensions:
    - sagellm version
    - workload
    - model name
    - precision
    - hardware model/count
    - node count
    - config type
    """
    parts = [
        _normalize_key_part(entry.get("sagellm_version")),
        _normalize_key_part(_extract_workload_for_key(entry)),
        _normalize_key_part(entry.get("model", {}).get("name")),
        _normalize_key_part(entry.get("model", {}).get("precision")),
        _normalize_key_part(entry.get("hardware", {}).get("chip_model")),
        _normalize_key_part(entry.get("hardware", {}).get("chip_count")),
        _normalize_key_part(entry.get("cluster", {}).get("node_count", 1)),
        _normalize_key_part(entry.get("config_type")),
    ]
    return "|".join(parts)


def build_canonical_path(entry: dict) -> str:
    """Build canonical dataset path from idempotency key."""
    key = build_idempotency_key(entry)
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    return f"canonical/{digest}_leaderboard.json"


def _parse_entry_time(entry: dict) -> tuple[datetime | None, datetime | None]:
    """Parse submitted_at and release_date from leaderboard entry metadata."""
    metadata = entry.get("metadata", {}) if isinstance(entry, dict) else {}
    submitted_raw = metadata.get("submitted_at")
    release_raw = metadata.get("release_date")

    submitted_dt = None
    if isinstance(submitted_raw, str) and submitted_raw:
        try:
            submitted_dt = datetime.fromisoformat(submitted_raw.replace("Z", "+00:00"))
        except ValueError:
            submitted_dt = None

    release_dt = None
    if isinstance(release_raw, str) and release_raw:
        try:
            release_dt = datetime.fromisoformat(release_raw)
        except ValueError:
            release_dt = None

    return submitted_dt, release_dt


def _prefer_newer_entry(current: dict, candidate: dict) -> dict:
    """Pick preferred entry between two same-idempotency-key candidates."""
    current_submitted, current_release = _parse_entry_time(current)
    candidate_submitted, candidate_release = _parse_entry_time(candidate)

    if current_submitted and candidate_submitted and candidate_submitted != current_submitted:
        return candidate if candidate_submitted > current_submitted else current
    if current_submitted is None and candidate_submitted is not None:
        return candidate
    if current_submitted is not None and candidate_submitted is None:
        return current

    if current_release and candidate_release and candidate_release != current_release:
        return candidate if candidate_release > current_release else current
    if current_release is None and candidate_release is not None:
        return candidate
    if current_release is not None and candidate_release is None:
        return current

    current_tps = float(current.get("metrics", {}).get("throughput_tps") or 0.0)
    candidate_tps = float(candidate.get("metrics", {}).get("throughput_tps") or 0.0)
    if candidate_tps != current_tps:
        return candidate if candidate_tps > current_tps else current

    return current


def _normalize_entries_payload(payload: dict | list) -> list[dict]:
    """Normalize leaderboard JSON payload to a list of entries."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


@main.command()
@click.option(
    "--dataset",
    type=str,
    default="intellistream/sagellm-benchmark-results",
    help="Hugging Face dataset repo ID (e.g., intellistream/sagellm-benchmark-results).",
)
@click.option(
    "--input",
    "input_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default="outputs",
    show_default=True,
    help="Input directory to scan recursively for *_leaderboard.json files.",
)
@click.option(
    "--token",
    type=str,
    default=None,
    help="Hugging Face token (fallback to HF_TOKEN env var).",
)
@click.option(
    "--private/--public",
    default=False,
    help="Create dataset repo as private/public if it does not exist.",
)
def upload_hf(dataset: str, input_dir: str, token: str | None, private: bool) -> None:
    """Upload benchmark leaderboard files to Hugging Face dataset."""
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        console.print("[red]❌ missing dependency: huggingface_hub[/red]")
        console.print("Install with: [cyan]pip install huggingface_hub[/cyan]")
        sys.exit(1)

    resolved_token = token or os.getenv("HF_TOKEN")
    if not resolved_token:
        console.print("[red]❌ HF token not provided[/red]")
        console.print("Use --token or set HF_TOKEN environment variable")
        sys.exit(1)

    hf_endpoint = os.getenv("HF_ENDPOINT", "https://huggingface.co")
    os.environ["HF_ENDPOINT"] = hf_endpoint

    input_path = Path(input_dir)
    leaderboard_files = sorted(input_path.rglob("*_leaderboard.json"))

    if not leaderboard_files:
        console.print(f"[red]❌ No leaderboard files found under: {input_path}[/red]")
        sys.exit(1)

    api = HfApi(endpoint=hf_endpoint, token=resolved_token)

    try:
        api.repo_info(repo_id=dataset, repo_type="dataset")
        console.print(f"[green]✓ Dataset exists:[/green] {dataset}")
    except Exception:
        console.print(f"[yellow]⚠ Dataset not found, creating:[/yellow] {dataset}")
        api.create_repo(repo_id=dataset, repo_type="dataset", private=private)
        console.print(f"[green]✓ Created dataset:[/green] {dataset}")

    console.print(f"[cyan]Endpoint:[/cyan] {hf_endpoint}")
    console.print(
        f"[cyan]Scanning[/cyan] {len(leaderboard_files)} leaderboard files from {input_path}"
    )

    canonical_entries: dict[str, dict] = {}
    parse_errors: list[str] = []
    for file_path in leaderboard_files:
        try:
            with open(file_path) as f:
                payload = json.load(f)
        except Exception as exc:
            parse_errors.append(f"{file_path}: {exc}")
            continue

        for entry in _normalize_entries_payload(payload):
            key = build_idempotency_key(entry)
            entry_with_key = json.loads(json.dumps(entry))
            metadata = entry_with_key.setdefault("metadata", {})
            metadata["idempotency_key"] = key
            entry_with_key["canonical_path"] = build_canonical_path(entry_with_key)

            existing = canonical_entries.get(key)
            canonical_entries[key] = (
                _prefer_newer_entry(existing, entry_with_key) if existing else entry_with_key
            )

    if parse_errors:
        console.print("[yellow]⚠ Some files could not be parsed and were skipped:[/yellow]")
        for error in parse_errors:
            console.print(f"  - {error}")

    if not canonical_entries:
        console.print("[red]❌ No valid leaderboard entries found for upload[/red]")
        sys.exit(1)

    console.print(
        f"[cyan]Idempotent entries:[/cyan] {len(canonical_entries)} "
        f"(from {len(leaderboard_files)} files)"
    )

    upload_errors: list[str] = []
    skipped_count = 0
    uploaded_count = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading canonical entries", total=len(canonical_entries))

        for key, entry in canonical_entries.items():
            path_in_repo = entry["canonical_path"]
            try:
                local_is_newer = True
                try:
                    remote_file = hf_hub_download(
                        repo_id=dataset,
                        filename=path_in_repo,
                        repo_type="dataset",
                        token=resolved_token,
                        endpoint=hf_endpoint,
                    )
                    with open(remote_file) as f:
                        remote_payload = json.load(f)
                    remote_entries = _normalize_entries_payload(remote_payload)
                    if remote_entries:
                        preferred = _prefer_newer_entry(remote_entries[0], entry)
                        local_is_newer = preferred is entry
                except Exception:
                    local_is_newer = True

                if not local_is_newer:
                    skipped_count += 1
                    continue

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", encoding="utf-8", delete=False
                ) as temp_file:
                    json.dump(entry, temp_file, indent=2)
                    temp_path = temp_file.name

                api.upload_file(
                    path_or_fileobj=temp_path,
                    path_in_repo=path_in_repo,
                    repo_id=dataset,
                    repo_type="dataset",
                    commit_message=(
                        f"Upsert canonical leaderboard {path_in_repo} "
                        f"({datetime.now().isoformat()})"
                    ),
                )
                uploaded_count += 1
                Path(temp_path).unlink(missing_ok=True)
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                upload_errors.append(f"{path_in_repo}: {exc}")
            finally:
                progress.advance(task)

    if upload_errors:
        console.print("[red]❌ Upload completed with errors:[/red]")
        for error in upload_errors:
            console.print(f"  - {error}")
        sys.exit(1)

    console.print("[bold green]✅ Upload complete![/bold green]")
    console.print(f"[green]Uploaded:[/green] {uploaded_count}")
    console.print(f"[yellow]Skipped (remote newer/same):[/yellow] {skipped_count}")
    console.print(f"🔗 https://huggingface.co/datasets/{dataset}")


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
        subprocess.run([sys.executable, str(aggregate_script)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ 聚合失败: {e}[/red]")
        sys.exit(1)


@main.command()
@click.option(
    "--results",
    default="./benchmark_results",
    show_default=True,
    help="Directory containing JSON benchmark result files.",
)
@click.option(
    "--output",
    default="dashboard.html",
    show_default=True,
    help="Output HTML file path.",
)
@click.option(
    "--title",
    default="SageLLM Performance Leaderboard",
    show_default=True,
    help="Dashboard page title.",
)
@click.option(
    "--sort-by",
    default="throughput_tps",
    type=click.Choice(["throughput_tps", "ttft_ms", "latency_p99_ms", "tbt_ms"]),
    show_default=True,
    help="Default sort column for ranking.",
)
def dashboard(results: str, output: str, title: str, sort_by: str) -> None:
    """生成交互式 HTML 性能排行榜（Dashboard）.

    从 benchmark_results/ 目录加载 JSON 结果，生成可排序的 HTML 排行榜页面，
    支持按场景/数据集分 Tab 展示不同工作负载的性能排名。

    示例:

        sagellm-benchmark dashboard --results ./benchmark_results --output dashboard.html
    """
    from sagellm_benchmark.dashboard import RankingDashboard

    db = RankingDashboard(results_dir=results)
    db.load()

    if not db._entries:
        console.print(f"[yellow]⚠️  No results found in {results}[/yellow]")
        console.print("[dim]Run 'sagellm-benchmark run' to generate results first.[/dim]")
        return

    db.generate(output_path=output, title=title, sort_by=sort_by)
    n = len(db._entries)
    console.print(f"[bold green]✅ Dashboard generated: {output}[/bold green]")
    console.print(f"[green]   Entries: {n} result row(s)[/green]")
    console.print(f"[dim]   Open {output} in a browser to view the leaderboard.[/dim]")


@main.command("workload-template")
@click.option(
    "--output",
    default="workloads_template.json",
    show_default=True,
    help="Output path for the template file (.json or .yaml/.yml).",
)
@click.option(
    "--format",
    "fmt",
    default="json",
    type=click.Choice(["json", "yaml"]),
    show_default=True,
    help="Template file format.",
)
def workload_template(output: str, fmt: str) -> None:
    """生成工作负载配置模板文件 (YAML / JSON).

    生成一个包含预设示例的模板文件，用户可基于此模板自定义 workload 配置，
    然后通过 ``--workload-file`` 参数加载。

    示例:

        sagellm-benchmark workload-template --output my_workloads.yaml --format yaml

        sagellm-benchmark run --workload-file my_workloads.yaml ...
    """
    from sagellm_benchmark.workloads import WorkloadTemplateGenerator

    if fmt == "yaml":
        WorkloadTemplateGenerator.generate_yaml(output)
    else:
        WorkloadTemplateGenerator.generate_json(output)

    console.print(f"[bold green]✅ Workload template written to: {output}[/bold green]")
    console.print("[dim]Edit the file and use --workload-file to load custom workloads.[/dim]")


if __name__ == "__main__":
    main()
