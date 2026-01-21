# sageLLM Benchmark Usage Guide

## Quick Start

### 1. Installation

```bash
pip install isagellm-benchmark
```

### 2. Run Benchmark

The easiest way is to use the one-click script:

```bash
./run_benchmark.sh
```

This will:
- Run all three Year 1 workloads (short/long/stress)
- Generate metrics JSON files
- Create summary report
- Generate markdown report

## CLI Reference

### `sagellm-benchmark run`

Run benchmark workloads.

**Options:**

- `--workload`: Workload type to run
  - `year1`: All three workloads (default)
  - `short`: Short input only
  - `long`: Long input only
  - `stress`: Stress test only

- `--backend`: Backend engine to use
  - `mock`: Mock backend (no GPU, default)
  - `cpu`: CPU inference with HuggingFace
  - `lmdeploy`: LMDeploy (coming soon)
  - `vllm`: vLLM (coming soon)

- `--model`: Model path (required for non-mock backends)
  - Example: `gpt2`, `facebook/opt-125m`

- `--output`, `-o`: Output directory
  - Default: `./benchmark_results`

- `--verbose`, `-v`: Enable verbose logging

**Examples:**

```bash
# Run all workloads with mock backend
sagellm-benchmark run --workload year1 --backend mock

# Run short input with CPU backend
sagellm-benchmark run --workload short --backend cpu --model gpt2

# Run stress test with verbose output
sagellm-benchmark run --workload stress --backend mock -v -o ./my_results
```

### `sagellm-benchmark report`

Generate report from benchmark results.

**Options:**

- `--input`, `-i`: Input summary JSON file
  - Default: `./benchmark_results/benchmark_summary.json`

- `--format`: Output format
  - `table`: Rich terminal table (default)
  - `json`: JSON output
  - `markdown`: Markdown format

**Examples:**

```bash
# Display table in terminal
sagellm-benchmark report

# Generate markdown report
sagellm-benchmark report --format markdown > REPORT.md

# Display raw JSON
sagellm-benchmark report --format json
```

## Workload Details

### Short Input (short_input)

- **Prompt tokens**: ~128
- **Output tokens**: 128
- **Requests**: 5 sequential
- **Purpose**: Test basic inference latency

### Long Input (long_input)

- **Prompt tokens**: ~200
- **Output tokens**: 200
- **Requests**: 3 sequential
- **Purpose**: Test long-context handling

### Stress Test (stress_test)

- **Prompt tokens**: ~256
- **Output tokens**: 256
- **Requests**: 10 concurrent
- **Purpose**: Test concurrent request handling and KV cache pressure

## Understanding Metrics

### Latency Metrics

- **TTFT (Time to First Token)**: Time from request submission to first token generation
  - Lower is better
  - Critical for interactive applications

- **TBT (Time Between Tokens)**: Average time between consecutive tokens
  - Lower is better
  - Affects user experience during streaming

- **TPOT (Time Per Output Token)**: Average time per generated token
  - Similar to TBT but includes first token
  - Lower is better

### Throughput Metrics

- **Throughput (tokens/sec)**: Number of tokens generated per second
  - Higher is better
  - Key metric for batch processing

### Memory Metrics

- **Peak Memory (MB)**: Maximum memory usage during workload
  - Lower is better (for same performance)
  - Important for resource planning

- **Average Memory (MB)**: Average memory usage
  - Indicates typical resource consumption

### Reliability Metrics

- **Error Rate**: Proportion of failed requests
  - Lower is better
  - Target: < 5% for stress tests

- **Total/Successful/Failed Requests**: Request counts
  - Validate all requests are tracked

### KV Cache Metrics

- **KV Used Tokens**: Number of tokens in KV cache
  - Indicates cache utilization

- **KV Used Bytes**: Memory used by KV cache
  - Important for memory planning

- **Prefix Hit Rate**: Proportion of cache hits
  - Higher is better
  - Indicates cache efficiency

- **Evict Count**: Number of cache evictions
  - Lower is better (but expected under pressure)

