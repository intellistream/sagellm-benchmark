#!/usr/bin/env python3
"""示例：使用 HuggingFace ShareGPT 数据集进行 Benchmark。

使用方法：
    python examples/use_huggingface_sharegpt.py
"""

from __future__ import annotations

import asyncio
import logging

from sagellm_benchmark.datasets import ShareGPTDataset
from sagellm_benchmark.types import WorkloadSpec, WorkloadType
from sagellm_core import create_backend, create_engine
from sagellm_core.config import BackendConfig, EngineConfig
from sagellm_protocol import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """使用 HuggingFace ShareGPT 数据集测试推理。"""

    # 1. 加载 HuggingFace ShareGPT 数据集
    logger.info("Loading ShareGPT dataset from HuggingFace...")
    dataset = ShareGPTDataset.from_huggingface(
        repo_id="anon8231489123/ShareGPT_Vicuna_unfiltered",
        split="train[:100]",  # 只加载前 100 条，加快速度
        min_prompt_len=50,
        max_prompt_len=5000,
        seed=42,
    )

    logger.info(f"Dataset loaded: {len(dataset)} prompts")

    # 2. 定义 Workload 规格
    spec = WorkloadSpec(
        name="sharegpt_short",
        workload_type=WorkloadType.SHORT,
        prompt_len=128,      # 目标 prompt 长度（tokens）
        output_len=128,      # 生成长度
        num_requests=3,      # 采样 3 个请求
        kv_budget_tokens=None,
    )

    # 3. 从数据集采样请求
    logger.info(f"Sampling {spec.num_requests} requests...")
    benchmark_requests = dataset.sample(spec)

    for i, req in enumerate(benchmark_requests, 1):
        logger.info(f"Request {i} prompt preview: {req.prompt[:100]}...")

    # 4. 创建引擎（使用 CPU）
    logger.info("Creating CPU engine...")
    backend_config = BackendConfig(kind="cpu", device="cpu")
    backend_provider = create_backend(backend_config)

    engine_config = EngineConfig(
        kind="cpu",
        model="gpt2",
        model_path="gpt2",
        device="cpu",
    )
    engine = create_engine(engine_config, backend_provider)

    await engine.start()
    logger.info("Engine started")

    # 5. 执行推理
    logger.info("Running inference...")
    for i, bench_req in enumerate(benchmark_requests, 1):
        # 转换为 Protocol Request
        request = Request(
            request_id=bench_req.request_id,
            trace_id=f"sharegpt-{spec.name}",
            model="gpt2",
            prompt=bench_req.prompt,
            max_tokens=bench_req.max_tokens,
            temperature=None,
            stream=False,
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Request {i}/{len(benchmark_requests)}")
        logger.info(f"Prompt length: {len(bench_req.prompt)} chars")

        response = await engine.execute(request)

        logger.info(f"TTFT: {response.metrics.ttft_ms:.2f} ms")
        logger.info(f"Throughput: {response.metrics.throughput_tps:.2f} tokens/s")
        logger.info(f"Output preview: {response.output_text[:200]}...")

    # 6. 停止引擎
    await engine.stop()
    logger.info("\nBenchmark completed!")


if __name__ == "__main__":
    asyncio.run(main())
