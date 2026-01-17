"""Abstract base class for benchmark clients.

This module defines the BenchmarkClient interface that all backend implementations
must follow. It provides:
- Single request execution: generate()
- Batch execution: generate_batch() with concurrent/sequential modes
- Health check: health_check()

All implementations must return BenchmarkResult with complete Metrics.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sagellm_benchmark.types import BenchmarkRequest, BenchmarkResult

logger = logging.getLogger(__name__)


class BenchmarkClient(ABC):
    """Abstract base class for benchmark clients.

    All backend implementations (Mock, OpenAI, vLLM, LMDeploy, etc.) must
    inherit from this class and implement the abstract methods.

    The client is responsible for:
    1. Converting BenchmarkRequest to backend-specific format
    2. Executing the request on the backend
    3. Collecting metrics (TTFT, TBT, throughput, etc.)
    4. Converting response to BenchmarkResult with Protocol Metrics

    Attributes:
        name: Client name for logging.
        timeout: Default timeout for requests (seconds).
    """

    def __init__(self, name: str = "base", timeout: float = 60.0) -> None:
        """Initialize client.

        Args:
            name: Client name for logging.
            timeout: Default timeout for requests (seconds).
        """
        self.name = name
        self.timeout = timeout
        logger.info(f"Initialized {self.name} client (timeout={timeout}s)")

    @abstractmethod
    async def generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Execute a single request.

        Args:
            request: Benchmark request.

        Returns:
            Benchmark result with complete metrics.

        Raises:
            TimeoutError: If request exceeds timeout.
            Exception: Backend-specific errors.
        """
        pass

    async def generate_batch(
        self,
        requests: list[BenchmarkRequest],
        concurrent: bool = False,
        timeout: float | None = None,
    ) -> list[BenchmarkResult]:
        """Execute a batch of requests.

        Args:
            requests: List of benchmark requests.
            concurrent: If True, execute concurrently. If False, sequential.
            timeout: Timeout for each request (uses self.timeout if None).

        Returns:
            List of benchmark results in the same order as input.

        Note:
            - Result order is preserved (same as input order)
            - Failed requests have success=False and error message
            - Timeout errors are caught and recorded in error field
        """
        if not requests:
            return []

        effective_timeout = timeout if timeout is not None else self.timeout
        original_timeout = self.timeout
        self.timeout = effective_timeout

        try:
            if concurrent:
                logger.info(f"Running {len(requests)} requests concurrently")
                results = await self._run_concurrent(requests)
            else:
                logger.info(f"Running {len(requests)} requests sequentially")
                results = await self._run_sequential(requests)

            return results
        finally:
            self.timeout = original_timeout

    async def _run_concurrent(self, requests: list[BenchmarkRequest]) -> list[BenchmarkResult]:
        """Run requests concurrently with asyncio.gather.

        Args:
            requests: List of requests.

        Returns:
            Results in the same order as input.
        """
        tasks = [self._safe_generate(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    async def _run_sequential(self, requests: list[BenchmarkRequest]) -> list[BenchmarkResult]:
        """Run requests sequentially.

        Args:
            requests: List of requests.

        Returns:
            Results in the same order as input.
        """
        results = []
        for req in requests:
            result = await self._safe_generate(req)
            results.append(result)
        return results

    async def _safe_generate(self, request: BenchmarkRequest) -> BenchmarkResult:
        """Safely execute a request with error handling.

        Args:
            request: Benchmark request.

        Returns:
            BenchmarkResult (success=False if error occurs).
        """
        try:
            # Add timeout wrapper
            result = await asyncio.wait_for(self.generate(request), timeout=self.timeout)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Request {request.request_id} timed out after {self.timeout}s")
            # Import here to avoid circular dependency
            from sagellm_benchmark.types import BenchmarkResult

            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=f"Timeout after {self.timeout}s",
                metrics=None,
            )
        except Exception as e:
            logger.error(f"Request {request.request_id} failed: {e}", exc_info=True)
            from sagellm_benchmark.types import BenchmarkResult

            return BenchmarkResult(
                request_id=request.request_id,
                success=False,
                error=str(e),
                metrics=None,
            )

    async def health_check(self) -> bool:
        """Check if backend is healthy.

        Returns:
            True if backend is reachable and healthy, False otherwise.

        Note:
            Default implementation returns True. Override for real backends.
        """
        logger.info(f"{self.name} health check (default=True)")
        return True

    async def close(self) -> None:
        """Close client and cleanup resources.

        Override this method if your client needs cleanup (e.g., close HTTP session).
        """
        logger.info(f"Closing {self.name} client")
        pass
