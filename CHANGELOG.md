# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0.2] - 2026-01-28

### Changed
- 更新依赖到最新版本：
  - `isagellm-protocol>=0.3.0.1,<0.4.0`
  - `isagellm-backend>=0.3.0.3` (在 sagellm-client 和 all-clients extras 中)

## [0.3.0.1] - 2026-01-28

### Added
- sageLLM 0.3 release alignment.
- Ascend engine benchmark demo configuration (Task F - MVP).
- `examples/ascend_demo.py` - Python script for Ascend benchmark.
- `examples/ascend_config_example.yaml` - YAML configuration example for Ascend.
- `docs/ASCEND_BENCHMARK.md` - Documentation for running benchmarks on Ascend backend.

### Changed
- Bumped version to 0.3.0.0.
- Updated dependency ranges to >=0.3.0.0,<0.4.0 where applicable.
- quickstart.sh 现在要求先创建并激活 conda/venv 环境后再继续。

## [0.1.1.1] - 2026-01-26

### Added
- Initial benchmark suite implementation
- Traffic controller and request generator
- Benchmark client for E2E testing
