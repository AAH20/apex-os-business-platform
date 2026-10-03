"""Tests for Continuous BI advanced features."""
import pytest
from apex_os_bp.continuous_bi.advanced import (
    AlertEngine, AlertRule, ZScoreAnomalyDetector,
    LinearPredictor, NLQueryEngine, CollaborativeFilter,
)


class TestAlertEngine:
    def test_rule_triggers(self):
        engine = AlertEngine()
        engine.add_rule(AlertRule("high_temp", lambda e: e.get("temp", 0) > 100, "critical"))
        alerts = engine.evaluate({"temp": 120, "timestamp": 1.0})
        assert len(alerts) == 1
        assert alerts[0].rule == "high_temp"
        assert alerts[0].severity == "critical"

    def test_no_trigger(self):
        engine = AlertEngine()
        engine.add_rule(AlertRule("high_temp", lambda e: e.get("temp", 0) > 100))
        assert engine.evaluate({"temp": 50}) == []

    def test_handler_called(self):
        engine = AlertEngine()
        received = []
        engine.on_alert(received.append)
        engine.add_rule(AlertRule("r", lambda e: True))
        engine.evaluate({"x": 1})
        assert len(received) == 1


class TestZScoreAnomalyDetector:
    def test_normal_values(self):
        d = ZScoreAnomalyDetector(threshold=3.0)
        assert not d.update(10.0)
        assert not d.update(11.0)
        assert not d.update(10.5)

    def test_anomaly_detected(self):
        d = ZScoreAnomalyDetector(threshold=2.0)
        d.update(10.0)
        d.update(11.0)
        d.update(10.5)
        assert d.update(100.0)


class TestLinearPredictor:
    def test_perfect_line(self):
        p = LinearPredictor()
        p.fit([1, 2, 3], [2, 4, 6])
        assert p.predict(4) == pytest.approx(8.0)

    def test_empty(self):
        p = LinearPredictor()
        assert p.predict(5) == 0.0


class TestNLQueryEngine:
    def test_avg_query(self):
        nl = NLQueryEngine()
        nl.register("revenue", [10, 20, 30])
        result = nl.query("what is the average revenue")
        assert result["revenue"] == pytest.approx(20.0)

    def test_max_query(self):
        nl = NLQueryEngine()
        nl.register("sales", [5, 15, 10])
        result = nl.query("max sales")
        assert result["sales"] == 15

    def test_no_match(self):
        nl = NLQueryEngine()
        nl.register("revenue", [1, 2, 3])
        assert nl.query("unknown metric") == {}


class TestCollaborativeFilter:
    def test_recommendation(self):
        cf = CollaborativeFilter()
        cf.add_rating("alice", "item1", 5.0)
        cf.add_rating("alice", "item2", 3.0)
        cf.add_rating("bob", "item1", 4.0)
        cf.add_rating("bob", "item3", 5.0)
        recs = cf.recommend("alice")
        assert len(recs) == 1
        assert recs[0][0] == "item3"

    def test_no_recommendations(self):
        cf = CollaborativeFilter()
        cf.add_rating("alice", "item1", 5.0)
        assert cf.recommend("bob") == []
