#!/usr/bin/env python3
"""
手动上传 Benchmark 结果到 Hugging Face（可选的高级功能）

⚠️ 注意：这是可选功能！推荐使用标准流程（aggregate → git push → Actions 自动上传）

适用场景：
- 核心团队成员有 HF_TOKEN，想立即上传
- 测试上传流程
- GitHub Actions 故障时的降级方案

标准流程（推荐）：
    sagellm-benchmark aggregate
    git add hf_data/ && git commit && git push
    # GitHub Actions 会自动上传

手动上传（本脚本）：
    export HF_TOKEN=hf_xxx
    python scripts/manual_upload.py

功能：
1. 从 HF 拉取最新数据（公开访问）
2. 与 hf_data/ 或 outputs/ 数据合并（并发安全）
3. 上传到 HF（需要 HF_TOKEN）
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# =============================================================================
# 配置
# =============================================================================

HF_REPO = "intellistream/sagellm-benchmark-results"
HF_BRANCH = "main"
# 支持 HF 镜像站（中国用户可设置 HF_ENDPOINT=https://hf-mirror.com）
HF_ENDPOINT = os.environ.get("HF_ENDPOINT", "https://huggingface.co")

# 路径
BASE_DIR = Path(__file__).parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
HF_DATA_DIR = BASE_DIR / "hf_data"


# =============================================================================
# Step 1: 从 HF 下载现有数据
# =============================================================================


def download_from_hf(filename: str) -> list[dict]:
    """从 Hugging Face 下载现有数据"""
    url = f"{HF_ENDPOINT}/datasets/{HF_REPO}/resolve/{HF_BRANCH}/{filename}"
    print(f"  📥 下载: {url}")

    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            print(f"     ✓ 成功: {len(data)} 条记录")
            return data
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"     ⚠️ 文件不存在（首次上传）")
        else:
            print(f"     ⚠️ HTTP 错误 {e.code}: {e.reason}")
        return []
    except Exception as e:
        print(f"     ⚠️ 下载失败: {e}")
        return []


# =============================================================================
# Step 2: 加载本地数据
# =============================================================================


def load_local_results() -> list[dict]:
    """递归加载 outputs 目录下的所有 leaderboard JSON 文件"""
    all_results = []

    if not OUTPUTS_DIR.exists():
        print(f"  ⚠️ outputs 目录不存在")
        return []

    for json_file in OUTPUTS_DIR.rglob("*_leaderboard.json"):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                all_results.append(data)
                print(f"  ✓ 加载: {json_file.relative_to(OUTPUTS_DIR)}")
        except Exception as e:
            print(f"  ✗ 加载失败: {json_file} - {e}")

    return all_results


# =============================================================================
# Step 3: 智能合并
# =============================================================================


def get_config_key(entry: dict) -> str:
    """生成配置唯一标识 key"""
    hw = entry.get("hardware", {})
    model = entry.get("model", {})
    workload = entry.get("workload", {})
    cluster = entry.get("cluster")

    parts = [
        hw.get("chip_model", "unknown"),
        str(hw.get("chip_count", 1)),
        model.get("name", "unknown"),
        model.get("precision", "FP16"),
        str(workload.get("input_length", 0)),
        str(workload.get("output_length", 0)),
    ]

    if cluster and cluster.get("node_count", 1) > 1:
        parts.append(f"nodes_{cluster['node_count']}")

    return "|".join(parts)


def is_better_result(new_entry: dict, existing_entry: dict) -> bool:
    """判断新结果是否比现有结果更好"""
    new_metrics = new_entry.get("metrics", {})
    old_metrics = existing_entry.get("metrics", {})

    # throughput 高更好
    new_tps = new_metrics.get("throughput_tps", 0)
    old_tps = old_metrics.get("throughput_tps", 0)
    if new_tps > old_tps * 1.05:
        return True
    if old_tps > new_tps * 1.05:
        return False

    # ttft 低更好
    new_ttft = new_metrics.get("ttft_ms", float("inf"))
    old_ttft = old_metrics.get("ttft_ms", float("inf"))
    if new_ttft < old_ttft * 0.95:
        return True
    if old_ttft < new_ttft * 0.95:
        return False

    # error_rate 低更好
    new_err = new_metrics.get("error_rate", 1)
    old_err = old_metrics.get("error_rate", 1)
    if new_err < old_err:
        return True

    return False


def merge_results(existing: list[dict], new_results: list[dict]) -> list[dict]:
    """合并现有数据和新数据"""
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
            merged[config_key] = entry
            added += 1
        else:
            if is_better_result(entry, merged[config_key]):
                merged[config_key] = entry
                updated += 1
            else:
                skipped += 1

    print(f"     📊 新增 {added}, 更新 {updated}, 跳过 {skipped}, 总计 {len(merged)}")
    return list(merged.values())


def categorize_results(results: list[dict]) -> tuple[list, list]:
    """将结果分类为单机和多机"""
    single = []
    multi = []

    for entry in results:
        cluster = entry.get("cluster")
        if cluster and cluster.get("node_count", 1) > 1:
            multi.append(entry)
        else:
            single.append(entry)

    return single, multi


# =============================================================================
# Step 4: 上传到 HF
# =============================================================================


def upload_to_hf(token: str) -> None:
    """上传文件到 Hugging Face"""
    try:
        from huggingface_hub import HfApi, login
    except ImportError:
        print("❌ 请先安装 huggingface_hub: pip install huggingface_hub")
        sys.exit(1)

    login(token=token)
    api = HfApi()

    # 确保 repo 存在
    try:
        api.repo_info(repo_id=HF_REPO, repo_type="dataset")
        print(f"  ✓ Repo 存在: {HF_REPO}")
    except Exception:
        print(f"  📦 创建 Repo: {HF_REPO}")
        api.create_repo(repo_id=HF_REPO, repo_type="dataset", private=False)

    # 上传文件
    files = [
        HF_DATA_DIR / "leaderboard_single.json",
        HF_DATA_DIR / "leaderboard_multi.json",
    ]

    for local_path in files:
        if not local_path.exists():
            print(f"  ⚠️ 文件不存在: {local_path}")
            continue

        print(f"  📤 上传: {local_path.name}")
        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=local_path.name,
            repo_id=HF_REPO,
            repo_type="dataset",
            commit_message=f"Update {local_path.name} - {datetime.now().isoformat()}",
        )
        print(f"     ✓ 完成")


# =============================================================================
# Main
# =============================================================================


def main():
    print("=" * 70)
    print("📦 sagellm-benchmark 手动上传到 Hugging Face（高级功能）")
    print("=" * 70)
    print("\n⚠️  提示: 推荐使用标准流程（aggregate → git push → Actions）")
    print("   只有在以下情况才需要手动上传:")
    print("   - 你有 HF_TOKEN 且想立即上传")
    print("   - 测试上传流程")
    print("   - GitHub Actions 故障时的降级方案\n")

    # 检查 token
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ 错误: HF_TOKEN 环境变量未设置")
        print("\n请设置 HF_TOKEN:")
        print("  export HF_TOKEN=hf_xxx")
        print("\n或者:")
        print("  HF_TOKEN=hf_xxx python scripts/manual_upload.py")
        print("\n💡 如果你没有 HF_TOKEN，请使用标准流程:")
        print("   1. sagellm-benchmark aggregate")
        print("   2. git add hf_data/ && git commit && git push")
        sys.exit(1)

    print(f"✅ HF_TOKEN 已设置")
    print(f"📍 HF 仓库: {HF_REPO}")

    # Step 1: 从 HF 拉取现有数据（并发安全）
    print("\n" + "-" * 70)
    print("Step 1: 从 Hugging Face 拉取最新数据（并发安全）")
    print("-" * 70)
    existing_single = download_from_hf("leaderboard_single.json")
    existing_multi = download_from_hf("leaderboard_multi.json")

    # Step 2: 优先使用 hf_data/，降级到 outputs/
    print("\n" + "-" * 70)
    print("Step 2: 加载本地数据")
    print("-" * 70)

    # 优先使用 hf_data/（如果已经运行过 aggregate）
    if HF_DATA_DIR.exists():
        single_file = HF_DATA_DIR / "leaderboard_single.json"
        multi_file = HF_DATA_DIR / "leaderboard_multi.json"

        if single_file.exists() and multi_file.exists():
            print("  ✓ 发现 hf_data/ 目录（优先使用）")
            with open(single_file, encoding="utf-8") as f:
                local_single = json.load(f)
            with open(multi_file, encoding="utf-8") as f:
                local_multi = json.load(f)
            print(f"  📊 Single: {len(local_single)} 条")
            print(f"  📊 Multi: {len(local_multi)} 条")
        else:
            print("  ⚠️  hf_data/ 存在但文件不完整，降级到 outputs/")
            local_results = load_local_results()
            local_single, local_multi = categorize_results(local_results)
    else:
        print("  📂 未找到 hf_data/，扫描 outputs/")
        local_results = load_local_results()
        print(f"  📊 共加载 {len(local_results)} 条本地结果")
        local_single, local_multi = categorize_results(local_results)

    if not local_single and not local_multi and not existing_single and not existing_multi:
        print("\n⚠️ 没有任何数据可上传")
        sys.exit(0)

    # Step 3: 智能合并（并发安全）
    print("\n" + "-" * 70)
    print("Step 3: 智能合并（并发安全，基于 HF 最新数据）")
    print("-" * 70)

    print(f"\n  Single (单机单卡+多卡):")
    merged_single = merge_results(existing_single, local_single)

    print(f"\n  Multi (多机多卡):")
    merged_multi = merge_results(existing_multi, local_multi)

    # 保存合并结果到本地
    HF_DATA_DIR.mkdir(exist_ok=True)

    single_file = HF_DATA_DIR / "leaderboard_single.json"
    multi_file = HF_DATA_DIR / "leaderboard_multi.json"

    with open(single_file, "w", encoding="utf-8") as f:
        json.dump(merged_single, f, indent=2, ensure_ascii=False)

    with open(multi_file, "w", encoding="utf-8") as f:
        json.dump(merged_multi, f, indent=2, ensure_ascii=False)

    print(f"\n  💾 已保存合并结果到 hf_data/")
    print(f"     - {single_file.name}: {len(merged_single)} 条")
    print(f"     - {multi_file.name}: {len(merged_multi)} 条")

    # Step 4: 上传到 HF
    print("\n" + "-" * 70)
    print("Step 4: 上传到 Hugging Face")
    print("-" * 70)
    upload_to_hf(token)

    # 完成
    print("\n" + "=" * 70)
    print("✅ 完成！")
    print(f"🔗 https://huggingface.co/datasets/{HF_REPO}")
    print("=" * 70)
    print("=" * 60)


if __name__ == "__main__":
    main()
