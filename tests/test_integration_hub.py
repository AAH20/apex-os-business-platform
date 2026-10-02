"""Tests for the Integration Hub."""

import asyncio
import pytest

from apex_os_bp.integration_hub import (
    APIOrchestrator,
    DataMapper,
    ErrorHandler,
    ErrorPolicy,
    ErrorSeverity,
    ErrorCategory,
    EventRouter,
    Event,
    EventPriority,
    EventStatus,
    HealthStatus,
    IntegrationMonitor,
    MappingDirection,
    MappingResult,
    MappingType,
    MetricSnapshot,
    MetricType,
    AlertSeverity,
    AlertRule,
    OrchestrationStep,
    OrchestrationResult,
    Route,
    RouteResult,
    FieldMapping,
    HealthCheck,
    ErrorRecord,
)


# ── API Orchestration Tests ──


class TestAPIOrchestrator:
    def test_add_and_get_step(self):
        orch = APIOrchestrator("test")
        step = OrchestrationStep(name="step1", handler=_async_noop)
        orch.add_step(step)
        assert orch.get_step("step1") is step

    def test_remove_step(self):
        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(name="s1", handler=_async_noop))
        orch.remove_step("s1")
        assert orch.get_step("s1") is None

    def test_step_duration(self):
        step = OrchestrationStep(name="s", handler=_async_noop)
        assert step.duration is None
        step.started_at = 1.0
        step.completed_at = 2.5
        assert step.duration == 1.5

    @pytest.mark.asyncio
    async def test_execute_single_step(self):
        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="fetch",
            handler=_async_return_value({"data": 42}),
        ))
        result = await orch.execute()
        assert result.success is True
        assert result.data["fetch"] == {"data": 42}
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_execute_with_dependencies(self):
        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="auth",
            handler=_async_return_value("token123"),
        ))
        orch.add_step(OrchestrationStep(
            name="fetch_user",
            handler=_async_return_value({"user": "alice"}),
            depends_on=["auth"],
        ))
        result = await orch.execute()
        assert result.success is True
        assert result.data["auth"] == "token123"
        assert result.data["fetch_user"] == {"user": "alice"}

    @pytest.mark.asyncio
    async def test_dependency_failure_skips_dependent(self):
        orch = APIOrchestrator("test")

        async def fail_handler(results):
            raise ValueError("auth failed")

        orch.add_step(OrchestrationStep(name="auth", handler=fail_handler))
        orch.add_step(OrchestrationStep(
            name="fetch",
            handler=_async_return_value({"data": 1}),
            depends_on=["auth"],
        ))
        result = await orch.execute()
        assert result.success is False
        assert "auth" in result.failed_steps
        assert result.steps["fetch"].status == "skipped"

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        call_count = 0

        async def flaky_handler(results):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="flaky",
            handler=flaky_handler,
            max_retries=3,
        ))
        result = await orch.execute()
        assert result.success is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_timeout(self):
        async def slow_handler(results):
            await asyncio.sleep(10)
            return "done"

        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="slow",
            handler=slow_handler,
            timeout=0.1,
            max_retries=0,
        ))
        result = await orch.execute()
        assert result.success is False
        assert "slow" in result.failed_steps

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        order = []

        async def make_handler(name, delay):
            async def handler(results):
                await asyncio.sleep(delay)
                order.append(name)
                return name
            return handler

        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(name="a", handler=await make_handler("a", 0.05)))
        orch.add_step(OrchestrationStep(name="b", handler=await make_handler("b", 0.01)))
        orch.add_step(OrchestrationStep(name="c", handler=await make_handler("c", 0.03)))
        result = await orch.execute()
        assert result.success is True
        assert len(order) == 3

    @pytest.mark.asyncio
    async def test_reset(self):
        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="s1",
            handler=_async_return_value(1),
        ))
        await orch.execute()
        orch.reset()
        step = orch.get_step("s1")
        assert step.status == "pending"
        assert step.result is None

    @pytest.mark.asyncio
    async def test_circular_dependency_breaks(self):
        orch = APIOrchestrator("test")
        orch.add_step(OrchestrationStep(
            name="a",
            handler=_async_return_value(1),
            depends_on=["b"],
        ))
        orch.add_step(OrchestrationStep(
            name="b",
            handler=_async_return_value(2),
            depends_on=["a"],
        ))
        result = await orch.execute()
        # Circular dependency causes all steps to be skipped
        assert len(result.completed_steps) == 0
        assert result.steps["a"].status == "skipped"
        assert result.steps["b"].status == "skipped"


