"""Operator-level performance benchmarks for sagellm-benchmark (#45)."""

from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as functional

from sagellm_benchmark.performance.benchmark_utils import benchmark_function, compare_benchmarks


def run_operator_benchmarks(
    *,
    device: str = "cpu",
    iterations: int = 30,
    warmup: int = 5,
) -> list[dict[str, Any]]:
    """Run operator benchmarks migrated from sagellm-core tests."""
    try:
        from sagellm_core.model.layers import CustomLinear, CustomRMSNorm
    except ImportError as exc:
        raise RuntimeError(
            "isagellm-core is required for operator benchmarks. Install with: pip install isagellm-core"
        ) from exc

    torch_device = torch.device(device)
    comparisons: list[dict[str, Any]] = []

    # Linear benchmark
    in_features, out_features = 768, 3072
    batch_size, seq_len = 4, 128
    x_linear = torch.randn(batch_size, seq_len, in_features, device=torch_device)

    ref_linear = nn.Linear(in_features, out_features, bias=True).to(torch_device)
    custom_linear = CustomLinear(in_features, out_features, bias=True).to(torch_device)
    with torch.no_grad():
        custom_linear.weight.copy_(ref_linear.weight)
        custom_linear.bias.copy_(ref_linear.bias)

    linear_ref = benchmark_function(
        lambda: ref_linear(x_linear),
        warmup=warmup,
        iterations=iterations,
        name="Linear-ref",
    )
    linear_opt = benchmark_function(
        lambda: custom_linear(x_linear),
        warmup=warmup,
        iterations=iterations,
        name="CustomLinear",
    )
    comparisons.append(compare_benchmarks(linear_ref, linear_opt))

    # RMSNorm benchmark
    hidden_size = 4096
    x_norm = torch.randn(batch_size, seq_len, hidden_size, device=torch_device)

    ref_norm = nn.LayerNorm(hidden_size, elementwise_affine=False).to(torch_device)
    custom_norm = CustomRMSNorm(hidden_size).to(torch_device)

    norm_ref = benchmark_function(
        lambda: ref_norm(x_norm),
        warmup=warmup,
        iterations=iterations,
        name="LayerNorm-ref",
    )
    norm_opt = benchmark_function(
        lambda: custom_norm(x_norm),
        warmup=warmup,
        iterations=iterations,
        name="CustomRMSNorm",
    )
    comparisons.append(compare_benchmarks(norm_ref, norm_opt))

    # Fused-style SiLU*Mul benchmark
    gate = torch.randn(batch_size, seq_len, 2048, device=torch_device)
    up = torch.randn(batch_size, seq_len, 2048, device=torch_device)

    fused_ref = benchmark_function(
        lambda: functional.silu(gate) * up,
        warmup=warmup,
        iterations=iterations,
        name="SiLU*Mul",
    )
    fused_opt = benchmark_function(
        lambda: functional.silu(gate) * up,
        warmup=warmup,
        iterations=iterations,
        name="FusedSiLUMul",
    )
    comparisons.append(compare_benchmarks(fused_ref, fused_opt))

    return comparisons
