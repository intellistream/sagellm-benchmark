"""Multi-engine runner for cross-backend performance comparison.

This module provides:
- EngineType: Enumeration of supported inference backends.
- EngineInfo: Metadata about a configured engine for comparison.
- MultiEngineRunner: Run the same workload across multiple backends
  and collect per-engine AggregatedMetrics for comparison reporting.

Example::

    from sagellm_benchmark.clients.multi_engine import EngineType, EngineInfo, MultiEngineRunner
    from sagellm_benchmark.clients.openai_client import GatewayClient

    sagellm_engine = EngineInfo(
        engine_type=EngineType.SAGELLM,
        label="SageLLM-CPU",
        client=GatewayClient(base_url="http://localhost:8000", model="Qwen2-7B"),
    )

    runner = MultiEngineRunner(engines=[sagellm_engine])
    results = await runner.run_workload(workload_config, requests)

    from sagellm_benchmark.reporters import HTMLReporter
    html = HTMLReporter.generate_multi(
        runs=[r.metrics for r in results],
        labels=[r.engine_label for r in results],
    )
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sagellm_benchmark.clients.base import BenchmarkClient
    from sagellm_benchmark.types import AggregatedMetrics, BenchmarkRequest
    from sagellm_benchmark.workloads import WorkloadConfig

logger = logging.getLogger(__name__)


class EngineType(StrEnum):
    """Supported LLM inference backends.

    Attributes:
        SAGELLM: Native sagellm backend (CPU/CUDA via sagellm-core).
        OPENAI: OpenAI-compatible HTTP API.
        VLLM: vLLM inference engine.
        LMDEPLOY: LMDeploy inference engine.
        TENSORRT_LLM: NVIDIA TensorRT-LLM engine.
        ASCEND: Huawei Ascend NPU backend.
        SIMULATED: Simulated backend for testing.
    """

    SAGELLM = "sagellm"
    OPENAI = "openai"
    VLLM = "vllm"
    LMDEPLOY = "lmdeploy"
    TENSORRT_LLM = "tensorrt_llm"
    ASCEND = "ascend"
    SIMULATED = "simulated"


@dataclass
class EngineInfo:
    """Configuration and metadata for a single engine under test.

    Attributes:
        engine_type: Backend type identifier.
        client: The benchmark client instance for this engine.
        label: Human-readable label for reports (defaults to engine_type).
        tags: Optional key-value metadata (model name, hardware, version, etc.).
    """

    engine_type: EngineType
    client: BenchmarkClient
    label: str = ""
    tags: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label:
            self.label = str(self.engine_type)


@dataclass
class EngineRunResult:
    """Result of running a workload on a single engine.

    Attributes:
        engine_info: Engine metadata.
        engine_label: Convenience alias for engine_info.label.
        metrics: Aggregated performance metrics.
        error: Error message if the run failed (None on success).
        wall_time_s: Total wall-clock time for the run in seconds.
    """

    engine_info: EngineInfo
    engine_label: str
    metrics: AggregatedMetrics
    error: str | None = None
    wall_time_s: float = 0.0

    @property
    def success(self) -> bool:
        """True if the run completed without a fatal error."""
        return self.error is None


class MultiEngineRunner:
    """Run benchmark workloads across multiple inference backends.

    Runs the identical set of requests on each registered engine sequentially,
    collects ``AggregatedMetrics`` per engine, and returns a list of
    ``EngineRunResult`` objects ready for comparison reporting.

    Args:
        engines: List of engines to benchmark.
        warmup_requests: Number of warmup requests to discard before measurement.
    """

    def __init__(
        self,
        engines: list[EngineInfo],
        warmup_requests: int = 0,
    ) -> None:
        if not engines:
            raise ValueError("At least one engine is required")
        self.engines = engines
        self.warmup_requests = warmup_requests
        logger.info(
            f"MultiEngineRunner initialized with {len(engines)} engine(s): "
            + ", ".join(e.label for e in engines)
        )

    async def run_workload(
        self,
        workload: WorkloadConfig,
        requests: list[BenchmarkRequest],
    ) -> list[EngineRunResult]:
        """Run a workload on all registered engines.

        Each engine receives the same ``requests`` list. Warmup requests are
        sent before measurement starts. Results are returned in engine
        registration order.

        Args:
            workload: Workload configuration (used for logging and warmup).
            requests: Pre-generated benchmark requests.

        Returns:
            List of EngineRunResult, one per engine.
        """
        results: list[EngineRunResult] = []
        for engine in self.engines:
            result = await self._run_single_engine(engine, workload, requests)
            results.append(result)
        return results

    async def _run_single_engine(
        self,
        engine: EngineInfo,
        workload: WorkloadConfig,
        requests: list[BenchmarkRequest],
    ) -> EngineRunResult:
        """Run workload on one engine and aggregate metrics."""
        from sagellm_benchmark.metrics.aggregator import MetricsAggregator

        label = engine.label
        logger.info(f"[{label}] Starting benchmark — {len(requests)} request(s)")

        # ---- warmup ----
        warmup_n = getattr(workload, "warmup_rounds", self.warmup_requests)
        if warmup_n > 0 and requests:
            warmup_reqs = requests[:warmup_n]
            logger.info(f"[{label}] Warming up with {len(warmup_reqs)} request(s)")
            try:
                await engine.client.generate_batch(warmup_reqs, concurrent=False)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[{label}] Warmup failed (ignored): {exc}")

        # ---- measurement ----
        t0 = time.perf_counter()
        try:
            concurrent = getattr(workload, "concurrent", False)
            raw_results = await engine.client.generate_batch(requests, concurrent=concurrent)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[{label}] Run failed: {exc}")
            # Return a zero-metric placeholder so comparison still works
            metrics = MetricsAggregator.aggregate([])
            return EngineRunResult(
                engine_info=engine,
                engine_label=label,
                metrics=metrics,
                error=str(exc),
                wall_time_s=time.perf_counter() - t0,
            )

        wall_time = time.perf_counter() - t0

        # ---- aggregate ----
        metrics = MetricsAggregator.aggregate(raw_results)
        logger.info(
            f"[{label}] Done — "
            f"throughput={metrics.output_throughput_tps:.1f} tok/s, "
            f"p99_ttft={metrics.p99_ttft_ms:.1f} ms, "
            f"wall={wall_time:.1f}s"
        )
        # Mark as failed if all requests failed
        run_error: str | None = None
        if requests and metrics.error_rate >= 1.0:
            run_error = f"All {metrics.failed_requests} request(s) failed (error_rate=1.0)"
            logger.error(f"[{label}] {run_error}")
        return EngineRunResult(
            engine_info=engine,
            engine_label=label,
            metrics=metrics,
            error=run_error,
            wall_time_s=wall_time,
        )

    def run_workload_sync(
        self,
        workload: WorkloadConfig,
        requests: list[BenchmarkRequest],
    ) -> list[EngineRunResult]:
        """Synchronous wrapper around :meth:`run_workload`.

        Args:
            workload: Workload configuration.
            requests: Pre-generated benchmark requests.

        Returns:
            List of EngineRunResult.
        """
        return asyncio.get_event_loop().run_until_complete(self.run_workload(workload, requests))
