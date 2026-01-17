"""随机数据集实现。

生成随机 prompt 用于 Mock 测试，无需外部数据依赖。
支持字符级或近似 token 级长度控制。
"""

from __future__ import annotations

import random
import string
import uuid
from typing import Literal

from sagellm_benchmark.datasets.base import BenchmarkDataset
from sagellm_benchmark.types import BenchmarkRequest, WorkloadSpec

# 常用英文词汇表，用于生成更真实的随机 prompt
WORD_POOL = [
    "the",
    "be",
    "to",
    "of",
    "and",
    "a",
    "in",
    "that",
    "have",
    "I",
    "it",
    "for",
    "not",
    "on",
    "with",
    "he",
    "as",
    "you",
    "do",
    "at",
    "this",
    "but",
    "his",
    "by",
    "from",
    "they",
    "we",
    "say",
    "her",
    "she",
    "or",
    "an",
    "will",
    "my",
    "one",
    "all",
    "would",
    "there",
    "their",
    "what",
    "so",
    "up",
    "out",
    "if",
    "about",
    "who",
    "get",
    "which",
    "go",
    "me",
    "when",
    "make",
    "can",
    "like",
    "time",
    "no",
    "just",
    "him",
    "know",
    "take",
    "people",
    "into",
    "year",
    "your",
    "good",
    "some",
    "could",
    "them",
    "see",
    "other",
    "than",
    "then",
    "now",
    "look",
    "only",
    "come",
    "its",
    "over",
    "think",
    "also",
    "back",
    "after",
    "use",
    "two",
    "how",
    "our",
    "work",
    "first",
    "well",
    "way",
    "even",
    "new",
    "want",
    "because",
    "any",
    "these",
    "give",
    "day",
    "most",
    "us",
    # 技术词汇
    "AI",
    "model",
    "data",
    "system",
    "code",
    "function",
    "algorithm",
    "network",
    "machine",
    "learning",
    "deep",
    "neural",
    "transformer",
    "attention",
    "token",
    "embedding",
    "layer",
    "training",
    "inference",
    "batch",
    "optimize",
    "compute",
    "memory",
    "cache",
    "latency",
    "throughput",
    "performance",
    "benchmark",
    "test",
    "validate",
    "deploy",
    "scale",
    "parallel",
]

# 任务前缀，使 prompt 更真实
TASK_PREFIXES = [
    "Please explain",
    "Can you describe",
    "Write a detailed explanation of",
    "Tell me about",
    "I need help understanding",
    "Could you elaborate on",
    "Provide information about",
    "Summarize the concept of",
    "What are the key aspects of",
    "Help me learn about",
]

# 上下文模板
CONTEXT_TEMPLATES = [
    "In the context of {topic}, {details}",
    "Regarding {topic}: {details}",
    "About {topic}, consider the following: {details}",
    "When discussing {topic}, it's important to note that {details}",
    "The subject of {topic} involves {details}",
]

# 技术主题
TOPICS = [
    "large language models",
    "machine learning optimization",
    "distributed computing systems",
    "neural network architectures",
    "natural language processing",
    "computer vision applications",
    "reinforcement learning algorithms",
    "data preprocessing pipelines",
    "model inference optimization",
    "hardware acceleration techniques",
]


