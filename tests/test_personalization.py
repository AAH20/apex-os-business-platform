"""Tests for the personalization system."""

from __future__ import annotations

import time
import unittest

from apex_os_bp.personalization.ab_testing import ABTestManager, Variant
from apex_os_bp.personalization.analytics import PersonalizationAnalytics
from apex_os_bp.personalization.behavior import BehaviorTracker
from apex_os_bp.personalization.profiles import ProfileStore, UserProfile
from apex_os_bp.personalization.rules import (
    PersonalizationRule,
    RuleCondition,
    RuleEngine,
)


class TestUserProfile(unittest.TestCase):
    """Tests for UserProfile."""

    def test_create_profile(self) -> None:
        profile = UserProfile(user_id="u1")
        self.assertEqual(profile.user_id, "u1")
        self.assertEqual(profile.segments, [])
        self.assertEqual(profile.preferences, {})

    def test_add_segment(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.add_segment("premium")
        self.assertIn("premium", profile.segments)
        profile.add_segment("premium")
        self.assertEqual(profile.segments.count("premium"), 1)

    def test_remove_segment(self) -> None:
        profile = UserProfile(user_id="u1", segments=["premium", "beta"])
        profile.remove_segment("premium")
        self.assertNotIn("premium", profile.segments)
        self.assertIn("beta", profile.segments)

    def test_preferences(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.set_preference("theme", "dark")
        self.assertEqual(profile.get_preference("theme"), "dark")
        self.assertEqual(profile.get_preference("missing", "default"), "default")

    def test_attributes(self) -> None:
        profile = UserProfile(user_id="u1")
        profile.set_attribute("age", 30)
        self.assertEqual(profile.get_attribute("age"), 30)

    def test_serialization(self) -> None:
        profile = UserProfile(
            user_id="u1",
            segments=["premium"],
            preferences={"theme": "dark"},
            attributes={"age": 30},
        )
        data = profile.to_dict()
        restored = UserProfile.from_dict(data)
        self.assertEqual(restored.user_id, "u1")
        self.assertEqual(restored.segments, ["premium"])
        self.assertEqual(restored.preferences, {"theme": "dark"})
        self.assertEqual(restored.attributes, {"age": 30})


class TestProfileStore(unittest.TestCase):
    """Tests for ProfileStore."""

    def setUp(self) -> None:
        self.store = ProfileStore()

    def test_create_and_get(self) -> None:
        profile = self.store.create("u1", segments=["premium"])
        self.assertEqual(profile.user_id, "u1")
        fetched = self.store.get("u1")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.segments, ["premium"])

    def test_create_duplicate_raises(self) -> None:
        self.store.create("u1")
        with self.assertRaises(ValueError):
            self.store.create("u1")

    def test_get_or_create(self) -> None:
        p1 = self.store.get_or_create("u1")
        p2 = self.store.get_or_create("u1")
        self.assertIs(p1, p2)

    def test_update(self) -> None:
        self.store.create("u1")
        self.store.update("u1", segments=["beta"])
        profile = self.store.get("u1")
        self.assertEqual(profile.segments, ["beta"])

    def test_update_missing_raises(self) -> None:
        with self.assertRaises(KeyError):
            self.store.update("nonexistent", segments=["x"])

    def test_delete(self) -> None:
        self.store.create("u1")
        self.assertTrue(self.store.delete("u1"))
        self.assertFalse(self.store.delete("u1"))
        self.assertIsNone(self.store.get("u1"))

    def test_find_by_segment(self) -> None:
        self.store.create("u1", segments=["premium", "beta"])
        self.store.create("u2", segments=["free"])
        self.store.create("u3", segments=["premium"])
        results = self.store.find_by_segment("premium")
        self.assertEqual(len(results), 2)

    def test_count(self) -> None:
        self.assertEqual(self.store.count(), 0)
        self.store.create("u1")
        self.store.create("u2")
        self.assertEqual(self.store.count(), 2)


class TestBehaviorTracker(unittest.TestCase):
    """Tests for BehaviorTracker."""

    def setUp(self) -> None:
        self.tracker = BehaviorTracker()

    def test_track_event(self) -> None:
        event = self.tracker.track("u1", "page_view", {"url": "/home"})
        self.assertEqual(event.user_id, "u1")
        self.assertEqual(event.event_type, "page_view")
        self.assertEqual(event.properties["url"], "/home")

    def test_get_user_events(self) -> None:
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "page_view")
        self.tracker.track("u2", "click")
        events = self.tracker.get_user_events("u1")
        self.assertEqual(len(events), 2)

    def test_filter_by_event_type(self) -> None:
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "page_view")
        clicks = self.tracker.get_user_events("u1", "click")
        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0].event_type, "click")

    def test_session_tracking(self) -> None:
        self.tracker.track("u1", "click", session_id="s1")
        self.tracker.track("u1", "page_view", session_id="s1")
        self.tracker.track("u1", "click", session_id="s2")
        s1_events = self.tracker.get_session_events("s1")
        self.assertEqual(len(s1_events), 2)

    def test_event_count(self) -> None:
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "view")
        self.tracker.track("u2", "click")
        self.assertEqual(self.tracker.get_event_count(), 3)
        self.assertEqual(self.tracker.get_event_count("u1"), 2)

    def test_event_types(self) -> None:
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "view")
        types = self.tracker.get_event_types("u1")
        self.assertEqual(types["click"], 2)
        self.assertEqual(types["view"], 1)

    def test_last_and_first_event(self) -> None:
        self.tracker.track("u1", "first", timestamp=100.0)
        self.tracker.track("u1", "last", timestamp=200.0)
        first = self.tracker.get_first_event("u1")
        last = self.tracker.get_last_event("u1")
        self.assertEqual(first.event_type, "first")
        self.assertEqual(last.event_type, "last")

    def test_clear(self) -> None:
        self.tracker.track("u1", "click")
        self.tracker.clear()
        self.assertEqual(self.tracker.get_event_count(), 0)


