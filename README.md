# sagellm-benchmark

[![CI](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/intellistream/sagellm-benchmark/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/intellistream/sagellm-benchmark/branch/main/graph/badge.svg)](https://codecov.io/gh/intellistream/sagellm-benchmark)
[![PyPI version](https://badge.fury.io/py/isagellm-benchmark.svg)](https://badge.fury.io/py/isagellm-benchmark)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Private](https://img.shields.io/badge/License-Private-red.svg)](LICENSE)

Benchmark Suite & End-to-End Testing for sageLLM inference engine.

> **🚀 New to sageLLM Benchmark?** Check out [QUICKSTART.md](QUICKSTART.md) for a 5-minute guide!

## Overview

This package provides comprehensive benchmarking and validation for Year 1/2/3:
- E2E workload execution and performance benchmarking (short/long/stress tests)
- Metrics collection and reporting with standardized JSON output
- Mock-first testing infrastructure (no GPU required)
- Integration with all sageLLM modules
- One-click benchmark runner with automated reporting

## Installation

```bash
pip install isagellm-benchmark
```

## Quick Start

### One-Click Benchmark (Recommended)

```bash
# Run complete Year 1 benchmark suite with one command
./run_benchmark.sh

# Or specify custom output directory
./run_benchmark.sh ./my_results
```

This will:
1. Run all three workloads (short/long/stress)
2. Generate metrics JSON files for each workload
3. Create summary report with aggregated statistics
4. Generate markdown report

### Manual CLI Usage

```bash
# Run Year 1 benchmark with mock backend (no GPU required)
sagellm-benchmark run --workload year1 --backend mock

# Run with CPU backend (uses HuggingFace Transformers)
sagellm-benchmark run --workload year1 --backend cpu --model gpt2

# Run specific workload only
sagellm-benchmark run --workload short --backend mock
sagellm-benchmark run --workload long --backend mock
sagellm-benchmark run --workload stress --backend mock

# Generate reports
sagellm-benchmark report --input ./benchmark_results/benchmark_summary.json --format table
sagellm-benchmark report --input ./benchmark_results/benchmark_summary.json --format markdown
```

## Year 1 Benchmark Contract

The benchmark validates all modules against this contract:

### Three Workload Types

1. **Short input**: 128 tokens prompt → 128 tokens output (5 requests)
   - Tests basic inference latency
   - Validates TTFT and throughput metrics

2. **Long input**: 200 tokens prompt → 200 tokens output (3 requests)
   - Tests long-context handling
   - Validates memory management

3. **Stress test**: 256 tokens prompt → 256 tokens output (10 concurrent requests)
   - Tests concurrent request handling
   - Validates KV cache eviction under pressure
   - May trigger errors intentionally (validates error handling)

### Required Metrics Output

Each workload produces a JSON file with these fields:

```json
{
  "avg_ttft_ms": 45.2,          // Average time to first token
  "p50_ttft_ms": 40.0,          // Median TTFT
  "p95_ttft_ms": 55.0,          // 95th percentile TTFT
  "p99_ttft_ms": 60.0,          // 99th percentile TTFT
  "avg_tbt_ms": 12.5,           // Average time between tokens
  "avg_tpot_ms": 12.5,          // Average time per output token
  "avg_throughput_tps": 80.0,   // Average throughput (tokens/sec)
  "peak_mem_mb": 24576,         // Peak memory usage
  "avg_mem_mb": 20480.0,        // Average memory usage
  "error_rate": 0.02,           // Error rate (0.0-1.0)
  "total_requests": 10,         // Total requests
  "successful_requests": 9,     // Successful requests
  "failed_requests": 1,         // Failed requests
  "kv_used_tokens": 4096,       // KV cache tokens used
  "kv_used_bytes": 134217728,   // KV cache bytes used
  "prefix_hit_rate": 0.85,      // Prefix cache hit rate
  "evict_count": 3,             // Number of evictions
  "evict_ms": 2.1,              // Eviction time
  "spec_accept_rate": 0.72,     // Speculative decoding accept rate
  "total_time_s": 15.5,         // Total benchmark time
  "start_time": 1705430400.0,   // Start timestamp
  "end_time": 1705430415.5      // End timestamp
}
```

### Output Files

After running `./run_benchmark.sh`, you will find:

```
benchmark_results/
├── benchmark_summary.json       # Aggregated summary of all workloads
├── short_input_metrics.json     # Short input workload metrics
├── long_input_metrics.json      # Long input workload metrics
├── stress_test_metrics.json     # Stress test workload metrics
└── REPORT.md                    # Human-readable markdown report
```

See `examples/` directory for sample output files.

## Backend Support

Currently supported backends:

- **mock**: Simulated backend with predictable outputs (no GPU required, fast)
  - Default TTFT: 10ms, TBT: 5ms, Throughput: 100 tok/s
  - Perfect for CI/CD and quick validation

- **cpu**: Real CPU inference using HuggingFace Transformers
  - Requires `--model` parameter (e.g., `gpt2`, `facebook/opt-125m`)
  - Real inference with actual model loading
  - Collects accurate TTFT/TBT/throughput metrics

Coming soon:
- **lmdeploy**: LMDeploy backend for GPU inference
- **vllm**: vLLM backend for high-performance GPU inference

## Mock-First Development

All benchmarks can run without GPU using the mock backend:

```bash
# CI-friendly benchmark (no GPU needed)
sagellm-benchmark run --workload year1 --backend mock

# Produces same JSON structure as real backends
# Enables testing in CI/CD pipelines
```

## Team Assignment

- **Task0.2 E2E Benchmark Suite**: 张书豪老师团队
- **Task0.8 Service Integration**: All teams (integration testing)

## Dependencies

Required:
- `isagellm>=0.1.0` (umbrella package, includes protocol/backend/core)
- `click>=8.0.0` (CLI framework)
- `rich>=13.0.0` (terminal UI)

Optional:
- `isagellm-kv-cache>=0.1.0` - KV cache metrics
- `isagellm-comm>=0.1.0` - Communication metrics
- `isagellm-compression>=0.1.0` - Compression metrics

## Development

```bash
# Clone and install
git clone git@github.com:intellistream/sagellm-benchmark.git
cd sagellm-benchmark
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run linter
ruff check .
ruff format .

# Test one-click runner
./run_benchmark.sh

# Test specific workload
sagellm-benchmark run --workload short --backend mock -v
```

## CI Integration

Example GitHub Actions workflow:

```yaml
- name: Run sageLLM Benchmark
  run: |
    pip install isagellm-benchmark
    sagellm-benchmark run --workload year1 --backend mock

- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: benchmark_results/
```

## License

Private - IntelliStream Research Project
