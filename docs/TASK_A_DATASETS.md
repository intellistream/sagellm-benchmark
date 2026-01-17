# 任务书 A：Datasets & Workloads

## 目标
构建可扩展的数据集与 Workload 生成模块，为 Benchmark Runner 提供统一的 `BenchmarkRequest[]` 输入。

## 范围
- 数据集加载与采样
- Year1/2/3 Demo Workload 生成
- WorkloadSpec 与 BenchmarkRequest 数据结构

## 非目标
- 不实现请求执行逻辑
- 不实现指标聚合与报告
- 不接触引擎接口

## 交付物
- `src/sagellm_benchmark/datasets/` 目录及模块
- `WorkloadSpec` 数据类
- `dataset.sample()` 输出 `BenchmarkRequest[]`
- 单元测试：基础采样可用

## 目录建议
```
src/sagellm_benchmark/datasets/
  __init__.py
  base.py
  random.py
  year_demo.py
  sharegpt.py   # 可选
```

## 设计要求
1. **Protocol-First**：仅使用协议层类型，不定义重复指标。
2. **Mock-First**：无外部数据时支持随机数据。
3. **可扩展**：新增数据集无需修改既有逻辑。

## 关键数据结构

> ⚠️ 参考 `docs/INTERFACE_CONTRACT.md` 获取完整定义

```python
from enum import Enum

class WorkloadType(str, Enum):
    SHORT = "short"
    LONG = "long"
    STRESS = "stress"

@dataclass
class WorkloadSpec:
    name: str
    workload_type: WorkloadType
    prompt_len: int
    output_len: int
    num_requests: int
    concurrent: bool = False
    kv_budget_tokens: int | None = None

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
```

## 实现清单
### 1) base.py
- `BenchmarkDataset` 抽象基类
- `sample(spec: WorkloadSpec) -> list[BenchmarkRequest]`

### 2) random.py
- 随机 prompt 生成
- 支持 `prompt_len` 控制（字符级或 token 级近似）

### 3) year_demo.py
- Year1/2/3 预置 Workload：short/long/stress
- 返回 `WorkloadSpec` 列表

### 4) sharegpt.py（可选）
- JSON 数据集加载
- 过滤短样本与超长样本

## 验收标准
- `year_demo.get_year1_workloads()` 返回 3 个 workload
- `RandomDataset.sample()` 返回 `BenchmarkRequest[]`
- 每个 request 都有唯一 `request_id`

## 开发建议
- prompt_len 允许“近似”即可
- 不要引入 heavy 依赖（datasets/transformers 可选）

## 交付验收用例
- 运行一个脚本：
  - 构造 Year1 workload
  - 采样 5 条 request
  - 打印 request_id 与 prompt 长度

## 注意事项
1. **必读**：先阅读 `docs/INTERFACE_CONTRACT.md` 了解完整接口约定
2. `BenchmarkRequest` 的 `model` 和 `stream` 字段有默认值，Dataset 可不填
3. 生成的 `request_id` 必须全局唯一（建议用 UUID）
4. `prompt_len` 是期望长度，允许误差 ±10%

