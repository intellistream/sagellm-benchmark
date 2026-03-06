#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${BENCH_VLLM_ASCEND_PY:-/opt/miniconda3/envs/bench-vllm-ascend/bin/python}"
SAGELLM_ROOT="${SAGELLM_ROOT:-/home/user8/sagellm}"
ASCEND_WRAPPER="${SAGELLM_ROOT}/scripts/sagellm_with_ascend_env.sh"

echo "[setup_vllm_ascend_compare_env] python=${PYTHON_BIN}"
echo "[setup_vllm_ascend_compare_env] sagellm_root=${SAGELLM_ROOT}"

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERROR: python not executable: ${PYTHON_BIN}" >&2
    exit 1
fi

if [[ ! -x "${ASCEND_WRAPPER}" ]]; then
    echo "ERROR: Ascend wrapper not executable: ${ASCEND_WRAPPER}" >&2
    exit 1
fi

"${PYTHON_BIN}" -m pip install -U \
    torch==2.7.1 \
    torch-npu==2.7.1 \
    torchvision==0.22.1 \
    torchaudio==2.7.1 \
    transformers==4.57.1 \
    vllm-ascend==0.11.0

"${PYTHON_BIN}" -m pip check

"${ASCEND_WRAPPER}" "${PYTHON_BIN}" - <<'PY'
import torch, torch_npu

print('torch', torch.__version__)
print('torch_npu', torch_npu.__version__)
print('npu_available', torch.npu.is_available())

if not torch.npu.is_available():
    raise RuntimeError('torch.npu.is_available() == False')

torch.npu.set_device('npu:0')
x = torch.ones(1, device='npu')
print('tensor_ok', (x + 1).cpu().tolist())
PY

echo "[setup_vllm_ascend_compare_env] OK"
