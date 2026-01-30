#!/usr/bin/env python3
"""
并发安全的合并和上传脚本

用于 GitHub Actions，在上传到 HF 前再次合并最新数据，解决并发冲突。

工作流程：
1. 读取用户提交的 hf_data/（可能基于旧版本 HF 数据）
2. 从 HF 下载最新数据（可能已被其他用户更新）
3. 三方智能合并（以 HF 最新版本为基准）
4. 保存合并结果（供 upload_to_hf.py 使用）

这样即使多个用户并发提交，也不会丢失数据。
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

# HF 配置
HF_REPO = "wangyao36/sagellm-benchmark-results"
HF_BRANCH = "main"


def download_from_hf(filename: str) -> list[dict]:
    """从 HF 下载最新数据（公开，无需 token）"""
    url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_BRANCH}/{filename}"
    print(f"  📥 {url}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"    ✓ {len(data)} 条记录")
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"    ⚠️ 文件不存在（首次上传）")
        else:
            print(f"    ⚠️ HTTP {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"    ⚠️ 下载失败: {e}")
        return []


def get_config_key(entry: dict) -> str:
    """
    生成配置唯一标识 key

    相同配置 = 相同硬件 + 相同模型 + 相同 workload + 相同精度
    """
    hw = entry.get("hardware", {})
    model = entry.get("model", {})
    workload = entry.get("workload", {})
    cluster = entry.get("cluster")

    # 构建配置 key
    parts = [
        hw.get("chip_model", "unknown"),
        str(hw.get("chip_count", 1)),
        model.get("name", "unknown"),
        model.get("precision", "FP16"),
        str(workload.get("input_length", 0)),
        str(workload.get("output_length", 0)),
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


def smart_merge(hf_latest: list[dict], user_data: list[dict]) -> list[dict]:
    """
    三方智能合并

    关键规则：
    1. HF 最新数据为基准（权威版本）
    2. 用户数据追加或更新
    3. 相同配置时，选择性能更好的
    4. 不同配置则追加

    这样即使用户基于旧版本 HF 数据合并，也能与最新版本正确合并。
    """
    merged: dict[str, dict] = {}

    # 先加入 HF 最新数据（权威版本）
    for entry in hf_latest:
        config_key = get_config_key(entry)
        merged[config_key] = entry

    added = 0
    updated = 0
    skipped = 0

    # 合并用户数据
    for entry in user_data:
        config_key = get_config_key(entry)

        if config_key not in merged:
            # 新配置，直接添加
            merged[config_key] = entry
            added += 1
            print(f"    ✓ 新增: {config_key[:60]}...")
        else:
            # 已存在，比较性能
            if is_better_result(entry, merged[config_key]):
                merged[config_key] = entry
                updated += 1
                print(f"    ↑ 更新: {config_key[:60]}...")
            else:
                skipped += 1
                # 不打印跳过的（太多）

    print(f"\n  📊 合并结果: 新增 {added}, 更新 {updated}, 跳过 {skipped}, 总计 {len(merged)}")
    return list(merged.values())


def main():
    print("=" * 60)
    print("🔀 并发安全合并（GitHub Actions）")
    print("=" * 60)

    # 路径设置
    hf_data_dir = Path("hf_data")

    if not hf_data_dir.exists():
        print(f"\n❌ hf_data/ 目录不存在")
        print("💡 用户应该先运行 'sagellm-benchmark aggregate'")
        exit(1)

    # 1. 读取用户提交的数据
    print("\n📂 读取用户提交的数据...")
    user_single_file = hf_data_dir / "leaderboard_single.json"
    user_multi_file = hf_data_dir / "leaderboard_multi.json"

    if not user_single_file.exists() or not user_multi_file.exists():
        print(f"  ⚠️ 缺少必要文件")
        exit(1)

    user_single = json.loads(user_single_file.read_text(encoding="utf-8"))
    user_multi = json.loads(user_multi_file.read_text(encoding="utf-8"))
    print(f"  ✓ Single: {len(user_single)} 条")
    print(f"  ✓ Multi: {len(user_multi)} 条")

    # 2. 从 HF 下载最新数据（可能已被其他用户更新）
    print("\n📥 从 Hugging Face 下载最新数据...")
    hf_single = download_from_hf("leaderboard_single.json")
    hf_multi = download_from_hf("leaderboard_multi.json")

    # 3. 智能合并
    print("\n🔀 智能合并（解决并发冲突）...")
    print("\n  Single (单机):")
    merged_single = smart_merge(hf_single, user_single)

    print("\n  Multi (多机):")
    merged_multi = smart_merge(hf_multi, user_multi)

    # 4. 保存合并结果（覆盖用户提交的版本）
    print("\n💾 保存合并结果...")
    user_single_file.write_text(
        json.dumps(merged_single, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    user_multi_file.write_text(
        json.dumps(merged_multi, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  ✓ {user_single_file}")
    print(f"  ✓ {user_multi_file}")

    print("\n✅ 并发安全合并完成！")
    print("💡 下一步: 运行 upload_to_hf.py 上传到 Hugging Face")


if __name__ == "__main__":
    main()
