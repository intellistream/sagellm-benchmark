# 公共契约：sagellm-benchmark 模块间接口

> ⚠️ **重要**：三个模块开发时必须严格遵循此契约，确保接口一致。

## 1. BenchmarkRequest（A→B 传递）

```python
from dataclasses import dataclass

@dataclass
class BenchmarkRequest:
    """Benchmark 请求，用于 Dataset→Runner 传递"""
    prompt: str
    max_tokens: int
    request_id: str
    # 可选参数
    model: str = "default"           # 模型名称
    stream: bool = False             # 是否流式
    temperature: float | None = None
    top_p: float | None = None
    kv_budget_tokens: int | None = None
```

**说明**：
- `model` 和 `stream` 是 Protocol 必填字段，必须提供默认值
- Dataset 生成时可不指定，由 Runner 填充

---

## 2. BenchmarkResult（B→C 传递）

```python
from dataclasses import dataclass
from sagellm_protocol import Metrics

@dataclass
class BenchmarkResult:
    """单请求执行结果"""
    request_id: str
    success: bool
    error: str | None
    # 直接复用 Protocol Metrics
    metrics: Metrics
    # 可选：原始输出
    output_text: str = ""
    output_tokens: int = 0
    prompt_tokens: int = 0
```

**说明**：
- `metrics` 直接使用 `sagellm_protocol.Metrics`，不重复定义
- Runner 负责填充完整的 Metrics

---

## 3. WorkloadSpec（A 内部使用）

```python
from dataclasses import dataclass
from enum import Enum

class WorkloadType(str, Enum):
    SHORT = "short"
    LONG = "long"
    STRESS = "stress"

@dataclass
class WorkloadSpec:
    """Workload 规格描述"""
    name: str
    workload_type: WorkloadType
    prompt_len: int          # 期望的 prompt 长度
    output_len: int          # 期望的输出长度
    num_requests: int        # 请求数量
    concurrent: bool = False # 是否并发
    kv_budget_tokens: int | None = None  # KV 预算
```

---

## 4. AggregatedMetrics（C 输出）

```python
from dataclasses import dataclass

@dataclass
class AggregatedMetrics:
    """聚合指标（多请求统计）"""
    # 延迟指标
    avg_ttft_ms: float
    p50_ttft_ms: float
    p95_ttft_ms: float
    p99_ttft_ms: float
    
    avg_tbt_ms: float
    avg_tpot_ms: float
    
    # 吞吐
    avg_throughput_tps: float
    total_throughput_tps: float  # 总吞吐
    
    # 错误率
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float
    
    # 内存（取 max）
    peak_mem_mb: int
    
    # KV Cache（取 sum/avg）
    total_kv_used_tokens: int
    total_kv_used_bytes: int
    avg_prefix_hit_rate: float
    total_evict_count: int
    total_evict_ms: float
    
    # Speculative（取 avg）
    avg_spec_accept_rate: float
    
    # 时间
    total_time_s: float
    start_time: float
    end_time: float
```

---

## 5. ContractResult（C 输出）

```python
from dataclasses import dataclass
from enum import Enum

class ContractVersion(str, Enum):
    YEAR1 = "year1"
    YEAR2 = "year2"
    YEAR3 = "year3"

@dataclass
class ContractResult:
    """Contract 验证结果"""
    passed: bool
    version: ContractVersion
    checks: dict[str, bool]      # 每项检查的结果
    details: dict[str, str]      # 每项检查的详细说明
    summary: str                 # 总结
```

---

## 6. 接口约定

### Dataset（模块A）
```python
class BenchmarkDataset(ABC):
    @abstractmethod
    def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        """根据 WorkloadSpec 生成请求列表"""
        ...
```

### Runner（模块B）
```python
class BenchmarkRunner:
    async def run(
        self,
        requests: list[BenchmarkRequest],
        concurrent: bool = False,
        timeout: float = 60.0,
    ) -> list[BenchmarkResult]:
        """执行请求，返回结果"""
        ...
```

### Aggregator（模块C）
```python
class MetricsAggregator:
    @staticmethod
    def aggregate(results: list[BenchmarkResult]) -> AggregatedMetrics:
        """聚合多个结果"""
        ...
```

### ContractVerifier（模块C）
```python
class ContractVerifier:
    @staticmethod
    def verify(
        metrics: AggregatedMetrics,
        version: ContractVersion,
    ) -> ContractResult:
        """验证是否满足 Demo Contract"""
        ...
```

---

## 7. 依赖关系

```
Dataset (A) ──BenchmarkRequest[]──► Runner (B) ──BenchmarkResult[]──► Aggregator (C)
                                                                            │
                                                                            ▼
                                                                     AggregatedMetrics
                                                                            │
                                                                            ▼
                                                                   ContractVerifier (C)
                                                                            │
                                                                            ▼
                                                                     ContractResult
```

---

## 8. 开发顺序建议

1. **先定义公共类型**（本文件中的 dataclass）放到 `src/sagellm_benchmark/types.py`
2. **三人并行开发**各自模块
3. **最后整合测试**
