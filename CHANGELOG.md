# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Issue #45: 迁移 sagellm-core 性能测试框架到 sagellm-benchmark
  - 新增 `sagellm_benchmark.performance` 模块（`benchmark_utils`、`operator_benchmarks`、`model_benchmarks`）
  - 新增 CLI 子命令：`sagellm-benchmark perf --type operator|e2e`
  - 新增性能相关测试：`tests/test_performance_utils.py`、`tests/test_performance_cli.py`
- Issue #46: 性能对比可视化图表生成
  - 新增 `sagellm_benchmark.performance.plotting`，支持折线图/柱状图/热力图
  - 支持导出 `png` / `pdf`，支持 `light` / `dark` 主题与 `--dpi`
  - `perf` / `report` 命令均支持 `--plot` 生成图表

### Changed
- 扩展 `report` 命令，支持读取 `perf` 产物（operator/e2e JSON）并输出 table/json/markdown
- 更新 README，补充性能基准命令示例与报告示例
- 扩展 e2e 性能数据维度，新增 `precision` 字段用于模型×精度热力图

### Fixed
- 修复 agent 指令中的命令错误（sage-dev gh → sagellm-dev gh）

### Added
- agent 指令新增文档规范：禁止创建总结性文档

### Added
- 新增 `WORKFLOW.md` 文档
  - 清晰说明用户工作流程（运行 → 聚合 → 推送）
  - 详细解释自动化流程（拉取 → 合并 → 上传 → 清理）
  - 包含完整流程图和常见问题解答

### Changed
- 更新 HuggingFace 数据集仓库地址
  - 从 `wangyao36/sagellm-benchmark-results` 迁移到 `intellistream/sagellm-benchmark-results`
  - 更新所有脚本和配置文件中的仓库引用

### Fixed
- 修复 HuggingFace 数据下载和上传的端点问题
  - 默认使用官方地址 `https://huggingface.co` 替代镜像站
  - 支持环境变量 `HF_ENDPOINT` 自定义端点
  - 官方地址失败时自动回退到 `https://hf-mirror.com`
  - 更新 `scripts/merge_and_upload.py`、`scripts/aggregate_for_hf.py` 和 `scripts/upload_to_hf.py`
  - 修复上传脚本默认使用镜像导致连接超时的问题
  - 移除 GitHub Actions 中硬编码的镜像端点配置

## [0.4.0.0] - 2026-01-30

### Changed
- 版本号升级至 0.4.0.0，与核心包保持一致
- 更新依赖：
  - `isagellm-protocol>=0.4.0.0,<0.5.0`
  - `isagellm-core>=0.4.0.0,<0.5.0`
  - `isagellm-backend>=0.4.0.1,<0.5.0`

## [0.3.0.3] - 2026-01-28

### Changed
- 更新依赖到最新版本：
  - `isagellm-protocol>=0.3.0.1,<0.4.0`
  - `isagellm-backend>=0.3.0.3` (在 sagellm-client 和 all-clients extras 中)

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
