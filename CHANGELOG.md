# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `scripts/publish_pipeline.sh`: 一键发布流水线脚本，自动完成「运行基准测试 → 聚合结果 → 上传 HuggingFace → 触发 website 刷新」全流程
  - 支持 `--model`, `--workload`, `--backend`, `--backend-url` 参数
  - 支持 `--skip-run`（仅聚合+上传）、`--skip-upload`（本地调试）、`--local-only`、`--dry-run` 等模式
  - 自动读取 `~/sagellm/.env` 中的 `HF_TOKEN`
- `.github/workflows/benchmark-publish.yml`: 自动化发布 GitHub Actions Workflow
  - 触发方式：手动（workflow_dispatch，支持参数）、定时（每周一 UTC 02:00）、push 到 `outputs/`
  - 4 个 Jobs：Run & Aggregate → Upload to HF → Notify Website → Summary
  - 支持 `dry_run` 参数，不实际上传用于测试流程
  - 自动启动 sagellm 服务（如果 self-hosted 上未运行）
  - Job Summary 输出美观的发布摘要表格


- `model_benchmarks.py`：实现 live E2E benchmark 模式（`--live` flag）
  - `run_e2e_model_benchmarks` 新增 `backend_url`、`api_key`、`request_timeout`、`server_wait_s` 参数
  - `simulate=False` 时通过 `GatewayClient`（OpenAI 兼容协议）向真实 API 服务器发送并发请求
  - 自动执行 server ready 等待（最多 `server_wait_s` 秒重试），避免服务器正在启动时立刻超时
  - 自动执行模型名称发现（`/info` + `/v1/models`），当请求 model 与服务器加载 model 不一致时自动覆盖并告警
  - 按 scenario 逐批并发，聚合真实 TTFT/TBT/throughput/latency 指标
- CLI `perf` 命令新增选项：`--backend-url`、`--api-key`、`--request-timeout`、`--server-wait`
- live 模式自动开启 INFO 日志，实时显示服务器等待/发现/请求进度
- CLI `perf` 命令新增选项 `--max-seq-len`：手动指定模型最大上下文窗口，覆盖自动检测值（`/info` → AutoConfig → 1024）
- CLI `perf` 命令新增选项 `--max-output-tokens`：对 live E2E 模式每个请求的输出 token 数设置硬上限，避免 CPU/慢速模型因单次推理耗时超过 `request_timeout` 而超时（如 tiny-gpt2 CPU 模式建议设置 8-16）
- `_discover_max_seq_len()`：自动探测模型最大序列长度（`/info` → transformers AutoConfig → fallback 1024）
- live 模式按 scenario 自动 clamp prompt_tokens / output_tokens 防止超出上下文窗口

### Fixed
- `GatewayClient.health_check()`：从 OpenAI SDK `models.list()`（会 404/hang）改为先试 `/health`，再试 `/v1/models`，均使用 httpx 带超时
- `GatewayClient` 新增 `discover_model()` 方法：通过 `/info` 或 `/v1/models` 获取服务器实际加载的模型名称
- live 模式 prompt/output token 数 clamp 修复 `IndexError: index out of range in self`（短上下文模型如 sshleifer/tiny-gpt2 位置编码上限 1024，long_b1 scenario 默认 2048 prompt tokens 越界）

## [0.5.1.2] - 2025-07-25

### Fixed
- `sagellm_client.py`：修复 vLLM/SGLang 兼容吞吐量指标全为 0.00 的三个 bug
  - `prompt_tokens`：`response.prompt_tokens` 为 Pydantic 默认 `None` 导致存储 `None`，改为 `is not None` 判断后回落到 request.prompt 词数估算
  - `total_time_s = 0`：`response.timestamps` 未注入到 `metrics.timestamps`，导致 aggregator 无法计算时间窗口；现通过 `model_copy` 将 `response.timestamps` 复制到 `metrics.timestamps`
  - `e2e_latency_ms`：新增从 `response.timestamps.queued_at/completed_at` 计算 E2E 延迟并写入 `BenchmarkResult.e2e_latency_ms`

### Added
- Issue #45: 迁移 sagellm-core 性能测试框架到 sagellm-benchmark
  - 新增 `sagellm_benchmark.performance` 模块（`benchmark_utils`、`operator_benchmarks`、`model_benchmarks`）
  - 新增 CLI 子命令：`sagellm-benchmark perf --type operator|e2e`
  - 新增性能相关测试：`tests/test_performance_utils.py`、`tests/test_performance_cli.py`
- Issue #46: 性能对比可视化图表生成
  - 新增 `sagellm_benchmark.performance.plotting`，支持折线图/柱状图/热力图
  - 支持导出 `png` / `pdf`，支持 `light` / `dark` 主题与 `--dpi`
  - `perf` / `report` 命令均支持 `--plot` 生成图表
- Issue #47: CI 性能回归自动检测
  - 新增基准线文件：`benchmarks/baselines/perf_baseline_e2e.json`
  - 新增回归对比脚本：`scripts/compare_performance_baseline.py`
  - 新增 CI workflow：`.github/workflows/performance-regression.yml`
  - 支持阈值分级：Critical >10%，Warning 5-10%，Acceptable <5%
  - 支持 PR 自动评论告警与性能报告 artifact 上传
- agent 指令新增文档规范：禁止创建总结性文档
- 新增 `WORKFLOW.md` 文档
  - 清晰说明用户工作流程（运行 → 聚合 → 推送）
  - 详细解释自动化流程（拉取 → 合并 → 上传 → 清理）
  - 包含完整流程图和常见问题解答

### Changed
- 发布版本升级至 `0.5.1.0`，并统一 `protocol/core/backend` 依赖约束到 `>=0.5.1.0,<0.6.0`。
- 扩展 `report` 命令，支持读取 `perf` 产物（operator/e2e JSON）并输出 table/json/markdown
- 更新 README，补充性能基准命令示例与报告示例
- 扩展 e2e 性能数据维度，新增 `precision` 字段用于模型×精度热力图
- 修复 e2e 模拟基准种子策略，改为稳定哈希，确保 CI 基准对比可复现
- 更新 HuggingFace 数据集仓库地址
  - 从 `wangyao36/sagellm-benchmark-results` 迁移到 `intellistream/sagellm-benchmark-results`
  - 更新所有脚本和配置文件中的仓库引用

### Fixed
- 修复 agent 指令中的命令错误（sage-dev gh → sagellm-dev gh）
- 修复 HuggingFace 数据下载和上传的端点问题
  - 默认使用官方地址 `https://huggingface.co` 替代镜像站
  - 支持环境变量 `HF_ENDPOINT` 自定义端点
  - 官方地址失败时自动回退到 `https://hf-mirror.com`
  - 更新 `scripts/merge_and_upload.py`、`scripts/aggregate_for_hf.py` 和 `scripts/upload_to_hf.py`
  - 修复上传脚本默认使用镜像导致连接超时的问题
  - 移除 GitHub Actions 中硬编码的镜像端点配置

### Removed
- 暂无变更

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
