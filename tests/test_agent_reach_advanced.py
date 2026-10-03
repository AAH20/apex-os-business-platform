"""Tests for Agent-Reach advanced features."""
import time
import pytest
from apex_os_bp.agent_reach.advanced import (
    CircuitBreaker, CircuitState, HealthCheck, MetricsCollector, RateLimiter, retry,
)

def _fail():
    raise ValueError("fail")

class TestCircuitBreaker:
    def test_closed_on_success(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.call(lambda: 42) == 42
        assert cb.state is CircuitState.CLOSED

    def test_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(_fail)
        assert cb.state is CircuitState.OPEN

    def test_blocks_when_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        with pytest.raises(ValueError):
            cb.call(_fail)
        with pytest.raises(RuntimeError, match="OPEN"):
            cb.call(lambda: 1)

    def test_half_open_recovery(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        with pytest.raises(ValueError):
            cb.call(_fail)
        time.sleep(0.02)
        assert cb.call(lambda: 99) == 99
        assert cb.state is CircuitState.CLOSED

class TestRetry:
    def test_succeeds_first_try(self):
        assert retry(lambda: 5) == 5

    def test_retries_until_success(self):
        calls = []
        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"
        assert retry(flaky, max_attempts=3, base_delay=0.001) == "ok"

    def test_raises_after_max_attempts(self):
        with pytest.raises(ValueError):
            retry(_fail, max_attempts=2, base_delay=0.001)

    def test_exponential_backoff(self):
        delays = []
        orig = time.sleep
        time.sleep = lambda d: delays.append(d)
        try:
            with pytest.raises(ValueError):
                retry(_fail, max_attempts=4, base_delay=0.1)
        finally:
            time.sleep = orig
        assert delays == [0.1, 0.2, 0.4]

class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(max_calls=3, period=1.0)
        assert all(rl.acquire() for _ in range(3))

    def test_blocks_over_limit(self):
        rl = RateLimiter(max_calls=2, period=1.0)
        rl.acquire(); rl.acquire()
        assert not rl.acquire()

    def test_window_expires(self):
        rl = RateLimiter(max_calls=1, period=0.05)
        assert rl.acquire()
        assert not rl.acquire()
        time.sleep(0.06)
        assert rl.acquire()

    def test_decorator(self):
        rl = RateLimiter(max_calls=1, period=1.0)
        @rl
        def fn():
            return True
        assert fn()
        with pytest.raises(RuntimeError, match="Rate limit"):
            fn()

class TestHealthCheck:
    def test_healthy(self):
        hc = HealthCheck("test", lambda: True, interval=0)
        assert hc.run() is True
        assert hc.healthy is True

    def test_unhealthy(self):
        hc = HealthCheck("test", lambda: False, interval=0)
        assert hc.run() is False
        assert hc.healthy is False

    def test_exception_is_unhealthy(self):
        hc = HealthCheck("test", lambda: 1 / 0, interval=0)
        assert hc.run() is False

    def test_interval_throttles(self):
        calls = []
        hc = HealthCheck("test", lambda: calls.append(1) or True, interval=60)
        hc.run(); hc.run()
        assert len(calls) == 1

class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("hits"); m.increment("hits", 2)
        assert m.snapshot()["counters"]["hits"] == 3

    def test_record_latency(self):
        m = MetricsCollector()
        m.record_latency("op", 0.5); m.record_latency("op", 1.5)
        snap = m.snapshot()
        assert snap["latencies"]["op"]["count"] == 2
        assert snap["latencies"]["op"]["avg"] == 1.0

    def test_measure_decorator(self):
        m = MetricsCollector()
        @m.measure("work")
        def work():
            return 7
        assert work() == 7
        assert m.snapshot()["latencies"]["work"]["count"] == 1

    def test_measure_records_on_exception(self):
        m = MetricsCollector()
        @m.measure("bad")
        def bad():
            raise ValueError("x")
        with pytest.raises(ValueError):
            bad()
        assert m.snapshot()["latencies"]["bad"]["count"] == 1


class TestMultiAgentOrchestration:
    @pytest.mark.asyncio
    async def test_orchestrate_agents(self):
        from apex_os_bp.agent_reach.advanced import Orchestrator
        orch = Orchestrator()
        results = await orch.run(["a1", "a2"], lambda x: x.upper())
        assert results == ["A1", "A2"]

    @pytest.mark.asyncio
    async def test_orchestrate_empty(self):
        from apex_os_bp.agent_reach.advanced import Orchestrator
        orch = Orchestrator()
        assert await orch.run([], lambda x: x) == []


class TestMessageRouting:
    @pytest.mark.asyncio
    async def test_route_to_agent(self):
        from apex_os_bp.agent_reach.advanced import MessageRouter
        router = MessageRouter()
        router.register("a1", lambda m: f"routed:{m}")
        assert await router.route("a1", "hi") == "routed:hi"

    @pytest.mark.asyncio
    async def test_route_unknown_raises(self):
        from apex_os_bp.agent_reach.advanced import MessageRouter
        router = MessageRouter()
        with pytest.raises(KeyError):
            await router.route("nope", "hi")


class TestLoadBalancer:
    @pytest.mark.asyncio
    async def test_least_loaded(self):
        from apex_os_bp.agent_reach.advanced import LoadBalancer
        lb = LoadBalancer([("a1", 8), ("a2", 2), ("a3", 5)])
        assert await lb.select() == "a2"

    @pytest.mark.asyncio
    async def test_distribute_evenly(self):
        from apex_os_bp.agent_reach.advanced import LoadBalancer
        lb = LoadBalancer([("a1", 0), ("a2", 0), ("a3", 0)])
        dist = await lb.distribute(9)
        assert sum(len(v) for v in dist.values()) == 9
