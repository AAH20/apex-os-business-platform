"""Tests for the tracing system."""
import time
import pytest
from apex_os_bp.tracing.span import Span, SpanContext, SpanEvent, SpanKind, SpanStatus
from apex_os_bp.tracing.sampling import (
    SamplingDecision,
    SamplingStrategy,
    AlwaysOffSampler,
    AlwaysOnSampler,
    RateBasedSampler,
    ProbabilisticSampler,
    TailBasedSampler,
)
from apex_os_bp.tracing.distributed_tracing import (
    DistributedTracer,
    TraceContext,
    inject_context,
    extract_context,
)
from apex_os_bp.tracing.analytics import TraceAnalytics, TraceSummary, ServiceMetrics
from apex_os_bp.tracing.visualization import TraceVisualizer, TraceTree


# ===========================================================================
# Span Management Tests
# ===========================================================================


class TestSpan:
    """Test span creation and lifecycle."""

    def test_span_creation_defaults(self):
        span = Span("test-op")
        assert span.name == "test-op"
        assert span.trace_id is not None
        assert span.span_id is not None
        assert span.parent_span_id is None
        assert span.kind == SpanKind.INTERNAL
        assert span.status == SpanStatus.UNSET
        assert span.is_recording is True

    def test_span_unique_ids(self):
        s1 = Span("op1")
        s2 = Span("op2")
        assert s1.span_id != s2.span_id
        assert s1.trace_id != s2.trace_id

    def test_span_with_explicit_ids(self):
        span = Span("op", trace_id="abc123", span_id="def456")
        assert span.trace_id == "abc123"
        assert span.span_id == "def456"

    def test_span_with_parent(self):
        parent = Span("parent")
        child = Span("child", trace_id=parent.trace_id, parent_span_id=parent.span_id)
        assert child.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id

    def test_span_set_attribute(self):
        span = Span("op")
        span.set_attribute("key", "value")
        assert span.attributes["key"] == "value"

    def test_span_set_attributes(self):
        span = Span("op")
        span.set_attributes({"a": 1, "b": 2})
        assert span.attributes["a"] == 1
        assert span.attributes["b"] == 2

    def test_span_add_event(self):
        span = Span("op")
        span.add_event("test-event", {"k": "v"})
        assert len(span.events) == 1
        assert span.events[0].name == "test-event"
        assert span.events[0].attributes["k"] == "v"

    def test_span_add_link(self):
        span = Span("op")
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span.add_link(ctx, {"rel": "test"})
        assert len(span.links) == 1
        assert span.links[0].context.trace_id == "t1"

    def test_span_set_status(self):
        span = Span("op")
        span.set_status(SpanStatus.OK)
        assert span.status == SpanStatus.OK

    def test_span_set_status_with_message(self):
        span = Span("op")
        span.set_status(SpanStatus.ERROR, "something failed")
        assert span.status == SpanStatus.ERROR
        assert span.status_message == "something failed"

    def test_span_record_exception(self):
        span = Span("op")
        try:
            raise ValueError("test error")
        except ValueError as e:
            span.record_exception(e)
        assert span.status == SpanStatus.ERROR
        assert span.status_message == "test error"
        assert len(span.events) == 1
        assert span.events[0].name == "exception"

    def test_span_end(self):
        span = Span("op")
        span.end()
        assert span.is_recording is False
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

    def test_span_end_idempotent(self):
        span = Span("op")
        span.end()
        end_time = span.end_time
        span.end()
        assert span.end_time == end_time

    def test_span_duration(self):
        span = Span("op")
        time.sleep(0.01)
        span.end()
        assert span.duration_ms >= 10.0

    def test_span_context_property(self):
        span = Span("op", trace_id="t1", span_id="s1")
        ctx = span.context
        assert ctx.trace_id == "t1"
        assert ctx.span_id == "s1"

    def test_span_to_dict(self):
        span = Span("op", trace_id="t1", span_id="s1")
        span.set_attribute("k", "v")
        span.end()
        d = span.to_dict()
        assert d["name"] == "op"
        assert d["trace_id"] == "t1"
        assert d["span_id"] == "s1"
        assert d["attributes"]["k"] == "v"
        assert d["end_time"] is not None

    def test_span_from_dict(self):
        span = Span("op", trace_id="t1", span_id="s1", parent_span_id="p1")
        span.set_attribute("k", "v")
        span.add_event("evt")
        span.set_status(SpanStatus.OK)
        span.end()
        d = span.to_dict()
        restored = Span.from_dict(d)
        assert restored.name == "op"
        assert restored.trace_id == "t1"
        assert restored.span_id == "s1"
        assert restored.parent_span_id == "p1"
        assert restored.attributes["k"] == "v"
        assert len(restored.events) == 1
        assert restored.status == SpanStatus.OK

    def test_span_repr(self):
        span = Span("my-op", trace_id="t1", span_id="s1")
        r = repr(span)
        assert "my-op" in r
        assert "t1" in r
        assert "s1" in r


