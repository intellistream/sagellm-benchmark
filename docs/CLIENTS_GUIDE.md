# Benchmark Clients Guide

## ⚠️ 重要说明：生产环境 vs 基准测试

### sageLLM 生产环境使用方式

**对外服务（生产环境）推荐架构**：

```
外部用户
    ↓ (HTTP API - OpenAI 协议)
┌─────────────────────────────────┐
│   sagellm-gateway (L5)          │  ← 必须通过 Gateway（HTTP API）
│   - OpenAI 兼容 API             │
│   - 会话管理                    │
│   - 认证授权                    │
└─────────────────────────────────┘
    ↓ (内部调用)
┌─────────────────────────────────┐
│   Control Plane (L4)            │  ← 调度、负载均衡
│   - 请求路由                    │
│   - 引擎调度                    │
└─────────────────────────────────┘
    ↓ (内部调用)
┌─────────────────────────────────┐
│   sagellm-core + backend (L1-L3)│  ← 推理引擎
│   - 实际推理执行                │
└─────────────────────────────────┘
```

**✅ 生产环境使用方式**：

1. **对外 HTTP API（推荐）**：
   ```bash
   # 一键启动完整服务
   pip install 'isagellm[server]'
   sage-llm serve --model Qwen2-7B --port 8000

   # 外部用户通过 OpenAI 协议访问
   curl http://your-server:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "Qwen2-7B", "messages": [...]}'
   ```

2. **Python API（内部集成）**：
   ```python
   # 仅用于 Python 应用内部集成，不对外暴露
   from sagellm import ControlPlaneManager

   manager = ControlPlaneManager(...)
   result = await manager.route_request(request)
   ```

**❌ 不推荐**：直接调用 sagellm-backend（跳过 Control Plane）

### 基准测试场景

sagellm-benchmark 的客户端是为了 **性能测试**，不是生产部署：

## Overview

sagellm-benchmark 提供多种客户端，用于测试不同的 LLM 服务：

| 客户端 | 用途 | 连接方式 |
|--------|------|---------|
| **GatewayClient** | sagellm-gateway（OpenAI 协议） | HTTP API |
| **SageLLMClient** | sagellm-backend 原生引擎 | 直接调用（无 HTTP） |
| **VLLMClient** | vLLM | HTTP API |
| **LMDeployClient** | LMDeploy | HTTP API |

## GatewayClient（推荐用于完整系统测试）

### 什么是 GatewayClient？

`GatewayClient` 是用于连接 **OpenAI 协议** HTTP API 的客户端。它主要用于：

1. **测试 sagellm-gateway** - sageLLM 的 API 网关服务
2. **对比 OpenAI API** - 可连接 OpenAI 官方 API 进行性能对比
3. **测试其他兼容服务** - vLLM OpenAI server、LMDeploy OpenAI server 等

### 为什么不叫 OpenAIClient？

之前叫 `OpenAIClient`，但容易混淆：
- ❌ 用户误以为是 OpenAI 公司专用
- ❌ 不清楚可以连接 sagellm-gateway
- ✅ 改名为 `GatewayClient` 更清晰

### 使用示例

```python
from sagellm_benchmark.clients.openai_client import GatewayClient
from sagellm_benchmark.types import BenchmarkRequest

# 连接 sagellm-gateway（主要用途）
client = GatewayClient(
    base_url="http://localhost:8000/v1",
    api_key="benchmark",
)

# 创建请求
request = BenchmarkRequest(
    prompt="Hello!",
    max_tokens=100,
)

# 执行
result = await client.generate(request)
print(f"TTFT: {result.metrics.ttft_ms:.2f}ms")
```

### 对比：OpenAI 官方 API

```python
# 也可以连接 OpenAI 官方 API（用于性能对比）
openai_client = GatewayClient(
    base_url="https://api.openai.com/v1",
    api_key="sk-...",  # 真实 API key
)
```

## SageLLMClient（用于原生后端测试）

### 什么是 SageLLMClient？

`SageLLMClient` 直接使用 **sagellm-backend** 原生引擎，**不通过 HTTP**。

适用场景：
- 测试引擎核心性能（无网络开销）
- 本地开发和调试
- 单元测试

### 使用示例

```python
from sagellm_benchmark.clients.sagellm_client import SageLLMClient
from sagellm_backend import CPUEngine

# 创建原生引擎
engine = CPUEngine(
    model_path="gpt2",
    device="cpu",
)

# 包装为 benchmark 客户端
client = SageLLMClient(engine=engine)

# 使用方式相同
result = await client.generate(request)
```

