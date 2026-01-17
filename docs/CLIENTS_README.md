# Benchmark Clients 模块

## 概述

`sagellm_benchmark.clients` 模块提供了统一的客户端抽象层，支持多种 LLM 后端：

| 客户端 | 后端类型 | 使用场景 | 依赖包 |
|--------|---------|---------|--------|
| **MockClient** | 模拟后端 | CI/测试，无需 GPU | 无 |
| **OpenAIClient** | OpenAI 兼容 API | sagellm-gateway, OpenAI API | `openai` |
| **VLLMClient** | vLLM | vLLM 服务器或本地 | `vllm`, `openai` (server) |
| **LMDeployClient** | LMDeploy | LMDeploy 服务器或本地 | `lmdeploy`, `httpx` (server) |
| **SageLLMClient** | sagellm-backend | 原生 sagellm 引擎 | `isagellm-backend` |

## 核心接口

所有客户端都实现 `BenchmarkClient` 抽象基类：

```python
class BenchmarkClient(ABC):
    @abstractmethod
    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """执行单个请求"""
        pass
    
    async def generate_batch(
        self,
        requests: list[BenchmarkRequest],
        concurrent: bool = False,
        timeout: float | None = None,
    ) -> list[BenchmarkResult]:
        """批量执行请求（支持并发/顺序）"""
        pass
    
    async def health_check(self) -> bool:
        """健康检查"""
        pass
    
    async def close(self) -> None:
        """关闭客户端，清理资源"""
        pass
```

## 使用示例

### 1. MockClient - 测试和 CI

```python
from sagellm_benchmark.clients import MockClient
from sagellm_benchmark.types import BenchmarkRequest

# 创建 Mock 客户端
client = MockClient(
    ttft_ms=50.0,        # 首 token 延迟
    tbt_ms=15.0,         # token 间延迟
    throughput_tps=80.0, # 吞吐量
    error_rate=0.0,      # 失败率 (0.0-1.0)
    timeout=60.0,        # 超时
)

# 执行单个请求
request = BenchmarkRequest(
    prompt="What is AI?",
    max_tokens=100,
    request_id="test-001",
)

result = await client.generate(request)
print(f"Success: {result.success}")
print(f"TTFT: {result.metrics.ttft_ms}ms")
print(f"Output: {result.output_text}")

await client.close()
```

### 2. OpenAIClient - sagellm-gateway 或 OpenAI API

```python
from sagellm_benchmark.clients.openai_client import OpenAIClient

# 连接到 sagellm-gateway
client = OpenAIClient(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key",
)

# 健康检查
if await client.health_check():
    result = await client.generate(request)
    print(f"TTFT: {result.metrics.ttft_ms:.2f}ms")

await client.close()
```

### 3. VLLMClient - vLLM 后端

#### 服务器模式（推荐）

```python
from sagellm_benchmark.clients.vllm_client import VLLMClient

# 连接到 vLLM 服务器
client = VLLMClient(
    mode="server",
    base_url="http://localhost:8000/v1",
)

result = await client.generate(request)
await client.close()
```

#### 本地模式（in-process）

```python
client = VLLMClient(
    mode="local",
    model_path="/path/to/model",
    gpu_memory_utilization=0.9,
)

result = await client.generate(request)
await client.close()
```

### 4. LMDeployClient - LMDeploy 后端

```python
from sagellm_benchmark.clients.lmdeploy_client import LMDeployClient

# 服务器模式
client = LMDeployClient(
    mode="server",
    base_url="http://localhost:23333",
)

# 或本地模式
client = LMDeployClient(
    mode="local",
    model_path="/path/to/model",
    tp=1,  # tensor parallelism
)

result = await client.generate(request)
await client.close()
```

### 5. SageLLMClient - 原生 sagellm-backend

```python
from sagellm_backend import CPUEngine, CPUConfig
from sagellm_benchmark.clients.sagellm_client import SageLLMClient

# 创建并启动引擎
config = CPUConfig(model_path="/path/to/model")
engine = CPUEngine(config)
await engine.start()

# 创建客户端
client = SageLLMClient(engine=engine)

result = await client.generate(request)
# 注意：client.close() 不会停止 engine
await client.close()

# 需要手动停止引擎
await engine.stop()
```

## 批量执行

所有客户端支持批量执行，可选择并发或顺序模式：

### 顺序执行

```python
requests = [
    BenchmarkRequest(prompt=f"Question {i}", max_tokens=50, request_id=f"req-{i}")
    for i in range(10)
]

# 顺序执行（一个接一个）
results = await client.generate_batch(requests, concurrent=False)
```

### 并发执行

