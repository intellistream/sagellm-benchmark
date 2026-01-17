# Task C: Metrics Aggregation & Reporting - 实现文档

## 概述

Task C 负责实现指标聚合、Demo Contract 验证和多格式报告生成。

## 实现结构

```
src/sagellm_benchmark/
├── metrics/                    # Task C - Metrics 模块
│   ├── __init__.py
│   ├── aggregator.py          # MetricsAggregator - 指标聚合器
│   └── contract.py            # ContractVerifier - Contract 验证器
└── reporters/                  # Task C - Reporters 模块
    ├── __init__.py
    ├── json_reporter.py       # JSONReporter - JSON 报告生成
    ├── markdown_reporter.py   # MarkdownReporter - Markdown 报告生成
    └── table_reporter.py      # TableReporter - 终端表格输出

tests/
├── test_metrics_aggregator.py # Metrics & Contract 测试
└── test_reporters.py          # Reporters 测试

examples/
└── task_c_demo.py             # 端到端示例
```

## 核心组件

### 1. MetricsAggregator（指标聚合器）

**位置**: `src/sagellm_benchmark/metrics/aggregator.py`

**功能**: 将多个 `BenchmarkResult` 聚合为 `AggregatedMetrics`

**聚合规则**:
- **延迟类** (ttft_ms, tbt_ms, tpot_ms): 取平均值 + 百分位 (P50/P95/P99)
- **内存** (peak_mem_mb): 取最大值
- **KV Cache 计数** (evict_count, kv_used_tokens): 取总和
- **比率类** (prefix_hit_rate, spec_accept_rate): 取平均值
- **吞吐**: 计算平均吞吐和总吞吐

**使用示例**:

```python
from sagellm_benchmark.metrics import MetricsAggregator
from sagellm_benchmark.types import BenchmarkResult

results: list[BenchmarkResult] = [...]  # 从 Runner 获取
aggregated = MetricsAggregator.aggregate(results)

print(f"Avg TTFT: {aggregated.avg_ttft_ms:.2f}ms")
print(f"P95 TTFT: {aggregated.p95_ttft_ms:.2f}ms")
print(f"Error Rate: {aggregated.error_rate * 100:.2f}%")
```

### 2. ContractVerifier（Contract 验证器）

**位置**: `src/sagellm_benchmark/metrics/contract.py`

**功能**: 验证 `AggregatedMetrics` 是否满足 Year1/2/3 Demo Contract

**阈值定义**:

| Contract | TTFT | TBT | TPOT | 吞吐 | 错误率 | 内存 | Prefix 命中率 | Spec 接受率 |
|----------|------|-----|------|------|--------|------|---------------|-------------|
| Year1    | <100ms | <20ms | <20ms | >50 tps | <5% | <32GB | - | - |
| Year2    | <50ms | <10ms | <10ms | >100 tps | <2% | <24GB | >70% | - |
| Year3    | <30ms | <5ms | <5ms | >200 tps | <1% | <16GB | >85% | >60% |

**使用示例**:

```python
from sagellm_benchmark.metrics import ContractVerifier
from sagellm_benchmark.types import ContractVersion

result = ContractVerifier.verify(aggregated, ContractVersion.YEAR1)

if result.passed:
    print(f"✅ {result.summary}")
else:
    print(f"❌ {result.summary}")
    
for check_name, passed in result.checks.items():
    status = "✅" if passed else "❌"
    detail = result.details.get(check_name, "")
    print(f"{status} {check_name}: {detail}")
```

### 3. Reporters（报告生成器）

#### 3.1 JSONReporter

**功能**: 生成 JSON 格式的指标报告

```python
from sagellm_benchmark.reporters import JSONReporter

json_str = JSONReporter.generate(
    metrics=aggregated,
    contract=contract_result,
    output_path="report.json",
    version="0.1.0.2",
)
```

**输出格式**:

```json
{
  "metrics": {
    "avg_ttft_ms": 20.0,
    "p95_ttft_ms": 30.0,
    ...
  },
  "contract": {
    "passed": true,
    "version": "year1",
    "checks": {...},
    "details": {...}
  },
  "version": "0.1.0.2"
}
```

#### 3.2 MarkdownReporter

**功能**: 生成 Markdown 格式的报告（表格 + 结论）

```python
from sagellm_benchmark.reporters import MarkdownReporter

md_str = MarkdownReporter.generate(
    metrics=aggregated,
    contract=contract_result,
    output_path="report.md",
    title="Benchmark Report",
    version="0.1.0.2",
)
```

#### 3.3 TableReporter

**功能**: 在终端输出彩色表格（使用 Rich）

