#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${BENCH_VLLM_ASCEND_PY:-/opt/miniconda3/envs/bench-vllm-ascend/bin/python}"
SAGELLM_ROOT="${SAGELLM_ROOT:-/home/user8/sagellm}"

echo "[setup_vllm_ascend_compare_env] python=${PYTHON_BIN}"
echo "[setup_vllm_ascend_compare_env] sagellm_root=${SAGELLM_ROOT}"
echo "[compat] setup_vllm_ascend_compare_env.sh now delegates to: sagellm-benchmark vllm-compare install-ascend"

exec sagellm-benchmark vllm-compare install-ascend \
    --python-bin "${PYTHON_BIN}" \
    --sagellm-root "${SAGELLM_ROOT}"
