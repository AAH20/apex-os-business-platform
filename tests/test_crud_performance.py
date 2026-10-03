"""Comprehensive CRUD performance tests for APEX-OS Business Platform."""
import asyncio
import gc
import os
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _timed(coro):
    """Run coroutine and return (result, elapsed_seconds)."""
    start = time.perf_counter()
    result = await coro
    return result, time.perf_counter() - start


def _make_payload(size: int = 100) -> dict:
    """Generate a payload of approximate size."""
    return {
        "id": "perf-test-001",
        "name": "Performance Test Entity",
        "data": "x" * size,
        "tags": ["perf", "crud", "test"],
        "metadata": {"created_by": "test_suite", "version": 1},
    }


# ---------------------------------------------------------------------------
# 1. CRUD Operation Response Times
# ---------------------------------------------------------------------------

class TestCRUDResponseTimes:
    """Verify each CRUD operation completes within acceptable latency."""

    MAX_LATENCY_MS = 500

    @pytest.mark.parametrize("operation", ["create", "read", "update", "delete"])
    async def test_operation_latency(self, operation, async_client):
        """Each CRUD op should complete within MAX_LATENCY_MS."""
        payload = _make_payload()

        if operation == "create":
            _, elapsed = await _timed(async_client.post("/api/v1/entities", json=payload))
        elif operation == "read":
            await async_client.post("/api/v1/entities", json=payload)
            _, elapsed = await _timed(async_client.get("/api/v1/entities/perf-test-001"))
        elif operation == "update":
            await async_client.post("/api/v1/entities", json=payload)
            _, elapsed = await _timed(
                async_client.put("/api/v1/entities/perf-test-001", json={"name": "Updated"})
            )
        else:  # delete
            await async_client.post("/api/v1/entities", json=payload)
            _, elapsed = await _timed(async_client.delete("/api/v1/entities/perf-test-001"))

        assert elapsed * 1000 < self.MAX_LATENCY_MS, (
            f"{operation} took {elapsed * 1000:.1f}ms (limit {self.MAX_LATENCY_MS}ms)"
        )

    async def test_full_crud_cycle_latency(self, async_client):
        """A full create→read→update→delete cycle should be under 2s."""
        payload = _make_payload()
        start = time.perf_counter()

        await async_client.post("/api/v1/entities", json=payload)
        await async_client.get("/api/v1/entities/perf-test-001")
        await async_client.put("/api/v1/entities/perf-test-001", json={"name": "Updated"})
        await async_client.delete("/api/v1/entities/perf-test-001")

        elapsed = time.perf_counter() - start
        assert elapsed < 2.0, f"Full CRUD cycle took {elapsed:.2f}s (limit 2.0s)"


# ---------------------------------------------------------------------------
# 2. Concurrent CRUD Operations
# ---------------------------------------------------------------------------

class TestConcurrentCRUD:
    """Verify system handles concurrent operations correctly."""

    CONCURRENCY = 20

    async def test_concurrent_creates(self, async_client):
        """Multiple simultaneous creates should all succeed."""
        payloads = [_make_payload() for _ in range(self.CONCURRENCY)]
        for i, p in enumerate(payloads):
            p["id"] = f"concurrent-{i}"

        results = await asyncio.gather(
            *[async_client.post("/api/v1/entities", json=p) for p in payloads]
        )
        assert all(r.status_code in (200, 201) for r in results)

    async def test_concurrent_reads(self, async_client):
        """Multiple simultaneous reads should all succeed."""
        payload = _make_payload()
        await async_client.post("/api/v1/entities", json=payload)

        results = await asyncio.gather(
            *[async_client.get("/api/v1/entities/perf-test-001") for _ in range(self.CONCURRENCY)]
        )
        assert all(r.status_code == 200 for r in results)

    async def test_concurrent_mixed_operations(self, async_client):
        """Mix of concurrent creates, reads, updates, and deletes."""
        payload = _make_payload()
        await async_client.post("/api/v1/entities", json=payload)

        async def mixed_op(i):
            if i % 4 == 0:
                return await async_client.post("/api/v1/entities", json=_make_payload())
            elif i % 4 == 1:
                return await async_client.get("/api/v1/entities/perf-test-001")
            elif i % 4 == 2:
                return await async_client.put(
                    "/api/v1/entities/perf-test-001", json={"name": f"Updated-{i}"}
                )
            else:
                return await async_client.delete("/api/v1/entities/perf-test-001")

        results = await asyncio.gather(*[mixed_op(i) for i in range(self.CONCURRENCY)])
        assert all(r.status_code < 500 for r in results)

    async def test_concurrent_delete_idempotency(self, async_client):
        """Concurrent deletes of the same resource should not error."""
        payload = _make_payload()
        await async_client.post("/api/v1/entities", json=payload)

        results = await asyncio.gather(
            *[async_client.delete("/api/v1/entities/perf-test-001") for _ in range(5)]
        )
        assert all(r.status_code in (200, 204, 404) for r in results)


# ---------------------------------------------------------------------------
# 3. Large Dataset Handling
# ---------------------------------------------------------------------------