```python
from sagellm_benchmark.reporters import TableReporter

TableReporter.generate(
    metrics=aggregated,
    contract=contract_result,
    show_contract=True,
)
```

**特性**:
- ✅ 自动使用 Rich 库（如已安装）
- ✅ Fallback 到纯文本（无 Rich）
- ✅ 彩色输出、表格美化

## 测试

### 运行测试

```bash
# 使用 sagellm conda 环境
conda activate sagellm

# 运行 Metrics & Contract 测试
pytest tests/test_metrics_aggregator.py -v

# 运行 Reporters 测试
pytest tests/test_reporters.py -v

# 运行所有 Task C 测试
pytest tests/test_metrics_aggregator.py tests/test_reporters.py -v
```

### 测试覆盖

- ✅ `test_aggregator_basic`: 基本聚合功能
- ✅ `test_aggregator_with_failures`: 包含失败请求的聚合
- ✅ `test_contract_year1_pass`: Year1 Contract 通过
- ✅ `test_contract_year2_fail`: Year2 Contract 失败（prefix_hit_rate 不足）
- ✅ `test_contract_year3_all_checks`: Year3 Contract 所有检查项
- ✅ `test_json_reporter_basic`: JSON 报告生成
- ✅ `test_json_reporter_with_contract`: 包含 Contract 的 JSON 报告
- ✅ `test_json_reporter_load`: 从文件加载 JSON 报告
- ✅ `test_markdown_reporter_basic`: Markdown 报告生成
- ✅ `test_markdown_reporter_with_contract`: 包含 Contract 的 Markdown 报告
- ✅ `test_table_reporter_plain_text`: 纯文本表格输出
- ✅ `test_table_reporter_with_rich`: Rich 表格输出

## 端到端示例

运行完整示例：

```bash
conda activate sagellm
python examples/task_c_demo.py
```

**示例流程**:

1. 创建 5 个 Mock BenchmarkResult
2. 使用 MetricsAggregator 聚合指标
3. 验证 Year1 Contract（通过）
4. 验证 Year2 Contract（失败：吞吐不足）
5. 生成 JSON 报告 (`benchmark_results/task_c_demo.json`)
6. 生成 Markdown 报告 (`benchmark_results/task_c_demo.md`)
7. 终端输出 Rich 表格

## 公共 API

所有 Task C 模块已导出到顶层包：

```python
from sagellm_benchmark import (
    # Metrics Aggregation & Contract
    MetricsAggregator,
    ContractVerifier,
    
    # Reporters
    JSONReporter,
    MarkdownReporter,
    TableReporter,
    
    # Types
    AggregatedMetrics,
    ContractResult,
    ContractVersion,
)
```

## 依赖关系

```
Task C (本模块)
    ↑
    │ 依赖
    ↓
Task B (Runner) ──► BenchmarkResult[]
    ↓
Task C (Aggregator) ──► AggregatedMetrics
    ↓
Task C (Contract Verifier) ──► ContractResult
    ↓
Task C (Reporters) ──► JSON/Markdown/Table
```

## 注意事项

1. **Timestamps 访问**: Protocol 的时间戳通过 `metrics.timestamps` 对象访问，而非直接字段：
   ```python
   # ✅ 正确
   queued_at = metrics.timestamps.queued_at
   
   # ❌ 错误
   queued_at = metrics.queued_at  # AttributeError
   ```

2. **百分位计算**: 使用排序后的索引法：
   ```python
   sorted_samples = sorted(samples)
   p95_index = int(len(sorted_samples) * 0.95)
   p95_value = sorted_samples[p95_index]
   ```

3. **Contract 阈值**: Year1/2/3 阈值定义在 `ContractVerifier` 类中，可根据需求调整。

4. **Rich 依赖**: TableReporter 优先使用 Rich，但在 Rich 未安装时会 fallback 到纯文本输出。

## 验收清单

- ✅ MetricsAggregator 实现（聚合逻辑正确）
- ✅ ContractVerifier 实现（Year1/2/3 阈值定义）
- ✅ JSONReporter 实现（JSON 输出 + 加载）
- ✅ MarkdownReporter 实现（表格 + 结论）
- ✅ TableReporter 实现（Rich + Fallback）
- ✅ 12 个测试用例全部通过
- ✅ 端到端示例可运行
- ✅ 公共 API 导出
- ✅ 文档完整

## 下一步

Task C 已完成，可以：

1. 与 Task A (Datasets) 和 Task B (Runner) 集成
2. 在 CLI 中使用 Reporters 输出报告
3. 扩展更多报告格式（HTML, CSV 等）
4. 优化 Contract 阈值（根据实际测试数据）

---

**状态**: ✅ 完成  
**测试**: ✅ 12/12 通过  
**文档**: ✅ 完整
