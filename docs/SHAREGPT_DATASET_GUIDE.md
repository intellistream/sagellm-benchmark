# ShareGPT 数据集使用指南

sagellm-benchmark 支持三种方式加载 ShareGPT 数据集：

## 1. 从 ModelScope 加载（推荐 - 支持中英文）

```python
from sagellm_benchmark.datasets import ShareGPTDataset

# 加载中英文 ShareGPT 数据集（90k 条对话）
dataset = ShareGPTDataset.from_modelscope(
    dataset_id="AI-ModelScope/ShareGPT-Chinese-English-90k",
    split="train",
    min_prompt_len=50,
    max_prompt_len=5000,
    seed=42,
)

print(f"Loaded {len(dataset)} prompts")
```

**优点**：
- ✅ 包含中英文对话（90k 条）
- ✅ 国内访问速度快
- ✅ 真实用户对话数据

**数据集来源**：https://modelscope.cn/datasets/AI-ModelScope/ShareGPT-Chinese-English-90k

## 2. 从 HuggingFace 加载

```python
dataset = ShareGPTDataset.from_huggingface(
    repo_id="anon8231489123/ShareGPT_Vicuna_unfiltered",
    split="train",
    seed=42,
)
```

**优点**：
- ✅ 数据量大
- ⚠️ 国内访问可能较慢

## 3. 从本地 JSON 文件加载

```python
dataset = ShareGPTDataset.from_file("path/to/sharegpt.json")
```

**JSON 格式**：
```json
[
  {
    "conversations": [
      {"from": "human", "value": "你好，请介绍一下深度学习"},
      {"from": "gpt", "value": "深度学习是机器学习的一个分支..."}
    ]
  }
]
```

## 完整使用示例

参见：`examples/use_modelscope_sharegpt.py`

```bash
# 1. 安装依赖
pip install modelscope

# 2. 运行示例
python examples/use_modelscope_sharegpt.py
```

## WorkloadSpec 定义

```python
from sagellm_benchmark.types import WorkloadSpec, WorkloadType

spec = WorkloadSpec(
    name="sharegpt_test",
    workload_type=WorkloadType.SHORT,
    prompt_len=128,      # 目标 prompt 长度（tokens）
    output_len=128,      # 生成长度
    num_requests=5,      # 采样请求数
    kv_budget_tokens=None,
)

# 从数据集采样
requests = dataset.sample(spec)
```

## 数据集统计

| 数据集 | 来源 | 规模 | 语言 | 访问速度 |
|--------|------|------|------|---------|
| **AI-ModelScope/ShareGPT-Chinese-English-90k** | ModelScope | 90k | 中英文 | 快 ✅ |
| anon8231489123/ShareGPT_Vicuna_unfiltered | HuggingFace | 125k | 英文 | 慢 ⚠️ |

## 常见问题

### Q1: ModelScope 数据集下载失败？

```bash
# 设置 ModelScope 缓存目录
export MODELSCOPE_CACHE=~/.cache/modelscope

# 检查网络连接
ping modelscope.cn
```

### Q2: 如何过滤 prompt 长度？

```python
dataset = ShareGPTDataset.from_modelscope(
    min_prompt_len=100,   # 最小字符数
    max_prompt_len=2000,  # 最大字符数
)
```

### Q3: 如何查看数据集内容？

```python
# 采样 1 个请求查看
spec = WorkloadSpec(
    name="preview",
    workload_type=WorkloadType.SHORT,
    prompt_len=100,
    output_len=50,
    num_requests=1,
)

requests = dataset.sample(spec)
print(requests[0].prompt)
```

## 贡献

欢迎提交 PR 支持更多数据集！
