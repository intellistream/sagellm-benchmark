"""Performance visualization utilities for sagellm-benchmark (#46)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_perf_charts(
    result_data: dict[str, Any],
    *,
    output_dir: str | Path,
    formats: list[str],
    theme: str = "light",
    dpi: int = 300,
) -> list[str]:
    """Generate charts for perf result payload.

    Supported chart families:
    - operator: speedup bar chart
    - e2e: latency line chart, throughput bar chart, model-precision heatmap
    """
    kind = str(result_data.get("kind", "")).lower()
    if kind not in {"operator", "e2e"}:
        raise ValueError("Unsupported perf result kind for plotting. Expected 'operator' or 'e2e'.")

    valid_formats = [fmt.lower() for fmt in formats]
    if not valid_formats:
        raise ValueError("At least one plot format must be provided.")
    invalid = [fmt for fmt in valid_formats if fmt not in {"png", "pdf"}]
    if invalid:
        raise ValueError(f"Unsupported plot format(s): {','.join(invalid)}. Use png/pdf.")

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plt, sns = _import_plot_libraries()
    _apply_theme(sns, theme)

    generated: list[str] = []
    if kind == "operator":
        generated.extend(_plot_operator_speedup(plt, result_data, out_dir, valid_formats, dpi))
    else:
        rows = result_data.get("rows", [])
        if not isinstance(rows, list) or not rows:
            raise ValueError("E2E perf result does not contain rows for plotting.")

        generated.extend(_plot_latency_line(plt, result_data, out_dir, valid_formats, dpi))
        generated.extend(_plot_throughput_bar(plt, result_data, out_dir, valid_formats, dpi))
        generated.extend(
            _plot_model_precision_heatmap(plt, sns, result_data, out_dir, valid_formats, dpi)
        )

    return generated


def _import_plot_libraries():
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
    except ImportError as exc:
        raise RuntimeError(
            "Plot generation requires matplotlib and seaborn. "
            "Install with: pip install matplotlib seaborn"
        ) from exc
    return plt, sns


def _apply_theme(sns, theme: str) -> None:
    normalized = theme.lower()
    if normalized not in {"light", "dark"}:
        raise ValueError("Theme must be 'light' or 'dark'.")
    if normalized == "dark":
        sns.set_theme(style="darkgrid")
    else:
        sns.set_theme(style="whitegrid")


def _plot_operator_speedup(
    plt, data: dict[str, Any], out_dir: Path, formats: list[str], dpi: int
) -> list[str]:
    comparisons = data.get("comparisons", [])
    if not isinstance(comparisons, list) or not comparisons:
        raise ValueError("Operator perf result does not contain comparisons for plotting.")

    names = [str(item.get("optimized_name", "unknown")) for item in comparisons]
    values = [float(item.get("speedup", 1.0)) for item in comparisons]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(names, values)
    ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
    ax.set_title("Operator Speedup Comparison")
    ax.set_ylabel("Speedup (x)")
    ax.set_xlabel("Operator")
    ax.tick_params(axis="x", rotation=25)

    for bar, speedup in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{speedup:.2f}x",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    return _save_figure(plt, fig, out_dir, "speedup_bar", formats, dpi)


def _plot_latency_line(
    plt, data: dict[str, Any], out_dir: Path, formats: list[str], dpi: int
) -> list[str]:
    grouped: dict[tuple[str, str], list[tuple[int, float]]] = {}
    for row in data.get("rows", []):
        model = str(row.get("model", "unknown"))
        precision = str(row.get("precision", "default"))
        batch_size = int(row.get("batch_size", 1))
        latency = float(row.get("latency_p95_ms", row.get("ttft_ms", 0.0)))
        grouped.setdefault((model, precision), []).append((batch_size, latency))

    if not grouped:
        raise ValueError("No e2e latency data available for line plot.")

    fig, ax = plt.subplots(figsize=(10, 6))
    for (model, precision), points in grouped.items():
        points_sorted = sorted(points, key=lambda x: x[0])
        x = [batch for batch, _ in points_sorted]
        y = [value for _, value in points_sorted]
        ax.plot(x, y, marker="o", label=f"{model} ({precision})")

    ax.set_title("Latency vs Batch Size (P95)")
    ax.set_xlabel("Batch Size")
    ax.set_ylabel("Latency P95 (ms)")
    ax.legend(loc="best", fontsize=8)

    return _save_figure(plt, fig, out_dir, "latency_line", formats, dpi)


def _plot_throughput_bar(
    plt, data: dict[str, Any], out_dir: Path, formats: list[str], dpi: int
) -> list[str]:
    aggregate: dict[str, list[float]] = {}
    for row in data.get("rows", []):
        model = str(row.get("model", "unknown"))
        aggregate.setdefault(model, []).append(float(row.get("throughput_tps", 0.0)))

    if not aggregate:
        raise ValueError("No e2e throughput data available for bar plot.")

    labels = list(aggregate.keys())
    values = [sum(v) / len(v) for v in aggregate.values()]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, values)
    ax.set_title("Throughput Comparison")
    ax.set_ylabel("Throughput (tokens/s)")
    ax.set_xlabel("Model")
    ax.tick_params(axis="x", rotation=20)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    return _save_figure(plt, fig, out_dir, "throughput_bar", formats, dpi)


def _plot_model_precision_heatmap(
    plt,
    sns,
    data: dict[str, Any],
    out_dir: Path,
    formats: list[str],
    dpi: int,
) -> list[str]:
    matrix: dict[str, dict[str, list[float]]] = {}
    precisions: set[str] = set()

    for row in data.get("rows", []):
        model = str(row.get("model", "unknown"))
        precision = str(row.get("precision", "default"))
        precisions.add(precision)
        matrix.setdefault(model, {}).setdefault(precision, []).append(
            float(row.get("throughput_tps", 0.0))
        )

    if not matrix:
        raise ValueError("No e2e model/precision data available for heatmap.")

    precision_axis = sorted(precisions)
    model_axis = sorted(matrix.keys())

    heatmap_data: list[list[float]] = []
    for model in model_axis:
        row_values = []
        for precision in precision_axis:
            values = matrix[model].get(precision, [])
            row_values.append(sum(values) / len(values) if values else 0.0)
        heatmap_data.append(row_values)

    fig, ax = plt.subplots(figsize=(8, max(4, len(model_axis) * 0.8)))
    sns.heatmap(
        heatmap_data,
        annot=True,
        fmt=".1f",
        cmap="viridis",
        xticklabels=precision_axis,
        yticklabels=model_axis,
        cbar_kws={"label": "Throughput (tokens/s)"},
        ax=ax,
    )
    ax.set_title("Model × Precision Throughput Heatmap")
    ax.set_xlabel("Precision")
    ax.set_ylabel("Model")

    return _save_figure(plt, fig, out_dir, "model_precision_heatmap", formats, dpi)


def _save_figure(
    plt,
    fig,
    out_dir: Path,
    base_name: str,
    formats: list[str],
    dpi: int,
) -> list[str]:
    paths: list[str] = []
    for fmt in formats:
        file_path = out_dir / f"{base_name}.{fmt}"
        fig.savefig(file_path, dpi=dpi, bbox_inches="tight")
        paths.append(str(file_path))
    plt.close(fig)
    return paths