# ── Data Mapping Tests ──


class TestDataMapper:
    def test_direct_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(source_path="first_name", target_path="firstName"))
        result = mapper.map({"first_name": "Alice"})
        assert result.success is True
        assert result.data["firstName"] == "Alice"
        assert result.fields_mapped == 1

    def test_rename_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="user.name",
            target_path="userName",
            mapping_type=MappingType.RENAME,
        ))
        result = mapper.map({"user": {"name": "Bob"}})
        assert result.data["userName"] == "Bob"

    def test_transform_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="name",
            target_path="name_upper",
            mapping_type=MappingType.TRANSFORM,
            transform="upper",
        ))
        result = mapper.map({"name": "alice"})
        assert result.data["name_upper"] == "ALICE"

    def test_constant_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="unused",
            target_path="version",
            mapping_type=MappingType.CONSTANT,
            default="1.0",
        ))
        result = mapper.map({})
        assert result.data["version"] == "1.0"

    def test_default_value(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="missing",
            target_path="present",
            default="default_val",
        ))
        result = mapper.map({})
        assert result.data["present"] == "default_val"

    def test_required_field_missing(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="required_field",
            target_path="output",
            required=True,
        ))
        result = mapper.map({})
        assert result.success is False
        assert result.fields_failed == 1
        assert len(result.errors) > 0

    def test_nested_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="address",
            target_path="mapped_address",
            mapping_type=MappingType.NESTED,
            nested_mappings=[
                FieldMapping(source_path="street", target_path="streetName"),
                FieldMapping(source_path="zip", target_path="zipCode"),
            ],
        ))
        result = mapper.map({"address": {"street": "Main St", "zip": "12345"}})
        assert result.data["mapped_address"]["streetName"] == "Main St"
        assert result.data["mapped_address"]["zipCode"] == "12345"

    def test_collection_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="items",
            target_path="mapped_items",
            mapping_type=MappingType.COLLECTION,
            collection_item_mapping=FieldMapping(
                source_path="price",
                target_path="cost",
            ),
        ))
        result = mapper.map({"items": [{"price": 10}, {"price": 20}]})
        assert len(result.data["mapped_items"]) == 2
        assert result.data["mapped_items"][0]["cost"] == 10

    def test_conditional_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="status",
            target_path="isActive",
            condition=lambda d: d.get("type") == "premium",
        ))
        result = mapper.map({"status": "active", "type": "premium"})
        assert result.data["isActive"] == "active"

        result2 = mapper.map({"status": "active", "type": "basic"})
        assert "isActive" not in result2.data

    def test_direction_filtering(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="inbound_field",
            target_path="out",
            direction=MappingDirection.INBOUND,
        ))
        result = mapper.map({"inbound_field": "val"}, direction=MappingDirection.OUTBOUND)
        assert "out" not in result.data

    def test_reverse_map(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="external_id",
            target_path="internalId",
            direction=MappingDirection.BIDIRECTIONAL,
        ))
        result = mapper.reverse_map({"external_id": "ext-123"})
        assert result.data["internalId"] == "ext-123"

    def test_map_many(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(source_path="x", target_path="y"))
        results = mapper.map_many([{"x": 1}, {"x": 2}, {"x": 3}])
        assert len(results) == 3
        assert all(r.data["y"] == i + 1 for i, r in enumerate(results))

    def test_validate_schema(self):
        mapper = DataMapper("test")
        missing = mapper.validate_schema(
            {"a": 1, "b": {"c": 2}},
            ["a", "b.c", "d"],
        )
        assert "d" in missing
        assert "a" not in missing

    def test_builtin_transforms(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="val",
            target_path="upper",
            mapping_type=MappingType.TRANSFORM,
            transform="upper",
        ))
        result = mapper.map({"val": "hello"})
        assert result.data["upper"] == "HELLO"

    def test_custom_transform_registration(self):
        mapper = DataMapper("test")
        mapper.register_transform("double", lambda v: v * 2)
        mapper.add_mapping(FieldMapping(
            source_path="num",
            target_path="doubled",
            mapping_type=MappingType.TRANSFORM,
            transform="double",
        ))
        result = mapper.map({"num": 5})
        assert result.data["doubled"] == 10

    def test_snake_to_camel_transform(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(
            source_path="field_name",
            target_path="fieldName",
            mapping_type=MappingType.TRANSFORM,
            transform="snake_to_camel",
        ))
        result = mapper.map({"field_name": "val"})
        assert result.data["fieldName"] == "val"

    def test_remove_mapping(self):
        mapper = DataMapper("test")
        mapper.add_mapping(FieldMapping(source_path="a", target_path="b"))
        mapper.remove_mapping("a", "b")
        result = mapper.map({"a": 1})
        assert "b" not in result.data

    def test_get_value_nested(self):
        mapper = DataMapper("test")
        assert mapper._get_value({"a": {"b": {"c": 42}}}, "a.b.c") == 42
        assert mapper._get_value({"a": [10, 20, 30]}, "a.1") == 20
        assert mapper._get_value({"a": 1}, "x.y.z") is None

    def test_set_value_creates_intermediate(self):
        mapper = DataMapper("test")
        data = {}
        mapper._set_value(data, "a.b.c", 99)
        assert data["a"]["b"]["c"] == 99


