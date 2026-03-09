#!/usr/bin/env bash

set -euo pipefail

DEFAULT_VLLM_URL="${DEFAULT_VLLM_URL:-http://127.0.0.1:8000/v1}"
DEFAULT_SAGELLM_URL="${DEFAULT_SAGELLM_URL:-http://127.0.0.1:8901/v1}"

usage() {
    echo "Usage: $0 [vllm_url sagellm_url [model]]"
    echo ""
    echo "No-arg mode:"
    echo "  vllm_url=$DEFAULT_VLLM_URL"
    echo "  sagellm_url=$DEFAULT_SAGELLM_URL"
    echo "  model=Qwen/Qwen2.5-0.5B-Instruct"
    echo ""
    echo "Examples:"
    echo "  $0"
    echo "  $0 Qwen/Qwen2.5-0.5B-Instruct"
    echo "  $0 http://127.0.0.1:8000/v1 http://127.0.0.1:8901/v1"
    echo "  $0 http://127.0.0.1:8000/v1 http://127.0.0.1:8901/v1 Qwen/Qwen2.5-0.5B-Instruct"
}

case "$#" in
    0)
        VLLM_URL="$DEFAULT_VLLM_URL"
        SAGELLM_URL="$DEFAULT_SAGELLM_URL"
        MODEL="Qwen/Qwen2.5-0.5B-Instruct"
        ;;
    1)
        VLLM_URL="$DEFAULT_VLLM_URL"
        SAGELLM_URL="$DEFAULT_SAGELLM_URL"
        MODEL="$1"
        ;;
    2)
        VLLM_URL="$1"
        SAGELLM_URL="$2"
        MODEL="Qwen/Qwen2.5-0.5B-Instruct"
        ;;
    3)
        VLLM_URL="$1"
        SAGELLM_URL="$2"
        MODEL="$3"
        ;;
    *)
        usage
        exit 1
        ;;
esac
OUT_DIR="${OUT_DIR:-./benchmark_results/compare_$(date +%Y%m%d_%H%M%S)}"
MAX_OUTPUT_TOKENS="${MAX_OUTPUT_TOKENS:-64}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-120}"
BATCH_SIZES_CSV="${BATCH_SIZES:-1,2,4}"

mkdir -p "$OUT_DIR"

echo "[compat] compare_openai_endpoints.sh now delegates to: sagellm-benchmark vllm-compare run"
echo "Using vllm_url=$VLLM_URL"
echo "Using sagellm_url=$SAGELLM_URL"
echo "Using model=$MODEL"

IFS=',' read -r -a batch_sizes <<< "$BATCH_SIZES_CSV"

args=(
    vllm-compare
    run
    --sagellm-url "$SAGELLM_URL"
    --vllm-url "$VLLM_URL"
    --model "$MODEL"
    --request-timeout "$REQUEST_TIMEOUT"
    --output-dir "$OUT_DIR"
)

if [[ -n "$MAX_OUTPUT_TOKENS" ]]; then
    args+=(--max-output-tokens "$MAX_OUTPUT_TOKENS")
fi

for bs in "${batch_sizes[@]}"; do
    bs_trimmed="${bs//[[:space:]]/}"
    if [[ -n "$bs_trimmed" ]]; then
        args+=(--batch-size "$bs_trimmed")
    fi
done

echo "===== Running canonical compare entrypoint (batch_sizes=$BATCH_SIZES_CSV) ====="
sagellm-benchmark "${args[@]}"

echo ""
echo "Saved reports under: $OUT_DIR"
