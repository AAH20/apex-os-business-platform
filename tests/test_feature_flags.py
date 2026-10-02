"""Comprehensive tests for the feature flag system."""

import pytest
import time
from apex_os_bp.feature_flags import (
    Flag,
    FlagState,
    TargetingRule,
    RolloutConfig,
    RolloutStrategy,
    FlagAnalytics,
    FlagDependency,
    FeatureFlagManager,
    TargetingEngine,
    RolloutEngine,
    AnalyticsEngine,
    DependencyEngine,
)


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def manager():
    return FeatureFlagManager()


@pytest.fixture
def targeting_engine():
    return TargetingEngine()


@pytest.fixture
def rollout_engine():
    return RolloutEngine()


@pytest.fixture
def analytics_engine():
    return AnalyticsEngine()


@pytest.fixture
def dependency_engine():
    return DependencyEngine()


# ════════════════════════════════════════════════════════════════════
# 1. FLAG MANAGEMENT
# ════════════════════════════════════════════════════════════════════


class TestFlagManagement:
    """Tests for flag CRUD and lifecycle management."""

    def test_create_flag(self, manager):
        flag = manager.create_flag("test-flag", "A test flag")
        assert flag.name == "test-flag"
        assert flag.description == "A test flag"
        assert flag.state == FlagState.DISABLED
        assert flag.version == 1

    def test_create_duplicate_flag_raises(self, manager):
        manager.create_flag("dup-flag")
        with pytest.raises(ValueError, match="already exists"):
            manager.create_flag("dup-flag")

    def test_get_flag(self, manager):
        manager.create_flag("get-flag")
        flag = manager.get_flag("get-flag")
        assert flag is not None
        assert flag.name == "get-flag"

    def test_get_nonexistent_flag_returns_none(self, manager):
        assert manager.get_flag("nope") is None

    def test_list_flags(self, manager):
        manager.create_flag("f1")
        manager.create_flag("f2")
        manager.create_flag("f3")
        assert len(manager.list_flags()) == 3

    def test_list_flags_filtered_by_state(self, manager):
        manager.create_flag("f1", state=FlagState.ENABLED)
        manager.create_flag("f2", state=FlagState.DISABLED)
        enabled = manager.list_flags(state=FlagState.ENABLED)
        assert len(enabled) == 1
        assert enabled[0].name == "f1"

    def test_list_flags_filtered_by_tags(self, manager):
        manager.create_flag("f1", tags={"backend", "v2"})
        manager.create_flag("f2", tags={"frontend"})
        backend_flags = manager.list_flags(tags={"backend"})
        assert len(backend_flags) == 1
        assert backend_flags[0].name == "f1"

    def test_update_flag(self, manager):
        manager.create_flag("upd", description="old")
        manager.update_flag("upd", description="new")
        assert manager.get_flag("upd").description == "new"

    def test_update_flag_version_bump(self, manager):
        manager.create_flag("ver")
        v1 = manager.get_flag("ver").version
        manager.update_flag("ver", description="changed")
        v2 = manager.get_flag("ver").version
        assert v2 == v1 + 1

    def test_update_nonexistent_flag_raises(self, manager):
        with pytest.raises(KeyError):
            manager.update_flag("ghost", description="x")

    def test_update_disallowed_field_raises(self, manager):
        manager.create_flag("f")
        with pytest.raises(ValueError):
            manager.update_flag("f", name="new-name")

    def test_delete_flag(self, manager):
        manager.create_flag("del")
        manager.delete_flag("del")
        assert manager.get_flag("del") is None

    def test_delete_nonexistent_flag_raises(self, manager):
        with pytest.raises(KeyError):
            manager.delete_flag("ghost")

    def test_delete_flag_removes_from_dependents(self, manager):
        manager.create_flag("parent")
        manager.create_flag("child")
        manager.add_dependency("child", "parent")
        manager.delete_flag("parent")
        assert "parent" not in manager.get_flag("child").dependencies

    def test_flag_states(self, manager):
        manager.create_flag("disabled", state=FlagState.DISABLED)
        manager.create_flag("enabled", state=FlagState.ENABLED)
        manager.create_flag("rollout", state=FlagState.ROLLOUT)
        manager.create_flag("archived", state=FlagState.ARCHIVED)

        assert manager.is_enabled("disabled") is False
        assert manager.is_enabled("enabled") is True
        assert manager.is_enabled("rollout") is False  # needs user_id
        assert manager.is_enabled("archived") is False

    def test_flag_with_tags(self, manager):
        flag = manager.create_flag("tagged", tags={"api", "v2", "experimental"})
        assert "api" in flag.tags
        assert "v2" in flag.tags
        assert "experimental" in flag.tags

    def test_flag_timestamps(self, manager):
        before = time.time()
        flag = manager.create_flag("ts")
        after = time.time()
        assert before <= flag.created_at <= after
        assert before <= flag.updated_at <= after