# ── Event Routing Tests ──


class TestEventRouter:
    def test_register_and_get_route(self):
        router = EventRouter("test")
        route = Route(name="r1", event_type="user.created", handler=_async_noop)
        router.register_route(route)
        assert router.get_route("r1") is route

    def test_unregister_route(self):
        router = EventRouter("test")
        router.register_route(Route(name="r1", event_type="test", handler=_async_noop))
        router.unregister_route("r1")
        assert router.get_route("r1") is None

    def test_route_matching_by_type(self):
        router = EventRouter("test")
        route = Route(name="r1", event_type="order.placed", handler=_async_noop)
        assert route.matches(Event(event_type="order.placed")) is True
        assert route.matches(Event(event_type="order.cancelled")) is False

    def test_route_matching_wildcard(self):
        route = Route(name="r1", event_type="*", handler=_async_noop)
        assert route.matches(Event(event_type="anything")) is True

    def test_route_filter(self):
        route = Route(
            name="r1",
            event_type="user.created",
            handler=_async_noop,
            filter_fn=lambda e: e.payload.get("plan") == "premium",
        )
        assert route.matches(Event(event_type="user.created", payload={"plan": "premium"})) is True
        assert route.matches(Event(event_type="user.created", payload={"plan": "free"})) is False

    def test_route_disabled(self):
        route = Route(name="r1", event_type="test", handler=_async_noop, enabled=False)
        assert route.matches(Event(event_type="test")) is False

    @pytest.mark.asyncio
    async def test_route_event(self):
        router = EventRouter("test")
        handled = []

        async def handler(event):
            handled.append(event.event_id)
            return "ok"

        router.register_route(Route(name="r1", event_type="test", handler=handler))
        event = Event(event_type="test", payload={"x": 1})
        results = await router.route(event)
        assert len(results) == 1
        assert results[0].success is True
        assert event.status == EventStatus.HANDLED

    @pytest.mark.asyncio
    async def test_emit(self):
        router = EventRouter("test")
        router.register_route(Route(name="r1", event_type="ping", handler=_async_noop))
        results = await router.emit("ping", {"data": 1})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_no_matching_routes_dead_letter(self):
        router = EventRouter("test")
        event = Event(event_type="unknown")
        results = await router.route(event)
        assert len(results) == 0
        assert event.status == EventStatus.DEAD_LETTER
        assert len(router.get_dead_letter()) == 1

    @pytest.mark.asyncio
    async def test_middleware(self):
        router = EventRouter("test")
        processed = []

        async def mw(event):
            processed.append(event.event_type)
            event.metadata["mw"] = True
            return event

        router.add_middleware(mw)
        router.register_route(Route(name="r1", event_type="test", handler=_async_noop))
        await router.emit("test", {})
        assert len(processed) == 1

    @pytest.mark.asyncio
    async def test_route_timeout(self):
        router = EventRouter("test")

        async def slow_handler(event):
            await asyncio.sleep(10)

        router.register_route(Route(
            name="r1", event_type="test", handler=slow_handler, timeout=0.1,
        ))
        results = await router.emit("test", {})
        assert results[0].success is False
        assert "Timeout" in results[0].error

    @pytest.mark.asyncio
    async def test_route_handler_exception(self):
        router = EventRouter("test")

        async def bad_handler(event):
            raise ValueError("boom")

        router.register_route(Route(name="r1", event_type="test", handler=bad_handler))
        results = await router.emit("test", {})
        assert results[0].success is False
        assert "boom" in results[0].error

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        router = EventRouter("test")
        order = []

        async def make_handler(name):
            async def h(event):
                order.append(name)
            return h

        router.register_route(Route(name="low", event_type="test", handler=await make_handler("low"), priority=1))
        router.register_route(Route(name="high", event_type="test", handler=await make_handler("high"), priority=10))
        await router.emit("test", {})
        assert order[0] == "high"

    @pytest.mark.asyncio
    async def test_history(self):
        router = EventRouter("test")
        router.register_route(Route(name="r1", event_type="test", handler=_async_noop))
        await router.emit("test", {})
        await router.emit("test", {})
        history = router.get_history()
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_route_stats(self):
        router = EventRouter("test")
        router.register_route(Route(name="r1", event_type="test", handler=_async_noop))
        await router.emit("test", {})
        stats = router.get_route_stats()
        assert "r1" in stats
        assert stats["r1"]["total"] == 1
        assert stats["r1"]["success"] == 1

    @pytest.mark.asyncio
    async def test_clear_dead_letter(self):
        router = EventRouter("test")
        await router.emit("unknown", {})
        assert len(router.get_dead_letter()) == 1
        router.clear_dead_letter()
        assert len(router.get_dead_letter()) == 0

    def test_event_to_dict(self):
        event = Event(event_type="test", payload={"a": 1}, source="test_src")
        d = event.to_dict()
        assert d["event_type"] == "test"
        assert d["source"] == "test_src"
        assert d["status"] == "pending"