class TestSpanContext:
    """Test span context."""

    def test_context_creation(self):
        ctx = SpanContext(trace_id="t1", span_id="s1")
        assert ctx.trace_id == "t1"
        assert ctx.span_id == "s1"
        assert ctx.trace_flags == 1

    def test_context_to_dict(self):
        ctx = SpanContext(trace_id="t1", span_id="s1", trace_state={"k": "v"})
        d = ctx.to_dict()
        assert d["trace_id"] == "t1"
        assert d["span_id"] == "s1"
        assert d["trace_state"]["k"] == "v"

    def test_context_from_dict(self):
        ctx = SpanContext(trace_id="t1", span_id="s1", trace_state={"k": "v"})
        d = ctx.to_dict()
        restored = SpanContext.from_dict(d)
        assert restored.trace_id == "t1"
        assert restored.span_id == "s1"
        assert restored.trace_state["k"] == "v"


# ===========================================================================
# Sampling Tests
# ===========================================================================


class TestAlwaysOnSampler:
    def test_samples_everything(self):
        sampler = AlwaysOnSampler()
        for i in range(100):
            decision = sampler.should_sample(f"trace-{i}", "op")
            assert decision.sampled is True


class TestAlwaysOffSampler:
    def test_samples_nothing(self):
        sampler = AlwaysOffSampler()
        for i in range(100):
            decision = sampler.should_sample(f"trace-{i}", "op")
            assert decision.sampled is False


class TestRateBasedSampler:
    def test_samples_within_rate(self):
        sampler = RateBasedSampler(samples_per_second=1000.0)
        # Should sample many with high rate
        sampled_count = sum(1 for _ in range(100) if sampler.should_sample("t", "op").sampled)
        assert sampled_count > 50

    def test_rate_limits(self):
        sampler = RateBasedSampler(samples_per_second=1.0)
        # First sample should succeed
        assert sampler.should_sample("t1", "op").sampled is True
        # Immediate second should fail (token bucket empty)
        assert sampler.should_sample("t2", "op").sampled is False

    def test_token_refill(self):
        sampler = RateBasedSampler(samples_per_second=100.0)
        # Exhaust tokens
        for _ in range(100):
            sampler.should_sample("t", "op")
        # Wait for refill
        time.sleep(0.05)
        # Should have tokens now
        assert sampler.should_sample("t", "op").sampled is True


class TestProbabilisticSampler:
    def test_probability_one(self):
        sampler = ProbabilisticSampler(probability=1.0)
        for _ in range(100):
            assert sampler.should_sample("t", "op").sampled is True

    def test_probability_zero(self):
        sampler = ProbabilisticSampler(probability=0.0)
        for _ in range(100):
            assert sampler.should_sample("t", "op").sampled is False

    def test_probability_half(self):
        sampler = ProbabilisticSampler(probability=0.5)
        sampled = sum(1 for _ in range(1000) if sampler.should_sample("t", "op").sampled)
        # Should be roughly 500, allow wide margin
        assert 300 < sampled < 700

    def test_invalid_probability(self):
        with pytest.raises(ValueError):
            ProbabilisticSampler(probability=1.5)
        with pytest.raises(ValueError):
            ProbabilisticSampler(probability=-0.1)


class TestTailBasedSampler:
    def test_sample_errors(self):
        sampler = TailBasedSampler(sample_errors=True)
        decision = sampler.should_sample("t", "op", {"error": True})
        assert decision.sampled is True

    def test_no_sample_without_error(self):
        sampler = TailBasedSampler(sample_errors=True)
        decision = sampler.should_sample("t", "op", {"error": False})
        assert decision.sampled is False

    def test_duration_threshold(self):
        sampler = TailBasedSampler(duration_threshold_ms=100.0)
        decision = sampler.should_sample_completed_trace(150.0, False)
        assert decision.sampled is True

    def test_below_duration_threshold(self):
        sampler = TailBasedSampler(duration_threshold_ms=100.0)
        decision = sampler.should_sample_completed_trace(50.0, False)
        assert decision.sampled is False

    def test_attribute_rules(self):
        sampler = TailBasedSampler(attribute_rules={"env": "prod"})
        decision = sampler.should_sample("t", "op", {"env": "prod"})
        assert decision.sampled is True

    def test_attribute_rules_no_match(self):
        sampler = TailBasedSampler(attribute_rules={"env": "prod"})
        decision = sampler.should_sample("t", "op", {"env": "dev"})
        assert decision.sampled is False

    def test_completed_trace_with_error(self):
        sampler = TailBasedSampler(sample_errors=True)
        decision = sampler.should_sample_completed_trace(10.0, True)
        assert decision.sampled is True