# ════════════════════════════════════════════════════════════════════
# 2. TARGETING RULES
# ════════════════════════════════════════════════════════════════════


class TestTargetingRules:
    """Tests for targeting rule evaluation."""

    def test_eq_operator(self, targeting_engine):
        rule = TargetingRule("plan", "eq", "premium")
        assert rule.matches({"plan": "premium"}) is True
        assert rule.matches({"plan": "free"}) is False

    def test_ne_operator(self, targeting_engine):
        rule = TargetingRule("plan", "ne", "free")
        assert rule.matches({"plan": "premium"}) is True
        assert rule.matches({"plan": "free"}) is False

    def test_in_operator(self, targeting_engine):
        rule = TargetingRule("country", "in", ["US", "CA", "UK"])
        assert rule.matches({"country": "US"}) is True
        assert rule.matches({"country": "FR"}) is False

    def test_not_in_operator(self, targeting_engine):
        rule = TargetingRule("country", "not_in", ["US", "CA"])
        assert rule.matches({"country": "FR"}) is True
        assert rule.matches({"country": "US"}) is False

    def test_gt_operator(self, targeting_engine):
        rule = TargetingRule("age", "gt", 18)
        assert rule.matches({"age": 21}) is True
        assert rule.matches({"age": 18}) is False

    def test_lt_operator(self, targeting_engine):
        rule = TargetingRule("age", "lt", 65)
        assert rule.matches({"age": 30}) is True
        assert rule.matches({"age": 65}) is False

    def test_contains_operator(self, targeting_engine):
        rule = TargetingRule("email", "contains", "@company.com")
        assert rule.matches({"email": "user@company.com"}) is True
        assert rule.matches({"email": "user@gmail.com"}) is False

    def test_missing_attribute_no_match(self, targeting_engine):
        rule = TargetingRule("plan", "eq", "premium")
        assert rule.matches({}) is False

    def test_unknown_operator_no_match(self, targeting_engine):
        rule = TargetingRule("x", "unknown_op", "val")
        assert rule.matches({"x": "val"}) is False

    def test_evaluate_all_rules_must_pass(self, targeting_engine):
        rules = [
            TargetingRule("plan", "eq", "premium"),
            TargetingRule("country", "in", ["US", "CA"]),
        ]
        assert targeting_engine.evaluate(rules, {"plan": "premium", "country": "US"}) is True
        assert targeting_engine.evaluate(rules, {"plan": "premium", "country": "FR"}) is False
        assert targeting_engine.evaluate(rules, {"plan": "free", "country": "US"}) is False

    def test_evaluate_empty_rules_returns_true(self, targeting_engine):
        assert targeting_engine.evaluate([], {}) is True

    def test_evaluate_any(self, targeting_engine):
        rules = [
            TargetingRule("plan", "eq", "premium"),
            TargetingRule("plan", "eq", "enterprise"),
        ]
        assert targeting_engine.evaluate_any(rules, {"plan": "enterprise"}) is True
        assert targeting_engine.evaluate_any(rules, {"plan": "free"}) is False

    def test_priority_ordering(self, targeting_engine):
        rules = [
            TargetingRule("a", "eq", "1", priority=1),
            TargetingRule("b", "eq", "2", priority=10),
        ]
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        assert sorted_rules[0].attribute == "b"

    def test_manager_targeting_integration(self, manager):
        manager.create_flag(
            "targeted",
            state=FlagState.ENABLED,
            targeting_rules=[
                TargetingRule("plan", "eq", "premium"),
            ],
        )
        assert manager.is_enabled("targeted", {"plan": "premium"}) is True
        assert manager.is_enabled("targeted", {"plan": "free"}) is False

    def test_manager_multiple_targeting_rules(self, manager):
        manager.create_flag(
            "multi-target",
            state=FlagState.ENABLED,
            targeting_rules=[
                TargetingRule("plan", "in", ["premium", "enterprise"]),
                TargetingRule("country", "eq", "US"),
            ],
        )
        ctx = {"plan": "premium", "country": "US"}
        assert manager.is_enabled("multi-target", ctx) is True
        ctx2 = {"plan": "free", "country": "US"}
        assert manager.is_enabled("multi-target", ctx2) is False


