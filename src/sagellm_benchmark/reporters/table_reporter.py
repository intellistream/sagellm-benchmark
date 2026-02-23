"""Table 报告生成器 - 使用 Rich 输出终端表格。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sagellm_benchmark.types import AggregatedMetrics, ContractResult


class TableReporter:
    """终端表格报告生成器（使用 Rich）。

    输出彩色终端表格，适合 CLI 实时展示。
    """

    @staticmethod
    def generate(
        metrics: AggregatedMetrics,
        contract: ContractResult | None = None,
        show_contract: bool = True,
    ) -> None:
        """生成并打印终端表格。

        Args:
            metrics: 聚合指标。
            contract: Contract 验证结果（可选）。
            show_contract: 是否显示 Contract 验证结果。
        """
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError:
            # Fallback: 简单文本输出
            TableReporter._generate_plain_text(metrics, contract, show_contract)
            return

        console = Console()

        # === 总览表格 ===
        summary_table = Table(title="📊 Benchmark Summary", show_header=True, header_style="bold")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")

        summary_table.add_row("Total Requests", str(metrics.total_requests))
        summary_table.add_row("Successful", str(metrics.successful_requests))
        summary_table.add_row("Failed", str(metrics.failed_requests))
        summary_table.add_row("Error Rate", f"{metrics.error_rate * 100:.2f}%")
        summary_table.add_row("Total Time", f"{metrics.total_time_s:.2f}s")

        console.print(summary_table)
        console.print()

        # === Contract 验证 ===
        if contract and show_contract:
            contract_table = Table(
                title=f"✅ Contract Validation ({contract.version.value.upper()})",
                show_header=True,
                header_style="bold",
            )
            contract_table.add_column("Check", style="cyan")
            contract_table.add_column("Status", style="bold")
            contract_table.add_column("Details", style="dim")

            for check_name, passed in contract.checks.items():
                status = "[green]✅ PASS[/green]" if passed else "[red]❌ FAIL[/red]"
                detail = contract.details.get(check_name, "N/A")
                contract_table.add_row(check_name, status, detail)

            console.print(contract_table)
            console.print()
            console.print(f"[bold]{contract.summary}[/bold]")
            console.print()

        # === 延迟指标 ===
        latency_table = Table(title="⏱️  Latency Metrics", show_header=True, header_style="bold")
        latency_table.add_column("Metric", style="cyan")
        latency_table.add_column("Value", style="magenta")

        latency_table.add_row("Avg TTFT", f"{metrics.avg_ttft_ms:.2f} ms")
        latency_table.add_row("P50 TTFT", f"{metrics.p50_ttft_ms:.2f} ms")
        latency_table.add_row("P95 TTFT", f"{metrics.p95_ttft_ms:.2f} ms")
        latency_table.add_row("P99 TTFT", f"{metrics.p99_ttft_ms:.2f} ms")
        latency_table.add_row("Avg TBT", f"{metrics.avg_tbt_ms:.2f} ms")
        latency_table.add_row("Avg TPOT", f"{metrics.avg_tpot_ms:.2f} ms")

        console.print(latency_table)
        console.print()

        # === 吞吐 ===
        throughput_table = Table(title="🚀 Throughput", show_header=True, header_style="bold")
        throughput_table.add_column("Metric", style="cyan")
        throughput_table.add_column("Value", style="magenta")

        # 对标 vLLM/SGLang 的新增吞吐量指标
        throughput_table.add_row("Request Throughput", f"{metrics.request_throughput_rps:.2f} req/s")
        throughput_table.add_row(
            "Input Throughput", f"{metrics.input_throughput_tps:.2f} tokens/s"
        )
        throughput_table.add_row(
            "Output Throughput", f"{metrics.output_throughput_tps:.2f} tokens/s"
        )
        throughput_table.add_row("Total Throughput", f"{metrics.total_throughput_tps:.2f} tokens/s")
        # 保持现有指标
        throughput_table.add_row("Avg Throughput", f"{metrics.avg_throughput_tps:.2f} tokens/s")

        console.print(throughput_table)
        console.print()

        # === 内存 & KV Cache ===
        resource_table = Table(title="💾 Memory & KV Cache", show_header=True, header_style="bold")
        resource_table.add_column("Metric", style="cyan")
        resource_table.add_column("Value", style="magenta")

        resource_table.add_row("Peak Memory", f"{metrics.peak_mem_mb} MB")
        resource_table.add_row("Total KV Used Tokens", str(metrics.total_kv_used_tokens))
        resource_table.add_row("Total KV Used Bytes", str(metrics.total_kv_used_bytes))
        resource_table.add_row("Avg Prefix Hit Rate", f"{metrics.avg_prefix_hit_rate * 100:.2f}%")
        resource_table.add_row("Total Evict Count", str(metrics.total_evict_count))
        resource_table.add_row("Total Evict Time", f"{metrics.total_evict_ms:.2f} ms")

        console.print(resource_table)
        console.print()

        # === Speculative ===
        if metrics.avg_spec_accept_rate > 0:
            spec_table = Table(
                title="🎯 Speculative Decoding", show_header=True, header_style="bold"
            )
            spec_table.add_column("Metric", style="cyan")
            spec_table.add_column("Value", style="magenta")

            spec_table.add_row(
                "Avg Speculative Accept Rate", f"{metrics.avg_spec_accept_rate * 100:.2f}%"
            )

            console.print(spec_table)
            console.print()

    @staticmethod
    def _generate_plain_text(
        metrics: AggregatedMetrics,
        contract: ContractResult | None = None,
        show_contract: bool = True,
    ) -> None:
        """Fallback: 简单文本输出（无 Rich）。"""
        print("\n=== Benchmark Summary ===")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful: {metrics.successful_requests}")
        print(f"Failed: {metrics.failed_requests}")
        print(f"Error Rate: {metrics.error_rate * 100:.2f}%")
        print(f"Total Time: {metrics.total_time_s:.2f}s")

        if contract and show_contract:
            print(f"\n=== Contract Validation ({contract.version.value.upper()}) ===")
            print(f"Result: {contract.summary}")

            for check_name, passed in contract.checks.items():
                status = "PASS" if passed else "FAIL"
                detail = contract.details.get(check_name, "N/A")
                print(f"  {check_name}: {status} - {detail}")

        print("\n=== Latency Metrics ===")
        print(f"Avg TTFT: {metrics.avg_ttft_ms:.2f} ms")
        print(f"P50 TTFT: {metrics.p50_ttft_ms:.2f} ms")
        print(f"P95 TTFT: {metrics.p95_ttft_ms:.2f} ms")
        print(f"P99 TTFT: {metrics.p99_ttft_ms:.2f} ms")
        print(f"Avg TBT: {metrics.avg_tbt_ms:.2f} ms")
        print(f"Avg TPOT: {metrics.avg_tpot_ms:.2f} ms")

        print("\n=== Throughput ===")
        print(f"Request Throughput: {metrics.request_throughput_rps:.2f} req/s")
        print(f"Input Throughput: {metrics.input_throughput_tps:.2f} tokens/s")
        print(f"Output Throughput: {metrics.output_throughput_tps:.2f} tokens/s")
        print(f"Total Throughput: {metrics.total_throughput_tps:.2f} tokens/s")
        print(f"Avg Throughput: {metrics.avg_throughput_tps:.2f} tokens/s")

        print("\n=== Memory & KV Cache ===")
        print(f"Peak Memory: {metrics.peak_mem_mb} MB")
        print(f"Total KV Used Tokens: {metrics.total_kv_used_tokens}")
        print(f"Total KV Used Bytes: {metrics.total_kv_used_bytes}")
        print(f"Avg Prefix Hit Rate: {metrics.avg_prefix_hit_rate * 100:.2f}%")
        print(f"Total Evict Count: {metrics.total_evict_count}")
        print(f"Total Evict Time: {metrics.total_evict_ms:.2f} ms")

        if metrics.avg_spec_accept_rate > 0:
            print("\n=== Speculative Decoding ===")
            print(f"Avg Speculative Accept Rate: {metrics.avg_spec_accept_rate * 100:.2f}%")

        print()
