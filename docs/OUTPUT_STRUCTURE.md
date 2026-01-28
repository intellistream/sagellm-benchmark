# sagellm-benchmark 输出目录结构设计

## 设计原则

1. **按配置层级组织**：backend → model → workload 逐层分类
2. **语义化命名**：目录名直观反映测试配置
3. **快速查找**：通过目录层级快速定位目标结果
4. **避免时间戳混乱**：时间戳仅作为后缀区分同配置的多次运行

## 推荐方案：层级结构

```
outputs/
├── cpu/                                # Backend 层
│   ├── gpt2/                          # Model 层
│   │   ├── m1_20260128_001/           # Workload_日期_序号
│   │   │   ├── config.json
│   │   │   ├── summary.json
│   │   │   ├── short_input_metrics.json
│   │   │   ├── long_input_metrics.json
│   │   │   └── stress_test_metrics.json
│   │   ├── short_20260128_002/
│   │   │   └── ...
│   │   └── latest -> m1_20260128_001/  # 软链接到最新运行
│   │
│   └── Qwen2-7B/
│       ├── m1_20260128_001/
│       └── stress_20260128_001/
│
├── cuda/                               # 其他 backend
│   └── llama-3-8b/
│       └── ...
│
└── vllm/
    └── ...
```

## 目录命名规则

### 层级 1: Backend
- 目录名：backend 名称（cpu, cuda, vllm, lmdeploy）
- 示例：`cpu/`, `cuda/`, `vllm/`

### 层级 2: Model
- 目录名：模型名称（简化路径，替换特殊字符）
- 规则：
  - `sshleifer/tiny-gpt2` → `tiny-gpt2`
  - `Qwen/Qwen2-7B-Instruct` → `Qwen2-7B-Instruct`
  - `/path/to/model` → 取最后一级目录名
- 示例：`gpt2/`, `Qwen2-7B/`, `llama-3-8b/`

### 层级 3: Run（workload + 日期 + 序号）
- 格式：`{workload}_{YYYYMMDD}_{NNN}`
- workload: m1, short, long, stress
- 日期：当天日期（便于区分不同日期的运行）
- 序号：001, 002, ... （同一天多次运行的序号）
- 示例：`m1_20260128_001/`, `short_20260128_002/`

## 查找场景示例

### 场景 1: 查看 CPU backend + gpt2 模型的所有测试
```bash
ls outputs/cpu/gpt2/
# 输出：
# m1_20260128_001/
# short_20260128_002/
# latest -> m1_20260128_001/
```

### 场景 2: 查看最新的 CPU + gpt2 测试结果
```bash
cat outputs/cpu/gpt2/latest/summary.json
```

### 场景 3: 对比同一模型不同 workload 的结果
```bash
diff outputs/cpu/gpt2/short_20260128_001/summary.json \
     outputs/cpu/gpt2/stress_20260128_001/summary.json
```

### 场景 4: 查找所有 Qwen2-7B 的测试（跨 backend）
```bash
find outputs -name "Qwen2-7B" -type d
# 输出：
# outputs/cpu/Qwen2-7B
# outputs/cuda/Qwen2-7B
```

## 文件内容

### config.json（运行配置）
```json
{
  "run_id": "m1_20260128_001",
  "timestamp": "2026-01-28T08:14:23",
  "backend": "cpu",
  "model": "gpt2",
  "model_path": "sshleifer/tiny-gpt2",
  "workload": "m1",
  "dataset": "default",
  "num_samples": 5,
  "versions": {
    "sagellm_benchmark": "0.3.0.3",
    "sagellm_core": "0.3.0.5",
    "sagellm_backend": "0.3.0.6"
  }
}
```

### summary.json（汇总结果）
```json
{
  "run_id": "m1_20260128_001",
  "backend": "cpu",
  "model": "gpt2",
  "total_workloads": 3,
  "successful": 3,
  "failed": 0,
  "overall_metrics": {
    "avg_ttft_ms": 45.2,
    "avg_throughput_tps": 80.0
  },
  "workloads": {
    "short_input": {
      "status": "success",
      "ttft_ms": 45.2,
      "metrics_file": "short_input_metrics.json"
    },
    "long_input": {...},
    "stress_test": {...}
  }
}
```

## CLI 使用

```bash
# 默认使用层级结构
sagellm-benchmark run --workload m1 --backend cpu --model gpt2
# 输出到：outputs/cpu/gpt2/m1_20260128_001/

# 再次运行（同一天）
sagellm-benchmark run --workload m1 --backend cpu --model gpt2
# 输出到：outputs/cpu/gpt2/m1_20260128_002/

# 不同 workload
sagellm-benchmark run --workload short --backend cpu --model gpt2
# 输出到：outputs/cpu/gpt2/short_20260128_001/

# 查看最新结果
cat outputs/cpu/gpt2/latest/summary.json

# 自定义输出路径（可选）
sagellm-benchmark run --workload m1 --output /tmp/my_test
```

## 向后兼容

- 保留 `--output` 参数作为高级选项
- 如果指定 `--output`，则完全使用用户路径，不创建层级结构
- 如果未指定，则自动使用 `outputs/<backend>/<model>/<workload_date_seq>/`

## 优势对比

| 方案 | 查找速度 | 可读性 | 占用空间 |
|-----|---------|-------|---------|
| 时间戳（旧） | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| 层级结构（新） | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**查找速度提升**：
- 旧方案：需要打开每个时间戳目录查看 config.json
- 新方案：通过目录路径直接看到 backend/model/workload

**可读性提升**：
- 旧方案：`20260128_081423` 无法看出测试内容
- 新方案：`outputs/cpu/gpt2/m1_20260128_001` 一目了然