class TestRuleCondition(unittest.TestCase):
    """Tests for RuleCondition."""

    def test_eq_operator(self) -> None:
        cond = RuleCondition("attributes.age", "eq", 30)
        profile = UserProfile(user_id="u1", attributes={"age": 30})
        self.assertTrue(cond.evaluate(profile))

    def test_gt_operator(self) -> None:
        cond = RuleCondition("attributes.age", "gt", 25)
        profile = UserProfile(user_id="u1", attributes={"age": 30})
        self.assertTrue(cond.evaluate(profile))

    def test_lt_operator(self) -> None:
        cond = RuleCondition("attributes.age", "lt", 25)
        profile = UserProfile(user_id="u1", attributes={"age": 30})
        self.assertFalse(cond.evaluate(profile))

    def test_contains_operator(self) -> None:
        cond = RuleCondition("segments", "contains", "premium")
        profile = UserProfile(user_id="u1", segments=["premium", "beta"])
        self.assertTrue(cond.evaluate(profile))

    def test_in_operator(self) -> None:
        cond = RuleCondition("attributes.plan", "in", ["pro", "enterprise"])
        profile = UserProfile(user_id="u1", attributes={"plan": "pro"})
        self.assertTrue(cond.evaluate(profile))

    def test_preference_field(self) -> None:
        cond = RuleCondition("preferences.theme", "eq", "dark")
        profile = UserProfile(user_id="u1", preferences={"theme": "dark"})
        self.assertTrue(cond.evaluate(profile))

    def test_unknown_operator_raises(self) -> None:
        cond = RuleCondition("attributes.age", "unknown_op", 30)
        profile = UserProfile(user_id="u1", attributes={"age": 30})
        with self.assertRaises(ValueError):
            cond.evaluate(profile)


class TestPersonalizationRule(unittest.TestCase):
    """Tests for PersonalizationRule."""

    def test_evaluate_all_conditions(self) -> None:
        rule = PersonalizationRule(
            rule_id="r1",
            name="premium_dark",
            conditions=[
                RuleCondition("segments", "contains", "premium"),
                RuleCondition("preferences.theme", "eq", "dark"),
            ],
            action={"show_banner": True},
        )
        profile = UserProfile(
            user_id="u1",
            segments=["premium"],
            preferences={"theme": "dark"},
        )
        self.assertTrue(rule.evaluate(profile))

    def test_evaluate_fails_if_any_condition_fails(self) -> None:
        rule = PersonalizationRule(
            rule_id="r1",
            name="test",
            conditions=[
                RuleCondition("segments", "contains", "premium"),
                RuleCondition("preferences.theme", "eq", "light"),
            ],
        )
        profile = UserProfile(
            user_id="u1",
            segments=["premium"],
            preferences={"theme": "dark"},
        )
        self.assertFalse(rule.evaluate(profile))

    def test_disabled_rule_never_matches(self) -> None:
        rule = PersonalizationRule(
            rule_id="r1",
            name="test",
            conditions=[RuleCondition("segments", "contains", "premium")],
            enabled=False,
        )
        profile = UserProfile(user_id="u1", segments=["premium"])
        self.assertFalse(rule.evaluate(profile))

    def test_serialization(self) -> None:
        rule = PersonalizationRule(
            rule_id="r1",
            name="test",
            conditions=[RuleCondition("segments", "contains", "premium")],
            action={"key": "value"},
            priority=5,
        )
        data = rule.to_dict()
        self.assertEqual(data["rule_id"], "r1")
        self.assertEqual(data["priority"], 5)
        self.assertEqual(len(data["conditions"]), 1)