# ════════════════════════════════════════════════════════════════════
# 3. GRADUAL ROLLOUT
# ════════════════════════════════════════════════════════════════════


class TestGradualRollout:
    """Tests for gradual rollout strategies."""

    def test_percentage_rollout_zero(self, manager):
        manager.create_flag(
            "pct",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=0),
        )
        assert manager.is_enabled("pct", user_id="anyone") is False

    def test_percentage_rollout_full(self, manager):
        manager.create_flag(
            "pct-full",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=100),
        )
        assert manager.is_enabled("pct-full", user_id="anyone") is True

    def test_percentage_rollout_deterministic(self, manager):
        config = RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=50)
        results = {config.is_user_in_rollout(f"user-{i}") for i in range(100)}
        # Should have both True and False with 50%
        assert True in results
        assert False in results

    def test_percentage_rollout_consistency(self, manager):
        """Same user should always get the same result."""
        config = RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=50)
        user = "test-user-42"
        result1 = config.is_user_in_rollout(user)
        result2 = config.is_user_in_rollout(user)
        assert result1 == result2

    def test_user_list_rollout(self, manager):
        manager.create_flag(
            "ulist",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_LIST,
                user_ids={"user1", "user2"},
            ),
        )
        assert manager.is_enabled("ulist", user_id="user1") is True
        assert manager.is_enabled("ulist", user_id="user2") is True
        assert manager.is_enabled("ulist", user_id="user3") is False

    def test_ring_rollout(self, manager):
        manager.create_flag(
            "ring",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.RING,
                rings=[{"u1", "u2"}, {"u3", "u4"}, {"u5"}],
                current_ring=0,
            ),
        )
        assert manager.is_enabled("ring", user_id="u1") is True
        assert manager.is_enabled("ring", user_id="u3") is False

        manager.advance_rollout_ring("ring")
        assert manager.is_enabled("ring", user_id="u3") is True
        assert manager.is_enabled("ring", user_id="u5") is False

        manager.advance_rollout_ring("ring")
        assert manager.is_enabled("ring", user_id="u5") is True

    def test_advance_ring_beyond_last(self, manager):
        manager.create_flag(
            "ring-max",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.RING,
                rings=[{"u1"}],
                current_ring=0,
            ),
        )
        # Should not raise, just stay at last ring
        manager.advance_rollout_ring("ring-max")
        assert manager.get_flag("ring-max").rollout_config.current_ring == 0

    def test_set_rollout_percentage(self, manager):
        manager.create_flag("pct-set", state=FlagState.ROLLOUT)
        manager.set_rollout_percentage("pct-set", 75)
        assert manager.get_flag("pct-set").rollout_config.percentage == 75

    def test_set_rollout_percentage_clamped(self, manager):
        manager.create_flag("pct-clamp", state=FlagState.ROLLOUT)
        manager.set_rollout_percentage("pct-clamp", 150)
        assert manager.get_flag("pct-clamp").rollout_config.percentage == 100
        manager.set_rollout_percentage("pct-clamp", -10)
        assert manager.get_flag("pct-clamp").rollout_config.percentage == 0

    def test_add_user_to_rollout(self, manager):
        manager.create_flag(
            "add-user",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(strategy=RolloutStrategy.USER_LIST),
        )
        manager.add_user_to_rollout("add-user", "special-user")
        assert manager.is_enabled("add-user", user_id="special-user") is True

    def test_remove_user_from_rollout(self, manager):
        manager.create_flag(
            "rm-user",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.USER_LIST,
                user_ids={"keep", "remove"},
            ),
        )
        manager.remove_user_from_rollout("rm-user", "remove")
        assert manager.is_enabled("rm-user", user_id="keep") is True
        assert manager.is_enabled("rm-user", user_id="remove") is False

    def test_rollout_requires_user_id(self, manager):
        manager.create_flag(
            "needs-uid",
            state=FlagState.ROLLOUT,
            rollout_config=RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=100),
        )
        assert manager.is_enabled("needs-uid") is False

    def test_rollout_engine_get_active_ring_users(self, rollout_engine):
        config = RolloutConfig(
            strategy=RolloutStrategy.RING,
            rings=[{"a", "b"}, {"c"}, {"d"}],
            current_ring=1,
        )
        users = rollout_engine.get_active_ring_users(config)
        assert users == {"a", "b", "c"}

    def test_rollout_engine_set_percentage(self, rollout_engine):
        config = RolloutConfig(strategy=RolloutStrategy.PERCENTAGE, percentage=10)
        rollout_engine.set_percentage(config, 50)
        assert config.percentage == 50
        rollout_engine.set_percentage(config, 200)
        assert config.percentage == 100


