# 任务书 B：Runner & Client Pipeline

## 目标
实现执行与调度逻辑，把 `BenchmarkRequest[]` 变成 `BenchmarkResult[]`。

## 范围
- Runner 编排（串行/并发）
- BenchmarkClient 抽象
- MockClient 实现（用于 CI）

## 非目标
- 不实现数据集加载
- 不实现指标聚合与报告
- 不对 Contract 做校验

## 交付物
- `src/sagellm_benchmark/runner.py`
- `src/sagellm_benchmark/clients/` 模块
- 并发与超时策略

## 目录建议
```
src/sagellm_benchmark/clients/
  __init__.py
  base.py
  mock.py

src/sagellm_benchmark/
  runner.py
```

## 关键数据结构

> ⚠️ 参考 `docs/INTERFACE_CONTRACT.md` 获取完整定义

```python
@dataclass
class BenchmarkRequest:
    prompt: str
    max_tokens: int
    request_id: str
    model: str = "default"           # Protocol 必填
    stream: bool = False             # Protocol 必填
    temperature: float | None = None
    top_p: float | None = None
    kv_budget_tokens: int | None = None

@dataclass
class BenchmarkResult:
    request_id: str
    success: bool
    error: str | None
    metrics: sagellm_protocol.Metrics  # 直接复用 Protocol
    output_text: str = ""
    output_tokens: int = 0
    prompt_tokens: int = 0
```

## 实现清单
### 1) clients/base.py
- `BenchmarkClient` 抽象
  - `generate(request) -> BenchmarkResult`
  - `generate_batch(requests, concurrent: bool) -> list[BenchmarkResult]`
  - `health_check() -> bool`

### 2) clients/mock.py
- MockClient
- 可配置 TTFT/TBT/吞吐率
- 输出 `sagellm_protocol.Metrics`

### 3) runner.py
- `BenchmarkRunner.run()`
- 支持 concurrent 执行（`asyncio.gather`）
- 支持超时与错误捕获

## 运行策略
- concurrent=True：并发执行所有请求
- concurrent=False：顺序执行
- timeout 可配置（默认 60s）

## 验收标准
- 输入 10 个 request → 输出 10 个 BenchmarkResult
- concurrent 模式返回顺序与输入顺序一致
- error 统计正确（success=false 时 error 不为空）

## 交付验收用例
- 用 MockClient 执行 5 条 request
- 返回 Metrics 字段完整

## 注意事项
1. **必读**：先阅读 `docs/INTERFACE_CONTRACT.md` 了解完整接口约定
2. `BenchmarkResult.metrics` 必须是完整的 `sagellm_protocol.Metrics` 对象
3. MockClient 需要支持可配置的 TTFT/TBT 模拟值
4. 并发执行时，结果顺序必须与输入顺序一致（用 `asyncio.gather` + 索引）
5. 超时和错误必须捕获，设置 `success=False` 和 `error` 字段