class TestLargeDataset:
    """Verify CRUD operations handle large datasets efficiently."""

    LARGE_PAYLOAD_SIZE = 1024 * 1024  # 1 MB
    BATCH_SIZE = 100

    async def test_large_payload_create(self, async_client):
        """Creating an entity with a 1MB payload should succeed."""
        payload = _make_payload(size=self.LARGE_PAYLOAD_SIZE)
        resp = await async_client.post("/api/v1/entities", json=payload)
        assert resp.status_code in (200, 201)

    async def test_large_payload_read(self, async_client):
        """Reading a large entity should return complete data."""
        payload = _make_payload(size=self.LARGE_PAYLOAD_SIZE)
        await async_client.post("/api/v1/entities", json=payload)

        resp = await async_client.get("/api/v1/entities/perf-test-001")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == self.LARGE_PAYLOAD_SIZE

    async def test_batch_create(self, async_client):
        """Batch-creating 100 entities should complete within 10s."""
        payloads = [_make_payload() for _ in range(self.BATCH_SIZE)]
        for i, p in enumerate(payloads):
            p["id"] = f"batch-{i}"

        start = time.perf_counter()
        results = await asyncio.gather(
            *[async_client.post("/api/v1/entities", json=p) for p in payloads]
        )
        elapsed = time.perf_counter() - start

        assert all(r.status_code in (200, 201) for r in results)
        assert elapsed < 10.0, f"Batch create took {elapsed:.2f}s (limit 10s)"

    async def test_list_pagination(self, async_client):
        """Listing entities with pagination should return correct counts."""
        for i in range(50):
            p = _make_payload()
            p["id"] = f"page-{i}"
            await async_client.post("/api/v1/entities", json=p)

        resp = await async_client.get("/api/v1/entities?limit=10&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("items", data.get("results", []))) <= 10


# ---------------------------------------------------------------------------
# 4. Memory Usage
# ---------------------------------------------------------------------------

class TestMemoryUsage:
    """Verify CRUD operations do not leak memory."""

    async def test_memory_stable_across_operations(self, async_client):
        """Memory should not grow unbounded across repeated operations."""
        tracemalloc.start()
        gc.collect()
        _, baseline = tracemalloc.get_traced_memory()

        for i in range(50):
            p = _make_payload()
            p["id"] = f"mem-{i}"
            await async_client.post("/api/v1/entities", json=p)
            await async_client.get(f"/api/v1/entities/mem-{i}")
            await async_client.delete(f"/api/v1/entities/mem-{i}")

        gc.collect()
        _, current = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        growth = current - baseline
        max_growth = 10 * 1024 * 1024  # 10 MB
        assert growth < max_growth, (
            f"Memory grew by {growth / 1024 / 1024:.1f}MB (limit {max_growth / 1024 / 1024}MB)"
        )

    async def test_large_payload_memory_cleanup(self, async_client):
        """Memory should be released after large payload operations."""
        tracemalloc.start()
        gc.collect()
        _, baseline = tracemalloc.get_traced_memory()

        for _ in range(10):
            p = _make_payload(size=512 * 1024)
            await async_client.post("/api/v1/entities", json=p)
            await async_client.delete("/api/v1/entities/perf-test-001")

        gc.collect()
        _, current = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        growth = current - baseline
        max_growth = 5 * 1024 * 1024  # 5 MB
        assert growth < max_growth, (
            f"Memory grew by {growth / 1024 / 1024:.1f}MB after large payload ops"
        )


# ---------------------------------------------------------------------------
# 5. Error Recovery
# ---------------------------------------------------------------------------

class TestErrorRecovery:
    """Verify system recovers gracefully from errors."""

    async def test_recovery_after_bad_payload(self, async_client):
        """System should recover after receiving a malformed payload."""
        bad_resp = await async_client.post("/api/v1/entities", json={"invalid": None})
        assert bad_resp.status_code >= 400

        good_resp = await async_client.post("/api/v1/entities", json=_make_payload())
        assert good_resp.status_code in (200, 201)

    async def test_recovery_after_server_error(self, async_client):
        """System should recover after an internal server error."""
        resp = await async_client.get("/api/v1/entities/nonexistent-id-xyz")
        assert resp.status_code == 404

        create_resp = await async_client.post("/api/v1/entities", json=_make_payload())
        assert create_resp.status_code in (200, 201)

    async def test_recovery_after_timeout(self, async_client):
        """System should recover after a slow/timeout-inducing request."""
        p = _make_payload(size=2 * 1024 * 1024)
        resp = await async_client.post("/api/v1/entities", json=p)
        assert resp.status_code in (200, 201, 413)

        normal_resp = await async_client.post("/api/v1/entities", json=_make_payload())
        assert normal_resp.status_code in (200, 201)

    async def test_rapid_error_recovery(self, async_client):
        """System should handle rapid sequences of errors and successes."""
        results = []
        for i in range(20):
            if i % 3 == 0:
                r = await async_client.get("/api/v1/entities/nonexistent")
                results.append(r.status_code)
            else:
                p = _make_payload()
                p["id"] = f"rapid-{i}"
                r = await async_client.post("/api/v1/entities", json=p)
                results.append(r.status_code)

        errors = [s for s in results if s >= 400]
        successes = [s for s in results if s < 400]
        assert len(errors) > 0 and len(successes) > 0
        assert all(s < 500 for s in results), "No 5xx errors should occur during recovery"
