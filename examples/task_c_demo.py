"""端到端示例：演示 Aggregator + Contract + Reporters 完整流程。

用法:
    python examples/task_c_demo.py
"""

from __future__ import annotations

from pathlib import Path

from sagellm_protocol import Metrics, Timestamps

from sagellm_benchmark.metrics import ContractVerifier, MetricsAggregator
from sagellm_benchmark.reporters import JSONReporter, MarkdownReporter, TableReporter
from sagellm_benchmark.types import BenchmarkResult, ContractVersion


def create_sample_results() -> list[BenchmarkResult]:
    """创建 5 个示例 BenchmarkResult（Year1 水平）。"""
    results = []

    for i in range(5):
        timestamps = Timestamps(
            queued_at=1000.0 + i * 2.0,
            scheduled_at=1000.0 + i * 2.0 + 0.1,
            executed_at=1000.0 + i * 2.0 + 0.2,
            completed_at=1000.0 + i * 2.0 + 0.3,
        )

        metrics = Metrics(
            ttft_ms=10.0 + i * 5.0,  # 10, 15, 20, 25, 30 (avg=20ms)
            tbt_ms=2.0 + i * 1.0,  # 2, 3, 4, 5, 6 (avg=4ms)
            tpot_ms=2.5 + i * 0.5,  # 2.5, 3.0, 3.5, 4.0, 4.5 (avg=3.5ms)
            throughput_tps=100.0 - i * 10.0,  # 100, 90, 80, 70, 60 (avg=80 tokens/s)
            peak_mem_mb=1024 + i * 256,  # 1024 ~ 2048 (max=2048)
            error_rate=0.0,  # 无错误
            kv_used_tokens=128 + i * 32,  # 128 ~ 256
            kv_used_bytes=(128 + i * 32) * 16,
            prefix_hit_rate=0.8 + i * 0.02,  # 0.8 ~ 0.88 (avg=0.84)
            evict_count=i,  # 0, 1, 2, 3, 4 (sum=10)
            evict_ms=0.5 * i,  # 0, 0.5, 1.0, 1.5, 2.0 (sum=5.0ms)
            spec_accept_rate=0.7 + i * 0.01,  # 0.7 ~ 0.74 (avg=0.72)
            timestamps=timestamps,
        )

        result = BenchmarkResult(
            request_id=f"req-{i:03d}",
            success=True,
            error=None,
            metrics=metrics,
            output_text=f"Generated output for request {i}",
            output_tokens=50 + i * 10,  # 50, 60, 70, 80, 90 (total=350)
            prompt_tokens=100,
        )

        results.append(result)

    return results


def main() -> None:
    """运行完整的 Task C 示例。"""
    print("=" * 80)
    print("Task C 端到端示例：Metrics Aggregation & Reporting")
    print("=" * 80)
    print()

    # === 步骤 1: 创建示例数据 ===
    print("📦 Step 1: 创建 5 个示例 BenchmarkResult...")
    results = create_sample_results()
    print(f"✅ 成功创建 {len(results)} 个请求结果")
    print()

    # === 步骤 2: 聚合指标 ===
    print("📊 Step 2: 聚合指标...")
    aggregated = MetricsAggregator.aggregate(results)
    print("✅ 聚合完成")
    print(f"   - Avg TTFT: {aggregated.avg_ttft_ms:.2f}ms")
    print(f"   - P95 TTFT: {aggregated.p95_ttft_ms:.2f}ms")
    print(f"   - Avg Throughput: {aggregated.avg_throughput_tps:.2f} tokens/s")
    print(f"   - Error Rate: {aggregated.error_rate * 100:.2f}%")
    print()

    # === 步骤 3: Year1 Contract 验证 ===
    print("✅ Step 3: Year1 Contract 验证...")
    year1_result = ContractVerifier.verify(aggregated, ContractVersion.YEAR1)
    print(f"   {year1_result.summary}")

    for check_name, passed in year1_result.checks.items():
        status = "✅" if passed else "❌"
        detail = year1_result.details.get(check_name, "")
        print(f"   {status} {check_name}: {detail}")
    print()

    # === 步骤 4: Year2 Contract 验证（预期部分不通过）===
    print("🔍 Step 4: Year2 Contract 验证（更严格）...")
    year2_result = ContractVerifier.verify(aggregated, ContractVersion.YEAR2)
    print(f"   {year2_result.summary}")

    for check_name, passed in year2_result.checks.items():
        status = "✅" if passed else "❌"
        detail = year2_result.details.get(check_name, "")
        print(f"   {status} {check_name}: {detail}")
    print()

    # === 步骤 5: 生成 JSON 报告 ===
    print("💾 Step 5: 生成 JSON 报告...")
    output_dir = Path("./benchmark_results")
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "task_c_demo.json"
    JSONReporter.generate(
        metrics=aggregated,
        contract=year1_result,
        output_path=json_path,
        version="0.1.0.2",
        timestamp="2026-01-17T10:30:00",
    )
    print(f"✅ JSON 报告已保存: {json_path}")
    print()

    # === 步骤 6: 生成 Markdown 报告 ===
    print("📝 Step 6: 生成 Markdown 报告...")
    md_path = output_dir / "task_c_demo.md"
    MarkdownReporter.generate(
        metrics=aggregated,
        contract=year1_result,
        output_path=md_path,
        title="Task C Demo - Benchmark Report",
        version="0.1.0.2",
    )
    print(f"✅ Markdown 报告已保存: {md_path}")
    print()

    # === 步骤 7: 终端表格输出 ===
    print("📋 Step 7: 终端表格输出（Rich）")
    print("-" * 80)
    TableReporter.generate(
        metrics=aggregated,
        contract=year1_result,
        show_contract=True,
    )

    print("=" * 80)
    print("✅ Task C 示例完成！")
    print(f"📁 报告输出目录: {output_dir.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    main()
