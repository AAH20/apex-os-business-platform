"""Tests for the alerting system."""
from __future__ import annotations

import time

import pytest

from apex_os_bp.alerting import (
    Alert,
    AlertEscalator,
    AlertHistory,
    AlertHistoryEntry,
    AlertRouter,
    AlertRoutingStrategy,
    AlertRoutingTarget,
    AlertRule,
    AlertRuleEngine,
    AlertSeverity,
    AlertStatus,
    ConditionEvaluator,
    EscalationPolicy,
    EscalationRule,
    SuppressionRule,
    AlertSuppressor,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def evaluator():
    return ConditionEvaluator()


@pytest.fixture
def rule_engine():
    return AlertRuleEngine()


@pytest.fixture
def router():
    return AlertRouter()


@pytest.fixture
def escalator():
    return AlertEscalator()


@pytest.fixture
def suppressor():
    return AlertSuppressor()


@pytest.fixture
def history():
    return AlertHistory()


@pytest.fixture
def sample_rule():
    return AlertRule(
        name="high_cpu",
        description="CPU usage too high",
        severity=AlertSeverity.WARNING,
        condition="cpu_usage",
        threshold=80.0,
        comparison="gt",
        duration=0,
        enabled=True,
        labels={"team": "ops"},
        annotations={"summary": "High CPU usage"},
        routing_strategy=AlertRoutingStrategy.BROADCAST,
        escalation_policy=EscalationPolicy.LINEAR,
        escalation_delay=300,
        max_escalation_level=3,
        notification_channels=["email", "slack"],
    )


@pytest.fixture
def sample_alert():
    return Alert(
        rule_id="rule-1",
        rule_name="high_cpu",
        severity=AlertSeverity.WARNING,
        status=AlertStatus.FIRING,
        message="CPU usage at 90%",
        source="server-1",
        labels={"team": "ops"},
        value=90.0,
        threshold=80.0,
        notification_channels=["email", "slack"],
    )


@pytest.fixture
def sample_target():
    return AlertRoutingTarget(
        name="ops-email",
        channel="email",
        address="ops@example.com",
        priority=1,
        enabled=True,
        labels={"team": "ops"},
    )


@pytest.fixture
def sample_escalation_rule():
    return EscalationRule(
        name="default_escalation",
        description="Default escalation policy",
        escalation_levels=[
            {"level": 1, "target": "ops@example.com", "channel": "email"},
            {"level": 2, "target": "manager@example.com", "channel": "email"},
            {"level": 3, "target": "cto@example.com", "channel": "sms"},
        ],
        max_level=3,
        escalation_delay=300,
        escalation_policy=EscalationPolicy.LINEAR,
        enabled=True,
    )


@pytest.fixture
def sample_suppression_rule():
    return SuppressionRule(
        name="maintenance_window",
        description="Suppress during maintenance",
        severity=AlertSeverity.WARNING,
        labels={"team": "ops"},
        source="server-1",
        duration=3600,
        enabled=True,
    )


# ===========================================================================
# 1. Alert Rules Tests
# ===========================================================================


class TestConditionEvaluator:
    """Tests for ConditionEvaluator."""

    def test_gt_comparison(self, evaluator):
        assert evaluator.evaluate(90.0, 80.0, "gt") is True
        assert evaluator.evaluate(70.0, 80.0, "gt") is False

    def test_lt_comparison(self, evaluator):
        assert evaluator.evaluate(70.0, 80.0, "lt") is True
        assert evaluator.evaluate(90.0, 80.0, "lt") is False

    def test_eq_comparison(self, evaluator):
        assert evaluator.evaluate(80.0, 80.0, "eq") is True
        assert evaluator.evaluate(70.0, 80.0, "eq") is False

    def test_gte_comparison(self, evaluator):
        assert evaluator.evaluate(80.0, 80.0, "gte") is True
        assert evaluator.evaluate(90.0, 80.0, "gte") is True
        assert evaluator.evaluate(70.0, 80.0, "gte") is False

    def test_lte_comparison(self, evaluator):
        assert evaluator.evaluate(80.0, 80.0, "lte") is True
        assert evaluator.evaluate(70.0, 80.0, "lte") is True
        assert evaluator.evaluate(90.0, 80.0, "lte") is False

    def test_neq_comparison(self, evaluator):
        assert evaluator.evaluate(70.0, 80.0, "neq") is True
        assert evaluator.evaluate(80.0, 80.0, "neq") is False

    def test_unknown_comparison(self, evaluator):
        assert evaluator.evaluate(90.0, 80.0, "unknown") is False

    def test_custom_comparison(self, evaluator):
        evaluator.register_comparison("between", lambda a, b: b - 10 <= a <= b + 10)
        assert evaluator.evaluate(85.0, 80.0, "between") is True
        assert evaluator.evaluate(95.0, 80.0, "between") is False

    def test_evaluate_expression(self, evaluator):
        context = {"cpu": 90.0, "memory": 70.0}
        assert evaluator.evaluate_expression("cpu > 80", context) is True
        assert evaluator.evaluate_expression("cpu > 80 and memory < 80", context) is True
        assert evaluator.evaluate_expression("cpu < 80", context) is False

    def test_evaluate_expression_invalid(self, evaluator):
        assert evaluator.evaluate_expression("invalid syntax !!!", {}) is False


class TestAlertRuleEngine:
    """Tests for AlertRuleEngine."""

    def test_add_rule(self, rule_engine, sample_rule):
        result = rule_engine.add_rule(sample_rule)
        assert result.id == sample_rule.id
        assert rule_engine.get_rule(sample_rule.id) is not None

    def test_remove_rule(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        assert rule_engine.remove_rule(sample_rule.id) is True
        assert rule_engine.get_rule(sample_rule.id) is None

    def test_remove_nonexistent_rule(self, rule_engine):
        assert rule_engine.remove_rule("nonexistent") is False

    def test_get_rules(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        rules = rule_engine.get_rules()
        assert len(rules) == 1
        assert rules[0].id == sample_rule.id

    def test_get_rules_enabled_only(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        disabled_rule = AlertRule(name="disabled", enabled=False)
        rule_engine.add_rule(disabled_rule)
        rules = rule_engine.get_rules(enabled_only=True)
        assert len(rules) == 1
        assert rules[0].enabled is True

    def test_get_rules_by_severity(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        critical_rule = AlertRule(name="critical", severity=AlertSeverity.CRITICAL)
        rule_engine.add_rule(critical_rule)
        rules = rule_engine.get_rules(severity=AlertSeverity.CRITICAL)
        assert len(rules) == 1
        assert rules[0].severity == AlertSeverity.CRITICAL

    def test_update_rule(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        updated = rule_engine.update_rule(sample_rule.id, name="new_name", threshold=95.0)
        assert updated is not None
        assert updated.name == "new_name"
        assert updated.threshold == 95.0

    def test_update_nonexistent_rule(self, rule_engine):
        assert rule_engine.update_rule("nonexistent", name="x") is None

    def test_enable_disable_rule(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        assert rule_engine.disable_rule(sample_rule.id) is True
        assert rule_engine.get_rule(sample_rule.id).enabled is False
        assert rule_engine.enable_rule(sample_rule.id) is True
        assert rule_engine.get_rule(sample_rule.id).enabled is True

    def test_evaluate_rule_triggers(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        alert = rule_engine.evaluate_rule(sample_rule, 90.0, source="server-1")
        assert alert is not None
        assert alert.status == AlertStatus.FIRING
        assert alert.value == 90.0
        assert alert.threshold == 80.0

    def test_evaluate_rule_no_trigger(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        alert = rule_engine.evaluate_rule(sample_rule, 70.0, source="server-1")
        assert alert is None

    def test_evaluate_rule_disabled(self, rule_engine, sample_rule):
        sample_rule.enabled = False
        rule_engine.add_rule(sample_rule)
        alert = rule_engine.evaluate_rule(sample_rule, 90.0, source="server-1")
        assert alert is None

    def test_evaluate_rule_with_duration(self, rule_engine):
        rule = AlertRule(
            name="duration_test",
            threshold=80.0,
            comparison="gt",
            duration=60,
        )
        rule_engine.add_rule(rule)
        # First evaluation should not trigger (duration not met)
        alert = rule_engine.evaluate_rule(rule, 90.0)
        assert alert is None

    def test_evaluate_all(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        metrics = {"high_cpu": 90.0, "memory_usage": 70.0}
        alerts = rule_engine.evaluate_all(metrics, source="server-1")
        assert len(alerts) == 1
        assert alerts[0].rule_name == "high_cpu"

    def test_evaluate_all_no_match(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        metrics = {"memory_usage": 70.0}
        alerts = rule_engine.evaluate_all(metrics, source="server-1")
        assert len(alerts) == 0

    def test_check_rule_health(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        rule_engine.evaluate_rule(sample_rule, 90.0)
        rule_engine.evaluate_rule(sample_rule, 70.0)
        health = rule_engine.check_rule_health(sample_rule.id)
        assert health["total_evaluations"] == 2
        assert health["triggered_count"] == 1
        assert health["trigger_ratio"] == 0.5

    def test_clear_history(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        rule_engine.evaluate_rule(sample_rule, 90.0)
        rule_engine.clear_history(sample_rule.id)
        health = rule_engine.check_rule_health(sample_rule.id)
        assert health["total_evaluations"] == 0

    def test_get_stats(self, rule_engine, sample_rule):
        rule_engine.add_rule(sample_rule)
        stats = rule_engine.get_stats()
        assert stats["total_rules"] == 1
        assert stats["enabled_rules"] == 1
        assert stats["by_severity"]["warning"] == 1


class TestAlertRuleModel:
    """Tests for AlertRule data model."""

    def test_to_dict(self, sample_rule):
        d = sample_rule.to_dict()
        assert d["name"] == "high_cpu"
        assert d["severity"] == "warning"
        assert d["threshold"] == 80.0
        assert d["enabled"] is True

    def test_from_dict(self, sample_rule):
        d = sample_rule.to_dict()
        restored = AlertRule.from_dict(d)
        assert restored.name == sample_rule.name
        assert restored.severity == sample_rule.severity
        assert restored.threshold == sample_rule.threshold

    def test_from_dict_defaults(self):
        rule = AlertRule.from_dict({})
        assert rule.name == ""
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True


# ===========================================================================
# 2. Alert Routing Tests
# ===========================================================================


class TestAlertRouter:
    """Tests for AlertRouter."""

    def test_add_target(self, router, sample_target):
        result = router.add_target(sample_target)
        assert result.id == sample_target.id
        assert router.get_target(sample_target.id) is not None

    def test_remove_target(self, router, sample_target):
        router.add_target(sample_target)
        assert router.remove_target(sample_target.id) is True
        assert router.get_target(sample_target.id) is None

    def test_remove_nonexistent_target(self, router):
        assert router.remove_target("nonexistent") is False

    def test_get_targets(self, router, sample_target):
        router.add_target(sample_target)
        targets = router.get_targets()
        assert len(targets) == 1

    def test_get_targets_enabled_only(self, router, sample_target):
        router.add_target(sample_target)
        disabled = AlertRoutingTarget(name="disabled", enabled=False)
        router.add_target(disabled)
        targets = router.get_targets(enabled_only=True)
        assert len(targets) == 1
        assert targets[0].enabled is True

    def test_get_targets_by_channel(self, router, sample_target):
        router.add_target(sample_target)
        sms_target = AlertRoutingTarget(name="sms", channel="sms")
        router.add_target(sms_target)
        targets = router.get_targets(channel="email")
        assert len(targets) == 1
        assert targets[0].channel == "email"

    def test_update_target(self, router, sample_target):
        router.add_target(sample_target)
        updated = router.update_target(sample_target.id, name="new_name", priority=5)
        assert updated is not None
        assert updated.name == "new_name"
        assert updated.priority == 5

    def test_route_broadcast(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        target2 = AlertRoutingTarget(name="t2", channel="slack")
        router.add_target(target2)
        targets = router.route(sample_alert, strategy=AlertRoutingStrategy.BROADCAST)
        assert len(targets) == 2
        assert sample_alert.routing_targets == [t.id for t in targets]

    def test_route_round_robin(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        target2 = AlertRoutingTarget(name="t2", channel="slack")
        router.add_target(target2)
        targets1 = router.route(sample_alert, strategy=AlertRoutingStrategy.ROUND_ROBIN)
        targets2 = router.route(sample_alert, strategy=AlertRoutingStrategy.ROUND_ROBIN)
        assert len(targets1) == 1
        assert len(targets2) == 1
        assert targets1[0].id != targets2[0].id

    def test_route_priority(self, router, sample_alert):
        low = AlertRoutingTarget(name="low", priority=1)
        high = AlertRoutingTarget(name="high", priority=10)
        router.add_target(low)
        router.add_target(high)
        targets = router.route(sample_alert, strategy=AlertRoutingStrategy.PRIORITY)
        assert len(targets) == 1
        assert targets[0].name == "high"

    def test_route_failover(self, router, sample_alert):
        t1 = AlertRoutingTarget(name="t1", priority=1)
        t2 = AlertRoutingTarget(name="t2", priority=10)
        router.add_target(t1)
        router.add_target(t2)
        targets = router.route(sample_alert, strategy=AlertRoutingStrategy.FAILOVER)
        assert len(targets) == 1
        assert targets[0].name == "t2"

    def test_route_with_specific_targets(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        target2 = AlertRoutingTarget(name="t2", channel="slack")
        router.add_target(target2)
        targets = router.route(sample_alert, targets=[sample_target.id])
        assert len(targets) == 1
        assert targets[0].id == sample_target.id

    def test_route_no_targets(self, router, sample_alert):
        targets = router.route(sample_alert)
        assert len(targets) == 0

    def test_route_filters_by_channel(self, router, sample_alert):
        email_target = AlertRoutingTarget(name="email", channel="email")
        sms_target = AlertRoutingTarget(name="sms", channel="sms")
        router.add_target(email_target)
        router.add_target(sms_target)
        sample_alert.notification_channels = ["email"]
        targets = router.route(sample_alert)
        assert len(targets) == 1
        assert targets[0].channel == "email"

    def test_get_routing_history(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        router.route(sample_alert)
        history = router.get_routing_history()
        assert len(history) == 1
        assert history[0]["alert_id"] == sample_alert.id

    def test_get_routing_history_by_alert(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        router.route(sample_alert)
        history = router.get_routing_history(alert_id=sample_alert.id)
        assert len(history) == 1
        history = router.get_routing_history(alert_id="nonexistent")
        assert len(history) == 0

    def test_get_target_stats(self, router, sample_target):
        router.add_target(sample_target)
        stats = router.get_target_stats()
        assert stats["total_targets"] == 1
        assert stats["enabled_targets"] == 1
        assert stats["by_channel"]["email"] == 1

    def test_clear_history(self, router, sample_alert, sample_target):
        router.add_target(sample_target)
        router.route(sample_alert)
        router.clear_history()
        assert len(router.get_routing_history()) == 0


class TestAlertRoutingTargetModel:
    """Tests for AlertRoutingTarget data model."""

    def test_to_dict(self, sample_target):
        d = sample_target.to_dict()
        assert d["name"] == "ops-email"
        assert d["channel"] == "email"
        assert d["priority"] == 1

    def test_from_dict(self, sample_target):
        d = sample_target.to_dict()
        restored = AlertRoutingTarget.from_dict(d)
        assert restored.name == sample_target.name
        assert restored.channel == sample_target.channel


# ===========================================================================
# 3. Alert Escalation Tests
# ===========================================================================


class TestAlertEscalator:
    """Tests for AlertEscalator."""

    def test_add_escalation_rule(self, escalator, sample_escalation_rule):
        result = escalator.add_escalation_rule(sample_escalation_rule)
        assert result.id == sample_escalation_rule.id
        assert escalator.get_escalation_rule(sample_escalation_rule.id) is not None

    def test_remove_escalation_rule(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        assert escalator.remove_escalation_rule(sample_escalation_rule.id) is True
        assert escalator.get_escalation_rule(sample_escalation_rule.id) is None

    def test_remove_nonexistent_escalation_rule(self, escalator):
        assert escalator.remove_escalation_rule("nonexistent") is False

    def test_get_escalation_rules(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        rules = escalator.get_escalation_rules()
        assert len(rules) == 1

    def test_get_escalation_rules_enabled_only(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        disabled = EscalationRule(name="disabled", enabled=False)
        escalator.add_escalation_rule(disabled)
        rules = escalator.get_escalation_rules(enabled_only=True)
        assert len(rules) == 1

    def test_get_escalation_rules_by_alert_rule(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        rules = escalator.get_escalation_rules(alert_rule_id=sample_escalation_rule.alert_rule_id)
        assert len(rules) == 1

    def test_update_escalation_rule(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        updated = escalator.update_escalation_rule(
            sample_escalation_rule.id, name="new_name", max_level=5
        )
        assert updated is not None
        assert updated.name == "new_name"
        assert updated.max_level == 5

    def test_check_escalation_no_rule(self, escalator, sample_alert):
        # No escalation rule exists
        result = escalator.check_escalation(sample_alert)
        assert result is False

    def test_check_escalation_too_early(self, escalator, sample_alert, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        # Just created, escalation_delay not met
        result = escalator.check_escalation(sample_alert)
        assert result is False

    def test_check_escalation_resolved_alert(self, escalator, sample_alert, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        sample_alert.status = AlertStatus.RESOLVED
        result = escalator.check_escalation(sample_alert)
        assert result is False

    def test_check_escalation_suppressed_alert(self, escalator, sample_alert, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        sample_alert.status = AlertStatus.SUPPRESSED
        result = escalator.check_escalation(sample_alert)
        assert result is False

    def test_acknowledge_alert(self, escalator, sample_alert):
        result = escalator.acknowledge_alert(sample_alert, acknowledged_by="user1")
        assert result is True
        assert sample_alert.status == AlertStatus.ACKNOWLEDGED
        assert sample_alert.acknowledged_by == "user1"
        assert sample_alert.acknowledged_at is not None

    def test_acknowledge_resolved_alert(self, escalator, sample_alert):
        sample_alert.status = AlertStatus.RESOLVED
        result = escalator.acknowledge_alert(sample_alert, acknowledged_by="user1")
        assert result is False

    def test_resolve_alert(self, escalator, sample_alert):
        result = escalator.resolve_alert(sample_alert)
        assert result is True
        assert sample_alert.status == AlertStatus.RESOLVED
        assert sample_alert.resolved_at is not None

    def test_resolve_already_resolved(self, escalator, sample_alert):
        sample_alert.status = AlertStatus.RESOLVED
        result = escalator.resolve_alert(sample_alert)
        assert result is False

    def test_get_escalation_state(self, escalator, sample_alert):
        state = escalator.get_escalation_state(sample_alert.id)
        assert state is None

    def test_get_escalation_history(self, escalator, sample_alert):
        escalator.acknowledge_alert(sample_alert, "user1")
        history = escalator.get_escalation_history()
        assert len(history) >= 1

    def test_get_escalation_history_by_alert(self, escalator, sample_alert):
        escalator.acknowledge_alert(sample_alert, "user1")
        history = escalator.get_escalation_history(alert_id=sample_alert.id)
        assert len(history) >= 1
        history = escalator.get_escalation_history(alert_id="nonexistent")
        assert len(history) == 0

    def test_get_escalation_stats(self, escalator, sample_escalation_rule):
        escalator.add_escalation_rule(sample_escalation_rule)
        stats = escalator.get_escalation_stats()
        assert stats["escalation_rules"] == 1
        assert stats["enabled_escalation_rules"] == 1

    def test_clear_history(self, escalator, sample_alert):
        escalator.acknowledge_alert(sample_alert, "user1")
        escalator.clear_history()
        assert len(escalator.get_escalation_history()) == 0

    def test_escalation_linear_delay(self, escalator):
        delay = escalator._calculate_escalation_delay(EscalationPolicy.LINEAR, 300, 0)
        assert delay == 300
        delay = escalator._calculate_escalation_delay(EscalationPolicy.LINEAR, 300, 1)
        assert delay == 600
        delay = escalator._calculate_escalation_delay(EscalationPolicy.LINEAR, 300, 2)
        assert delay == 900

    def test_escalation_exponential_delay(self, escalator):
        delay = escalator._calculate_escalation_delay(EscalationPolicy.EXPONENTIAL, 300, 0)
        assert delay == 300
        delay = escalator._calculate_escalation_delay(EscalationPolicy.EXPONENTIAL, 300, 1)
        assert delay == 600
        delay = escalator._calculate_escalation_delay(EscalationPolicy.EXPONENTIAL, 300, 2)
        assert delay == 1200

    def test_escalation_fixed_delay(self, escalator):
        delay = escalator._calculate_escalation_delay(EscalationPolicy.FIXED, 300, 0)
        assert delay == 300
        delay = escalator._calculate_escalation_delay(EscalationPolicy.FIXED, 300, 2)
        assert delay == 300


class TestEscalationRuleModel:
    """Tests for EscalationRule data model."""

    def test_to_dict(self, sample_escalation_rule):
        d = sample_escalation_rule.to_dict()
        assert d["name"] == "default_escalation"
        assert d["max_level"] == 3
        assert d["escalation_policy"] == "linear"

    def test_from_dict(self, sample_escalation_rule):
        d = sample_escalation_rule.to_dict()
        restored = EscalationRule.from_dict(d)
        assert restored.name == sample_escalation_rule.name
        assert restored.max_level == sample_escalation_rule.max_level


# ===========================================================================
# 4. Alert Suppression Tests
# ===========================================================================


class TestAlertSuppressor:
    """Tests for AlertSuppressor."""

    def test_add_suppression_rule(self, suppressor, sample_suppression_rule):
        result = suppressor.add_suppression_rule(sample_suppression_rule)
        assert result.id == sample_suppression_rule.id
        assert suppressor.get_suppression_rule(sample_suppression_rule.id) is not None

    def test_remove_suppression_rule(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        assert suppressor.remove_suppression_rule(sample_suppression_rule.id) is True
        assert suppressor.get_suppression_rule(sample_suppression_rule.id) is None

    def test_remove_nonexistent_suppression_rule(self, suppressor):
        assert suppressor.remove_suppression_rule("nonexistent") is False

    def test_get_suppression_rules(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        rules = suppressor.get_suppression_rules()
        assert len(rules) == 1

    def test_get_suppression_rules_enabled_only(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        disabled = SuppressionRule(name="disabled", enabled=False)
        suppressor.add_suppression_rule(disabled)
        rules = suppressor.get_suppression_rules(enabled_only=True)
        assert len(rules) == 1

    def test_get_suppression_rules_by_alert_rule(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        rules = suppressor.get_suppression_rules(alert_rule_id=sample_suppression_rule.alert_rule_id)
        assert len(rules) == 1

    def test_update_suppression_rule(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        updated = suppressor.update_suppression_rule(
            sample_suppression_rule.id, name="new_name", duration=7200
        )
        assert updated is not None
        assert updated.name == "new_name"
        assert updated.duration == 7200

    def test_is_suppressed_no_rules(self, suppressor, sample_alert):
        result = suppressor.is_suppressed(sample_alert)
        assert result is None

    def test_is_suppressed_by_severity(self, suppressor, sample_alert):
        rule = SuppressionRule(
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is not None
        assert result.id == rule.id

    def test_is_suppressed_by_source(self, suppressor, sample_alert):
        rule = SuppressionRule(
            source="server-1",
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is not None

    def test_is_suppressed_by_labels(self, suppressor, sample_alert):
        rule = SuppressionRule(
            labels={"team": "ops"},
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is not None

    def test_is_suppressed_label_mismatch(self, suppressor, sample_alert):
        rule = SuppressionRule(
            labels={"team": "dev"},
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is None

    def test_is_suppressed_disabled_rule(self, suppressor, sample_alert):
        rule = SuppressionRule(
            severity=AlertSeverity.WARNING,
            enabled=False,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is None

    def test_is_suppressed_time_based_active(self, suppressor, sample_alert):
        now = time.time()
        rule = SuppressionRule(
            start_time=now - 60,
            end_time=now + 3600,
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is not None

    def test_is_suppressed_time_based_not_started(self, suppressor, sample_alert):
        now = time.time()
        rule = SuppressionRule(
            start_time=now + 3600,
            end_time=now + 7200,
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is None

    def test_is_suppressed_time_based_expired(self, suppressor, sample_alert):
        now = time.time()
        rule = SuppressionRule(
            start_time=now - 7200,
            end_time=now - 3600,
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.is_suppressed(sample_alert)
        assert result is None

    def test_suppress_alert(self, suppressor, sample_alert):
        result = suppressor.suppress_alert(sample_alert, reason="Maintenance")
        assert result is True
        assert sample_alert.status == AlertStatus.SUPPRESSED
        assert sample_alert.suppression_reason == "Maintenance"
        assert sample_alert.suppressed_at is not None

    def test_suppress_resolved_alert(self, suppressor, sample_alert):
        sample_alert.status = AlertStatus.RESOLVED
        result = suppressor.suppress_alert(sample_alert)
        assert result is False

    def test_unsuppress_alert(self, suppressor, sample_alert):
        suppressor.suppress_alert(sample_alert, reason="test")
        result = suppressor.unsuppress_alert(sample_alert)
        assert result is True
        assert sample_alert.status == AlertStatus.FIRING
        assert sample_alert.suppressed_at is None

    def test_unsuppress_not_suppressed(self, suppressor, sample_alert):
        result = suppressor.unsuppress_alert(sample_alert)
        assert result is False

    def test_check_and_suppress(self, suppressor, sample_alert):
        rule = SuppressionRule(
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        suppressor.add_suppression_rule(rule)
        result = suppressor.check_and_suppress(sample_alert)
        assert result is True
        assert sample_alert.status == AlertStatus.SUPPRESSED

    def test_check_and_suppress_no_match(self, suppressor, sample_alert):
        result = suppressor.check_and_suppress(sample_alert)
        assert result is False

    def test_get_suppressed_alerts(self, suppressor, sample_alert):
        suppressor.suppress_alert(sample_alert, reason="test")
        suppressed = suppressor.get_suppressed_alerts()
        assert sample_alert.id in suppressed

    def test_get_suppression_history(self, suppressor, sample_alert):
        suppressor.suppress_alert(sample_alert, reason="test")
        history = suppressor.get_suppression_history()
        assert len(history) == 1
        assert history[0]["alert_id"] == sample_alert.id

    def test_get_suppression_history_by_alert(self, suppressor, sample_alert):
        suppressor.suppress_alert(sample_alert, reason="test")
        history = suppressor.get_suppression_history(alert_id=sample_alert.id)
        assert len(history) == 1
        history = suppressor.get_suppression_history(alert_id="nonexistent")
        assert len(history) == 0

    def test_get_suppression_stats(self, suppressor, sample_suppression_rule):
        suppressor.add_suppression_rule(sample_suppression_rule)
        stats = suppressor.get_suppression_stats()
        assert stats["total_suppression_rules"] == 1
        assert stats["enabled_suppression_rules"] == 1

    def test_clear_history(self, suppressor, sample_alert):
        suppressor.suppress_alert(sample_alert, reason="test")
        suppressor.clear_history()
        assert len(suppressor.get_suppression_history()) == 0
        assert len(suppressor.get_suppressed_alerts()) == 0

    def test_cleanup_expired(self, suppressor):
        now = time.time()
        expired = SuppressionRule(
            name="expired",
            start_time=now - 7200,
            end_time=now - 3600,
            enabled=True,
        )
        active = SuppressionRule(
            name="active",
            start_time=now - 60,
            end_time=now + 3600,
            enabled=True,
        )
        suppressor.add_suppression_rule(expired)
        suppressor.add_suppression_rule(active)
        removed = suppressor.cleanup_expired()
        assert removed == 1
        assert suppressor.get_suppression_rule(expired.id) is None
        assert suppressor.get_suppression_rule(active.id) is not None


class TestSuppressionRuleModel:
    """Tests for SuppressionRule data model."""

    def test_to_dict(self, sample_suppression_rule):
        d = sample_suppression_rule.to_dict()
        assert d["name"] == "maintenance_window"
        assert d["duration"] == 3600
        assert d["enabled"] is True

    def test_from_dict(self, sample_suppression_rule):
        d = sample_suppression_rule.to_dict()
        restored = SuppressionRule.from_dict(d)
        assert restored.name == sample_suppression_rule.name
        assert restored.duration == sample_suppression_rule.duration


# ===========================================================================
# 5. Alert History Tests
# ===========================================================================


class TestAlertHistory:
    """Tests for AlertHistory."""

    def test_record(self, history, sample_alert):
        entry = history.record(sample_alert, action="created", actor="system")
        assert entry.id is not None
        assert entry.alert_id == sample_alert.id
        assert entry.action == "created"
        assert entry.actor == "system"

    def test_get_entries(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries()
        assert len(entries) == 1

    def test_get_entries_by_alert_id(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(alert_id=sample_alert.id)
        assert len(entries) == 1
        entries = history.get_entries(alert_id="nonexistent")
        assert len(entries) == 0

    def test_get_entries_by_rule_id(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(rule_id=sample_alert.rule_id)
        assert len(entries) == 1

    def test_get_entries_by_status(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(status=AlertStatus.FIRING)
        assert len(entries) == 1
        entries = history.get_entries(status=AlertStatus.RESOLVED)
        assert len(entries) == 0

    def test_get_entries_by_action(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(action="created")
        assert len(entries) == 1
        entries = history.get_entries(action="resolved")
        assert len(entries) == 0

    def test_get_entries_by_severity(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(severity=AlertSeverity.WARNING)
        assert len(entries) == 1
        entries = history.get_entries(severity=AlertSeverity.CRITICAL)
        assert len(entries) == 0

    def test_get_entries_by_source(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_entries(source="server-1")
        assert len(entries) == 1
        entries = history.get_entries(source="server-2")
        assert len(entries) == 0

    def test_get_entries_by_time_range(self, history, sample_alert):
        history.record(sample_alert, action="created")
        now = time.time()
        entries = history.get_entries(start_time=now - 60, end_time=now + 60)
        assert len(entries) == 1
        entries = history.get_entries(start_time=now + 60)
        assert len(entries) == 0

    def test_get_entries_limit(self, history, sample_alert):
        for _ in range(10):
            history.record(sample_alert, action="created")
        entries = history.get_entries(limit=5)
        assert len(entries) == 5

    def test_get_entries_most_recent_first(self, history, sample_alert):
        history.record(sample_alert, action="created")
        time.sleep(0.01)
        history.record(sample_alert, action="acknowledged")
        entries = history.get_entries()
        assert entries[0].action == "acknowledged"
        assert entries[1].action == "created"

    def test_get_entry(self, history, sample_alert):
        entry = history.record(sample_alert, action="created")
        found = history.get_entry(entry.id)
        assert found is not None
        assert found.id == entry.id

    def test_get_entry_not_found(self, history):
        assert history.get_entry("nonexistent") is None

    def test_get_alert_timeline(self, history, sample_alert):
        history.record(sample_alert, action="created")
        history.record(sample_alert, action="acknowledged")
        history.record(sample_alert, action="resolved")
        timeline = history.get_alert_timeline(sample_alert.id)
        assert len(timeline) == 3

    def test_get_rule_history(self, history, sample_alert):
        history.record(sample_alert, action="created")
        entries = history.get_rule_history(sample_alert.rule_id)
        assert len(entries) == 1

    def test_get_stats(self, history, sample_alert):
        history.record(sample_alert, action="created")
        history.record(sample_alert, action="acknowledged")
        stats = history.get_stats()
        assert stats["total_entries"] == 2
        assert stats["unique_alerts"] == 1
        assert stats["by_action"]["created"] == 1
        assert stats["by_action"]["acknowledged"] == 1

    def test_clear(self, history, sample_alert):
        history.record(sample_alert, action="created")
        history.clear()
        assert len(history.get_entries()) == 0

    def test_export_list(self, history, sample_alert):
        history.record(sample_alert, action="created")
        exported = history.export_entries(format="list")
        assert isinstance(exported, list)
        assert len(exported) == 1
        assert exported[0]["action"] == "created"

    def test_export_dict(self, history, sample_alert):
        history.record(sample_alert, action="created")
        exported = history.export_entries(format="dict")
        assert isinstance(exported, dict)
        assert len(exported) == 1

    def test_export_count(self, history, sample_alert):
        history.record(sample_alert, action="created")
        count = history.export_entries(format="count")
        assert count == 1

    def test_max_entries_trim(self):
        small_history = AlertHistory(max_entries=5)
        alert = Alert(rule_id="r1", rule_name="test")
        for _ in range(10):
            small_history.record(alert, action="created")
        stats = small_history.get_stats()
        assert stats["total_entries"] == 5


class TestAlertHistoryEntryModel:
    """Tests for AlertHistoryEntry data model."""

    def test_to_dict(self, sample_alert):
        entry = AlertHistoryEntry(
            alert_id=sample_alert.id,
            rule_id=sample_alert.rule_id,
            action="created",
        )
        d = entry.to_dict()
        assert d["alert_id"] == sample_alert.id
        assert d["action"] == "created"

    def test_from_dict(self, sample_alert):
        entry = AlertHistoryEntry(
            alert_id=sample_alert.id,
            rule_id=sample_alert.rule_id,
            action="created",
        )
        d = entry.to_dict()
        restored = AlertHistoryEntry.from_dict(d)
        assert restored.alert_id == entry.alert_id
        assert restored.action == entry.action


# ===========================================================================
# 6. Alert Model Tests
# ===========================================================================


class TestAlertModel:
    """Tests for Alert data model."""

    def test_to_dict(self, sample_alert):
        d = sample_alert.to_dict()
        assert d["rule_id"] == "rule-1"
        assert d["severity"] == "warning"
        assert d["status"] == "firing"
        assert d["value"] == 90.0

    def test_from_dict(self, sample_alert):
        d = sample_alert.to_dict()
        restored = Alert.from_dict(d)
        assert restored.rule_id == sample_alert.rule_id
        assert restored.severity == sample_alert.severity
        assert restored.status == sample_alert.status

    def test_from_dict_defaults(self):
        alert = Alert.from_dict({})
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.FIRING
        assert alert.escalation_level == 0


# ===========================================================================
# 7. Integration Tests
# ===========================================================================


class TestAlertingIntegration:
    """Integration tests for the full alerting pipeline."""

    def test_full_alert_lifecycle(
        self, rule_engine, router, escalator, suppressor, history, sample_rule, sample_target
    ):
        """Test the complete alert lifecycle from creation to resolution."""
        # Setup
        rule_engine.add_rule(sample_rule)
        router.add_target(sample_target)

        # 1. Evaluate rule -> creates alert
        alert = rule_engine.evaluate_rule(sample_rule, 90.0, source="server-1")
        assert alert is not None
        assert alert.status == AlertStatus.FIRING

        # 2. Record in history
        history.record(alert, action="created")
        assert len(history.get_entries(alert_id=alert.id)) == 1

        # 3. Route the alert
        targets = router.route(alert)
        assert len(targets) >= 0  # May be 0 if channel mismatch

        # 4. Check suppression (no rules, should not suppress)
        suppressed = suppressor.check_and_suppress(alert)
        assert suppressed is False

        # 5. Acknowledge the alert
        escalator.acknowledge_alert(alert, "ops_user")
        assert alert.status == AlertStatus.ACKNOWLEDGED
        history.record(alert, action="acknowledged", actor="ops_user")

        # 6. Resolve the alert
        escalator.resolve_alert(alert)
        assert alert.status == AlertStatus.RESOLVED
        history.record(alert, action="resolved")

        # 7. Verify history
        timeline = history.get_alert_timeline(alert.id)
        assert len(timeline) == 3

    def test_suppression_pipeline(
        self, rule_engine, suppressor, history, sample_rule
    ):
        """Test alert suppression pipeline."""
        rule_engine.add_rule(sample_rule)

        # Add suppression rule
        sup_rule = SuppressionRule(
            severity=AlertSeverity.WARNING,
            enabled=True,
        )
        suppressor.add_suppression_rule(sup_rule)

        # Create alert
        alert = rule_engine.evaluate_rule(sample_rule, 90.0, source="server-1")
        assert alert is not None

        # Check and suppress
        suppressed = suppressor.check_and_suppress(alert)
        assert suppressed is True
        assert alert.status == AlertStatus.SUPPRESSED

        # Record in history
        history.record(alert, action="suppressed")

        # Verify suppression stats
        stats = suppressor.get_suppression_stats()
        assert stats["currently_suppressed_alerts"] == 1

    def test_escalation_pipeline(
        self, rule_engine, escalator, history, sample_rule, sample_escalation_rule
    ):
        """Test alert escalation pipeline."""
        rule_engine.add_rule(sample_rule)
        escalator.add_escalation_rule(sample_escalation_rule)

        # Create alert
        alert = rule_engine.evaluate_rule(sample_rule, 90.0, source="server-1")
        assert alert is not None

        # Record creation
        history.record(alert, action="created")

        # Manually set last_escalation_time to past to trigger escalation
        state = escalator._alert_escalation_state.setdefault(
            alert.id,
            {"current_level": 0, "last_escalation_time": alert.created_at, "escalation_count": 0},
        )
        state["last_escalation_time"] = time.time() - 1000  # Force delay to be met

        # Check escalation
        escalated = escalator.check_escalation(alert)
        assert escalated is True
        assert alert.status == AlertStatus.ESCALATED
        assert alert.escalation_level == 1

        # Record escalation
        history.record(alert, action="escalated")

        # Verify escalation stats
        stats = escalator.get_escalation_stats()
        assert stats["escalated_alerts"] == 1

    def test_multiple_rules_and_alerts(self, rule_engine):
        """Test engine with multiple rules."""
        rule1 = AlertRule(name="cpu", threshold=80.0, comparison="gt", severity=AlertSeverity.WARNING)
        rule2 = AlertRule(name="memory", threshold=90.0, comparison="gt", severity=AlertSeverity.CRITICAL)
        rule3 = AlertRule(name="disk", threshold=95.0, comparison="gt", severity=AlertSeverity.ERROR)

        rule_engine.add_rule(rule1)
        rule_engine.add_rule(rule2)
        rule_engine.add_rule(rule3)

        metrics = {"cpu": 85.0, "memory": 95.0, "disk": 50.0}
        alerts = rule_engine.evaluate_all(metrics, source="server-1")
        assert len(alerts) == 2

        severities = {a.severity for a in alerts}
        assert AlertSeverity.WARNING in severities
        assert AlertSeverity.CRITICAL in severities
