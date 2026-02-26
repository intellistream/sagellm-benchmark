#!/usr/bin/env python3
"""
用户本地聚合命令：从 HF 拉取最新数据并与本地结果合并

这是用户在本地运行的命令，用于准备上传到 GitHub 的数据。

工作流程：
1. 从 HF 下载公开的 leaderboard 数据（无需 token）
2. 扫描本地 outputs/ 目录的新结果
3. 智能合并（去重，选性能更好的）
4. 保存到 hf_data/ 目录
5. 用户提交 hf_data/ 到 git（不提交 outputs/）

运行方式：
    python scripts/aggregate_for_hf.py
    或
    sagellm-benchmark aggregate

HF 仓库（公开访问）：
    https://huggingface.co/datasets/intellistream/sagellm-benchmark-results
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

# HF 配置
HF_REPO = "intellistream/sagellm-benchmark-results"
HF_BRANCH = "main"


def download_from_hf(filename: str) -> list[dict]:
    """
    从 Hugging Face 下载现有数据

    端点选择策略（优先级从高到低）：
    1. 环境变量 HF_ENDPOINT（如果设置）
    2. 官方地址 https://huggingface.co（默认）
    3. 如果官方失败，自动回退到 https://hf-mirror.com
    """
    # 1. 优先使用环境变量指定的端点
    endpoint = os.getenv("HF_ENDPOINT", "https://huggingface.co")

    # 2. 定义备用端点列表（如果主端点失败）
    fallback_endpoints = []
    if endpoint != "https://hf-mirror.com":
        # 如果当前不是镜像，将镜像作为备用
        fallback_endpoints.append("https://hf-mirror.com")
    if endpoint != "https://huggingface.co":
        # 如果当前不是官方，将官方作为备用
        fallback_endpoints.append("https://huggingface.co")

    # 3. 尝试主端点
    endpoints_to_try = [endpoint] + fallback_endpoints

    for idx, ep in enumerate(endpoints_to_try):
        url = f"{ep}/datasets/{HF_REPO}/resolve/{HF_BRANCH}/{filename}"
        is_primary = idx == 0
        prefix = "📥 下载 HF 数据:" if is_primary else "  🔄 回退到:"

        print(f"{prefix} {url}")

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
                print(f"  ✓ 下载成功: {len(data)} 条记录")
                return data
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("  ⚠️ 文件不存在（首次上传）")
                return []  # 404 是确定的，无需重试
            else:
                print(f"  ⚠️ HTTP 错误 {e.code}: {e.reason}")
                if idx < len(endpoints_to_try) - 1:
                    continue  # 尝试下一个端点
                return []
        except Exception as e:
            print(f"  ⚠️ 下载失败: {e}")
            if idx < len(endpoints_to_try) - 1:
                continue  # 尝试下一个端点
            return []

    return []


def load_local_results(outputs_dir: Path) -> list[dict]:
    """递归加载 outputs 目录下的所有 leaderboard JSON 文件"""
    all_results = []

    for json_file in outputs_dir.rglob("*_leaderboard.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                all_results.append(data)
                print(f"  ✓ 加载: {json_file.relative_to(outputs_dir)}")
        except Exception as e:
            print(f"  ✗ 加载失败: {json_file} - {e}")

    return all_results


def get_config_key(entry: dict) -> str:
    """
    生成配置唯一标识 key

    相同配置 = 相同硬件 + 相同模型 + 相同 workload 场景 + 相同精度 + 相同版本
    """
    hw = entry.get("hardware", {})
    model = entry.get("model", {})
    cluster = entry.get("cluster")
    metadata = entry.get("metadata", {})

    # 提取 workload 场景名 (e.g. 'Benchmark run: Q1' -> 'Q1')
    notes = metadata.get("notes", "")
    workload_name = "default"
    if notes:
        m = re.search(r"\b(Q\d+|M\d+|year\d+|stress|short|long|all)\b", notes, re.IGNORECASE)
        if m:
            workload_name = m.group(1).upper()

    # 构建配置 key
    parts = [
        hw.get("chip_model", "unknown"),
        str(hw.get("chip_count", 1)),
        model.get("name", "unknown"),
        model.get("precision", "FP16"),
        workload_name,
        str(
            entry.get("sagellm_version") or entry.get("versions", {}).get("benchmark") or "unknown"
        ),
    ]

    # 如果是多节点，加入节点信息
    if cluster and cluster.get("node_count", 1) > 1:
        parts.append(f"nodes_{cluster['node_count']}")

    return "|".join(parts)


def is_better_result(new_entry: dict, existing_entry: dict) -> bool:
    """
    判断新结果是否比现有结果更好

    评判标准（优先级从高到低）：
    1. throughput_tps 越高越好
    2. ttft_ms 越低越好
    3. error_rate 越低越好
    """
    new_metrics = new_entry.get("metrics", {})
    old_metrics = existing_entry.get("metrics", {})

    # throughput 高更好
    new_tps = new_metrics.get("throughput_tps", 0)
    old_tps = old_metrics.get("throughput_tps", 0)
    if new_tps > old_tps * 1.05:  # 5% 容差
        return True
    if old_tps > new_tps * 1.05:
        return False

    # ttft 低更好
    new_ttft = new_metrics.get("ttft_ms", float("inf"))
    old_ttft = old_metrics.get("ttft_ms", float("inf"))
    if new_ttft < old_ttft * 0.95:  # 5% 容差
        return True
    if old_ttft < new_ttft * 0.95:
        return False

    # error_rate 低更好
    new_err = new_metrics.get("error_rate", 1)
    old_err = old_metrics.get("error_rate", 1)
    if new_err < old_err:
        return True

    # 默认保留现有的（不覆盖）
    return False


def sanitize_entry(entry: dict) -> dict:
    """确保所有字段类型一致，避免 HF Arrow schema 冲突（null vs double/string）"""
    hw = entry.get("hardware", {})
    env = entry.get("environment", {})

    # float 字段：null -> 0.0
    for key in ("memory_per_chip_gb", "total_memory_gb"):
        if hw.get(key) is None:
            hw[key] = 0.0

    # str 字段：null -> ""
    for key in ("cuda_version", "driver_version", "cann_version", "pytorch_version"):
        if env.get(key) is None:
            env[key] = ""

    return entry


def merge_results(existing: list[dict], new_results: list[dict]) -> list[dict]:
    """
    合并现有数据和新数据

    规则：
    - 基于配置 key 去重（相同硬件+模型+workload+精度）
    - 相同配置时，保留性能更好的结果
    - 不同配置则添加
    """
    # 使用 dict 以 config_key 为 key 进行合并
    merged: dict[str, dict] = {}

    # 先加入现有数据
    for entry in existing:
        config_key = get_config_key(entry)
        merged[config_key] = sanitize_entry(entry)

    added = 0
    updated = 0
    skipped = 0

    for entry in new_results:
        config_key = get_config_key(entry)
        entry = sanitize_entry(entry)

        if config_key not in merged:
            # 新配置，直接添加
            merged[config_key] = entry
            added += 1
        else:
            # 已存在，比较性能
            if is_better_result(entry, merged[config_key]):
                merged[config_key] = entry
                updated += 1
                print(f"    ↑ 更新 (更好): {config_key[:50]}...")
            else:
                skipped += 1
                print(f"    ○ 跳过 (已有更好): {config_key[:50]}...")

    print(f"  📊 合并结果: 新增 {added}, 更新 {updated}, 跳过 {skipped}, 总计 {len(merged)}")
    return list(merged.values())


def categorize_results(results: list[dict]) -> tuple[list, list, list]:
    """将结果分类为单机单卡、单机多卡、多机多卡"""
    single_chip = []
    multi_chip = []
    multi_node = []

    for entry in results:
        chip_count = entry["hardware"]["chip_count"]
        cluster = entry.get("cluster")

        if cluster and cluster.get("node_count", 1) > 1:
            multi_node.append(entry)
        elif chip_count > 1:
            multi_chip.append(entry)
        else:
            single_chip.append(entry)

    return single_chip, multi_chip, multi_node


def main():
    print("=" * 70)
    print("📦 sageLLM Benchmark - 本地聚合工具")
    print("=" * 70)

    # 路径设置
    base_dir = Path(__file__).parent.parent
    outputs_dir = base_dir / "outputs"
    hf_output_dir = base_dir / "hf_data"

    # 创建输出目录
    hf_output_dir.mkdir(exist_ok=True)

    # Step 1: 从 HF 下载现有数据（公开访问，无需 token）
    print("\n📥 从 Hugging Face 下载最新数据...")
    print(f"   仓库: https://huggingface.co/datasets/{HF_REPO}")
    existing_single = download_from_hf("leaderboard_single.json")
    existing_multi = download_from_hf("leaderboard_multi.json")

    # Step 2: 加载本地新结果
    print("\n📂 扫描本地 outputs/ 目录...")
    if not outputs_dir.exists():
        print("  ⚠️ outputs/ 目录不存在")
        print("  💡 请先运行 benchmark: sagellm-benchmark run --model <model>")
        local_results = []
    else:
        local_results = load_local_results(outputs_dir)
        if not local_results:
            print("  ⚠️ 未找到任何 *_leaderboard.json 文件")
            print("  💡 请先运行 benchmark 生成结果")
        else:
            print(f"  ✓ 找到 {len(local_results)} 条本地结果")

    # Step 3: 分类本地结果
    if local_results:
        local_single_chip, local_multi_chip, local_multi_node = categorize_results(local_results)
        local_single = local_single_chip + local_multi_chip
        print(f"  └─ 单机: {len(local_single)} 条, 多机: {len(local_multi_node)} 条")
    else:
        local_single = []
        local_multi_node = []

    # Step 4: 合并数据
    print("\n🔀 智能合并数据...")
    print("  Single (单机单卡+多卡):")
    merged_single = merge_results(existing_single, local_single)
    print("  Multi (多机多卡):")
    merged_multi = merge_results(existing_multi, local_multi_node)

    # Step 5: 保存到 JSON 文件
    print("\n💾 保存到 hf_data/ 目录...")
    single_file = hf_output_dir / "leaderboard_single.json"
    multi_file = hf_output_dir / "leaderboard_multi.json"

    with open(single_file, "w", encoding="utf-8") as f:
        json.dump(merged_single, f, indent=2, ensure_ascii=False)

    with open(multi_file, "w", encoding="utf-8") as f:
        json.dump(merged_multi, f, indent=2, ensure_ascii=False)

    print(f"  ✓ {single_file} ({len(merged_single)} 条)")
    print(f"  ✓ {multi_file} ({len(merged_multi)} 条)")

    # 友好提示
    print("\n" + "=" * 70)
    print("✅ 聚合完成！")
    print("=" * 70)
    print("\n📌 下一步操作：")
    print("  1. 提交聚合数据到 git:")
    print("     git add hf_data/")
    print("     git commit -m 'feat: add benchmark results'")
    print("     git push")
    print("\n  2. GitHub Actions 会自动:")
    print("     - 与 HF 最新数据合并（解决并发冲突）")
    print("     - 上传到 Hugging Face")
    print("     - 清理 hf_data/ 保持仓库轻量")
    print("\n💡 提示: outputs/ 目录不会被提交（在 .gitignore 中）")
    print("=" * 70)


if __name__ == "__main__":
    main()
