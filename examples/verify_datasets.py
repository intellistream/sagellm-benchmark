#!/usr/bin/env python3
"""验收脚本 - 验证 Datasets 模块功能。

按照 TASK_A_DATASETS.md 的交付验收用例：
- 构造 Year1 workload
- 采样 5 条 request
- 打印 request_id 与 prompt 长度
"""

from __future__ import annotations

from sagellm_benchmark.datasets import (
    MockShareGPTDataset,
    RandomDataset,
    get_year1_workloads,
)
from sagellm_benchmark.types import WorkloadSpec


def main() -> None:
    """运行验收测试。"""
    print("=" * 60)
    print("Datasets 模块验收测试")
    print("=" * 60)

    # 1. 获取 Year1 workloads
    workloads = get_year1_workloads()
    print(f"\n✅ Year1 Workloads 数量: {len(workloads)}")
    for w in workloads:
        print(
            f"   - {w.name}: type={w.workload_type.value}, "
            f"prompt={w.prompt_len}, output={w.output_len}"
        )

    # 2. 使用 RandomDataset 采样
    print("\n" + "-" * 60)
    print("RandomDataset 采样测试")
    print("-" * 60)

    dataset = RandomDataset(seed=42)
    print(f"Dataset: {dataset.name}")

    for spec in workloads:
        # 修改为采样 5 条
        modified_spec = WorkloadSpec(
            name=spec.name,
            workload_type=spec.workload_type,
            prompt_len=spec.prompt_len,
            output_len=spec.output_len,
            num_requests=5,  # 验收要求
            concurrent=spec.concurrent,
            kv_budget_tokens=spec.kv_budget_tokens,
        )

        requests = dataset.sample(modified_spec)
        print(f"\n{spec.name} (采样 5 条):")
        for req in requests:
            print(
                f"  - ID: {req.request_id[:8]}...  "
                f"prompt_len={len(req.prompt):4d} chars  "
                f"max_tokens={req.max_tokens}"
            )

    # 3. 使用 MockShareGPTDataset 采样
    print("\n" + "-" * 60)
    print("MockShareGPTDataset 采样测试")
    print("-" * 60)

    sharegpt = MockShareGPTDataset(seed=42)
    print(f"Dataset: {sharegpt.name}")

    spec = workloads[0]  # SHORT workload
    modified_spec = WorkloadSpec(
        name=spec.name,
        workload_type=spec.workload_type,
        prompt_len=spec.prompt_len,
        output_len=spec.output_len,
        num_requests=5,
    )

    requests = sharegpt.sample(modified_spec)
    print(f"\n{spec.name} (采样 5 条):")
    for req in requests:
        print(f"  - ID: {req.request_id[:8]}...  prompt_len={len(req.prompt):4d} chars")

    # 4. 验证 request_id 唯一性
    print("\n" + "-" * 60)
    print("Request ID 唯一性验证")
    print("-" * 60)

    all_ids = []
    dataset.reset_seed(123)
    for spec in workloads:
        modified_spec = WorkloadSpec(
            name=spec.name,
            workload_type=spec.workload_type,
            prompt_len=spec.prompt_len,
            output_len=spec.output_len,
            num_requests=10,
        )
        reqs = dataset.sample(modified_spec)
        all_ids.extend(r.request_id for r in reqs)

    unique_ids = set(all_ids)
    print(f"总 ID 数量: {len(all_ids)}")
    print(f"唯一 ID 数量: {len(unique_ids)}")
    if len(all_ids) == len(unique_ids):
        print("✅ 所有 request_id 唯一!")
    else:
        print("❌ 存在重复 request_id!")

    print("\n" + "=" * 60)
    print("验收测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
