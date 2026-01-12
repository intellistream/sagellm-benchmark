# sagellm-demo

Demo Runner & End-to-End Testing for sageLLM inference engine.

## Overview

This package provides the unified demo runner for Year 1/2/3 validation:
- E2E workload execution (Task0.2)
- Metrics collection and reporting
- Mock-first testing infrastructure
- Integration with all sageLLM modules

## Installation

```bash
pip install isagellm-demo
```

## Quick Start

```bash
# Run Year 1 demo with mock backend
sagellm-demo run --workload year1 --backend mock

# Run with real LMDeploy backend
sagellm-demo run --workload year1 --backend lmdeploy --model Qwen/Qwen2-7B

# Generate metrics report
sagellm-demo report --output metrics.json
```

## Year 1 Demo Contract

The demo validates all modules against this contract:

### Workload (3 segments)
1. **Short input**: 128 tokens prompt → 128 tokens output
2. **Long input**: 2048 tokens prompt → 512 tokens output
3. **Pressure test**: Concurrent requests, KV eviction

### Required Metrics
```json
{
  "ttft_ms": 45.2,
  "tbt_ms": 12.5,
  "tpot_ms": 12.5,
  "throughput_tps": 80.0,
  "peak_mem_mb": 24576,
  "error_rate": 0.02,
  "kv_used_tokens": 4096,
  "kv_used_bytes": 134217728,
  "prefix_hit_rate": 0.85,
  "evict_count": 3,
  "evict_ms": 2.1,
  "spec_accept_rate": 0.72
}
```

## Team Assignment

- **Task0.2 E2E Demo Runner**: 张书豪老师团队

## Dependencies

- `isagellm-protocol>=0.1.0` - Protocol definitions
- `isagellm-backend>=0.1.0` - Backend abstraction
- `isagellm-core>=0.1.0` - Engine core
- `isagellm-kv-cache>=0.1.0` - KV cache (optional)
- `isagellm-comm>=0.1.0` - Communication (optional)
- `isagellm-compression>=0.1.0` - Compression (optional)

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run mock demo
python -m sagellm_demo.cli run --backend mock
```

## License

Private - IntelliStream Research Project
