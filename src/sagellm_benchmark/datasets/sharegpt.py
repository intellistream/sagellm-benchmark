"""ShareGPT 数据集实现。

加载 ShareGPT 格式的对话数据集，用于真实场景 Benchmark。
支持从本地 JSON 文件或 HuggingFace Hub 加载。
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from pathlib import Path
from typing import Any

from sagellm_benchmark.datasets.base import BenchmarkDataset
from sagellm_benchmark.types import BenchmarkRequest, WorkloadSpec

logger = logging.getLogger(__name__)


class ShareGPTDataset(BenchmarkDataset):
    """ShareGPT 对话数据集。

    支持加载 ShareGPT 格式的 JSON 数据：
    [
        {
            "conversations": [
                {"from": "human", "value": "prompt text"},
                {"from": "gpt", "value": "response text"},
                ...
            ]
        },
        ...
    ]

    Example:
        >>> dataset = ShareGPTDataset.from_file("sharegpt.json")
        >>> spec = WorkloadSpec(
        ...     name="test",
        ...     workload_type=WorkloadType.SHORT,
        ...     prompt_len=128,
        ...     output_len=64,
        ...     num_requests=5,
        ... )
        >>> requests = dataset.sample(spec)
    """

    def __init__(
        self,
        data: list[dict[str, Any]],
        seed: int | None = None,
        min_prompt_len: int = 10,
        max_prompt_len: int = 10000,
    ) -> None:
        """初始化 ShareGPT 数据集。

        Args:
            data: ShareGPT 格式的对话数据列表。
            seed: 随机种子，用于可复现采样。
            min_prompt_len: 最小 prompt 长度（字符），过滤短样本。
            max_prompt_len: 最大 prompt 长度（字符），过滤超长样本。
        """
        self._raw_data = data
        self._seed = seed
        self._min_prompt_len = min_prompt_len
        self._max_prompt_len = max_prompt_len
        self._rng = random.Random(seed)

        # 预处理：提取 prompt
        self._prompts = self._extract_prompts(data)
        logger.info(
            f"ShareGPTDataset initialized with {len(self._prompts)} prompts "
            f"(filtered from {len(data)} conversations)"
        )

    @property
    def name(self) -> str:
        return "sharegpt"

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        seed: int | None = None,
        min_prompt_len: int = 10,
        max_prompt_len: int = 10000,
    ) -> ShareGPTDataset:
        """从 JSON 文件加载数据集。

        Args:
            path: JSON 文件路径。
            seed: 随机种子。
            min_prompt_len: 最小 prompt 长度。
            max_prompt_len: 最大 prompt 长度。

        Returns:
            加载的 ShareGPTDataset 实例。

        Raises:
            FileNotFoundError: 当文件不存在时。
            json.JSONDecodeError: 当 JSON 格式错误时。
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ShareGPT data file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Expected list, got {type(data)}")

        return cls(data, seed=seed, min_prompt_len=min_prompt_len, max_prompt_len=max_prompt_len)

    @classmethod
    def from_huggingface(
        cls,
        repo_id: str = "anon8231489123/ShareGPT_Vicuna_unfiltered",
        split: str = "train",
        seed: int | None = None,
        min_prompt_len: int = 10,
        max_prompt_len: int = 10000,
    ) -> ShareGPTDataset:
        """从 HuggingFace Hub 加载数据集。

        Args:
            repo_id: HuggingFace 数据集 ID。
            split: 数据集 split（如 "train"）。
            seed: 随机种子。
            min_prompt_len: 最小 prompt 长度。
            max_prompt_len: 最大 prompt 长度。

        Returns:
            加载的 ShareGPTDataset 实例。

        Raises:
            ImportError: 当 datasets 库未安装时。
        """
        try:
            from datasets import load_dataset
        except ImportError as e:
            raise ImportError(
                "datasets library required for HuggingFace loading. "
                "Install with: pip install datasets"
            ) from e

        logger.info(f"Loading ShareGPT from HuggingFace: {repo_id}")
        hf_dataset = load_dataset(repo_id, split=split)

        # 转换为列表
        data = list(hf_dataset)
        return cls(data, seed=seed, min_prompt_len=min_prompt_len, max_prompt_len=max_prompt_len)

    @classmethod
    def from_modelscope(
        cls,
        dataset_id: str = "AI-ModelScope/ShareGPT-Chinese-English-90k",
        split: str = "train",
        seed: int | None = None,
        min_prompt_len: int = 10,
        max_prompt_len: int = 10000,
    ) -> ShareGPTDataset:
        """从 ModelScope 加载数据集（支持中文 ShareGPT）。

        Args:
            dataset_id: ModelScope 数据集 ID。
            split: 数据集 split（如 "train"）。
            seed: 随机种子。
            min_prompt_len: 最小 prompt 长度。
            max_prompt_len: 最大 prompt 长度。

        Returns:
            加载的 ShareGPTDataset 实例。

        Raises:
            ImportError: 当 modelscope 库未安装时。

        Example:
            >>> # 加载中英文 ShareGPT 数据集
            >>> dataset = ShareGPTDataset.from_modelscope(
            ...     dataset_id="AI-ModelScope/ShareGPT-Chinese-English-90k"
            ... )
        """
        try:
            from modelscope.msdatasets import MsDataset
        except ImportError as e:
            raise ImportError(
                "modelscope library required for ModelScope loading. "
                "Install with: pip install modelscope"
            ) from e

        logger.info(f"Loading ShareGPT from ModelScope: {dataset_id}")
        ms_dataset = MsDataset.load(dataset_id, split=split)

        # 转换为列表
        data = list(ms_dataset)
        logger.info(f"Loaded {len(data)} conversations from ModelScope")
        
        return cls(data, seed=seed, min_prompt_len=min_prompt_len, max_prompt_len=max_prompt_len)

    def _extract_prompts(self, data: list[dict[str, Any]]) -> list[str]:
        """从 ShareGPT 数据中提取 prompt。

        Args:
            data: ShareGPT 格式的对话列表。

        Returns:
            过滤后的 prompt 列表。
        """
        prompts = []
        for item in data:
            conversations = item.get("conversations", [])
            if not conversations:
                continue

            # 取第一个 human turn 作为 prompt
            for turn in conversations:
                if turn.get("from") == "human":
                    prompt = turn.get("value", "")
                    # 长度过滤
                    if self._min_prompt_len <= len(prompt) <= self._max_prompt_len:
                        prompts.append(prompt)
                    break

        return prompts

    def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        """根据 WorkloadSpec 采样请求。

        Args:
            spec: Workload 规格描述。

        Returns:
            采样的 BenchmarkRequest 列表。

        Raises:
            ValueError: 当规格参数无效或数据集为空时。
        """
        self.validate_spec(spec)

        if not self._prompts:
            raise ValueError("ShareGPT dataset is empty after filtering")

        # 目标字符长度（近似 token）
        target_chars = spec.prompt_len * 4  # 1 token ≈ 4 chars
        tolerance = 0.3  # 允许 ±30% 误差

        # 查找长度匹配的 prompt
        candidates = []
        for prompt in self._prompts:
            prompt_len = len(prompt)
            min_len = target_chars * (1 - tolerance)
            max_len = target_chars * (1 + tolerance)
            if min_len <= prompt_len <= max_len:
                candidates.append(prompt)

        # 如果没有严格匹配，使用所有 prompt
        if not candidates:
            logger.warning(
                f"No prompts found matching length ~{target_chars} chars, "
                f"using all {len(self._prompts)} prompts"
            )
            candidates = self._prompts

        # 采样
        requests = []
        for _ in range(spec.num_requests):
            prompt = self._rng.choice(candidates)
            # 截断到目标长度
            if len(prompt) > target_chars * 1.1:
                prompt = prompt[: int(target_chars)]
                # 在空格处截断
                last_space = prompt.rfind(" ")
                if last_space > target_chars * 0.5:
                    prompt = prompt[:last_space]

            request = BenchmarkRequest(
                prompt=prompt,
                max_tokens=spec.output_len,
                request_id=str(uuid.uuid4()),
                kv_budget_tokens=spec.kv_budget_tokens,
            )
            requests.append(request)

        return requests

    def __len__(self) -> int:
        """返回数据集中的 prompt 数量。"""
        return len(self._prompts)

    def reset_seed(self, seed: int | None = None) -> None:
        """重置随机种子。

        Args:
            seed: 新的随机种子。None 表示使用原始种子。
        """
        if seed is None:
            seed = self._seed
        self._rng = random.Random(seed)


