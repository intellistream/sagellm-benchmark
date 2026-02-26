#!/bin/bash
# One-click benchmark runner for sageLLM Q1-Q8 workloads

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${1:-./benchmark_results}"

echo "======================================"
echo "  sageLLM Benchmark - Q1~Q8 Workloads"
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
echo "[1/4] Running Q1-Q8 workloads with CPU backend..."
sagellm-benchmark run --workload all --backend cpu --output "$OUTPUT_DIR" -v

echo ""
echo "[2/4] Generating summary report..."
sagellm-benchmark report --input "$OUTPUT_DIR/benchmark_summary.json" --format table

echo ""
echo "[3/4] Generating markdown report..."
sagellm-benchmark report --input "$OUTPUT_DIR/benchmark_summary.json" --format markdown > "$OUTPUT_DIR/REPORT.md"

echo ""
echo "[4/4] Results saved to:"
echo "  - $OUTPUT_DIR/benchmark_summary.json"
echo "  - $OUTPUT_DIR/Q1_metrics.json ... Q8_metrics.json"
echo "  - $OUTPUT_DIR/Q1_leaderboard.json ... Q8_leaderboard.json"
echo "  - $OUTPUT_DIR/REPORT.md"
echo ""

# Optional: Upload to Hugging Face (requires HF_TOKEN)
if [ -n "${HF_TOKEN:-}" ]; then
    echo "[5/5] Uploading leaderboard data to Hugging Face..."
    sagellm-benchmark upload-hf \
        --input "$OUTPUT_DIR" \
        --dataset intellistream/sagellm-benchmark-results \
        --token "$HF_TOKEN"
    echo ""
    echo "✓ HF upload complete!"
else
    echo "[5/5] Skipping HF upload (HF_TOKEN not set)"
    echo "      To enable: export HF_TOKEN=hf_xxx && ./run_benchmark.sh"
fi
echo ""
echo "✓ Benchmark completed successfully!"
