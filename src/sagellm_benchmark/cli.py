"""CLI for sagellm-benchmark."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="sagellm-benchmark")
def main() -> None:
    """sageLLM Benchmark Suite - Year 1 Demo Contract Validation."""
    pass


@main.command()
@click.option(
    "--workload",
    type=click.Choice(["year1", "short", "long", "stress"]),
    default="year1",
    help="Workload type to run.",
)
@click.option(
    "--backend",
    type=click.Choice(["mock", "cpu", "lmdeploy", "vllm"]),
    default="mock",
    help="Backend engine to use.",
)
@click.option(
    "--model",
    type=str,
    default=None,
    help="Model path (for non-mock backends).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="./benchmark_results",
    help="Output directory for results.",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging.",
)
def run(
    workload: str,
    backend: str,
    model: str | None,
    output: str,
    verbose: bool,
) -> None:
    """Run benchmark workloads."""
    console.print("[bold cyan]sageLLM Benchmark[/bold cyan]")
    console.print(f"Workload: {workload}")
    console.print(f"Backend: {backend}")

    # Import engine
    try:
        from sagellm_backend.engine import get_engine_factory
    except ImportError:
        console.print("[bold red]Error:[/bold red] isagellm-backend not installed.")
        console.print("Install with: pip install isagellm-backend")
        sys.exit(1)

    # Determine workloads to run
    from sagellm_benchmark.workloads import YEAR1_WORKLOADS, WorkloadType

    if workload == "year1":
        workloads = YEAR1_WORKLOADS
    elif workload == "short":
        workloads = [w for w in YEAR1_WORKLOADS if w.workload_type == WorkloadType.SHORT]
    elif workload == "long":
        workloads = [w for w in YEAR1_WORKLOADS if w.workload_type == WorkloadType.LONG]
    elif workload == "stress":
        workloads = [w for w in YEAR1_WORKLOADS if w.workload_type == WorkloadType.STRESS]
    else:
        console.print(f"[bold red]Unknown workload:[/bold red] {workload}")
        sys.exit(1)

    # Create engine
    engine_factory = get_engine_factory()

    if backend == "mock":
        from sagellm_backend.engine.mock import MockConfig

        config = MockConfig(
            model_path="mock-model",
            device="cpu",
            mock_ttft_ms=10.0,
            mock_tbt_ms=5.0,
            mock_throughput_tps=100.0,
        )
        engine = engine_factory.create_engine("mock", config)

    elif backend == "cpu":
        if model is None:
            console.print("[bold red]Error:[/bold red] --model required for CPU backend")
            console.print("Example: --model gpt2")
            sys.exit(1)

        from sagellm_backend.engine.cpu import CPUConfig

        config = CPUConfig(
            model_path=model,
            device="cpu",
        )
        engine = engine_factory.create_engine("cpu", config)

    else:
        console.print(f"[bold red]Backend not yet implemented:[/bold red] {backend}")
        console.print("Available: mock, cpu")
        sys.exit(1)

    # Run benchmark
    from sagellm_benchmark.runner import BenchmarkConfig, BenchmarkRunner

    bench_config = BenchmarkConfig(
        engine=engine,
        workloads=workloads,
        output_dir=Path(output),
        verbose=verbose,
    )

    runner = BenchmarkRunner(bench_config)

    console.print("\n[bold green]Starting benchmark...[/bold green]")
    console.print(f"Workloads: {len(workloads)}")
    console.print(f"Output: {output}\n")

    try:
        results = asyncio.run(runner.run())

        # Display summary
        console.print("\n[bold green]✓ Benchmark completed![/bold green]\n")
        _display_results(results)

        console.print(f"\n[dim]Results saved to: {output}/[/dim]")

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


if __name__ == "__main__":
    main()