class SyntheticShareGPTDataset(BenchmarkDataset):
    """Synthetic ShareGPT 数据集，用于无外部数据时的测试。

    生成模拟 ShareGPT 风格的 prompt（问答形式）。

    Example:
        >>> dataset = SyntheticShareGPTDataset(seed=42)
        >>> requests = dataset.sample(spec)
    """

    # 模拟问题模板
    QUESTION_TEMPLATES = [
        "What is {}?",
        "How does {} work?",
        "Can you explain {}?",
        "Tell me about {}",
        "What are the benefits of {}?",
        "What is the difference between {} and {}?",
        "How can I learn more about {}?",
        "What are some examples of {}?",
        "Why is {} important?",
        "How do you use {}?",
    ]

    TOPICS = [
        "machine learning",
        "neural networks",
        "natural language processing",
        "computer vision",
        "reinforcement learning",
        "deep learning",
        "data science",
        "artificial intelligence",
        "Python programming",
        "software engineering",
        "cloud computing",
        "distributed systems",
        "database design",
        "API development",
        "web development",
    ]

    def __init__(self, seed: int | None = None) -> None:
        """初始化 Synthetic ShareGPT 数据集。

        Args:
            seed: 随机种子。
        """
        self._seed = seed
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "synthetic_sharegpt"

    def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        """生成 ShareGPT 风格的请求。

        Args:
            spec: Workload 规格描述。

        Returns:
            模拟的 BenchmarkRequest 列表。
        """
        self.validate_spec(spec)

        target_chars = spec.prompt_len * 4
        requests = []

        for _ in range(spec.num_requests):
            prompt = self._generate_prompt(target_chars)
            request = BenchmarkRequest(
                prompt=prompt,
                max_tokens=spec.output_len,
                request_id=str(uuid.uuid4()),
                kv_budget_tokens=spec.kv_budget_tokens,
            )
            requests.append(request)

        return requests

    def _generate_prompt(self, target_chars: int) -> str:
        """生成问答 prompt。

        Args:
            target_chars: 目标字符数。

        Returns:
            生成的 prompt。
        """
        parts = []
        current_len = 0

        while current_len < target_chars:
            template = self._rng.choice(self.QUESTION_TEMPLATES)
            topic1 = self._rng.choice(self.TOPICS)
            topic2 = self._rng.choice(self.TOPICS)

            if "{}" in template:
                if template.count("{}") == 2:
                    question = template.format(topic1, topic2)
                else:
                    question = template.format(topic1)
            else:
                question = template

            parts.append(question)
            current_len = len(" ".join(parts))

        result = " ".join(parts)
        if len(result) > target_chars * 1.1:
            result = result[: int(target_chars)]

        return result

    def reset_seed(self, seed: int | None = None) -> None:
        """重置随机种子。"""
        if seed is None:
            seed = self._seed
        self._rng = random.Random(seed)
