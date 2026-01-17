"""Demo Contract 验证器 - 验证指标是否满足 Year1/2/3 性能要求。

符合 INTERFACE_CONTRACT.md §5 定义。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sagellm_benchmark.types import AggregatedMetrics, ContractResult, ContractVersion


class ContractVerifier:
    """Demo Contract 验证器。

    Year1/2/3 阈值定义参考 sageLLM Copilot Instructions 和 BENCHMARK_DESIGN.md。
    """

    # Year1 Demo Contract 阈值（基线要求）
    YEAR1_THRESHOLDS = {
        "ttft_ms": 100.0,  # TTFT < 100ms
        "tbt_ms": 20.0,  # TBT < 20ms
        "tpot_ms": 20.0,  # TPOT < 20ms
        "throughput_tps": 50.0,  # 吞吐 > 50 tokens/s
        "error_rate": 0.05,  # 错误率 < 5%
        "peak_mem_mb": 32768,  # 峰值内存 < 32GB
    }

    # Year2 Demo Contract 阈值（优化目标）
    YEAR2_THRESHOLDS = {
        "ttft_ms": 50.0,  # TTFT < 50ms（优化 50%）
        "tbt_ms": 10.0,  # TBT < 10ms
        "tpot_ms": 10.0,  # TPOT < 10ms
        "throughput_tps": 100.0,  # 吞吐 > 100 tokens/s（翻倍）
        "error_rate": 0.02,  # 错误率 < 2%
        "peak_mem_mb": 24576,  # 峰值内存 < 24GB（减少 25%）
        "prefix_hit_rate": 0.7,  # Prefix 命中率 > 70%
    }

    # Year3 Demo Contract 阈值（极致性能）
    YEAR3_THRESHOLDS = {
        "ttft_ms": 30.0,  # TTFT < 30ms
        "tbt_ms": 5.0,  # TBT < 5ms
        "tpot_ms": 5.0,  # TPOT < 5ms
        "throughput_tps": 200.0,  # 吞吐 > 200 tokens/s
        "error_rate": 0.01,  # 错误率 < 1%
        "peak_mem_mb": 16384,  # 峰值内存 < 16GB
        "prefix_hit_rate": 0.85,  # Prefix 命中率 > 85%
        "spec_accept_rate": 0.6,  # Speculative 接受率 > 60%
    }

    @staticmethod
    def verify(metrics: AggregatedMetrics, version: ContractVersion) -> ContractResult:
        """验证 AggregatedMetrics 是否满足 Demo Contract。

        Args:
            metrics: 聚合指标。
            version: Contract 版本（year1/year2/year3）。

        Returns:
            ContractResult，包含 pass/fail + 详细检查结果。
        """
        from sagellm_benchmark.types import ContractResult, ContractVersion

        # 选择阈值
        if version == ContractVersion.YEAR1:
            thresholds = ContractVerifier.YEAR1_THRESHOLDS
        elif version == ContractVersion.YEAR2:
            thresholds = ContractVerifier.YEAR2_THRESHOLDS
        elif version == ContractVersion.YEAR3:
            thresholds = ContractVerifier.YEAR3_THRESHOLDS
        else:
            raise ValueError(f"Unknown contract version: {version}")

        checks: dict[str, bool] = {}
        details: dict[str, str] = {}

        # === 检查 TTFT ===
        if "ttft_ms" in thresholds:
            passed = metrics.avg_ttft_ms <= thresholds["ttft_ms"]
            checks["ttft_ms"] = passed
            details["ttft_ms"] = (
                f"TTFT: {metrics.avg_ttft_ms:.2f}ms "
                f"{'≤' if passed else '>'} {thresholds['ttft_ms']}ms"
            )

        # === 检查 TBT ===
        if "tbt_ms" in thresholds:
            passed = metrics.avg_tbt_ms <= thresholds["tbt_ms"]
            checks["tbt_ms"] = passed
            details["tbt_ms"] = (
                f"TBT: {metrics.avg_tbt_ms:.2f}ms {'≤' if passed else '>'} {thresholds['tbt_ms']}ms"
            )

        # === 检查 TPOT ===
        if "tpot_ms" in thresholds:
            passed = metrics.avg_tpot_ms <= thresholds["tpot_ms"]
            checks["tpot_ms"] = passed
            details["tpot_ms"] = (
                f"TPOT: {metrics.avg_tpot_ms:.2f}ms "
                f"{'≤' if passed else '>'} {thresholds['tpot_ms']}ms"
            )

        # === 检查吞吐 ===
        if "throughput_tps" in thresholds:
            passed = metrics.avg_throughput_tps >= thresholds["throughput_tps"]
            checks["throughput_tps"] = passed
            details["throughput_tps"] = (
                f"Throughput: {metrics.avg_throughput_tps:.2f} tokens/s "
                f"{'≥' if passed else '<'} {thresholds['throughput_tps']} tokens/s"
            )

        # === 检查错误率 ===
        if "error_rate" in thresholds:
            passed = metrics.error_rate <= thresholds["error_rate"]
            checks["error_rate"] = passed
            details["error_rate"] = (
                f"Error Rate: {metrics.error_rate * 100:.2f}% "
                f"{'≤' if passed else '>'} {thresholds['error_rate'] * 100:.2f}%"
            )

        # === 检查内存 ===
        if "peak_mem_mb" in thresholds:
            passed = metrics.peak_mem_mb <= thresholds["peak_mem_mb"]
            checks["peak_mem_mb"] = passed
            details["peak_mem_mb"] = (
                f"Peak Memory: {metrics.peak_mem_mb}MB "
                f"{'≤' if passed else '>'} {thresholds['peak_mem_mb']}MB"
            )

        # === Year2/3 额外检查 ===
        if "prefix_hit_rate" in thresholds:
            passed = metrics.avg_prefix_hit_rate >= thresholds["prefix_hit_rate"]
            checks["prefix_hit_rate"] = passed
            details["prefix_hit_rate"] = (
                f"Prefix Hit Rate: {metrics.avg_prefix_hit_rate * 100:.2f}% "
                f"{'≥' if passed else '<'} {thresholds['prefix_hit_rate'] * 100:.2f}%"
            )

        if "spec_accept_rate" in thresholds:
            passed = metrics.avg_spec_accept_rate >= thresholds["spec_accept_rate"]
            checks["spec_accept_rate"] = passed
            details["spec_accept_rate"] = (
                f"Speculative Accept Rate: {metrics.avg_spec_accept_rate * 100:.2f}% "
                f"{'≥' if passed else '<'} {thresholds['spec_accept_rate'] * 100:.2f}%"
            )

        # === 计算总结 ===
        all_passed = all(checks.values())
        passed_count = sum(checks.values())
        total_count = len(checks)

        summary = (
            f"Contract {version.value.upper()}: "
            f"{'✅ PASSED' if all_passed else '❌ FAILED'} "
            f"({passed_count}/{total_count} checks passed)"
        )

        return ContractResult(
            passed=all_passed,
            version=version,
            checks=checks,
            details=details,
            summary=summary,
        )
