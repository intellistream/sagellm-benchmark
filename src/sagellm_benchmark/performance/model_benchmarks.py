"""E2E model-level benchmarks for sagellm-benchmark (#45)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class Scenario:
    name: str
    prompt_tokens: int
    output_tokens: int
    batch_size: int


def run_e2e_model_benchmarks(
    *,
    models: list[str],
    batch_sizes: list[int],
    simulate: bool = True,
) -> list[dict[str, Any]]:
    """Run E2E model benchmarks.

    Currently uses deterministic simulation mode by default to keep CI stable.
    """
    scenarios: list[Scenario] = []
    for batch_size in batch_sizes:
        scenarios.extend(
            [
                Scenario(f"short_b{batch_size}", 128, 128, batch_size),
                Scenario(f"long_b{batch_size}", 2048, 512, batch_size),
            ]
        )

    rows: list[dict[str, Any]] = []
    for model in models:
        for scenario in scenarios:
            if not simulate:
                raise RuntimeError(
                    "Live E2E benchmark mode is not enabled yet in sagellm-benchmark."
                )

            # deterministic synthetic metrics
            seed = hash((model, scenario.name)) % (2**32)
            rng = random.Random(seed)
            factor = 1.2 if "Llama" in model else (0.9 if "Phi" in model else 1.0)
            context_factor = 1.8 if scenario.prompt_tokens > 1000 else 1.0

            ttft = 45.0 * factor * context_factor * (1 + rng.uniform(-0.08, 0.08))
            tbt = 9.0 * factor * context_factor * (1 + rng.uniform(-0.08, 0.08))
            throughput = 100.0 / factor / context_factor * (scenario.batch_size**0.4)
            throughput *= 1 + rng.uniform(-0.08, 0.08)

            # simulate latency samples for quantiles
            latencies = []
            for _ in range(max(3, scenario.batch_size)):
                latencies.append(
                    ttft
                    + tbt * max(1, scenario.output_tokens - 1) / max(1.0, scenario.batch_size * 0.7)
                )

            rows.append(
                {
                    "model": model,
                    "scenario": scenario.name,
                    "batch_size": scenario.batch_size,
                    "ttft_ms": ttft,
                    "tbt_ms": tbt,
                    "throughput_tps": throughput,
                    "latency_p50_ms": _percentile(latencies, 50),
                    "latency_p95_ms": _percentile(latencies, 95),
                    "latency_p99_ms": _percentile(latencies, 99),
                    "memory_mb": 5000.0 * factor + scenario.prompt_tokens * 0.2,
                }
            )

    return rows


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * (p / 100.0)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = index - lower
    return sorted_values[lower] * (1 - frac) + sorted_values[upper] * frac


def summarize_e2e_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_rows": len(rows),
        "avg_ttft_ms": mean(row["ttft_ms"] for row in rows) if rows else 0.0,
        "avg_tbt_ms": mean(row["tbt_ms"] for row in rows) if rows else 0.0,
        "avg_throughput_tps": mean(row["throughput_tps"] for row in rows) if rows else 0.0,
    }