- **Evict Time**: Time spent on evictions
  - Lower is better

### Compression Metrics

- **Spec Accept Rate**: Speculative decoding acceptance rate
  - Higher is better (when spec decoding is enabled)
  - 0.0 when not enabled

## Output Files

### Per-Workload Metrics

`{workload_name}_metrics.json`:

```json
{
  "avg_ttft_ms": 10.0,
  "p50_ttft_ms": 10.0,
  "p95_ttft_ms": 10.0,
  "p99_ttft_ms": 10.0,
  "avg_tbt_ms": 5.0,
  "avg_tpot_ms": 5.0,
  "avg_throughput_tps": 100.0,
  "peak_mem_mb": 1024,
  ...
}
```

### Summary Report

`benchmark_summary.json`:

```json
{
  "workloads": {
    "short_input": { ... },
    "long_input": { ... },
    "stress_test": { ... }
  },
  "overall": {
    "total_workloads": 3,
    "total_requests": 18,
    "successful_requests": 17,
    "failed_requests": 1
  }
}
```

## Backend Selection

### Mock Backend

**When to use:**
- CI/CD pipelines (no GPU required)
- Quick validation
- Testing report generation
- Developing new features

**Characteristics:**
- Instant execution
- Predictable metrics
- No model loading
- No hardware requirements

**Example:**
```bash
sagellm-benchmark run --workload year1 --backend mock
```

### CPU Backend

**When to use:**
- Development without GPU
- Testing with real models
- Validating inference correctness
- Collecting realistic metrics

**Characteristics:**
- Real model loading (may be slow)
- Accurate TTFT/TBT/throughput
- Higher memory usage
- Slower than GPU

**Example:**
```bash
sagellm-benchmark run --workload year1 --backend cpu --model gpt2
```

## Troubleshooting

### "sagellm-benchmark not installed"

Install the package:
```bash
pip install isagellm-benchmark
```

### "Error: --model required for CPU backend"

CPU backend needs a model path:
```bash
sagellm-benchmark run --backend cpu --model gpt2
```

### "File not found: benchmark_summary.json"

Run benchmark first:
```bash
sagellm-benchmark run --workload year1 --backend mock
```

### High memory usage with CPU backend

Use smaller models:
```bash
sagellm-benchmark run --backend cpu --model gpt2  # 124M params
# Or
sagellm-benchmark run --backend cpu --model facebook/opt-125m
```

### Slow execution with CPU backend

This is expected. CPU inference is much slower than GPU. Consider:
- Using mock backend for quick tests
- Using smaller models
- Reducing num_requests in workload config

## Advanced Usage

### Custom Output Directory

```bash
sagellm-benchmark run --output ./my_results
sagellm-benchmark report --input ./my_results/benchmark_summary.json
```

### Verbose Logging

```bash
sagellm-benchmark run -v
```

### Running Single Workload

```bash
# Only short input
sagellm-benchmark run --workload short --backend mock

# Only stress test
sagellm-benchmark run --workload stress --backend cpu --model gpt2
```

### Generating Reports

```bash
# Terminal table
sagellm-benchmark report

# Markdown for documentation
sagellm-benchmark report --format markdown > REPORT.md

# JSON for processing
sagellm-benchmark report --format json | jq '.overall'
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Benchmark

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Install
        run: pip install isagellm-benchmark

      - name: Run Benchmark
        run: sagellm-benchmark run --workload year1 --backend mock

      - name: Generate Report
        run: sagellm-benchmark report --format markdown > REPORT.md

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: |
            benchmark_results/
            REPORT.md
```

### GitLab CI Example

```yaml
benchmark:
  stage: test
  script:
    - pip install isagellm-benchmark
    - sagellm-benchmark run --workload year1 --backend mock
    - sagellm-benchmark report --format markdown > REPORT.md
  artifacts:
    paths:
      - benchmark_results/
      - REPORT.md
```

## See Also

- [README.md](../README.md) - Overview and installation
- [examples/](../examples/) - Sample output files