# ===========================================================================
# Distributed Tracing Tests
# ===========================================================================


class TestTraceContext:
    def test_creation(self):
        ctx = TraceContext(trace_id="t1", span_id="s1")
        assert ctx.trace_id == "t1"
        assert ctx.span_id == "s1"
        assert ctx.trace_flags == 1

    def test_to_dict(self):
        ctx = TraceContext(trace_id="t1", span_id="s1", baggage={"k": "v"})
        d = ctx.to_dict()
        assert d["trace_id"] == "t1"
        assert d["baggage"]["k"] == "v"

    def test_from_dict(self):
        ctx = TraceContext(trace_id="t1", span_id="s1", baggage={"k": "v"})
        d = ctx.to_dict()
        restored = TraceContext.from_dict(d)
        assert restored.trace_id == "t1"
        assert restored.baggage["k"] == "v"


class TestDistributedTracer:
    def test_creation(self):
        tracer = DistributedTracer("test-service")
        assert tracer.service_name == "test-service"

    def test_start_span(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op")
        assert span.name == "op"
        assert span.attributes["service.name"] == "svc"

    def test_start_span_with_kind(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op", kind=SpanKind.SERVER)
        assert span.kind == SpanKind.SERVER

    def test_start_span_with_attributes(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op", attributes={"custom": "value"})
        assert span.attributes["custom"] == "value"

    def test_start_span_with_parent_context(self):
        tracer = DistributedTracer("svc")
        parent_ctx = TraceContext(trace_id="parent-t", span_id="parent-s")
        span = tracer.start_span("child", parent_context=parent_ctx)
        assert span.trace_id == "parent-t"
        assert span.parent_span_id == "parent-s"

    def test_end_span(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op")
        tracer.end_span(span)
        assert span.is_recording is False
        assert span in tracer.get_completed_spans()

    def test_span_context_manager(self):
        tracer = DistributedTracer("svc")
        with tracer.span("op") as span:
            assert span.is_recording is True
        assert span.is_recording is False

    def test_span_context_manager_with_exception(self):
        tracer = DistributedTracer("svc")
        with pytest.raises(ValueError):
            with tracer.span("op") as span:
                raise ValueError("test")
        assert span.status == SpanStatus.ERROR

    def test_inject_context(self):
        tracer = DistributedTracer("svc")
        ctx = TraceContext(trace_id="t1", span_id="s1")
        carrier = tracer.inject_context(ctx)
        assert carrier["x-trace-id"] == "t1"
        assert carrier["x-span-id"] == "s1"

    def test_inject_context_with_state(self):
        tracer = DistributedTracer("svc")
        ctx = TraceContext(trace_id="t1", span_id="s1", trace_state={"k": "v"})
        carrier = tracer.inject_context(ctx)
        assert "x-trace-state" in carrier

    def test_inject_context_with_baggage(self):
        tracer = DistributedTracer("svc")
        ctx = TraceContext(trace_id="t1", span_id="s1", baggage={"user": "u1"})
        carrier = tracer.inject_context(ctx)
        assert "x-baggage" in carrier

    def test_inject_empty_context(self):
        tracer = DistributedTracer("svc")
        carrier = tracer.inject_context()
        assert carrier == {}

    def test_extract_context(self):
        tracer = DistributedTracer("svc")
        carrier = {"x-trace-id": "t1", "x-span-id": "s1", "x-trace-flags": "1"}
        ctx = tracer.extract_context(carrier)
        assert ctx is not None
        assert ctx.trace_id == "t1"
        assert ctx.span_id == "s1"

    def test_extract_context_with_state(self):
        tracer = DistributedTracer("svc")
        carrier = {
            "x-trace-id": "t1",
            "x-span-id": "s1",
            "x-trace-state": "k1=v1,k2=v2",
        }
        ctx = tracer.extract_context(carrier)
        assert ctx.trace_state["k1"] == "v1"
        assert ctx.trace_state["k2"] == "v2"

    def test_extract_context_with_baggage(self):
        tracer = DistributedTracer("svc")
        carrier = {
            "x-trace-id": "t1",
            "x-span-id": "s1",
            "x-baggage": "user=u1,session=s1",
        }
        ctx = tracer.extract_context(carrier)
        assert ctx.baggage["user"] == "u1"
        assert ctx.baggage["session"] == "s1"

    def test_extract_empty_context(self):
        tracer = DistributedTracer("svc")
        ctx = tracer.extract_context({})
        assert ctx is None

    def test_extract_missing_trace_id(self):
        tracer = DistributedTracer("svc")
        ctx = tracer.extract_context({"x-span-id": "s1"})
        assert ctx is None

    def test_roundtrip_inject_extract(self):
        tracer = DistributedTracer("svc")
        original = TraceContext(
            trace_id="t1",
            span_id="s1",
            trace_state={"k": "v"},
            baggage={"user": "u1"},
        )
        carrier = tracer.inject_context(original)
        extracted = tracer.extract_context(carrier)
        assert extracted.trace_id == original.trace_id
        assert extracted.span_id == original.span_id
        assert extracted.trace_state["k"] == "v"
        assert extracted.baggage["user"] == "u1"

    def test_set_current_context(self):
        tracer = DistributedTracer("svc")
        ctx = TraceContext(trace_id="t1", span_id="s1")
        tracer.set_current_context(ctx)
        assert tracer.get_current_context() is not None
        assert tracer.get_current_context().trace_id == "t1"

    def test_clear_current_context(self):
        tracer = DistributedTracer("svc")
        ctx = TraceContext(trace_id="t1", span_id="s1")
        tracer.set_current_context(ctx)
        tracer.clear_current_context()
        assert tracer.get_current_context() is None

    def test_child_span_inherits_context(self):
        tracer = DistributedTracer("svc")
        parent = tracer.start_span("parent")
        tracer.set_current_context(parent.context)
        child = tracer.start_span("child")
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id

    def test_get_active_spans(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op")
        active = tracer.get_active_spans()
        assert span in active

    def test_get_completed_spans(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op")
        tracer.end_span(span)
        completed = tracer.get_completed_spans()
        assert span in completed

    def test_get_completed_spans_by_trace(self):
        tracer = DistributedTracer("svc")
        span1 = tracer.start_span("op1")
        tracer.end_span(span1)
        other_ctx = TraceContext(trace_id="other-trace", span_id="other-s")
        span2 = tracer.start_span("op2", parent_context=other_ctx)
        tracer.end_span(span2)
        completed = tracer.get_completed_spans(span1.trace_id)
        assert span1 in completed
        assert span2 not in completed

    def test_get_trace(self):
        tracer = DistributedTracer("svc")
        span1 = tracer.start_span("op1")
        tracer.end_span(span1)
        span1_ctx = TraceContext(trace_id=span1.trace_id, span_id="new-parent")
        span2 = tracer.start_span("op2", parent_context=span1_ctx)
        tracer.end_span(span2)
        trace_spans = tracer.get_trace(span1.trace_id)
        assert len(trace_spans) == 2

    def test_clear_completed(self):
        tracer = DistributedTracer("svc")
        span = tracer.start_span("op")
        tracer.end_span(span)
        tracer.clear_completed()
        assert tracer.get_completed_spans() == []

    def test_sampling_strategy_override(self):
        tracer = DistributedTracer("svc", sampling_strategy=AlwaysOffSampler())
        span = tracer.start_span("op")
        assert span.attributes["sampling.sampled"] is False

    def test_module_level_inject(self):
        ctx = TraceContext(trace_id="t1", span_id="s1")
        carrier = inject_context(ctx)
        assert carrier["x-trace-id"] == "t1"

    def test_module_level_extract(self):
        carrier = {"x-trace-id": "t1", "x-span-id": "s1"}
        ctx = extract_context(carrier)
        assert ctx.trace_id == "t1"


# ===========================================================================
# Analytics Tests
# ===========================================================================


class TestTraceAnalytics:
    def _make_span(self, name, trace_id="t1", parent_id=None, duration_ms=10.0,
                   status=SpanStatus.OK, service="svc1", kind=SpanKind.INTERNAL):
        span = Span(name, trace_id=trace_id, parent_span_id=parent_id, kind=kind)
        span.set_attribute("service.name", service)
        span.set_status(status)
        span._start_time = 1000.0
        span._end_time = 1000.0 + duration_ms / 1000.0
        return span

    def test_add_span(self):
        analytics = TraceAnalytics()
        span = self._make_span("op")
        analytics.add_span(span)
        summaries = analytics.get_trace_summaries()
        assert len(summaries) == 1

    def test_add_spans(self):
        analytics = TraceAnalytics()
        spans = [self._make_span("op1"), self._make_span("op2")]
        analytics.add_spans(spans)
        summaries = analytics.get_trace_summaries()
        assert len(summaries) == 1  # Same trace_id

    def test_clear(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op"))
        analytics.clear()
        assert analytics.get_trace_summaries() == []

    def test_trace_summary(self):
        analytics = TraceAnalytics()
        span = self._make_span("op", duration_ms=50.0)
        analytics.add_span(span)
        summaries = analytics.get_trace_summaries()
        assert summaries[0].trace_id == span.trace_id
        assert summaries[0].span_count == 1
        assert summaries[0].duration_ms == pytest.approx(50.0, abs=1.0)

    def test_trace_summary_with_error(self):
        analytics = TraceAnalytics()
        span = self._make_span("op", status=SpanStatus.ERROR)
        analytics.add_span(span)
        summaries = analytics.get_trace_summaries()
        assert summaries[0].has_error is True

    def test_service_metrics(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", service="svc1"))
        analytics.add_span(self._make_span("op2", service="svc1"))
        analytics.add_span(self._make_span("op3", service="svc2"))
        metrics = analytics.get_service_metrics()
        assert metrics["svc1"].total_spans == 2
        assert metrics["svc2"].total_spans == 1

    def test_service_error_rate(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", service="svc1", status=SpanStatus.ERROR))
        analytics.add_span(self._make_span("op2", service="svc1", status=SpanStatus.OK))
        metrics = analytics.get_service_metrics()
        assert metrics["svc1"].error_rate == pytest.approx(0.5)

    def test_service_duration_stats(self):
        analytics = TraceAnalytics()
        for d in [10.0, 20.0, 30.0, 40.0, 50.0]:
            analytics.add_span(self._make_span(f"op{d}", service="svc1", duration_ms=d))
        metrics = analytics.get_service_metrics()
        assert metrics["svc1"].avg_duration_ms == pytest.approx(30.0)
        assert metrics["svc1"].p50_duration_ms == pytest.approx(30.0)

    def test_get_error_traces(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", trace_id="t1", status=SpanStatus.ERROR))
        analytics.add_span(self._make_span("op2", trace_id="t2", status=SpanStatus.OK))
        error_traces = analytics.get_error_traces()
        assert error_traces == ["t1"]

    def test_get_slow_traces(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", trace_id="t1", duration_ms=50.0))
        analytics.add_span(self._make_span("op2", trace_id="t2", duration_ms=2000.0))
        slow = analytics.get_slow_traces(threshold_ms=1000.0)
        assert len(slow) == 1
        assert slow[0][0] == "t2"

    def test_get_service_dependencies(self):
        analytics = TraceAnalytics()
        parent = self._make_span("parent", service="svc1")
        child = self._make_span("child", trace_id=parent.trace_id,
                                parent_id=parent.span_id, service="svc2")
        analytics.add_spans([parent, child])
        deps = analytics.get_service_dependencies()
        assert "svc2" in deps.get("svc1", set())

    def test_get_span_kind_distribution(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", kind=SpanKind.SERVER))
        analytics.add_span(self._make_span("op2", kind=SpanKind.CLIENT))
        analytics.add_span(self._make_span("op3", kind=SpanKind.SERVER))
        dist = analytics.get_span_kind_distribution()
        assert dist["server"] == 2
        assert dist["client"] == 1

    def test_get_overall_stats(self):
        analytics = TraceAnalytics()
        analytics.add_span(self._make_span("op1", service="svc1", duration_ms=10.0))
        analytics.add_span(self._make_span("op2", service="svc2", duration_ms=20.0,
                                           status=SpanStatus.ERROR))
        stats = analytics.get_overall_stats()
        assert stats["total_spans"] == 2
        assert stats["total_traces"] == 1
        assert stats["error_count"] == 1
        assert stats["error_rate"] == pytest.approx(0.5)
        assert "svc1" in stats["services"]
        assert "svc2" in stats["services"]

    def test_empty_analytics(self):
        analytics = TraceAnalytics()
        stats = analytics.get_overall_stats()
        assert stats["total_spans"] == 0
        assert stats["total_traces"] == 0


class TestServiceMetrics:
    def test_to_dict(self):
        sm = ServiceMetrics(service_name="svc1", total_spans=10, error_count=2)
        sm.durations_ms = [10.0, 20.0, 30.0]
        d = sm.to_dict()
        assert d["service_name"] == "svc1"
        assert d["total_spans"] == 10
        assert d["error_count"] == 2
        assert d["error_rate"] == pytest.approx(0.2)

    def test_empty_metrics(self):
        sm = ServiceMetrics(service_name="svc1")
        assert sm.error_rate == 0.0
        assert sm.avg_duration_ms == 0.0
        assert sm.p50_duration_ms == 0.0


# ===========================================================================
# Visualization Tests
# ===========================================================================


class TestTraceVisualizer:
    def _make_span(self, name, trace_id="t1", parent_id=None, duration_ms=10.0,
                   status=SpanStatus.OK, kind=SpanKind.INTERNAL, service="svc1"):
        span = Span(name, trace_id=trace_id, parent_span_id=parent_id, kind=kind)
        span.set_attribute("service.name", service)
        span.set_status(status)
        span._start_time = 1000.0
        span._end_time = 1000.0 + duration_ms / 1000.0
        return span

    def test_render_tree(self):
        viz = TraceVisualizer()
        parent = self._make_span("parent")
        child = self._make_span("child", trace_id=parent.trace_id, parent_id=parent.span_id)
        result = viz.render_tree([parent, child])
        assert "parent" in result
        assert "child" in result

    def test_render_tree_empty(self):
        viz = TraceVisualizer()
        result = viz.render_tree([])
        assert result == "(no spans)"

    def test_render_timeline(self):
        viz = TraceVisualizer()
        spans = [self._make_span("op1", duration_ms=50.0)]
        result = viz.render_timeline(spans)
        assert "op1" in result
        assert "50.0ms" in result

    def test_render_timeline_empty(self):
        viz = TraceVisualizer()
        result = viz.render_timeline([])
        assert result == "(no spans)"

    def test_render_summary(self):
        viz = TraceVisualizer()
        spans = [self._make_span("op1", duration_ms=10.0)]
        result = viz.render_summary(spans)
        assert "Trace Summary" in result
        assert "Total Spans" in result

    def test_render_summary_empty(self):
        viz = TraceVisualizer()
        result = viz.render_summary([])
        assert result == "(no spans)"

    def test_render_span_details(self):
        viz = TraceVisualizer()
        span = self._make_span("op1", duration_ms=10.0)
        span.set_attribute("key", "value")
        result = viz.render_span_details(span)
        assert "op1" in result
        assert "key" in result
        assert "value" in result

    def test_render_flat(self):
        viz = TraceVisualizer()
        parent = self._make_span("parent")
        child = self._make_span("child", trace_id=parent.trace_id, parent_id=parent.span_id)
        result = viz.render_flat([parent, child])
        assert "parent" in result
        assert "child" in result

    def test_render_flat_empty(self):
        viz = TraceVisualizer()
        result = viz.render_flat([])
        assert result == "(no spans)"

    def test_status_indicator_error(self):
        viz = TraceVisualizer()
        span = self._make_span("op", status=SpanStatus.ERROR)
        indicator = viz._status_indicator(span)
        assert indicator == "❌"

    def test_status_indicator_ok(self):
        viz = TraceVisualizer()
        span = self._make_span("op", status=SpanStatus.OK)
        indicator = viz._status_indicator(span)
        assert indicator == "✅"

    def test_truncate(self):
        viz = TraceVisualizer()
        result = viz._truncate("hello world", 8)
        assert result == "hello..."

    def test_truncate_short_text(self):
        viz = TraceVisualizer()
        result = viz._truncate("hi", 8)
        assert result == "hi"


class TestTraceTree:
    def test_creation(self):
        span = Span("op")
        tree = TraceTree(span=span)
        assert tree.span == span
        assert tree.children == []

    def test_add_child(self):
        span = Span("op")
        tree = TraceTree(span=span)
        child_span = Span("child")
        child_tree = TraceTree(span=child_span)
        tree.add_child(child_tree)
        assert len(tree.children) == 1
        assert tree.children[0].span == child_span

    def test_to_dict(self):
        span = Span("op")
        tree = TraceTree(span=span)
        d = tree.to_dict()
        assert d["span"]["name"] == "op"
        assert d["children"] == []