# ════════════════════════════════════════════════════════════════════
# 4. FLAG ANALYTICS
# ════════════════════════════════════════════════════════════════════


class TestFlagAnalytics:
    """Tests for flag analytics tracking."""

    def test_analytics_recorded_on_evaluation(self, manager):
        manager.create_flag("tracked", state=FlagState.ENABLED)
        manager.is_enabled("tracked", user_id="user1")
        analytics = manager.get_analytics("tracked")
        assert analytics.evaluations == 1
        assert analytics.hits == 1
        assert analytics.misses == 0

    def test_analytics_misses(self, manager):
        manager.create_flag("miss", state=FlagState.DISABLED)
        manager.is_enabled("miss", user_id="user1")
        analytics = manager.get_analytics("miss")
        assert analytics.evaluations == 1
        assert analytics.hits == 0
        assert analytics.misses == 1

    def test_analytics_hit_rate(self, manager):
        manager.create_flag("rate", state=FlagState.ENABLED)
        for i in range(3):
            manager.is_enabled("rate", user_id=f"u{i}")
        manager.is_enabled("rate", user_id="u0")  # duplicate user
        analytics = manager.get_analytics("rate")
        assert analytics.hit_rate == 100.0

    def test_analytics_unique_users(self, manager):
        manager.create_flag("unique", state=FlagState.ENABLED)
        for i in range(5):
            manager.is_enabled("unique", user_id=f"user-{i}")
        manager.is_enabled("unique", user_id="user-0")  # duplicate
        analytics = manager.get_analytics("unique")
        assert len(analytics.unique_users) == 5

    def test_analytics_daily_counts(self, manager):
        manager.create_flag("daily", state=FlagState.ENABLED)
        manager.is_enabled("daily", user_id="u1")
        manager.is_enabled("daily", user_id="u2")
        analytics = manager.get_analytics("daily")
        from datetime import date

        today = date.today().isoformat()
        assert analytics.daily_counts[today] == 2

    def test_analytics_last_evaluated_at(self, manager):
        manager.create_flag("ts-flag", state=FlagState.ENABLED)
        assert manager.get_analytics("ts-flag").last_evaluated_at is None
        manager.is_enabled("ts-flag", user_id="u1")
        assert manager.get_analytics("ts-flag").last_evaluated_at is not None

    def test_analytics_engine_summary(self, analytics_engine):
        analytics = FlagAnalytics(flag_name="test")
        analytics.record_evaluation("u1", True)
        analytics.record_evaluation("u2", False)
        summary = analytics_engine.get_summary(analytics)
        assert summary["evaluations"] == 2
        assert summary["hits"] == 1
        assert summary["misses"] == 1
        assert summary["hit_rate"] == 50.0
        assert summary["unique_users"] == 2

    def test_analytics_engine_daily_summary(self, analytics_engine):
        analytics = FlagAnalytics(flag_name="test")
        analytics.record_evaluation("u1", True)
        daily = analytics_engine.get_daily_summary(analytics)
        from datetime import date

        today = date.today().isoformat()
        assert daily[today] == 1

    def test_get_all_analytics(self, manager):
        manager.create_flag("f1")
        manager.create_flag("f2")
        all_analytics = manager.get_all_analytics()
        assert "f1" in all_analytics
        assert "f2" in all_analytics

    def test_analytics_disabled_flag_still_recorded(self, manager):
        manager.create_flag("off", state=FlagState.DISABLED)
        manager.is_enabled("off", user_id="u1")
        analytics = manager.get_analytics("off")
        assert analytics.evaluations == 1
        assert analytics.misses == 1


# ════════════════════════════════════════════════════════════════════
# 5. FLAG DEPENDENCIES
# ════════════════════════════════════════════════════════════════════


