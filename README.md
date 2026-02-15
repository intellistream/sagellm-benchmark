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

- End-to-end workload execution (short, long, stress)
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
# With vLLM support
pip install isagellm-benchmark[vllm-client]

# With LMDeploy support
pip install isagellm-benchmark[lmdeploy-client]

# With OpenAI/Gateway support
pip install isagellm-benchmark[openai-client]
```

## Quick Start

```bash
# Run all workloads (Short, Long, Stress) uses CPU backend by default
sagellm-benchmark run --workload m1 --backend cpu --output ./benchmark_results

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
# Run the full suite with the CPU backend
sagellm-benchmark run --workload m1 --backend cpu

# Run with a CPU model
sagellm-benchmark run --workload m1 --backend cpu --model sshleifer/tiny-gpt2

# Run a single workload
sagellm-benchmark run --workload short --backend cpu

# Generate reports
sagellm-benchmark report --input ./benchmark_results/benchmark_summary.json --format markdown

# Generate report from perf JSON
sagellm-benchmark report --input ./benchmark_results/perf_results.json --format markdown

# Re-generate charts from existing perf JSON
sagellm-benchmark report --input ./benchmark_results/perf_results.json --plot --plot-format png
```

## Workloads

- **m1** (Year 1 Demo): Full suite of predefined workloads (Short + Long + Stress)
- **short**: 128 prompt → 128 output (5 requests)
- **long**: 200 prompt → 200 output (3 requests)
- **stress**: 256 prompt → 256 output (10 concurrent requests)

## Outputs

After running the benchmark, results are written to a folder like:

```
benchmark_results/
├── benchmark_summary.json
├── short_input_metrics.json
├── long_input_metrics.json
├── stress_test_metrics.json
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

# 2. Install in editable mode with dev dependencies
pip install -e .[dev,all-clients]
```

### Running Tests

```bash
pytest tests/
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