class TestRuleEngine(unittest.TestCase):
    """Tests for RuleEngine."""

    def setUp(self) -> None:
        self.engine = RuleEngine()

    def test_add_and_get_rule(self) -> None:
        rule = PersonalizationRule(rule_id="r1", name="test")
        self.engine.add_rule(rule)
        self.assertEqual(self.engine.get_rule("r1").name, "test")

    def test_remove_rule(self) -> None:
        self.engine.add_rule(PersonalizationRule(rule_id="r1", name="test"))
        self.assertTrue(self.engine.remove_rule("r1"))
        self.assertFalse(self.engine.remove_rule("r1"))

    def test_evaluate_returns_matching_actions(self) -> None:
        self.engine.add_rule(
            PersonalizationRule(
                rule_id="r1",
                name="premium",
                conditions=[RuleCondition("segments", "contains", "premium")],
                action={"banner": "premium_offer"},
                priority=10,
            )
        )
        self.engine.add_rule(
            PersonalizationRule(
                rule_id="r2",
                name="all_users",
                conditions=[],
                action={"banner": "general"},
                priority=1,
            )
        )
        profile = UserProfile(user_id="u1", segments=["premium"])
        actions = self.engine.evaluate(profile)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0]["banner"], "premium_offer")

    def test_evaluate_no_match(self) -> None:
        self.engine.add_rule(
            PersonalizationRule(
                rule_id="r1",
                name="enterprise_only",
                conditions=[RuleCondition("segments", "contains", "enterprise")],
                action={"x": 1},
            )
        )
        profile = UserProfile(user_id="u1", segments=["free"])
        actions = self.engine.evaluate(profile)
        self.assertEqual(actions, [])

    def test_evaluate_single(self) -> None:
        self.engine.add_rule(
            PersonalizationRule(
                rule_id="r1",
                name="test",
                conditions=[RuleCondition("segments", "contains", "premium")],
                action={"show": True},
            )
        )
        profile = UserProfile(user_id="u1", segments=["premium"])
        result = self.engine.evaluate_single(profile, "r1")
        self.assertIsNotNone(result)
        self.assertTrue(result["show"])

    def test_list_rules_sorted_by_priority(self) -> None:
        self.engine.add_rule(
            PersonalizationRule(rule_id="r1", name="low", priority=1)
        )
        self.engine.add_rule(
            PersonalizationRule(rule_id="r2", name="high", priority=10)
        )
        rules = self.engine.list_rules()
        self.assertEqual(rules[0].rule_id, "r2")
        self.assertEqual(rules[1].rule_id, "r1")


