#!/bin/bash
# One-click benchmark runner for sageLLM Year 1 Demo Contract

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-./benchmark_results}"

echo "======================================"
echo "  sageLLM Benchmark - Year 1 Demo"
echo "======================================"
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""

# Check if sagellm-benchmark is installed
if ! command -v sagellm-benchmark &> /dev/null; then
    echo "Error: sagellm-benchmark not installed"
    echo "Install with: pip install isagellm-benchmark"
    exit 1
fi

# Run benchmark with CPU backend (no GPU required)
echo "[1/4] Running Year 1 workloads with CPU backend..."
sagellm-benchmark run --workload year1 --backend cpu --output "$OUTPUT_DIR" -v

echo ""
echo "[2/4] Generating summary report..."
sagellm-benchmark report --input "$OUTPUT_DIR/benchmark_summary.json" --format table

echo ""
echo "[3/4] Generating markdown report..."
sagellm-benchmark report --input "$OUTPUT_DIR/benchmark_summary.json" --format markdown > "$OUTPUT_DIR/REPORT.md"

echo ""
echo "[4/4] Done! Results saved to:"
echo "  - $OUTPUT_DIR/benchmark_summary.json"
echo "  - $OUTPUT_DIR/short_input_metrics.json"
echo "  - $OUTPUT_DIR/long_input_metrics.json"
echo "  - $OUTPUT_DIR/stress_test_metrics.json"
echo "  - $OUTPUT_DIR/REPORT.md"
echo ""
echo "✓ Benchmark completed successfully!"