class RandomDataset(BenchmarkDataset):
    """随机数据集，生成随机 prompt 用于 Mock 测试。

    支持两种长度模式：
    - char: 字符级长度控制（精确）
    - token: 近似 token 级长度控制（1 token ≈ 4 chars）

    Example:
        >>> dataset = RandomDataset(seed=42, length_mode="token")
        >>> spec = WorkloadSpec(
        ...     name="test",
        ...     workload_type=WorkloadType.SHORT,
        ...     prompt_len=128,
        ...     output_len=64,
        ...     num_requests=5,
        ... )
        >>> requests = dataset.sample(spec)
        >>> len(requests)
        5
    """

    def __init__(
        self,
        seed: int | None = None,
        length_mode: Literal["char", "token"] = "token",
        realistic: bool = True,
    ) -> None:
        """初始化随机数据集。

        Args:
            seed: 随机种子，用于可复现性。None 表示不设种子。
            length_mode: 长度控制模式。
                - "char": 字符级（精确）
                - "token": token 级近似（1 token ≈ 4 chars）
            realistic: 是否生成更真实的 prompt（使用词汇表和模板）。
        """
        self._seed = seed
        self._length_mode = length_mode
        self._realistic = realistic
        self._rng = random.Random(seed)

    @property
    def name(self) -> str:
        return "random"

    def sample(self, spec: WorkloadSpec) -> list[BenchmarkRequest]:
        """根据 WorkloadSpec 生成随机请求列表。

        Args:
            spec: Workload 规格描述。

        Returns:
            包含 num_requests 个随机请求的列表。

        Raises:
            ValueError: 当规格参数无效时。
        """
        self.validate_spec(spec)

        requests = []
        for _ in range(spec.num_requests):
            prompt = self._generate_prompt(spec.prompt_len)
            request = BenchmarkRequest(
                prompt=prompt,
                max_tokens=spec.output_len,
                request_id=str(uuid.uuid4()),
                kv_budget_tokens=spec.kv_budget_tokens,
            )
            requests.append(request)

        return requests

    def _generate_prompt(self, target_len: int) -> str:
        """生成指定长度的随机 prompt。

        Args:
            target_len: 目标长度（根据 length_mode 解释）。

        Returns:
            生成的 prompt 字符串。
        """
        # 转换为字符长度
        if self._length_mode == "token":
            # 近似：1 token ≈ 4 chars（英文）
            target_chars = target_len * 4
        else:
            target_chars = target_len

        if self._realistic:
            return self._generate_realistic_prompt(target_chars)
        else:
            return self._generate_simple_prompt(target_chars)

    def _generate_simple_prompt(self, target_chars: int) -> str:
        """生成简单的随机字符串。

        Args:
            target_chars: 目标字符数。

        Returns:
            随机字符串。
        """
        chars = string.ascii_letters + string.digits + " "
        return "".join(self._rng.choices(chars, k=target_chars))

    def _generate_realistic_prompt(self, target_chars: int) -> str:
        """生成更真实的随机 prompt。

        使用词汇表和模板生成看起来更自然的 prompt。

        Args:
            target_chars: 目标字符数。

        Returns:
            生成的 prompt。
        """
        parts = []

        # 添加任务前缀
        prefix = self._rng.choice(TASK_PREFIXES)
        parts.append(prefix)

        # 选择主题
        topic = self._rng.choice(TOPICS)
        parts.append(topic)
        parts.append(".")

        # 添加上下文直到达到目标长度
        current_len = len(" ".join(parts))
        while current_len < target_chars:
            # 生成一个句子
            sentence_words = []
            sentence_len = self._rng.randint(8, 15)  # 每句 8-15 个词
            for _ in range(sentence_len):
                word = self._rng.choice(WORD_POOL)
                sentence_words.append(word)

            sentence = " ".join(sentence_words) + "."
            parts.append(sentence)
            current_len = len(" ".join(parts))

        # 组合并截断到目标长度（允许 ±10% 误差）
        result = " ".join(parts)
        min_len = int(target_chars * 0.9)
        max_len = int(target_chars * 1.1)

        if len(result) > max_len:
            result = result[:max_len]
            # 尝试在句号或空格处截断
            last_period = result.rfind(".")
            last_space = result.rfind(" ")
            if last_period > min_len:
                result = result[: last_period + 1]
            elif last_space > min_len:
                result = result[:last_space]

        return result

    def reset_seed(self, seed: int | None = None) -> None:
        """重置随机种子。

        Args:
            seed: 新的随机种子。None 表示使用原始种子。
        """
        if seed is None:
            seed = self._seed
        self._rng = random.Random(seed)
