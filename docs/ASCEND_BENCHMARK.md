# Ascend Endpoint Benchmark Guide

本文档记录在 Ascend 机器上**可复现**地对比 `vllm-ascend` 与 `sagellm` 的最小流程。

目标：后续继续做性能比较时，不需要再重新摸索环境安装、启动命令与判活步骤。

## 1. 适用范围

- 机器具备 Ascend NPU（`npu-smi` 可用）
- 使用 OpenAI-compatible endpoint 做 live benchmark
- 对比对象：
  - `vllm-ascend`
  - `sagellm serve --benchmark-mode`

## 2. 已验证的软件矩阵

当前已验证可跑通对比的版本组合：

- CANN toolkit: `8.3.RC2`
- `torch==2.7.1`
- `torch-npu==2.7.1`
- `torchvision==0.22.1`
- `torchaudio==2.7.1`
- `transformers==4.57.1`
- `vllm-ascend==0.11.0`

## 3. 一键安装对比环境

推荐直接使用仓库脚本：

```bash
cd sagellm-benchmark
bash scripts/setup_vllm_ascend_compare_env.sh
```

默认行为：

- 使用 `/opt/miniconda3/envs/bench-vllm-ascend/bin/python`
- 安装上面这组已验证版本
- 执行 `pip check`
- 执行最小 Ascend 烟测（`torch + torch_npu + npu tensor`）

如需覆盖 Python 路径：

```bash
BENCH_VLLM_ASCEND_PY=/path/to/python bash scripts/setup_vllm_ascend_compare_env.sh
```

## 4. 启动前烟测

在任意 `vllm-ascend` 启动前，必须先注入 Ascend 运行时环境：

```bash
cd /home/user8/sagellm
./scripts/sagellm_with_ascend_env.sh /opt/miniconda3/envs/bench-vllm-ascend/bin/python - <<'PY'
import torch, torch_npu
print('torch', torch.__version__)
print('torch_npu', torch_npu.__version__)
print('npu_available', torch.npu.is_available())
torch.npu.set_device('npu:0')
x = torch.ones(1, device='npu')
print('tensor_ok', (x + 1).cpu().tolist())
PY
```

任一步失败都不应继续 benchmark。

## 5. 启动 `vllm-ascend`

```bash
cd /home/user8/sagellm
./scripts/sagellm_with_ascend_env.sh \
  /opt/miniconda3/envs/bench-vllm-ascend/bin/python \
  -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --host 127.0.0.1 \
  --port 8000 \
  > /tmp/vllm_ascend_8000.log 2>&1
```

说明：

- 必须通过 `sagellm_with_ascend_env.sh` 注入环境
- 首次启动可能需要等待模型下载与 ACL graph capture

判活要求：

```bash
ss -ltnp | grep ':8000'
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/models
```

## 6. 启动 `sagellm`

用于 benchmark 时，必须显式开启 `--benchmark-mode`，避免 canary 影响启动与测量：

```bash
cd /home/user8/sagellm
HF_ENDPOINT=https://hf-mirror.com \
SAGELLM_ASCEND_TOOLKIT_HOME=/usr/local/Ascend/ascend-toolkit/8.3.RC2 \
./scripts/sagellm_with_ascend_env.sh \
  /opt/miniconda3/envs/sage/bin/sagellm serve \
  --backend ascend \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --host 127.0.0.1 \
  --port 8901 \
  --benchmark-mode \
  > /tmp/sagellm_8901.log 2>&1
```

判活要求：

```bash
ss -ltnp | grep ':8901'
curl http://127.0.0.1:8901/health
curl http://127.0.0.1:8901/v1/models
```

## 7. 运行对比 benchmark

```bash
cd /home/user8/sagellm-benchmark
BATCH_SIZES=1,2,4 MAX_OUTPUT_TOKENS=64 REQUEST_TIMEOUT=180 \
scripts/compare_openai_endpoints.sh \
  http://127.0.0.1:8000/v1 \
  http://127.0.0.1:8901/v1 \
  Qwen/Qwen2.5-0.5B-Instruct
```

输出目录默认在：

```text
benchmark_results/compare_<timestamp>/
```

包含：

- `endpoint_a.json`
- `endpoint_a.md`
- `endpoint_b.json`
- `endpoint_b.md`
- `comparison.md`

## 8. 当前已验证的一组结果

同一模型、同一 batch 档位下，已跑通 live benchmark，对比结论如下：

| Metric | `vllm-ascend` | `sagellm` |
|---|---:|---:|
| Avg TTFT (ms) | 165.83 | 541.75 |
| Avg TBT (ms) | 14.60 | 147.38 |
| Avg TPS | 52.50 | 8.06 |

该结果说明：

- 两边 endpoint 都已可用
- `sagellm-benchmark` 已可用于 Ascend 机器上的真实 live 对比

## 9. 注意事项

- 不要把华为 Ascend 安装包（`.run` / `.deb`）提交到仓库；它们体积大，且通常应按上游许可与分发方式获取
- 推荐把“版本矩阵 + 下载地址 + 脚本”固化到文档和脚本，而不是提交二进制包
- 若 `vllm-ascend` 首次启动慢，优先等待模型下载和 ACL graph capture 完成，不要过早判定失败
- 若 `sagellm` benchmark 启动失败，优先确认是否遗漏 `--benchmark-mode`
