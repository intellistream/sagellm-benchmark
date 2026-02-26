#!/usr/bin/env python3
"""
上传聚合后的 benchmark 结果到 Hugging Face Datasets Hub

运行方式：
    HF_TOKEN=hf_xxx python scripts/upload_to_hf.py
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from huggingface_hub import HfApi

# 配置
HF_REPO = "intellistream/sagellm-benchmark-results"
HF_DATA_DIR = Path(__file__).parent.parent / "hf_data"


def ensure_repo_exists(api: HfApi, repo_id: str) -> None:
    """确保 HF repo 存在，不存在则创建"""
    try:
        api.repo_info(repo_id=repo_id, repo_type="dataset")
        print(f"✓ Repo exists: {repo_id}")
    except Exception:
        print(f"📦 Creating repo: {repo_id}")
        api.create_repo(repo_id=repo_id, repo_type="dataset", private=False)
        print(f"✓ Created: {repo_id}")


def upload_files(api: HfApi, repo_id: str, files: list[Path]) -> None:
    """上传文件列表到 HF"""
    for local_path in files:
        if not local_path.exists():
            print(f"⚠️  File not found: {local_path}")
            continue

        remote_path = local_path.name
        print(f"📤 Uploading: {local_path.name} -> {remote_path}")

        api.upload_file(
            path_or_fileobj=str(local_path),
            path_in_repo=remote_path,
            repo_id=repo_id,
            repo_type="dataset",
            commit_message=f"Update {remote_path} - {datetime.now().isoformat()}",
        )
        print(f"✓ Uploaded: {remote_path}")


def main() -> None:
    # 检查 token
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("❌ HF_TOKEN 环境变量未设置")
        exit(1)

    # 配置 HF endpoint（默认使用官方地址）
    hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
    print(f"📡 Using HF endpoint: {hf_endpoint}")

    # 设置环境变量（huggingface_hub 会读取）
    os.environ["HF_ENDPOINT"] = hf_endpoint

    # 初始化 API（使用配置的 endpoint）
    api = HfApi(endpoint=hf_endpoint, token=token)

    # 确保 repo 存在
    ensure_repo_exists(api, HF_REPO)

    # 要上传的文件
    files_to_upload = [
        HF_DATA_DIR / "leaderboard_single.json",
        HF_DATA_DIR / "leaderboard_multi.json",
    ]

    # 检查文件是否存在
    if not HF_DATA_DIR.exists():
        print(f"❌ hf_data 目录不存在: {HF_DATA_DIR}")
        print("💡 请先运行 scripts/aggregate_for_hf.py")
        exit(1)

    # 上传
    print(f"\n📂 Uploading to: {HF_REPO}")
    upload_files(api, HF_REPO, files_to_upload)

    print("\n✅ Upload complete!")
    print(f"🔗 View at: https://huggingface.co/datasets/{HF_REPO}")


if __name__ == "__main__":
    main()