```python
# 并发执行（同时执行所有请求）
results = await client.generate_batch(requests, concurrent=True)

# 结果顺序与输入顺序一致
for i, result in enumerate(results):
    assert result.request_id == f"req-{i}"
```

### 自定义超时

```python
# 每个请求 30 秒超时
results = await client.generate_batch(
    requests,
    concurrent=True,
    timeout=30.0,
)
```

## 错误处理

客户端自动处理超时和异常：

```python
# 失败的请求会返回 success=False
result = await client.generate(request)

if not result.success:
    print(f"Error: {result.error}")
    # result.metrics 为 None
else:
    print(f"TTFT: {result.metrics.ttft_ms}ms")
```

## 指标收集

所有客户端返回符合 Protocol 的 `Metrics` 对象：

```python
result = await client.generate(request)

if result.success and result.metrics:
    print(f"TTFT: {result.metrics.ttft_ms}ms")
    print(f"TBT: {result.metrics.tbt_ms}ms")
    print(f"Throughput: {result.metrics.throughput_tps}tps")
    print(f"Peak Memory: {result.metrics.peak_mem_mb}MB")
    print(f"KV Tokens: {result.metrics.kv_used_tokens}")
```

**注意**：

- OpenAI/vLLM/LMDeploy 等外部后端可能不提供完整指标（如 KV cache）
- SageLLMClient 提供最完整的指标（因为是原生后端）
- MockClient 生成模拟指标用于测试

## 健康检查

在执行请求前检查后端是否可用：

```python
if await client.health_check():
    print("Backend is healthy")
    result = await client.generate(request)
else:
    print("Backend is not available")
```

## 资源清理

使用 `async with` 或手动 `close()`：

```python
# 方式 1: async with (推荐)
async with client:
    result = await client.generate(request)

# 方式 2: 手动 close
client = MockClient()
try:
    result = await client.generate(request)
finally:
    await client.close()
```

## 依赖安装

根据使用的客户端安装依赖：

```bash
# MockClient（无需额外依赖）
pip install isagellm-benchmark

# OpenAIClient
pip install isagellm-benchmark openai

# VLLMClient
pip install isagellm-benchmark vllm openai

# LMDeployClient
pip install isagellm-benchmark lmdeploy httpx

# SageLLMClient
pip install isagellm-benchmark isagellm-backend
```

## 完整示例

参考 [`examples/client_demo.py`](../examples/client_demo.py)：

```bash
cd /path/to/sagellm-benchmark
python examples/client_demo.py
```

## 开发自定义客户端

继承 `BenchmarkClient` 并实现 `generate()` 方法：

```python
from sagellm_benchmark.clients.base import BenchmarkClient
from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

class CustomClient(BenchmarkClient):
    def __init__(self, endpoint: str, timeout: float = 60.0):
        super().__init__(name="custom", timeout=timeout)
        self.endpoint = endpoint
    
    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        # 1. 调用你的后端 API
        response = await your_backend_api(request.prompt, request.max_tokens)
        
        # 2. 创建 Protocol Metrics
        from sagellm_protocol import Metrics
        metrics = Metrics(
            ttft_ms=...,
            tbt_ms=...,
            throughput_tps=...,
            # ... 其他指标
        )
        
        # 3. 返回 BenchmarkResult
        return BenchmarkResult(
            request_id=request.request_id,
            success=True,
            error=None,
            metrics=metrics,
            output_text=response.text,
            output_tokens=response.num_tokens,
        )
    
    async def health_check(self) -> bool:
        # 实现健康检查
        return await check_backend_health(self.endpoint)
```

## 常见问题

### Q: 如何选择客户端？

- **开发/测试**：使用 `MockClient`
- **对接 sagellm-gateway**：使用 `OpenAIClient`
- **对接 vLLM**：使用 `VLLMClient`
- **对接 LMDeploy**：使用 `LMDeployClient`
- **使用 sagellm-backend**：使用 `SageLLMClient`

### Q: 并发执行会影响结果顺序吗？

不会。`generate_batch()` 保证结果顺序与输入顺序一致，无论是否并发。

### Q: 如何获取最完整的指标？

使用 `SageLLMClient`（原生 sagellm-backend），它提供完整的 Protocol Metrics，包括 KV cache、内存等。

### Q: 超时如何处理？

超时的请求会返回 `success=False`，`error="Timeout after Xs"`。可以通过 `timeout` 参数调整。

## 参考

- [TASK_B_RUNNER.md](../docs/TASK_B_RUNNER.md) - 任务书
- [INTERFACE_CONTRACT.md](../docs/INTERFACE_CONTRACT.md) - 接口契约
- [examples/client_demo.py](../examples/client_demo.py) - 完整示例