class TestABTestManager(unittest.TestCase):
    """Tests for ABTestManager."""

    def setUp(self) -> None:
        self.manager = ABTestManager()

    def test_create_experiment(self) -> None:
        variants = [Variant("v1", "Control", 0.5), Variant("v2", "Treatment", 0.5)]
        exp = self.manager.create_experiment("exp1", "Test", variants)
        self.assertEqual(exp.experiment_id, "exp1")
        self.assertEqual(len(exp.variants), 2)

    def test_create_duplicate_raises(self) -> None:
        variants = [Variant("v1", "Control", 1.0)]
        self.manager.create_experiment("exp1", "Test", variants)
        with self.assertRaises(ValueError):
            self.manager.create_experiment("exp1", "Test 2", variants)

    def test_start_and_assign(self) -> None:
        variants = [Variant("v1", "Control", 0.5), Variant("v2", "Treatment", 0.5)]
        self.manager.create_experiment("exp1", "Test", variants)
        self.manager.start_experiment("exp1")
        variant = self.manager.assign_variant("exp1", "user1")
        self.assertIsNotNone(variant)
        self.assertIn(variant, ["v1", "v2"])

    def test_consistent_assignment(self) -> None:
        variants = [Variant("v1", "Control", 0.5), Variant("v2", "Treatment", 0.5)]
        self.manager.create_experiment("exp1", "Test", variants)
        self.manager.start_experiment("exp1")
        v1 = self.manager.assign_variant("exp1", "user1")
        v2 = self.manager.assign_variant("exp1", "user1")
        self.assertEqual(v1, v2)

    def test_assign_when_not_running(self) -> None:
        variants = [Variant("v1", "Control", 1.0)]
        self.manager.create_experiment("exp1", "Test", variants)
        result = self.manager.assign_variant("exp1", "user1")
        self.assertIsNone(result)

    def test_track_conversion(self) -> None:
        variants = [Variant("v1", "Control", 1.0)]
        self.manager.create_experiment("exp1", "Test", variants)
        self.manager.track_conversion("exp1", "v1", 1.0)
        self.manager.track_conversion("exp1", "v1", 1.0)
        data = self.manager.get_conversion_data("exp1")
        self.assertEqual(data["v1"]["count"], 2)
        self.assertEqual(data["v1"]["total"], 2.0)

    def test_pause_and_complete(self) -> None:
        variants = [Variant("v1", "Control", 1.0)]
        self.manager.create_experiment("exp1", "Test", variants)
        self.manager.start_experiment("exp1")
        self.manager.pause_experiment("exp1")
        exp = self.manager.get_experiment("exp1")
        self.assertEqual(exp.status, "paused")
        self.manager.complete_experiment("exp1")
        self.assertEqual(exp.status, "completed")
        self.assertIsNotNone(exp.end_time)

    def test_delete_experiment(self) -> None:
        variants = [Variant("v1", "Control", 1.0)]
        self.manager.create_experiment("exp1", "Test", variants)
        self.assertTrue(self.manager.delete_experiment("exp1"))
        self.assertFalse(self.manager.delete_experiment("exp1"))


class TestPersonalizationAnalytics(unittest.TestCase):
    """Tests for PersonalizationAnalytics."""

    def setUp(self) -> None:
        self.store = ProfileStore()
        self.tracker = BehaviorTracker()
        self.ab = ABTestManager()
        self.analytics = PersonalizationAnalytics(self.store, self.tracker, self.ab)

    def test_engagement_score_no_events(self) -> None:
        self.store.create("u1")
        score = self.analytics.compute_engagement_score("u1")
        self.assertEqual(score.score, 0.0)

    def test_engagement_score_with_events(self) -> None:
        self.store.create("u1")
        for i in range(5):
            self.tracker.track("u1", "click", session_id="s1")
        self.tracker.track("u1", "page_view", session_id="s1")
        score = self.analytics.compute_engagement_score("u1")
        self.assertGreater(score.score, 0.0)
        self.assertLessEqual(score.score, 100.0)
        self.assertIn("event_count", score.factors)

    def test_segment_distribution(self) -> None:
        self.store.create("u1", segments=["premium", "beta"])
        self.store.create("u2", segments=["free"])
        self.store.create("u3", segments=["premium"])
        dist = self.analytics.get_segment_distribution()
        self.assertEqual(dist["premium"], 2)
        self.assertEqual(dist["free"], 1)
        self.assertEqual(dist["beta"], 1)

    def test_top_preferences(self) -> None:
        self.store.create("u1", preferences={"theme": "dark", "lang": "en"})
        self.store.create("u2", preferences={"theme": "light"})
        self.store.create("u3", preferences={"theme": "dark"})
        top = self.analytics.get_top_preferences()
        self.assertEqual(top[0][0], "theme")
        self.assertEqual(top[0][1], 3)

    def test_experiment_summary(self) -> None:
        variants = [Variant("v1", "Control", 0.5), Variant("v2", "Treatment", 0.5)]
        self.ab.create_experiment("exp1", "Test", variants)
        self.ab.start_experiment("exp1")
        self.ab.track_conversion("exp1", "v1", 1.0)
        summary = self.analytics.get_experiment_summary("exp1")
        self.assertIsNotNone(summary)
        self.assertEqual(summary["experiment_id"], "exp1")
        self.assertEqual(len(summary["variants"]), 2)

    def test_overall_metrics(self) -> None:
        self.store.create("u1", segments=["premium"])
        self.store.create("u2", segments=["free"])
        self.tracker.track("u1", "click")
        self.tracker.track("u1", "view")
        self.tracker.track("u2", "click")
        metrics = self.analytics.get_overall_metrics()
        self.assertEqual(metrics["total_users"], 2)
        self.assertEqual(metrics["total_events"], 3)
        self.assertEqual(metrics["segments"]["premium"], 1)
        self.assertEqual(metrics["event_types"]["click"], 2)
        self.assertEqual(metrics["avg_events_per_user"], 1.5)


if __name__ == "__main__":
    unittest.main()
