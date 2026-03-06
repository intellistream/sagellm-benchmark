# sagellm-benchmark

## Protocol Compliance (Mandatory)

- MUST follow Protocol v0.1: https://github.com/intellistream/sagellm-docs/blob/main/docs/specs/protocol_v0.1.md
- Any globally shared definitions (fields, error codes, metrics, IDs, schemas) MUST be added to Protocol first.

[![CI](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/intellistream/sagellm-benchmark/branch/main/graph/badge.svg)](https://codecov.io/gh/intellistream/sagellm-benchmark)
[![PyPI version](https://badge.fury.io/py/isagellm-benchmark.svg)](https://badge.fury.io/py/isagellm-benchmark)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Private](https://img.shields.io/badge/License-Private-red.svg)](LICENSE)

Benchmark suite for sageLLM inference engine performance and validation.

New here? See [QUICKSTART.md](QUICKSTART.md) for a 5-minute guide.

## Features

- End-to-end Q1-Q8 query workloads covering diverse LLM scenarios
- Standardized JSON metrics and reports
- One-command benchmark runner
- Extensible backend support
- Performance benchmark CLI (`perf`) for operator and E2E benchmark baselines

## Dependencies

- **isagellm-protocol** (>=0.4.0.0)
- **isagellm-core** (>=0.4.0.0)
- **isagellm-backend** (>=0.4.0.1)

## Installation

```bash
pip install isagellm-benchmark
```

For specific backend support:

```bash
# With vLLM support (non-Ascend)
pip install isagellm-benchmark[vllm-client]

# With vLLM Ascend support (Ascend machines)
pip install isagellm-benchmark[vllm-ascend-client]

# With LMDeploy support
pip install isagellm-benchmark[lmdeploy-client]

# With OpenAI/Gateway support
pip install isagellm-benchmark[openai-client]
```

## Quick Start

```bash
# Run all Q1-Q8 workloads with CPU backend
sagellm-benchmark run --workload all --backend cpu --output ./benchmark_results

# Run a single query workload
sagellm-benchmark run --workload Q1 --backend cpu

# Generate a markdown report
sagellm-benchmark report --input ./benchmark_results/benchmark_summary.json --format markdown

# Run migrated performance benchmarks
sagellm-benchmark perf --type operator --device cpu
sagellm-benchmark perf --type e2e --model Qwen/Qwen2-7B-Instruct --batch-size 1 --batch-size 4

# Generate charts (PNG/PDF, dark theme)
sagellm-benchmark perf --type e2e --plot --plot-format png --plot-format pdf --theme dark
```

CLI examples:

```bash
# Run the full Q1-Q8 suite with the CPU backend
sagellm-benchmark run --workload all --backend cpu

# Run with a CPU model
sagellm-benchmark run --workload all --backend cpu --model sshleifer/tiny-gpt2

# Run a single query workload
sagellm-benchmark run --workload Q3 --backend cpu

# Generate reports
sagellm-benchmark report --input ./benchmark_results/benchmark_summary.json --format markdown

# Generate report from perf JSON
sagellm-benchmark report --input ./benchmark_results/perf_results.json --format markdown

# Re-generate charts from existing perf JSON
sagellm-benchmark report --input ./benchmark_results/perf_results.json --plot --plot-format png
```

## Ascend vLLM 对比评测

`sagellm-benchmark` 的 `perf --live` 已支持任意 OpenAI-compatible endpoint（包括 vLLM server）。

如需在 Ascend 机器上复现 `vllm-ascend` vs `sagellm` 对比，优先参考：

- [docs/ASCEND_BENCHMARK.md](docs/ASCEND_BENCHMARK.md)
- [scripts/setup_vllm_ascend_compare_env.sh](scripts/setup_vllm_ascend_compare_env.sh)

1. 分别启动两个服务（例如 `sageLLM` 与 `vLLM Ascend`），确保都提供 `/v1/models` 与 `/v1/chat/completions`。
2. 运行对比脚本：

```bash
cd sagellm-benchmark
chmod +x scripts/compare_openai_endpoints.sh
scripts/compare_openai_endpoints.sh \
   http://127.0.0.1:8901/v1 \
   http://127.0.0.1:8000/v1 \
   Qwen/Qwen2.5-0.5B-Instruct

# 可选：指定 batch 档位（默认 1,2,4）
BATCH_SIZES=1,2,4 MAX_OUTPUT_TOKENS=64 \
scripts/compare_openai_endpoints.sh \
   http://127.0.0.1:8901/v1 \
   http://127.0.0.1:8000/v1 \
   Qwen/Qwen2.5-0.5B-Instruct
```

输出会写入 `benchmark_results/compare_*/`，包含：

- `endpoint_a.json/.md`
- `endpoint_b.json/.md`
- `comparison.md`（汇总 TTFT/TBT/TPS 差异）

## Workloads

- **Q1**: Short Q&A — 32 prompt → 64 output (5 requests)
- **Q2**: Long context summarization — 512 prompt → 128 output (3 requests)
- **Q3**: Code generation — 128 prompt → 256 output (3 requests)
- **Q4**: Multi-turn conversation — 256 prompt → 256 output (3 requests)
- **Q5**: Concurrent short requests — 32 prompt → 64 output (10 concurrent)
- **Q6**: Concurrent long context — 512 prompt → 256 output (10 concurrent)
- **Q7**: Chain-of-thought reasoning — 256 prompt → 512 output (3 requests)
- **Q8**: Composite task — 192 prompt → 128 output (4 concurrent)

## Outputs

After running the benchmark, results are written to a folder like:

```
benchmark_results/
├── benchmark_summary.json
├── Q1_metrics.json
├── Q2_metrics.json
├── ...
├── Q8_metrics.json
└── REPORT.md
```

Metrics include latency, throughput, memory, and error rates. See
[docs/USAGE.md](docs/USAGE.md) for details.

## Backends

- **cpu**: CPU inference via HuggingFace Transformers (requires `--model`)
- **planned**: lmdeploy, vllm (Clients implemented, CLI integration pending)

## Development

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/intellistream/sagellm-benchmark.git
cd sagellm-benchmark

# 2. One-command setup (recommended)
./quickstart.sh --dev

# Optional: stable/release-oriented dependency baseline
./quickstart.sh --standard
```

Quickstart modes:

- `--standard`: installs baseline dependencies from PyPI, then installs current repo in editable mode.
- `--dev`: runs `standard` flow, then tries local editable overrides for sibling repos with `--no-deps`.
- Before install, `quickstart.sh` dynamically cleans existing `isagellm-*` packages for re-entrant setup.

### Running Tests

```bash
pytest tests/
```

### Local CI Fallback (when GitHub Actions is blocked)

```bash
bash scripts/local_ci_fallback.sh
```

This runs the same core checks as `.github/workflows/ci.yml` locally (pre-commit, version guard, pytest+coverage, build+twine).

### Performance Regression Check (CI)

- Workflow: `.github/workflows/benchmark.yml`
- Baseline directory: `benchmark_baselines/`
- PR: runs lightweight E2E benchmark and comments regression report on PR
- Release: runs fuller benchmark matrix and enforces regression thresholds
- Manual baseline refresh: trigger workflow with `update_baseline=true`

```bash
# Generate current perf snapshot
sagellm-benchmark perf \
   --type e2e \
   --model Qwen/Qwen2-7B-Instruct \
   --batch-size 1 --batch-size 4 --batch-size 8 \
   --precision fp16 --precision int8 \
   --output-json benchmark_results/perf_current.json \
   --output-markdown benchmark_results/perf_current.md

# Compare current snapshot with baseline
python scripts/compare_performance_baseline.py \
   --baseline benchmark_baselines/perf_baseline_e2e.json \
   --current benchmark_results/perf_current.json \
   --warning-threshold 5 \
   --critical-threshold 10 \
   --summary-json benchmark_results/perf_comparison_summary.json \
   --report-md benchmark_results/perf_comparison_report.md
```

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy src/
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - 5 分钟快速开始
- [docs/USAGE.md](docs/USAGE.md) - 详细使用指南
- [docs/CLIENTS_GUIDE.md](docs/CLIENTS_GUIDE.md) - 客户端选择指南
- [docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md) - 部署架构说明（HTTP API vs 直连）

## 🔄 贡献指南

请遵循以下工作流程：

1. **创建 Issue** - 描述问题/需求
   ```bash
   gh issue create --title "[Bug] 描述" --label "bug,sagellm-benchmark"
   ```

2. **开发修复** - 在本地 `fix/#123-xxx` 分支解决
   ```bash
   git checkout -b fix/#123-xxx origin/main-dev
   # 开发、测试...
   pytest -v
   ruff format . && ruff check . --fix
   ```

3. **发起 PR** - 提交到 `main-dev` 分支
   ```bash
   gh pr create --base main-dev --title "Fix: 描述" --body "Closes #123"
   ```

4. **合并** - 审批后合并到 `main-dev`

更多详情见 [.github/copilot-instructions.md](.github/copilot-instructions.md)

## License

Private - IntelliStream Research Project