class TestFlagDependencies:
    """Tests for flag dependency management."""

    def test_add_dependency(self, manager):
        manager.create_flag("parent")
        manager.create_flag("child")
        manager.add_dependency("child", "parent")
        assert "parent" in manager.get_dependencies("child")

    def test_add_dependency_nonexistent_flag_raises(self, manager):
        manager.create_flag("child")
        with pytest.raises(KeyError):
            manager.add_dependency("child", "ghost")

    def test_add_dependency_nonexistent_parent_raises(self, manager):
        manager.create_flag("parent")
        with pytest.raises(KeyError):
            manager.add_dependency("ghost", "parent")

    def test_remove_dependency(self, manager):
        manager.create_flag("parent")
        manager.create_flag("child")
        manager.add_dependency("child", "parent")
        manager.remove_dependency("child", "parent")
        assert "parent" not in manager.get_dependencies("child")

    def test_get_dependents(self, manager):
        manager.create_flag("base")
        manager.create_flag("mid")
        manager.create_flag("top")
        manager.add_dependency("mid", "base")
        manager.add_dependency("top", "mid")
        dependents = manager.get_dependents("base")
        assert "mid" in dependents

    def test_dependency_blocks_flag(self, manager):
        manager.create_flag("parent", state=FlagState.DISABLED)
        manager.create_flag("child", state=FlagState.ENABLED)
        manager.add_dependency("child", "parent")
        assert manager.is_enabled("child") is False

    def test_dependency_satisfied(self, manager):
        manager.create_flag("parent", state=FlagState.ENABLED)
        manager.create_flag("child", state=FlagState.ENABLED)
        manager.add_dependency("child", "parent")
        assert manager.is_enabled("child") is True

    def test_transitive_dependencies(self, manager):
        manager.create_flag("a", state=FlagState.ENABLED)
        manager.create_flag("b", state=FlagState.ENABLED)
        manager.create_flag("c", state=FlagState.ENABLED)
        manager.add_dependency("b", "a")
        manager.add_dependency("c", "b")
        assert manager.is_enabled("c") is True

    def test_transitive_dependency_broken(self, manager):
        manager.create_flag("a", state=FlagState.DISABLED)
        manager.create_flag("b", state=FlagState.ENABLED)
        manager.create_flag("c", state=FlagState.ENABLED)
        manager.add_dependency("b", "a")
        manager.add_dependency("c", "b")
        assert manager.is_enabled("c") is False

    def test_dependency_engine_add_and_get(self, dependency_engine):
        dependency_engine.add_dependency("child", "parent")
        assert dependency_engine.get_dependencies("child") == {"parent"}
        assert dependency_engine.get_dependents("parent") == {"child"}

    def test_dependency_engine_self_dependency_raises(self, dependency_engine):
        with pytest.raises(ValueError, match="cannot depend on itself"):
            dependency_engine.add_dependency("a", "a")

    def test_dependency_engine_clear(self, dependency_engine):
        dependency_engine.add_dependency("child", "parent")
        dependency_engine.clear_dependencies("child")
        assert dependency_engine.get_dependencies("child") == set()

    def test_dependency_engine_are_satisfied(self, dependency_engine):
        dependency_engine.add_dependency("child", "parent")
        evaluator = lambda name, ctx, uid: name == "parent"
        assert dependency_engine.are_satisfied("child", evaluator) is True

    def test_dependency_engine_not_satisfied(self, dependency_engine):
        dependency_engine.add_dependency("child", "parent")
        evaluator = lambda name, ctx, uid: False
        assert dependency_engine.are_satisfied("child", evaluator) is False

    def test_circular_dependency_detection(self, dependency_engine):
        dependency_engine.add_dependency("a", "b")
        dependency_engine.add_dependency("b", "a")
        assert dependency_engine.has_circular_dependency() is True

    def test_no_circular_dependency(self, dependency_engine):
        dependency_engine.add_dependency("a", "b")
        dependency_engine.add_dependency("b", "c")
        assert dependency_engine.has_circular_dependency() is False

    def test_self_circular_dependency(self, dependency_engine):
        # Self-dependency is prevented at add time, but test detection
        dependency_engine._graph["a"] = {"a"}
        assert dependency_engine.has_circular_dependency() is True

    def test_topological_order(self, dependency_engine):
        dependency_engine.add_dependency("c", "a")
        dependency_engine.add_dependency("c", "b")
        dependency_engine.add_dependency("b", "a")
        order = dependency_engine.get_topological_order()
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_dependency_engine_transitive_check(self, dependency_engine):
        dependency_engine.add_dependency("c", "b")
        dependency_engine.add_dependency("b", "a")

        def evaluator(name, ctx, uid):
            return name == "a"

        # b depends on a (enabled), c depends on b (which depends on a, enabled)
        assert dependency_engine.are_satisfied("c", evaluator) is True

    def test_manager_dependency_with_context(self, manager):
        manager.create_flag("parent", state=FlagState.ENABLED)
        manager.create_flag("child", state=FlagState.ENABLED)
        manager.add_dependency("child", "parent")
        assert manager.is_enabled("child", {"any": "context"}) is True

    def test_manager_dependency_bump_version(self, manager):
        manager.create_flag("parent")
        manager.create_flag("child")
        v1 = manager.get_flag("child").version
        manager.add_dependency("child", "parent")
        v2 = manager.get_flag("child").version
        assert v2 == v1 + 1