## 客户端选择指南

| 测试场景 | 推荐客户端 | 原因 |
|---------|-----------|------|
| 完整系统性能测试（生产架构）| **GatewayClient** | 包含完整调用链路（HTTP + Control Plane），符合生产部署 |
| API 网关功能测试 | **GatewayClient** | 直接测试 sagellm-gateway |
| 引擎核心性能测试（无网络开销）| **SageLLMClient** | 绕过网络层，聚焦引擎性能 |
| 与 OpenAI 对比 | **GatewayClient** | 可连接 OpenAI API |
| vLLM 对比测试 | **VLLMClient** | 专用客户端 |
| LMDeploy 对比测试 | **LMDeployClient** | 专用客户端 |

### 关键原则

1. **生产环境必须走 HTTP**：外部用户只能通过 sagellm-gateway（OpenAI API）访问
2. **基准测试模拟真实场景**：使用 GatewayClient 测试完整调用链路
3. **引擎性能测试可直连**：使用 SageLLMClient 排除网络干扰

## 架构说明

### 生产环境完整架构

```
外部用户（OpenAI SDK/curl）
    ↓ HTTP (OpenAI 协议)
┌───────────────────────────────────────┐
│  sagellm-gateway (API Gateway)        │
│  • OpenAI 兼容 endpoints              │
│  • 认证授权                            │
│  • 会话管理                            │
└───────────────────────────────────────┘
    ↓ 内部调用
┌───────────────────────────────────────┐
│  Control Plane (调度层)                │
│  • 请求路由                            │
│  • 负载均衡                            │
│  • 引擎生命周期管理                     │
└───────────────────────────────────────┘
    ↓ 内部调用
┌───────────────────────────────────────┐
│  sagellm-core + backend (引擎层)      │
│  • 实际推理执行                        │
│  • KV 缓存管理                         │
│  • 硬件加速（CPU/CUDA/Ascend）         │
└───────────────────────────────────────┘
```

### 基准测试客户端架构

```
┌─────────────────────────────────────────────────────────────┐
│                  sagellm-benchmark                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GatewayClient│  │ SageLLMClient│  │  VLLMClient  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │ HTTP            │ Direct          │ HTTP          │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐  ┌──────────────┐  ┌──────────────┐
│ sagellm-gateway │  │  sagellm-    │  │     vLLM     │
│  (生产架构)     │  │   backend    │  │    Server    │
│                 │  │ （引擎直连）  │  │              │
└─────────────────┘  └──────────────┘  └──────────────┘

说明：
• GatewayClient：测试生产环境完整链路（推荐）
• SageLLMClient：测试引擎性能（排除网络开销）
```

## 常见问题

### Q: sageLLM 对外使用时，是直连还是走 HTTP？

**A:** **必须走 HTTP**（sagellm-gateway）。

生产环境架构：
```
外部用户 → HTTP API (sagellm-gateway) → Control Plane → 引擎
```

原因：
1. ✅ 标准化接口：OpenAI 兼容协议，易于集成
2. ✅ 认证授权：Gateway 处理 API key、限流
3. ✅ 会话管理：多轮对话状态维护
4. ✅ 负载均衡：Control Plane 自动调度请求

**直连引擎仅用于**：
- 内部开发调试
- 性能基准测试（排除网络开销）
- Python 应用内嵌集成（非对外服务）

### Q: 为什么基准测试有两个客户端（GatewayClient 和 SageLLMClient）？

**A:**
- **GatewayClient**：测试完整系统（含 HTTP + Control Plane），符合真实部署
- **SageLLMClient**：测试引擎核心，排除网络干扰

两者测试不同层次的性能。

### Q: GatewayClient 能连接 OpenAI 官方 API 吗？

**A:** 可以！只需改变 `base_url` 和 `api_key`：

```python
GatewayClient(
    base_url="https://api.openai.com/v1",
    api_key="sk-YOUR_KEY",
)
```

### Q: 我应该用哪个客户端测试 sageLLM？

**A:** 优先使用 **GatewayClient + sagellm-gateway**，因为：
- 完整的调用链路（包括 Control Plane）
- 符合生产部署架构
- 可测试 API 网关功能

## 迁移指南（旧代码）

如果你的代码使用了旧的 `OpenAIClient`，请更新：

```python
# ❌ 旧代码
from sagellm_benchmark.clients.openai_client import OpenAIClient
client = OpenAIClient(...)

# ✅ 新代码
from sagellm_benchmark.clients.openai_client import GatewayClient
client = GatewayClient(...)
```

功能完全相同，只是名字更清晰。
