# Ascend Engine Benchmark (MVP)

本文档说明如何使用 sagellm-benchmark 对 Ascend 后端进行性能测试。

## 📋 MVP 目标

提供 Ascend demo 配置，演示如何在 Ascend 设备上运行 Year 1 Demo Contract 的 benchmark 测试。

**注意**：MVP 阶段不要求真实 Ascend 硬件，可以使用 CPU fallback 进行演示。

## 🚀 快速开始

### 1. Python 脚本方式

```bash
# 运行 Ascend demo（自动检测硬件可用性）
cd /home/shuhao/sagellm-benchmark
python examples/ascend_demo.py
```

**行为说明**：
- 如果 `torch_npu` 可用 → 使用 Ascend 引擎
- 如果 `torch_npu` 不可用 → 自动 fallback 到 CPU（附带警告信息）

### 2. YAML 配置方式

```bash
# 使用 YAML 配置文件（未来支持）
sage-llm benchmark --config examples/ascend_config_example.yaml
```

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `ascend_demo.py` | Ascend benchmark 示例脚本（Python API） |
| `ascend_config_example.yaml` | Ascend 配置示例（YAML 格式） |

## ⚙️ 配置说明

### Engine 配置

```yaml
engine:
  type: ascend              # 必须指定为 "ascend"
  device: "ascend:0"        # NPU 设备 ID
  model_path: "model_path"  # 模型路径
  max_new_tokens: 128       # 最大生成 tokens
```

### Workload 配置

遵循 Year 1 Demo Contract 的三段式测试：

1. **Short Input**：128 tokens prompt → 128 tokens output
2. **Long Input**：2048 tokens prompt → 512 tokens output
3. **Stress Test**：并发请求，触发 KV 驱逐

### Fallback 配置

```yaml
fallback:
  enable: true   # 启用 fallback
  backend: "cpu" # fallback 到 CPU
```

## 📊 预期输出

Benchmark 运行后会产出以下指标（符合 Year 1 Demo Contract）：

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

## 🔍 Observability

所有操作必须包含以下字段：

- `trace_id`: 请求追踪 ID
- `request_id`: 请求标识符
- `engine_id`: 引擎实例标识符
- `timestamps`: 时间戳（queued_at, scheduled_at, executed_at, completed_at）

## 🧪 测试模式

### Mock 模式（无真实硬件）

当 Ascend 硬件不可用时，系统会自动 fallback 到 CPU：

```bash
⚠️  Ascend backend not available: No module named 'torch_npu'
   Falling back to CPU for demo purposes...
```

这种模式适用于：
- CI/CD 测试
- 开发环境调试
- 无 Ascend 硬件的演示

### 真实硬件模式

当 `torch_npu` 可用时，会使用真实 Ascend 设备：

```bash
🚀 Starting benchmark with Ascend engine...
   Device: ascend:0
   Model: sshleifer/tiny-gpt2
```

## 📝 开发规范

遵循 sageLLM 核心开发原则：

1. **Protocol-First**：配置字段遵循 Protocol v0.1
2. **CPU-First**：必须支持 CPU fallback
3. **Fail-Fast**：配置错误必须明确报错
4. **Observability-First**：所有操作必须产出结构化日志和指标

## 🔗 相关文档

- Protocol v0.1: `sagellm-docs/docs/specs/protocol_v0.1.md`
- Task F 任务书: `sagellm-docs/agent_tasks/ascend_engine_mvp_tasks.md`
- Year 1 Demo Contract: `sagellm-docs/docs/demo_contract.md`

## ✅ MVP 验收标准

- [x] 提供 Ascend demo 配置示例（Python + YAML）
- [x] 支持自动 fallback 到 CPU
- [x] 配置符合 Year 1 Demo Contract
- [x] 文档说明清晰完整

## 📞 联系方式

如有问题，请联系：
- Task F 负责人：（待补充）
- sageLLM 团队：IntelliStream