# ── Error Handling Tests ──


class TestErrorHandler:
    def test_capture_error(self):
        handler = ErrorHandler()
        try:
            raise ValueError("test error")
        except ValueError as e:
            record = handler.capture(e, source="test_src", operation="test_op")
        assert record.category == ErrorCategory.UNKNOWN
        assert record.message == "test error"
        assert record.source == "test_src"

    def test_classify_timeout(self):
        handler = ErrorHandler()
        try:
            raise asyncio.TimeoutError("timed out")
        except asyncio.TimeoutError as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.TIMEOUT

    def test_classify_connection(self):
        handler = ErrorHandler()
        try:
            raise ConnectionError("refused")
        except ConnectionError as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.NETWORK

    def test_classify_auth(self):
        handler = ErrorHandler()
        try:
            raise Exception("Unauthorized access")
        except Exception as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.AUTH

    def test_classify_rate_limit(self):
        handler = ErrorHandler()
        try:
            raise Exception("429 Too Many Requests")
        except Exception as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.RATE_LIMIT

    def test_classify_not_found(self):
        handler = ErrorHandler()
        try:
            raise Exception("Resource not found")
        except Exception as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.NOT_FOUND

    def test_classify_validation(self):
        handler = ErrorHandler()
        try:
            raise Exception("Invalid schema provided")
        except Exception as e:
            record = handler.capture(e)
        assert record.category == ErrorCategory.VALIDATION

    def test_error_counts(self):
        handler = ErrorHandler()
        for _ in range(3):
            try:
                raise ValueError("err")
            except ValueError as e:
                handler.capture(e, source="src1")
        counts = handler.get_error_counts()
        assert counts.get("src1:unknown") == 3

    def test_get_errors_filter(self):
        handler = ErrorHandler()
        try:
            raise ValueError("v")
        except ValueError as e:
            handler.capture(e, source="s1")
        try:
            raise ConnectionError("c")
        except ConnectionError as e:
            handler.capture(e, source="s2")

        errors = handler.get_errors(source="s1")
        assert len(errors) == 1
        assert errors[0].source == "s1"

    def test_get_errors_by_severity(self):
        handler = ErrorHandler()
        try:
            raise ConnectionError("net")
        except ConnectionError as e:
            handler.capture(e)
        errors = handler.get_errors(severity=ErrorSeverity.WARNING)
        assert len(errors) == 1

    def test_resolve_error(self):
        handler = ErrorHandler()
        try:
            raise ValueError("fix me")
        except ValueError as e:
            record = handler.capture(e)
        assert handler.resolve_error(record.error_id, "fixed") is True
        assert record.resolved is True

    def test_resolve_nonexistent(self):
        handler = ErrorHandler()
        assert handler.resolve_error("nonexistent") is False

    @pytest.mark.asyncio
    async def test_execute_success(self):
        handler = ErrorHandler()

        async def ok_fn():
            return 42

        result = await handler.execute(ok_fn, source="test")
        assert result == 42

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self):
        handler = ErrorHandler(ErrorPolicy(max_retries=3, base_delay=0.01))
        call_count = 0

        async def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("transient")
            return "ok"

        result = await handler.execute(flaky, source="test")
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_exhausts_retries(self):
        handler = ErrorHandler(ErrorPolicy(max_retries=2, base_delay=0.01))

        async def always_fail():
            raise ConnectionError("down")

        with pytest.raises(ConnectionError):
            await handler.execute(always_fail, source="test")

    @pytest.mark.asyncio
    async def test_execute_fatal_no_retry(self):
        handler = ErrorHandler(ErrorPolicy(max_retries=5, base_delay=0.01))
        call_count = 0

        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Unauthorized")

        with pytest.raises(Exception, match="Unauthorized"):
            await handler.execute(auth_fail, source="test")
        assert call_count == 1  # No retries for auth errors

    @pytest.mark.asyncio
    async def test_circuit_breaker(self):
        handler = ErrorHandler(ErrorPolicy(max_retries=0))

        async def fail():
            raise ConnectionError("down")

        for _ in range(5):
            with pytest.raises(ConnectionError):
                await handler.execute(fail, source="cb_test")

        # Circuit should be open now
        with pytest.raises(Exception, match="Circuit breaker open"):
            await handler.execute(fail, source="cb_test")

    @pytest.mark.asyncio
    async def test_recovery_strategy(self):
        handler = ErrorHandler()
        recovered = []

        async def recover(record):
            recovered.append(record.error_id)

        handler.register_recovery(ErrorCategory.NETWORK, recover)
        try:
            raise ConnectionError("net")
        except ConnectionError as e:
            record = handler.capture(e)

        success = await handler.attempt_recovery(record)
        assert success is True
        assert record.resolved is True
        assert len(recovered) == 1

    @pytest.mark.asyncio
    async def test_recovery_no_strategy(self):
        handler = ErrorHandler()
        try:
            raise ValueError("v")
        except ValueError as e:
            record = handler.capture(e)
        success = await handler.attempt_recovery(record)
        assert success is False

    def test_clear(self):
        handler = ErrorHandler()
        try:
            raise ValueError("v")
        except ValueError as e:
            handler.capture(e)
        handler.clear()
        assert len(handler.get_errors()) == 0

    def test_error_policy_should_retry(self):
        policy = ErrorPolicy(max_retries=3)
        record = ErrorRecord(category=ErrorCategory.NETWORK, retry_count=1)
        assert policy.should_retry(record) is True
        record.retry_count = 5
        assert policy.should_retry(record) is False

    def test_error_policy_fatal_no_retry(self):
        policy = ErrorPolicy(max_retries=5)
        record = ErrorRecord(category=ErrorCategory.AUTH, retry_count=0)
        assert policy.should_retry(record) is False

    def test_error_policy_delay(self):
        policy = ErrorPolicy(base_delay=1.0, exponential_base=2.0, jitter=False)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_error_policy_max_delay(self):
        policy = ErrorPolicy(base_delay=10.0, max_delay=15.0, jitter=False)
        assert policy.get_delay(10) == 15.0

    def test_on_error_callback(self):
        captured = []
        policy = ErrorPolicy(on_error=lambda r: captured.append(r))
        handler = ErrorHandler(policy)
        try:
            raise ValueError("cb test")
        except ValueError as e:
            handler.capture(e)
        assert len(captured) == 1

    def test_on_retry_callback(self):
        retries = []

        async def test_fn():
            raise ConnectionError("retry")

        async def run():
            policy = ErrorPolicy(
                max_retries=2,
                base_delay=0.01,
                on_retry=lambda r, n: retries.append(n),
            )
            handler = ErrorHandler(policy)
            with pytest.raises(ConnectionError):
                await handler.execute(test_fn, source="test")

        asyncio.run(run())
        assert len(retries) > 0


