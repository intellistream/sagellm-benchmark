# 任务书 C：Metrics Aggregation & Reporting

## 目标
实现指标聚合、报告生成、Demo Contract 校验。

## 范围
- AggregatedMetrics 计算（平均值、百分位）
- JSON/Markdown/Table 报告输出
- Year1/2/3 Demo Contract 验证

## 非目标
- 不执行请求
- 不生成数据集

## 交付物
- `src/sagellm_benchmark/metrics/`
- `src/sagellm_benchmark/reporters/`
- Contract 校验器

## 目录建议
```
src/sagellm_benchmark/metrics/
  __init__.py
  aggregator.py
  contract.py

src/sagellm_benchmark/reporters/
  __init__.py
  json_reporter.py
  markdown_reporter.py
  table_reporter.py
```

## 关键数据结构

> ⚠️ 参考 `docs/INTERFACE_CONTRACT.md` 获取完整定义

```python
@dataclass
class AggregatedMetrics:
    # 延迟指标
    avg_ttft_ms: float
    p50_ttft_ms: float
    p95_ttft_ms: float
    p99_ttft_ms: float
    avg_tbt_ms: float
    avg_tpot_ms: float
    
    # 吞吐
    avg_throughput_tps: float
    total_throughput_tps: float
    
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

@dataclass
class ContractResult:
    passed: bool
    version: ContractVersion
    checks: dict[str, bool]
    details: dict[str, str]
    summary: str
```

## 实现清单
### 1) metrics/aggregator.py
- 输入：BenchmarkResult[]
- 输出：AggregatedMetrics
- 计算 p50/p95/p99

### 2) metrics/contract.py
- Year1/2/3 阈值定义
- `verify(aggregated, version) -> ContractResult`
- 输出 pass/fail + 详细原因

### 3) reporters
- JSON 输出
- Markdown 输出（表格 + 结论）
- Table 输出（Rich）

## 验收标准
- 聚合结果与样本一致（手动可验证）
- Contract 校验输出明确失败原因
- Markdown 报告结构稳定

## 交付验收用例
- 输入 5 条 MockResult
- 输出 p50/p95/p99 与平均值
- Contract 校验通过/失败可控

## 注意事项
1. **必读**：先阅读 `docs/INTERFACE_CONTRACT.md` 了解完整接口约定
2. 百分位计算：使用排序后的索引法（p95 = sorted_values[int(n * 0.95)]）
3. 聚合规则：
   - 延迟类（ttft_ms, tbt_ms）：取平均 + 百分位
   - 内存（peak_mem_mb）：取 max
   - KV Cache 计数（evict_count, kv_used_tokens）：取 sum
   - 比率类（prefix_hit_rate, spec_accept_rate）：取平均
4. Contract 验证阈值参考 `docs/BENCHMARK_DESIGN.md`
5. 报告输出必须包含时间戳和版本信息

