# sageLLM Benchmark - Quick Start Guide

## What is this?

sageLLM Benchmark is a standardized testing suite for validating LLM inference engines. It runs three types of workloads:

1. **Short input**: Fast requests with short prompts
2. **Long input**: Requests with longer context
3. **Stress test**: Concurrent requests to test system limits

## Installation

```bash
pip install isagellm-benchmark
```

## 5-Minute Quick Start

### Option 1: One-Click Script (Recommended)

```bash
cd sagellm-benchmark
./run_benchmark.sh
```

That's it! Results will be in `./benchmark_results/`

### Option 2: Manual CLI

```bash
# Run all three workloads
sagellm-benchmark run --workload m1 --backend cpu

# View results
sagellm-benchmark report
```

## What Gets Generated?

After running, you'll have:

```
benchmark_results/
├── benchmark_summary.json       # Overall summary
├── short_input_metrics.json     # Short workload metrics
├── long_input_metrics.json      # Long workload metrics
├── stress_test_metrics.json     # Stress test metrics
└── REPORT.md                    # Human-readable report
```

## Understanding the Output

### Terminal Output

```
Benchmark Results
┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┓
┃ Workload    ┃ Requests ┃ Errors ┃ Avg TTFT (ms) ┃ Throughput (tok/s) ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━┩
│ short_input │        5 │      0 │         10.00 │              100.00 │
│ long_input  │        3 │      0 │         15.00 │               75.00 │
│ stress_test │       10 │      1 │         12.00 │               90.00 │
└─────────────┴──────────┴────────┴───────────────┴────────────────────┘
```

### Key Metrics Explained

- **TTFT (Time to First Token)**: How long until the first word appears
  - Lower is better
  - Critical for interactive chat

- **Throughput**: Tokens generated per second
  - Higher is better
  - Important for batch processing

- **Error Rate**: Percentage of failed requests
  - Lower is better
  - Some errors expected in stress tests

## Backend Options

### CPU Backend

Real inference using HuggingFace models. Use for:
- Testing without GPU
- Validating correctness
- Getting realistic metrics

```bash
sagellm-benchmark run --backend cpu --model gpt2
```

**Note**: CPU inference is slow. Use small models like `gpt2` (124M params).

## Common Commands

```bash
# Run specific workload
sagellm-benchmark run --workload short --backend cpu

# Run in batch mode (offline throughput, vLLM/SGLang compatible)
sagellm-benchmark run --workload m1 --backend cpu --mode batch

# Run with custom JSON output
sagellm-benchmark run --workload m1 --backend cpu --output-json ./my_results.json

# Run with verbose logging
sagellm-benchmark run --workload m1 --backend cpu -v

# Custom output directory
sagellm-benchmark run --output ./my_results

# Generate markdown report
sagellm-benchmark report --format markdown > REPORT.md

# View raw JSON
sagellm-benchmark report --format json
```

## Troubleshooting

### Command not found

```bash
pip install isagellm-benchmark
```

### Need model for CPU backend

```bash
sagellm-benchmark run --backend cpu --model gpt2
```

### Results not found

Run benchmark first:
```bash
sagellm-benchmark run --workload year1 --backend cpu
```

## Next Steps

- Read [USAGE.md](../docs/USAGE.md) for detailed documentation
- Check [examples/](../examples/) for sample outputs
- See [README.md](../README.md) for architecture details
- **NEW:** See "Benchmarking Against vLLM/SGLang" section in [USAGE.md](../docs/USAGE.md) for comparison guide

## Comparing with vLLM/SGLang

sageLLM Benchmark now supports modes compatible with vLLM and SGLang:

```bash
# Batch mode - comparable to vLLM's offline throughput
sagellm-benchmark run --workload m1 --backend cpu --mode batch

# Traffic mode - comparable to SGLang's serving benchmark
sagellm-benchmark run --workload stress --backend cpu --mode traffic
```

**Output includes vLLM/SGLang compatible metrics:**
- Request Throughput (req/s)
- Input Throughput (tokens/s)
- Output Throughput (tokens/s)  
- Total Throughput (tokens/s)

See [USAGE.md - Benchmarking Against vLLM/SGLang](../docs/USAGE.md#benchmarking-against-vllmsglang) for detailed comparison workflow.

## Need Help?

- GitHub Issues: https://github.com/intellistream/sagellm-benchmark/issues
- Documentation: [docs/](../docs/)

## Summary

```bash
# Quick start in 3 commands:
pip install isagellm-benchmark
sagellm-benchmark run --workload year1 --backend cpu
sagellm-benchmark report
```

That's all you need to get started!
