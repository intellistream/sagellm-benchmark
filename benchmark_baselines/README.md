# Benchmark Baselines

This directory stores persisted baseline snapshots used by CI regression checks.

- `perf_baseline_e2e.json`: default E2E baseline consumed by `.github/workflows/benchmark.yml`

To refresh the baseline, run `Benchmark Regression` workflow via `workflow_dispatch` with `update_baseline=true`.