# ── Monitoring Tests ──


class TestIntegrationMonitor:
    def test_record_counter(self):
        mon = IntegrationMonitor("test")
        mon.record_counter("requests", 1)
        mon.record_counter("requests", 1)
        assert mon.get_counter("requests") == 2.0

    def test_record_gauge(self):
        mon = IntegrationMonitor("test")
        mon.record_gauge("cpu_usage", 75.5)
        assert mon.get_gauge("cpu_usage") == 75.5

    def test_record_histogram(self):
        mon = IntegrationMonitor("test")
        mon.record_histogram("response_size", 100)
        mon.record_histogram("response_size", 200)
        stats = mon.get_histogram_stats("response_size")
        assert stats["count"] == 2
        assert stats["min"] == 100
        assert stats["max"] == 200

    def test_record_timer(self):
        mon = IntegrationMonitor("test")
        mon.record_timer("latency", 0.5)
        mon.record_timer("latency", 1.5)
        stats = mon.get_timer_stats("latency")
        assert stats["count"] == 2
        assert stats["avg"] == 1.0

    def test_histogram_percentiles(self):
        mon = IntegrationMonitor("test")
        for i in range(100):
            mon.record_histogram("latency", float(i))
        stats = mon.get_histogram_stats("latency")
        assert stats["p50"] == 50.0
        assert stats["p95"] == 95.0
        assert stats["p99"] == 99.0

    def test_get_metric_history(self):
        mon = IntegrationMonitor("test")
        mon.record_counter("hits", 1)
        mon.record_counter("hits", 1)
        mon.record_counter("hits", 1)
        metrics = mon.get_metric("hits", last_n=2)
        assert len(metrics) == 2

    def test_register_health_check(self):
        mon = IntegrationMonitor("test")
        check = HealthCheck(name="db", check_fn=_async_true)
        mon.register_health_check(check)
        assert "db" in mon.get_health_check_status()

    @pytest.mark.asyncio
    async def test_run_health_check(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="hc", check_fn=_async_true))
        result = await mon.run_health_check("hc")
        assert result is True

    @pytest.mark.asyncio
    async def test_run_health_check_failure(self):
        mon = IntegrationMonitor("test")

        async def fail_check():
            return False

        mon.register_health_check(HealthCheck(name="hc", check_fn=fail_check))
        result = await mon.run_health_check("hc")
        assert result is False

    @pytest.mark.asyncio
    async def test_run_all_health_checks(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true))
        mon.register_health_check(HealthCheck(name="b", check_fn=_async_true))
        results = await mon.run_all_health_checks()
        assert results == {"a": True, "b": True}

    def test_overall_health_healthy(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true))
        assert mon.get_overall_health() == HealthStatus.HEALTHY

    def test_overall_health_unknown(self):
        mon = IntegrationMonitor("test")
        assert mon.get_overall_health() == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_overall_health_degraded(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true))
        mon.register_health_check(HealthCheck(name="b", check_fn=_async_false, max_failures=1))
        await mon.run_all_health_checks()
        assert mon.get_overall_health() == HealthStatus.DEGRADED

    def test_alert_rule_evaluate(self):
        rule = AlertRule(
            name="high_cpu",
            metric_name="cpu",
            condition=">",
            threshold=80.0,
        )
        assert rule.evaluate(90.0) is True
        assert rule.evaluate(70.0) is False

    def test_alert_rule_cooldown(self):
        import time as _time
        rule = AlertRule(
            name="test",
            metric_name="m",
            condition=">",
            threshold=0,
            cooldown=100,
        )
        assert rule.can_trigger() is True
        rule.last_triggered = _time.time()
        assert rule.can_trigger() is False

    def test_alert_triggered(self):
        mon = IntegrationMonitor("test")
        alerts_received = []
        mon.add_alert_handler(lambda a: alerts_received.append(a))
        mon.add_alert_rule(AlertRule(
            name="test_alert",
            metric_name="cpu",
            condition=">",
            threshold=80.0,
        ))
        mon.record_gauge("cpu", 95.0)
        assert len(alerts_received) == 1
        assert alerts_received[0].severity == AlertSeverity.WARNING

    def test_alert_acknowledgement(self):
        mon = IntegrationMonitor("test")
        alerts_received = []
        mon.add_alert_handler(lambda a: alerts_received.append(a))
        mon.add_alert_rule(AlertRule(
            name="test", metric_name="m", condition=">", threshold=0,
        ))
        mon.record_gauge("m", 100)
        alert = alerts_received[0]
        assert mon.acknowledge_alert(alert.alert_id) is True
        assert alert.acknowledged is True

    def test_alert_resolution(self):
        mon = IntegrationMonitor("test")
        alerts_received = []
        mon.add_alert_handler(lambda a: alerts_received.append(a))
        mon.add_alert_rule(AlertRule(
            name="test", metric_name="m", condition=">", threshold=0,
        ))
        mon.record_gauge("m", 100)
        alert = alerts_received[0]
        assert mon.resolve_alert(alert.alert_id) is True
        assert alert.resolved is True

    def test_get_alerts_filter(self):
        mon = IntegrationMonitor("test")
        alerts_received = []
        mon.add_alert_handler(lambda a: alerts_received.append(a))
        mon.add_alert_rule(AlertRule(
            name="warn", metric_name="m", condition=">", threshold=0,
            severity=AlertSeverity.WARNING,
        ))
        mon.add_alert_rule(AlertRule(
            name="crit", metric_name="m2", condition=">", threshold=0,
            severity=AlertSeverity.CRITICAL,
        ))
        mon.record_gauge("m", 100)
        mon.record_gauge("m2", 100)
        warnings = mon.get_alerts(severity=AlertSeverity.WARNING)
        assert len(warnings) == 1
        assert warnings[0].name == "warn"

    def test_get_summary(self):
        mon = IntegrationMonitor("test")
        mon.record_counter("requests", 5)
        mon.record_gauge("cpu", 50)
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true))
        summary = mon.get_summary()
        assert summary["name"] == "test"
        assert summary["overall_health"] == "healthy"
        assert summary["counter_count"] == 1
        assert summary["gauge_count"] == 1

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true, interval=0.01))
        await mon.start_monitoring(interval=0.01)
        await asyncio.sleep(0.05)
        await mon.stop_monitoring()
        assert mon._running is False

    def test_clear(self):
        mon = IntegrationMonitor("test")
        mon.record_counter("x", 1)
        mon.clear()
        assert mon.get_counter("x") == 0.0

    def test_metric_snapshot_to_dict(self):
        snap = MetricSnapshot(
            name="test", value=42.0, metric_type=MetricType.GAUGE,
            labels={"env": "prod"}, unit="ms",
        )
        d = snap.to_dict()
        assert d["name"] == "test"
        assert d["value"] == 42.0
        assert d["type"] == "gauge"
        assert d["unit"] == "ms"

    def test_alert_to_dict(self):
        from apex_os_bp.integration_hub.monitoring import Alert
        alert = Alert(name="test", severity=AlertSeverity.WARNING, message="msg")
        d = alert.to_dict()
        assert d["name"] == "test"
        assert d["severity"] == "warning"
        assert d["message"] == "msg"

    def test_remove_alert_rule(self):
        mon = IntegrationMonitor("test")
        mon.add_alert_rule(AlertRule(name="r", metric_name="m", condition=">", threshold=0))
        mon.remove_alert_rule("r")
        assert len(mon._alert_rules) == 0

    def test_remove_health_check(self):
        mon = IntegrationMonitor("test")
        mon.register_health_check(HealthCheck(name="a", check_fn=_async_true))
        mon.unregister_health_check("a")
        assert "a" not in mon.get_health_check_status()

    def test_unregister_nonexistent(self):
        mon = IntegrationMonitor("test")
        mon.unregister_health_check("nonexistent")  # Should not raise


# ── Helper Functions ──


async def _async_noop(*args, **kwargs):
    return None


def _async_return_value(val):
    async def handler(results):
        return val
    return handler


async def _async_true():
    return True


async def _async_false():
    return False
