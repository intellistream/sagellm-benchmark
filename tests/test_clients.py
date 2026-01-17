"""Tests for benchmark clients."""

from __future__ import annotations

import pytest

from sagellm_benchmark.clients import BenchmarkClient, MockClient
from sagellm_benchmark.types import BenchmarkRequest


@pytest.fixture
def sample_request() -> BenchmarkRequest:
    """Create a sample benchmark request."""
    return BenchmarkRequest(
        prompt="What is the capital of France?",
        max_tokens=50,
        request_id="test-001",
        model="mock-model",
        temperature=0.7,
        top_p=0.9,
    )


@pytest.fixture
def batch_requests() -> list[BenchmarkRequest]:
    """Create a batch of benchmark requests."""
    return [
        BenchmarkRequest(
            prompt=f"Question {i}",
            max_tokens=20,
            request_id=f"test-{i:03d}",
            model="mock-model",
        )
        for i in range(5)
    ]


class TestMockClient:
    """Tests for MockClient."""

    @pytest.mark.asyncio
    async def test_single_request(self, sample_request: BenchmarkRequest) -> None:
        """Test single request execution."""
        client = MockClient(ttft_ms=10.0, tbt_ms=5.0, throughput_tps=100.0)

        result = await client.generate(sample_request)

        assert result.success
        assert result.error is None
        assert result.request_id == sample_request.request_id
        assert result.metrics is not None
        assert result.metrics.ttft_ms == 10.0
        assert result.metrics.tbt_ms == 5.0
        assert result.output_tokens == sample_request.max_tokens

    @pytest.mark.asyncio
    async def test_sequential_batch(self, batch_requests: list[BenchmarkRequest]) -> None:
        """Test sequential batch execution."""
        client = MockClient(ttft_ms=5.0, tbt_ms=2.0)

        results = await client.generate_batch(batch_requests, concurrent=False)

        assert len(results) == len(batch_requests)
        for i, result in enumerate(results):
            assert result.request_id == batch_requests[i].request_id
            assert result.success

    @pytest.mark.asyncio
    async def test_concurrent_batch(self, batch_requests: list[BenchmarkRequest]) -> None:
        """Test concurrent batch execution."""
        client = MockClient(ttft_ms=5.0, tbt_ms=2.0)

        results = await client.generate_batch(batch_requests, concurrent=True)

        assert len(results) == len(batch_requests)
        # Verify order preservation
        for i, result in enumerate(results):
            assert result.request_id == batch_requests[i].request_id
            assert result.success

    @pytest.mark.asyncio
    async def test_error_simulation(self) -> None:
        """Test error simulation."""
        client = MockClient(error_rate=1.0)  # 100% failure rate

        request = BenchmarkRequest(
            prompt="Test",
            max_tokens=10,
            request_id="error-test",
        )

        result = await client.generate(request)

        assert not result.success
        assert result.error is not None
        assert "Simulated failure" in result.error

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """Test timeout handling."""
        # Create a very slow client with short timeout
        client = MockClient(ttft_ms=1000.0, tbt_ms=1000.0, timeout=0.1)

        request = BenchmarkRequest(
            prompt="Test",
            max_tokens=100,
            request_id="timeout-test",
        )

        result = await client.generate(request)

        assert not result.success
        assert result.error is not None
        assert "Timeout" in result.error

    @pytest.mark.asyncio
    async def test_health_check(self) -> None:
        """Test health check."""
        client = MockClient()

        is_healthy = await client.health_check()

        assert is_healthy


class TestBenchmarkClientInterface:
    """Tests for BenchmarkClient abstract interface."""

    def test_cannot_instantiate_abstract(self) -> None:
        """Test that abstract class cannot be instantiated."""
        with pytest.raises(TypeError):
            BenchmarkClient()  # type: ignore

    @pytest.mark.asyncio
    async def test_custom_client_implementation(self) -> None:
        """Test custom client implementation."""

        class CustomClient(BenchmarkClient):
            async def generate(self, request: BenchmarkRequest) -> BenchmarkRequest:  # type: ignore
                from sagellm_protocol import Metrics

                from sagellm_benchmark.types import BenchmarkResult

                return BenchmarkResult(
                    request_id=request.request_id,
                    success=True,
                    error=None,
                    metrics=Metrics(
                        ttft_ms=1.0,
                        tbt_ms=1.0,
                        tpot_ms=1.0,
                        throughput_tps=1.0,
                        peak_mem_mb=0,
                        error_rate=0.0,
                        kv_used_tokens=0,
                        kv_used_bytes=0,
                        prefix_hit_rate=0.0,
                        evict_count=0,
                        evict_ms=0.0,
                        spec_accept_rate=0.0,
                    ),
                )

        client = CustomClient(name="custom")

        request = BenchmarkRequest(
            prompt="Test",
            max_tokens=10,
            request_id="custom-001",
        )

        result = await client.generate(request)

        assert result.success
        assert result.request_id == "custom-001"


@pytest.mark.asyncio
async def test_batch_order_preservation() -> None:
    """Test that batch results preserve input order."""
    client = MockClient()

    requests = [
        BenchmarkRequest(
            prompt=f"Request {i}",
            max_tokens=10,
            request_id=f"order-{i:03d}",
        )
        for i in range(10)
    ]

    # Test both modes
    for concurrent in [True, False]:
        results = await client.generate_batch(requests, concurrent=concurrent)

        assert len(results) == len(requests)
        for i, result in enumerate(results):
            assert result.request_id == f"order-{i:03d}"


@pytest.mark.asyncio
async def test_batch_partial_failure() -> None:
    """Test batch execution with partial failures."""
    # 50% failure rate
    client = MockClient(error_rate=0.5)

    requests = [
        BenchmarkRequest(
            prompt=f"Request {i}",
            max_tokens=10,
            request_id=f"partial-{i:03d}",
        )
        for i in range(20)
    ]

    results = await client.generate_batch(requests, concurrent=True)

    assert len(results) == len(requests)

    successes = sum(1 for r in results if r.success)
    failures = sum(1 for r in results if not r.success)

    # With 50% error rate, expect roughly half to fail
    assert failures > 0
    assert successes > 0
    assert successes + failures == len(requests)
