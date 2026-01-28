#!/usr/bin/env python3
"""
聚合 outputs/ 目录下的所有 benchmark 结果，并与 HF 现有数据合并

关键逻辑：
1. 从 HF 下载现有的 leaderboard 数据
2. 加载本地 outputs/ 下的新结果
3. 基于配置 key 去重合并（选择性能较好的结果）
4. 保存到 hf_data/ 目录

运行方式：
    python scripts/aggregate_for_hf.py
    
HF 仓库：
    https://huggingface.co/datasets/wangyao36/sagellm-benchmark-results
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

# HF 配置
HF_REPO = "wangyao36/sagellm-benchmark-results"
HF_BRANCH = "main"


def download_from_hf(filename: str) -> list[dict]:
    """从 Hugging Face 下载现有数据"""
    url = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{HF_BRANCH}/{filename}"
    print(f"📥 下载 HF 数据: {url}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"  ✓ 下载成功: {len(data)} 条记录")
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  ⚠️ 文件不存在（首次上传）")
        else:
            print(f"  ⚠️ HTTP 错误 {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"  ⚠️ 下载失败: {e}")
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
        merged[config_key] = entry
    
    added = 0
    updated = 0
    skipped = 0
    
    for entry in new_results:
        config_key = get_config_key(entry)
        
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
    # 路径设置
    base_dir = Path(__file__).parent.parent
    outputs_dir = base_dir / "outputs"
    hf_output_dir = base_dir / "hf_data"

    # 创建输出目录
    hf_output_dir.mkdir(exist_ok=True)

    # Step 1: 从 HF 下载现有数据
    print(f"\n📡 从 Hugging Face 下载现有数据...")
    existing_single = download_from_hf("leaderboard_single.json")
    existing_multi = download_from_hf("leaderboard_multi.json")

    # Step 2: 加载本地新结果
    print(f"\n📂 从本地 {outputs_dir} 加载新结果...")
    if not outputs_dir.exists():
        print(f"  ⚠️ outputs 目录不存在，仅使用 HF 现有数据")
        local_results = []
    else:
        local_results = load_local_results(outputs_dir)
        print(f"  📊 加载了 {len(local_results)} 条本地结果")

    # Step 3: 分类本地结果
    if local_results:
        local_single_chip, local_multi_chip, local_multi_node = categorize_results(
            local_results
        )
        local_single = local_single_chip + local_multi_chip
    else:
        local_single = []
        local_multi_node = []

    # Step 4: 合并数据
    print(f"\n🔀 合并数据...")
    print(f"  Single (单机单卡+多卡):")
    merged_single = merge_results(existing_single, local_single)
    print(f"  Multi (多机多卡):")
    merged_multi = merge_results(existing_multi, local_multi_node)

    # Step 5: 保存到 JSON 文件
    single_file = hf_output_dir / "leaderboard_single.json"
    multi_file = hf_output_dir / "leaderboard_multi.json"

    with open(single_file, "w", encoding="utf-8") as f:
        json.dump(merged_single, f, indent=2, ensure_ascii=False)

    with open(multi_file, "w", encoding="utf-8") as f:
        json.dump(merged_multi, f, indent=2, ensure_ascii=False)

    # 统计信息
    print(f"\n✅ 聚合完成！")
    print(f"  📄 {single_file.name}: {len(merged_single)} 条")
    print(f"  📄 {multi_file.name}: {len(merged_multi)} 条")
    print(f"\n💡 下一步: 运行 scripts/upload_to_hf.py 上传到 HF")


if __name__ == "__main__":
    main()