# ════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ════════════════════════════════════════════════════════════════════


class TestIntegration:
    """End-to-end integration tests."""

    def test_full_lifecycle(self, manager):
        # Create
        flag = manager.create_flag(
            "lifecycle",
            description="Full lifecycle test",
            state=FlagState.DISABLED,
            tags={"test"},
        )
        assert flag.state == FlagState.DISABLED

        # Enable
        manager.update_flag("lifecycle", state=FlagState.ENABLED)
        assert manager.is_enabled("lifecycle") is True

        # Add targeting
        manager.update_flag(
            "lifecycle",
            targeting_rules=[TargetingRule("plan", "eq", "premium")],
        )
        assert manager.is_enabled("lifecycle", {"plan": "premium"}) is True
        assert manager.is_enabled("lifecycle", {"plan": "free"}) is False

        # Switch to rollout
        manager.update_flag("lifecycle", state=FlagState.ROLLOUT)
        manager.set_rollout_percentage("lifecycle", 100)
        assert manager.is_enabled("lifecycle", {"plan": "premium"}, user_id="u1") is True

        # Check analytics
        analytics = manager.get_analytics("lifecycle")
        assert analytics.evaluations > 0

        # Archive
        manager.update_flag("lifecycle", state=FlagState.ARCHIVED)
        assert manager.is_enabled("lifecycle") is False

        # Delete
        manager.delete_flag("lifecycle")
        assert manager.get_flag("lifecycle") is None

    def test_evaluate_all_flags(self, manager):
        manager.create_flag("f1", state=FlagState.ENABLED)
        manager.create_flag("f2", state=FlagState.DISABLED)
        manager.create_flag("f3", state=FlagState.ENABLED)
        results = manager.evaluate_all()
        assert results == {"f1": True, "f2": False, "f3": True}

    def test_complex_targeting_with_rollout(self, manager):
        manager.create_flag(
            "complex",
            state=FlagState.ROLLOUT,
            targeting_rules=[
                TargetingRule("plan", "in", ["premium", "enterprise"]),
                TargetingRule("country", "eq", "US"),
            ],
            rollout_config=RolloutConfig(
                strategy=RolloutStrategy.PERCENTAGE,
                percentage=100,
            ),
        )
        ctx = {"plan": "premium", "country": "US"}
        assert manager.is_enabled("complex", ctx, user_id="u1") is True

        ctx2 = {"plan": "free", "country": "US"}
        assert manager.is_enabled("complex", ctx2, user_id="u1") is False

    def test_dependency_chain_with_targeting(self, manager):
        manager.create_flag(
            "base",
            state=FlagState.ENABLED,
            targeting_rules=[TargetingRule("plan", "eq", "premium")],
        )
        manager.create_flag("dependent", state=FlagState.ENABLED)
        manager.add_dependency("dependent", "base")

        assert manager.is_enabled("dependent", {"plan": "premium"}) is True
        assert manager.is_enabled("dependent", {"plan": "free"}) is False

    def test_multiple_flags_with_shared_dependency(self, manager):
        manager.create_flag("shared", state=FlagState.ENABLED)
        manager.create_flag("a", state=FlagState.ENABLED)
        manager.create_flag("b", state=FlagState.ENABLED)
        manager.add_dependency("a", "shared")
        manager.add_dependency("b", "shared")

        assert manager.is_enabled("a") is True
        assert manager.is_enabled("b") is True

        manager.update_flag("shared", state=FlagState.DISABLED)
        assert manager.is_enabled("a") is False
        assert manager.is_enabled("b") is False
