"""Comprehensive tests for the A/B testing system.

Covers all five components:
1. Experiment management
2. Traffic splitting
3. Statistical analysis
4. Experiment reporting
5. Auto-optimization
"""

import math
import unittest
from datetime import datetime, timezone

from apex_os_bp.ab_testing import (
    Assignment,
    AutoOptimizer,
    Experiment,
    ExperimentManager,
    ExperimentNotFoundError,
    ExperimentReport,
    ExperimentResult,
    ExperimentStatus,
    ExperimentValidationError,
    MetricType,
    OptimizationAction,
    ReportGenerator,
    StatisticalAnalyzer,
    StatisticalResult,
    TrafficSplitter,
    Variant,
)


# ======================================================================
# Helper functions
# ======================================================================


def make_variant(name="control", allocation=50.0, is_control=False, config=None):
    """Create a Variant with sensible defaults."""
    return Variant(
        name=name,
        traffic_allocation=allocation,
        is_control=is_control,
        config=config or {},
    )


def make_experiment(
    name="test_experiment",
    status=ExperimentStatus.DRAFT,
    variants=None,
    min_sample_size=100,
    confidence_level=0.95,
):
    """Create an Experiment with sensible defaults."""
    if variants is None:
        variants = [
            make_variant("control", 50.0, is_control=True),
            make_variant("treatment", 50.0),
        ]
    return Experiment(
        name=name,
        status=status,
        variants=variants,
        primary_metric=MetricType.CONVERSION,
        min_sample_size=min_sample_size,
        confidence_level=confidence_level,
    )


def make_result(
    variant_id="v1",
    variant_name="control",
    visitors=1000,
    conversions=100,
    revenue=500.0,
    clicks=200,
):
    """Create an ExperimentResult with sensible defaults."""
    return ExperimentResult(
        variant_id=variant_id,
        variant_name=variant_name,
        visitors=visitors,
        conversions=conversions,
        revenue=revenue,
        clicks=clicks,
    )


# ======================================================================
# 1. Experiment Management Tests
# ======================================================================


class TestExperimentManagement(unittest.TestCase):
    """Tests for ExperimentManager CRUD and lifecycle operations."""

    def setUp(self):
        self.manager = ExperimentManager()

    def tearDown(self):
        self.manager.clear_all()

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------

    def test_create_experiment_basic(self):
        exp = self.manager.create_experiment(name="my_exp")
        self.assertIsNotNone(exp.id)
        self.assertEqual(exp.name, "my_exp")
        self.assertEqual(exp.status, ExperimentStatus.DRAFT)
        self.assertEqual(len(exp.variants), 2)

    def test_create_experiment_with_variants(self):
        variants = [
            make_variant("A", 34.0, is_control=True),
            make_variant("B", 33.0),
            make_variant("C", 33.0),
        ]
        exp = self.manager.create_experiment(
            name="multi_variant",
            variants=variants,
        )
        self.assertEqual(len(exp.variants), 3)
        self.assertEqual(exp.total_traffic_allocation, 100.0)

    def test_create_experiment_duplicate_name(self):
        self.manager.create_experiment(name="dup")
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(name="dup")

    def test_create_experiment_empty_name(self):
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(name="")

    def test_create_experiment_single_variant(self):
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(
                name="bad",
                variants=[make_variant("only", 100.0, is_control=True)],
            )

    def test_create_experiment_bad_traffic_allocation(self):
        variants = [
            make_variant("A", 60.0, is_control=True),
            make_variant("B", 60.0),
        ]
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(name="bad_alloc", variants=variants)

    def test_create_experiment_multiple_controls(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0, is_control=True),
        ]
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(name="multi_ctrl", variants=variants)

    def test_create_experiment_duplicate_variant_names(self):
        variants = [
            make_variant("same", 50.0, is_control=True),
            make_variant("same", 50.0),
        ]
        with self.assertRaises(ExperimentValidationError):
            self.manager.create_experiment(name="dup_names", variants=variants)

    def test_create_experiment_with_metrics(self):
        exp = self.manager.create_experiment(
            name="metrics_exp",
            primary_metric=MetricType.REVENUE,
            secondary_metrics=[MetricType.CONVERSION, MetricType.CLICK],
        )
        self.assertEqual(exp.primary_metric, MetricType.REVENUE)
        self.assertIn(MetricType.CONVERSION, exp.secondary_metrics)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def test_get_experiment_by_id(self):
        exp = self.manager.create_experiment(name="get_by_id")
        fetched = self.manager.get_experiment(exp.id)
        self.assertEqual(fetched.id, exp.id)
        self.assertEqual(fetched.name, "get_by_id")

    def test_get_experiment_by_name(self):
        exp = self.manager.create_experiment(name="get_by_name")
        fetched = self.manager.get_experiment_by_name("get_by_name")
        self.assertEqual(fetched.id, exp.id)

    def test_get_experiment_not_found(self):
        with self.assertRaises(ExperimentNotFoundError):
            self.manager.get_experiment("nonexistent-id")

    def test_get_experiment_by_name_not_found(self):
        with self.assertRaises(ExperimentNotFoundError):
            self.manager.get_experiment_by_name("nonexistent")

    def test_list_experiments(self):
        self.manager.create_experiment(name="exp1")
        self.manager.create_experiment(name="exp2")
        self.manager.create_experiment(name="exp3")
        all_exps = self.manager.list_experiments()
        self.assertEqual(len(all_exps), 3)

    def test_list_experiments_filtered_by_status(self):
        exp1 = self.manager.create_experiment(name="draft_exp")
        exp2 = self.manager.create_experiment(name="running_exp")
        self.manager.start_experiment(exp2.id)

        drafts = self.manager.list_experiments(status=ExperimentStatus.DRAFT)
        running = self.manager.list_experiments(status=ExperimentStatus.RUNNING)

        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].name, "draft_exp")
        self.assertEqual(len(running), 1)
        self.assertEqual(running[0].name, "running_exp")

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def test_update_experiment_description(self):
        exp = self.manager.create_experiment(name="update_desc")
        updated = self.manager.update_experiment(exp.id, description="New desc")
        self.assertEqual(updated.description, "New desc")

    def test_update_experiment_name(self):
        exp = self.manager.create_experiment(name="old_name")
        updated = self.manager.update_experiment(exp.id, name="new_name")
        self.assertEqual(updated.name, "new_name")
        # Old name should no longer work
        with self.assertRaises(ExperimentNotFoundError):
            self.manager.get_experiment_by_name("old_name")
        # New name should work
        fetched = self.manager.get_experiment_by_name("new_name")
        self.assertEqual(fetched.id, exp.id)

    def test_update_experiment_invalid_field(self):
        exp = self.manager.create_experiment(name="invalid_field")
        with self.assertRaises(ExperimentValidationError):
            self.manager.update_experiment(exp.id, status=ExperimentStatus.RUNNING)

    def test_update_non_draft_experiment(self):
        exp = self.manager.create_experiment(name="running")
        self.manager.start_experiment(exp.id)
        with self.assertRaises(ExperimentValidationError):
            self.manager.update_experiment(exp.id, description="new")

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def test_delete_experiment(self):
        exp = self.manager.create_experiment(name="to_delete")
        self.manager.delete_experiment(exp.id)
        with self.assertRaises(ExperimentNotFoundError):
            self.manager.get_experiment(exp.id)

    def test_delete_experiment_not_found(self):
        with self.assertRaises(ExperimentNotFoundError):
            self.manager.delete_experiment("nonexistent")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def test_start_experiment(self):
        exp = self.manager.create_experiment(name="start_me")
        started = self.manager.start_experiment(exp.id)
        self.assertEqual(started.status, ExperimentStatus.RUNNING)
        self.assertIsNotNone(started.start_time)

    def test_start_already_running(self):
        exp = self.manager.create_experiment(name="already_running")
        self.manager.start_experiment(exp.id)
        with self.assertRaises(ExperimentValidationError):
            self.manager.start_experiment(exp.id)

    def test_pause_experiment(self):
        exp = self.manager.create_experiment(name="pause_me")
        self.manager.start_experiment(exp.id)
        paused = self.manager.pause_experiment(exp.id)
        self.assertEqual(paused.status, ExperimentStatus.PAUSED)

    def test_pause_not_running(self):
        exp = self.manager.create_experiment(name="not_running")
        with self.assertRaises(ExperimentValidationError):
            self.manager.pause_experiment(exp.id)

    def test_resume_experiment(self):
        exp = self.manager.create_experiment(name="resume_me")
        self.manager.start_experiment(exp.id)
        self.manager.pause_experiment(exp.id)
        resumed = self.manager.resume_experiment(exp.id)
        self.assertEqual(resumed.status, ExperimentStatus.RUNNING)

    def test_resume_not_paused(self):
        exp = self.manager.create_experiment(name="not_paused")
        with self.assertRaises(ExperimentValidationError):
            self.manager.resume_experiment(exp.id)

    def test_complete_experiment(self):
        exp = self.manager.create_experiment(name="complete_me")
        self.manager.start_experiment(exp.id)
        completed = self.manager.complete_experiment(exp.id)
        self.assertEqual(completed.status, ExperimentStatus.COMPLETED)
        self.assertIsNotNone(completed.end_time)

    def test_archive_experiment(self):
        exp = self.manager.create_experiment(name="archive_me")
        archived = self.manager.archive_experiment(exp.id)
        self.assertEqual(archived.status, ExperimentStatus.ARCHIVED)

    def test_cannot_start_archived(self):
        exp = self.manager.create_experiment(name="archived")
        self.manager.archive_experiment(exp.id)
        with self.assertRaises(ExperimentValidationError):
            self.manager.start_experiment(exp.id)

    # ------------------------------------------------------------------
    # Variant management
    # ------------------------------------------------------------------

    def test_add_variant(self):
        exp = self.manager.create_experiment(name="add_variant")
        # Adding a variant with 20% would exceed 100% total
        with self.assertRaises(ExperimentValidationError):
            self.manager.add_variant(exp.id, "new_variant", 20.0)

    def test_add_variant_exceeds_traffic(self):
        exp = self.manager.create_experiment(name="exceed_traffic")
        with self.assertRaises(ExperimentValidationError):
            self.manager.add_variant(exp.id, "extra", 10.0)

    def test_remove_variant(self):
        variants = [
            make_variant("A", 34.0, is_control=True),
            make_variant("B", 33.0),
            make_variant("C", 33.0),
        ]
        exp = self.manager.create_experiment(name="remove_variant", variants=variants)
        variant_b = exp.variants[1]
        updated = self.manager.remove_variant(exp.id, variant_b.id)
        self.assertEqual(len(updated.variants), 2)

    def test_remove_last_two_variants(self):
        exp = self.manager.create_experiment(name="remove_last")
        variant = exp.variants[0]
        with self.assertRaises(ExperimentValidationError):
            self.manager.remove_variant(exp.id, variant.id)

    def test_update_variant_traffic(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = self.manager.create_experiment(name="update_traffic", variants=variants)
        variant_b = exp.variants[1]
        # This should fail because total won't be 100
        with self.assertRaises(ExperimentValidationError):
            self.manager.update_variant_traffic(exp.id, variant_b.id, 60.0)

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------

    def test_clone_experiment(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = self.manager.create_experiment(
            name="original",
            variants=variants,
            description="test clone",
        )
        cloned = self.manager.clone_experiment(exp.id, "cloned")
        self.assertEqual(cloned.name, "cloned")
        self.assertEqual(cloned.description, "test clone")
        self.assertEqual(len(cloned.variants), 2)
        self.assertEqual(cloned.status, ExperimentStatus.DRAFT)
        self.assertNotEqual(cloned.id, exp.id)

    def test_clone_duplicate_name(self):
        exp = self.manager.create_experiment(name="original")
        with self.assertRaises(ExperimentValidationError):
            self.manager.clone_experiment(exp.id, "original")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def test_get_experiment_count(self):
        self.assertEqual(self.manager.get_experiment_count(), 0)
        self.manager.create_experiment(name="counted")
        self.assertEqual(self.manager.get_experiment_count(), 1)

    def test_clear_all(self):
        self.manager.create_experiment(name="clear_me")
        self.manager.clear_all()
        self.assertEqual(self.manager.get_experiment_count(), 0)


# ======================================================================
# 2. Traffic Splitting Tests
# ======================================================================


class TestTrafficSplitting(unittest.TestCase):
    """Tests for TrafficSplitter assignment and distribution."""

    def setUp(self):
        self.splitter = TrafficSplitter()
        self.experiment = make_experiment(status=ExperimentStatus.RUNNING)

    def tearDown(self):
        self.splitter.clear_cache()

    # ------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------

    def test_assign_returns_assignment(self):
        assignment = self.splitter.assign(self.experiment, "user_123")
        self.assertIsInstance(assignment, Assignment)
        self.assertEqual(assignment.experiment_id, self.experiment.id)
        self.assertEqual(assignment.user_id, "user_123")
        self.assertIn(assignment.variant_id, [v.id for v in self.experiment.variants])

    def test_assign_deterministic(self):
        """Same user should always get the same variant."""
        a1 = self.splitter.assign(self.experiment, "user_456")
        a2 = self.splitter.assign(self.experiment, "user_456")
        self.assertEqual(a1.variant_id, a2.variant_id)
        self.assertEqual(a1.bucket, a2.bucket)

    def test_assign_different_users(self):
        """Different users should (usually) get different variants."""
        assignments = {}
        for i in range(100):
            a = self.splitter.assign(self.experiment, f"user_{i}")
            assignments[a.variant_id] = assignments.get(a.variant_id, 0) + 1
        # With 50/50 split and 100 users, we should see both variants
        self.assertGreater(len(assignments), 1)

    def test_assign_not_running_experiment(self):
        draft_exp = make_experiment(status=ExperimentStatus.DRAFT)
        with self.assertRaises(ValueError):
            self.splitter.assign(draft_exp, "user_123")

    def test_assign_caching(self):
        self.splitter.assign(self.experiment, "cached_user")
        self.assertEqual(self.splitter.get_cache_size(), 1)
        # Second call should use cache
        self.splitter.assign(self.experiment, "cached_user")
        self.assertEqual(self.splitter.get_cache_size(), 1)

    def test_assign_no_cache(self):
        self.splitter.assign(self.experiment, "no_cache_user", use_cache=False)
        self.assertEqual(self.splitter.get_cache_size(), 0)

    # ------------------------------------------------------------------
    # Batch assignment
    # ------------------------------------------------------------------

    def test_assign_batch(self):
        user_ids = [f"batch_user_{i}" for i in range(50)]
        assignments = self.splitter.assign_batch(self.experiment, user_ids)
        self.assertEqual(len(assignments), 50)
        for a in assignments:
            self.assertEqual(a.experiment_id, self.experiment.id)

    # ------------------------------------------------------------------
    # Distribution
    # ------------------------------------------------------------------

    def test_get_assignment_distribution(self):
        user_ids = [f"dist_user_{i}" for i in range(1000)]
        dist = self.splitter.get_assignment_distribution(self.experiment, user_ids)
        self.assertEqual(sum(dist.values()), 1000)
        # Both variants should have assignments
        self.assertGreater(len(dist), 1)

    def test_get_assignment_percentages(self):
        user_ids = [f"pct_user_{i}" for i in range(1000)]
        pcts = self.splitter.get_assignment_percentages(self.experiment, user_ids)
        total = sum(pcts.values())
        self.assertAlmostEqual(total, 100.0, places=1)

    def test_distribution_approximates_allocation(self):
        """With enough users, distribution should approximate allocation."""
        user_ids = [f"approx_user_{i}" for i in range(5000)]
        pcts = self.splitter.get_assignment_percentages(self.experiment, user_ids)
        for variant in self.experiment.variants:
            actual = pcts.get(variant.id, 0.0)
            expected = variant.traffic_allocation
            # Allow 5% tolerance
            self.assertAlmostEqual(actual, expected, delta=5.0)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def test_clear_cache(self):
        self.splitter.assign(self.experiment, "cache_clear_user")
        self.splitter.clear_cache()
        self.assertEqual(self.splitter.get_cache_size(), 0)

    def test_clear_cache_for_experiment(self):
        exp2 = make_experiment(name="other_exp", status=ExperimentStatus.RUNNING)
        self.splitter.assign(self.experiment, "user_a")
        self.splitter.assign(exp2, "user_b")
        self.assertEqual(self.splitter.get_cache_size(), 2)
        self.splitter.clear_cache_for_experiment(self.experiment.id)
        self.assertEqual(self.splitter.get_cache_size(), 1)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_validate_split(self):
        user_ids = [f"valid_user_{i}" for i in range(2000)]
        is_valid, actual = self.splitter.validate_split(
            self.experiment, user_ids, tolerance=5.0
        )
        self.assertTrue(is_valid)

    def test_validate_split_with_custom_allocation(self):
        variants = [
            make_variant("A", 70.0, is_control=True),
            make_variant("B", 30.0),
        ]
        exp = make_experiment(
            name="custom_split",
            status=ExperimentStatus.RUNNING,
            variants=variants,
        )
        user_ids = [f"custom_user_{i}" for i in range(3000)]
        is_valid, actual = self.splitter.validate_split(exp, user_ids, tolerance=5.0)
        self.assertTrue(is_valid)

    # ------------------------------------------------------------------
    # Bucket computation
    # ------------------------------------------------------------------

    def test_bucket_range(self):
        for i in range(100):
            bucket = self.splitter._compute_bucket(self.experiment.id, f"user_{i}")
            self.assertGreaterEqual(bucket, 0)
            self.assertLess(bucket, self.splitter.NUM_BUCKETS)

    def test_variant_for_bucket(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        # Bucket 0 should map to first variant
        v = self.splitter._variant_for_bucket(variants, 0)
        self.assertIsNotNone(v)
        # Bucket 9999 should map to one of the variants
        v = self.splitter._variant_for_bucket(variants, 9999)
        self.assertIsNotNone(v)


# ======================================================================
# 3. Statistical Analysis Tests
# ======================================================================


class TestStatisticalAnalysis(unittest.TestCase):
    """Tests for StatisticalAnalyzer computations."""

    def setUp(self):
        self.analyzer = StatisticalAnalyzer(confidence_level=0.95)

    # ------------------------------------------------------------------
    # Basic rate calculations
    # ------------------------------------------------------------------

    def test_conversion_rate(self):
        self.assertAlmostEqual(
            self.analyzer.conversion_rate(50, 1000), 0.05
        )

    def test_conversion_rate_zero_visitors(self):
        self.assertEqual(self.analyzer.conversion_rate(0, 0), 0.0)

    def test_uplift_positive(self):
        uplift = self.analyzer.uplift(0.10, 0.12)
        self.assertAlmostEqual(uplift, 0.20)

    def test_uplift_negative(self):
        uplift = self.analyzer.uplift(0.10, 0.08)
        self.assertAlmostEqual(uplift, -0.20)

    def test_uplift_zero_control(self):
        self.assertEqual(self.analyzer.uplift(0.0, 0.05), 0.0)

    # ------------------------------------------------------------------
    # Confidence intervals
    # ------------------------------------------------------------------

    def test_confidence_interval_basic(self):
        low, high = self.analyzer.confidence_interval(100, 1000)
        self.assertGreaterEqual(low, 0.0)
        self.assertLessEqual(high, 1.0)
        self.assertLess(low, high)
        # Rate is 0.10, CI should contain it
        self.assertLess(low, 0.10)
        self.assertGreater(high, 0.10)

    def test_confidence_interval_zero_visitors(self):
        low, high = self.analyzer.confidence_interval(0, 0)
        self.assertEqual(low, 0.0)
        self.assertEqual(high, 0.0)

    def test_confidence_interval_narrower_with_more_samples(self):
        low1, high1 = self.analyzer.confidence_interval(100, 1000)
        low2, high2 = self.analyzer.confidence_interval(1000, 10000)
        width1 = high1 - low1
        width2 = high2 - low2
        self.assertLess(width2, width1)

    def test_confidence_interval_for_difference(self):
        low, high = self.analyzer.confidence_interval_for_difference(
            100, 1000, 120, 1000
        )
        # Treatment rate (0.12) > control rate (0.10), diff = 0.02
        self.assertLess(low, 0.02)
        self.assertGreater(high, 0.02)

    # ------------------------------------------------------------------
    # Z-test
    # ------------------------------------------------------------------

    def test_z_test_no_difference(self):
        z, p = self.analyzer.z_test_proportions(100, 1000, 100, 1000)
        self.assertAlmostEqual(z, 0.0, places=5)
        self.assertGreater(p, 0.05)

    def test_z_test_significant_difference(self):
        z, p = self.analyzer.z_test_proportions(100, 1000, 200, 1000)
        self.assertGreater(abs(z), 1.96)
        self.assertLess(p, 0.05)

    def test_z_test_zero_visitors(self):
        z, p = self.analyzer.z_test_proportions(0, 0, 0, 0)
        self.assertEqual(z, 0.0)
        self.assertEqual(p, 1.0)

    # ------------------------------------------------------------------
    # Chi-square test
    # ------------------------------------------------------------------

    def test_chi_square_no_difference(self):
        chi2, p = self.analyzer.chi_square_test(100, 1000, 100, 1000)
        self.assertAlmostEqual(chi2, 0.0, places=5)
        self.assertGreater(p, 0.05)

    def test_chi_square_significant(self):
        chi2, p = self.analyzer.chi_square_test(100, 1000, 200, 1000)
        self.assertGreater(chi2, 3.84)  # critical value at alpha=0.05
        self.assertLess(p, 0.05)

    # ------------------------------------------------------------------
    # Sample size calculation
    # ------------------------------------------------------------------

    def test_calculate_sample_size(self):
        result = self.analyzer.calculate_sample_size(
            baseline_rate=0.10,
            minimum_detectable_effect=0.20,
            alpha=0.05,
            power=0.8,
        )
        self.assertGreater(result.required_sample_size_per_variant, 0)
        self.assertEqual(
            result.total_required_sample_size,
            result.required_sample_size_per_variant * 2,
        )

    def test_calculate_sample_size_larger_effect_needs_fewer(self):
        small_effect = self.analyzer.calculate_sample_size(0.10, 0.50)
        large_effect = self.analyzer.calculate_sample_size(0.10, 0.10)
        self.assertGreater(
            large_effect.required_sample_size_per_variant,
            small_effect.required_sample_size_per_variant,
        )

    def test_calculate_sample_size_invalid_baseline(self):
        with self.assertRaises(ValueError):
            self.analyzer.calculate_sample_size(0.0, 0.20)
        with self.assertRaises(ValueError):
            self.analyzer.calculate_sample_size(1.0, 0.20)

    def test_calculate_sample_size_invalid_effect(self):
        with self.assertRaises(ValueError):
            self.analyzer.calculate_sample_size(0.10, 0.0)

    # ------------------------------------------------------------------
    # Power analysis
    # ------------------------------------------------------------------

    def test_calculate_power(self):
        power = self.analyzer.calculate_power(
            baseline_rate=0.10,
            treatment_rate=0.12,
            sample_size_per_variant=1000,
        )
        self.assertGreater(power, 0.0)
        self.assertLessEqual(power, 1.0)

    def test_calculate_power_increases_with_sample_size(self):
        power_small = self.analyzer.calculate_power(0.10, 0.12, 100)
        power_large = self.analyzer.calculate_power(0.10, 0.12, 10000)
        self.assertGreater(power_large, power_small)

    def test_calculate_power_zero_sample(self):
        power = self.analyzer.calculate_power(0.10, 0.12, 0)
        self.assertEqual(power, 0.0)

    # ------------------------------------------------------------------
    # Comprehensive analysis
    # ------------------------------------------------------------------

    def test_analyze_experiment(self):
        exp = make_experiment(status=ExperimentStatus.RUNNING)
        control_id = exp.control_variant.id
        treatment_id = exp.treatment_variants[0].id

        results = [
            make_result(control_id, "control", 1000, 100),
            make_result(treatment_id, "treatment", 1000, 120),
        ]

        analysis = self.analyzer.analyze_experiment(exp, results)
        self.assertIn(treatment_id, analysis)
        stat = analysis[treatment_id]
        self.assertIsInstance(stat, StatisticalResult)
        self.assertAlmostEqual(stat.control_value, 0.10)
        self.assertAlmostEqual(stat.treatment_value, 0.12)

    def test_analyze_experiment_no_control(self):
        exp = make_experiment(status=ExperimentStatus.RUNNING)
        exp.variants = [make_variant("A", 50.0), make_variant("B", 50.0)]
        # No control set - should raise ValueError
        results = [make_result("v1", "A", 100, 10), make_result("v2", "B", 100, 12)]
        with self.assertRaises(ValueError):
            self.analyzer.analyze_experiment(exp, results)

    # ------------------------------------------------------------------
    # Significance helper
    # ------------------------------------------------------------------

    def test_is_significant(self):
        self.assertTrue(self.analyzer.is_significant(0.01, alpha=0.05))
        self.assertFalse(self.analyzer.is_significant(0.10, alpha=0.05))

    # ------------------------------------------------------------------
    # Z-score helper
    # ------------------------------------------------------------------

    def test_z_to_p_value(self):
        # z=1.96 should give p≈0.05
        p = self.analyzer._z_to_p_value(1.96)
        self.assertAlmostEqual(p, 0.05, delta=0.01)

    def test_z_to_cdf(self):
        cdf = self.analyzer._z_to_cdf(0)
        self.assertAlmostEqual(cdf, 0.5)

    # ------------------------------------------------------------------
    # Confidence level validation
    # ------------------------------------------------------------------

    def test_invalid_confidence_level(self):
        with self.assertRaises(ValueError):
            StatisticalAnalyzer(confidence_level=0.50)


# ======================================================================
# 4. Experiment Reporting Tests
# ======================================================================


class TestExperimentReporting(unittest.TestCase):
    """Tests for ReportGenerator output and formatting."""

    def setUp(self):
        self.generator = ReportGenerator(confidence_level=0.95)
        self.experiment = make_experiment(
            name="report_test",
            status=ExperimentStatus.RUNNING,
            min_sample_size=100,
        )

    def _make_results(self, control_conv=100, treatment_conv=120):
        control_id = self.experiment.control_variant.id
        treatment_id = self.experiment.treatment_variants[0].id
        return [
            make_result(control_id, "control", 1000, control_conv, 500.0, 200),
            make_result(treatment_id, "treatment", 1000, treatment_conv, 600.0, 220),
        ]

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def test_generate_report_basic(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertIsInstance(report, ExperimentReport)
        self.assertEqual(report.experiment_name, "report_test")
        self.assertEqual(report.total_visitors, 2000)
        self.assertEqual(report.total_conversions, 220)

    def test_generate_report_variant_count(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertEqual(len(report.variants), 2)

    def test_generate_report_comparison_count(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertEqual(len(report.comparisons), 1)

    def test_generate_report_is_ready(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertTrue(report.is_ready_for_decision)

    def test_generate_report_not_ready(self):
        results = self._make_results(control_conv=5, treatment_conv=6)
        # Override visitors to be below min_sample_size
        for r in results:
            r.visitors = 50
        report = self.generator.generate_report(self.experiment, results)
        self.assertFalse(report.is_ready_for_decision)

    def test_generate_report_winner(self):
        results = self._make_results(control_conv=100, treatment_conv=150)
        report = self.generator.generate_report(self.experiment, results)
        # Treatment should win with significant uplift
        if report.is_ready_for_decision:
            self.assertIsNotNone(report.winner_variant_name)

    def test_generate_report_no_when_not_significant(self):
        results = self._make_results(control_conv=100, treatment_conv=102)
        report = self.generator.generate_report(self.experiment, results)
        # Very small difference, likely not significant
        if not report.comparisons[0].is_significant:
            self.assertIsNone(report.winner_variant_id)

    # ------------------------------------------------------------------
    # Variant report fields
    # ------------------------------------------------------------------

    def test_variant_report_fields(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        for v in report.variants:
            self.assertGreaterEqual(v.visitors, 0)
            self.assertGreaterEqual(v.conversions, 0)
            self.assertGreaterEqual(v.conversion_rate, 0.0)
            self.assertGreaterEqual(v.revenue, 0.0)
            self.assertGreaterEqual(v.revenue_per_visitor, 0.0)

    def test_variant_report_control_flag(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        control_variants = [v for v in report.variants if v.is_control]
        self.assertEqual(len(control_variants), 1)

    # ------------------------------------------------------------------
    # Comparison report fields
    # ------------------------------------------------------------------

    def test_comparison_report_fields(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        for c in report.comparisons:
            self.assertIsNotNone(c.treatment_variant_name)
            self.assertIsNotNone(c.control_variant_name)
            self.assertGreaterEqual(c.p_value, 0.0)
            self.assertLessEqual(c.p_value, 1.0)
            self.assertIsInstance(c.is_significant, bool)

    # ------------------------------------------------------------------
    # Summary and recommendations
    # ------------------------------------------------------------------

    def test_summary_contains_experiment_name(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertIn("report_test", report.summary)

    def test_recommendations_present(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        self.assertIsInstance(report.recommendations, list)
        self.assertGreater(len(report.recommendations), 0)

    # ------------------------------------------------------------------
    # Export formats
    # ------------------------------------------------------------------

    def test_export_json(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        json_str = self.generator.export_json(report)
        self.assertIsInstance(json_str, str)
        self.assertIn("report_test", json_str)
        # Should be valid JSON
        import json
        parsed = json.loads(json_str)
        self.assertEqual(parsed["experiment_name"], "report_test")

    def test_export_markdown(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        md = self.generator.export_markdown(report)
        self.assertIsInstance(md, str)
        self.assertIn("# A/B Test Report", md)
        self.assertIn("report_test", md)
        self.assertIn("Variant Results", md)
        self.assertIn("Comparisons", md)

    def test_export_csv(self):
        results = self._make_results()
        report = self.generator.generate_report(self.experiment, results)
        csv_str = self.generator.export_csv(report)
        self.assertIsInstance(csv_str, str)
        lines = csv_str.strip().split("\n")
        # Header + 2 variant rows
        self.assertEqual(len(lines), 3)
        self.assertIn("variant_id", lines[0])

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_report_with_zero_visitors(self):
        control_id = self.experiment.control_variant.id
        treatment_id = self.experiment.treatment_variants[0].id
        results = [
            make_result(control_id, "control", 0, 0),
            make_result(treatment_id, "treatment", 0, 0),
        ]
        report = self.generator.generate_report(self.experiment, results)
        self.assertEqual(report.total_visitors, 0)
        self.assertEqual(report.overall_conversion_rate, 0.0)

    def test_report_with_multiple_treatments(self):
        variants = [
            make_variant("control", 34.0, is_control=True),
            make_variant("treatment_A", 33.0),
            make_variant("treatment_B", 33.0),
        ]
        exp = make_experiment(
            name="multi_treatment",
            status=ExperimentStatus.RUNNING,
            variants=variants,
        )
        results = [
            make_result(v.id, v.name, 1000, 100 + i * 10)
            for i, v in enumerate(variants)
        ]
        report = self.generator.generate_report(exp, results)
        self.assertEqual(len(report.variants), 3)
        self.assertEqual(len(report.comparisons), 2)


# ======================================================================
# 5. Auto-Optimization Tests
# ======================================================================


class TestAutoOptimization(unittest.TestCase):
    """Tests for AutoOptimizer decision-making and optimization."""

    def setUp(self):
        self.optimizer = AutoOptimizer(
            confidence_level=0.95,
            min_probability_threshold=0.95,
        )
        self.experiment = make_experiment(
            name="optimize_test",
            status=ExperimentStatus.RUNNING,
            min_sample_size=100,
        )

    def _make_results(self, control_conv=100, treatment_conv=120, visitors=1000):
        control_id = self.experiment.control_variant.id
        treatment_id = self.experiment.treatment_variants[0].id
        return [
            make_result(control_id, "control", visitors, control_conv),
            make_result(treatment_id, "treatment", visitors, treatment_conv),
        ]

    # ------------------------------------------------------------------
    # Bayesian analysis
    # ------------------------------------------------------------------

    def test_bayesian_analysis_basic(self):
        result = self.optimizer.bayesian_analysis(100, 1000, 120, 1000)
        self.assertGreaterEqual(result.probability_treatment_better, 0.0)
        self.assertLessEqual(result.probability_treatment_better, 1.0)
        self.assertGreaterEqual(result.expected_loss_control, 0.0)
        self.assertGreaterEqual(result.expected_loss_treatment, 0.0)

    def test_bayesian_analysis_clear_winner(self):
        """With a clear difference, probability should be high."""
        result = self.optimizer.bayesian_analysis(50, 1000, 200, 1000)
        self.assertGreater(result.probability_treatment_better, 0.9)

    def test_bayesian_analysis_clear_loser(self):
        """With treatment clearly worse, probability should be low."""
        result = self.optimizer.bayesian_analysis(200, 1000, 50, 1000)
        self.assertLess(result.probability_treatment_better, 0.1)

    def test_bayesian_analysis_zero_visitors(self):
        result = self.optimizer.bayesian_analysis(0, 0, 0, 0)
        self.assertEqual(result.probability_treatment_better, 0.5)

    def test_bayesian_credible_interval(self):
        result = self.optimizer.bayesian_analysis(100, 1000, 120, 1000)
        self.assertLess(result.credible_interval_low, result.credible_interval_high)

    # ------------------------------------------------------------------
    # Recommendation engine
    # ------------------------------------------------------------------

    def test_recommend_continue_insufficient_data(self):
        results = self._make_results(visitors=50)
        action = self.optimizer.recommend_action(self.experiment, results)
        self.assertEqual(action.action_type, "continue")
        self.assertIn("Insufficient", action.reason)

    def test_recommend_promote_winner(self):
        """Strong positive result should recommend promotion."""
        results = self._make_results(control_conv=50, treatment_conv=150)
        action = self.optimizer.recommend_action(self.experiment, results)
        # With such a large difference, should recommend promote or adjust
        self.assertIn(action.action_type, ["promote_winner", "adjust_traffic"])

    def test_recommend_stop_for_harm(self):
        """Significantly worse treatment should recommend stopping."""
        results = self._make_results(control_conv=200, treatment_conv=50)
        action = self.optimizer.recommend_action(self.experiment, results)
        self.assertEqual(action.action_type, "stop_experiment")

    def test_recommend_no_control(self):
        exp = make_experiment(status=ExperimentStatus.RUNNING)
        exp.variants = []  # No variants
        action = self.optimizer.recommend_action(exp, [])
        self.assertEqual(action.action_type, "continue")

    # ------------------------------------------------------------------
    # Auto-optimize with apply
    # ------------------------------------------------------------------

    def test_auto_optimize_promote(self):
        results = self._make_results(control_conv=50, treatment_conv=150)
        action = self.optimizer.auto_optimize(self.experiment, results, apply=True)
        if action.action_type == "promote_winner":
            self.assertTrue(action.applied)

    def test_auto_optimize_continue(self):
        results = self._make_results(visitors=50)
        action = self.optimizer.auto_optimize(self.experiment, results, apply=True)
        self.assertEqual(action.action_type, "continue")
        self.assertFalse(action.applied)

    # ------------------------------------------------------------------
    # Thompson Sampling
    # ------------------------------------------------------------------

    def test_thompson_sampling_returns_variant(self):
        variant_id = self.optimizer.thompson_sampling_assignment(
            self.experiment, "user_ts"
        )
        self.assertIn(variant_id, [v.id for v in self.experiment.variants])

    def test_thompson_sampling_no_variants(self):
        exp = make_experiment(status=ExperimentStatus.RUNNING)
        exp.variants = []
        with self.assertRaises(ValueError):
            self.optimizer.thompson_sampling_assignment(exp, "user_ts")

    def test_thompson_sampling_prefers_better_variant(self):
        """With clear data, Thompson Sampling should prefer the better variant."""
        control_id = self.experiment.control_variant.id
        treatment_id = self.experiment.treatment_variants[0].id

        # Set config with performance data
        self.experiment.variants[0].config = {"conversions": 50, "visitors": 1000}
        self.experiment.variants[1].config = {"conversions": 200, "visitors": 1000}

        # Run many trials, treatment should win most
        treatment_wins = 0
        trials = 500
        for i in range(trials):
            vid = self.optimizer.thompson_sampling_assignment(
                self.experiment, f"ts_user_{i}"
            )
            if vid == treatment_id:
                treatment_wins += 1

        # Treatment should win significantly more than 50%
        self.assertGreater(treatment_wins / trials, 0.6)

    # ------------------------------------------------------------------
    # Early stopping
    # ------------------------------------------------------------------

    def test_should_not_stop_early_insufficient_data(self):
        results = self._make_results(visitors=50)
        should_stop, reason = self.optimizer.should_stop_early(
            self.experiment, results
        )
        self.assertFalse(should_stop)

    def test_should_stop_early_for_harm(self):
        results = self._make_results(control_conv=200, treatment_conv=30)
        should_stop, reason = self.optimizer.should_stop_early(
            self.experiment, results
        )
        self.assertTrue(should_stop)
        self.assertIn("worse", reason.lower())

    def test_should_not_stop_early_for_similar(self):
        results = self._make_results(control_conv=100, treatment_conv=102)
        should_stop, reason = self.optimizer.should_stop_early(
            self.experiment, results
        )
        self.assertFalse(should_stop)

    # ------------------------------------------------------------------
    # Traffic optimization
    # ------------------------------------------------------------------

    def test_optimize_traffic_allocation(self):
        results = self._make_results(control_conv=100, treatment_conv=150)
        allocations = self.optimizer.optimize_traffic_allocation(
            self.experiment, results
        )
        self.assertEqual(len(allocations), 2)
        total = sum(allocations.values())
        self.assertAlmostEqual(total, 100.0, places=1)

    def test_optimize_traffic_favors_better_variant(self):
        control_id = self.experiment.control_variant.id
        treatment_id = self.experiment.treatment_variants[0].id
        results = self._make_results(control_conv=50, treatment_conv=200)
        allocations = self.optimizer.optimize_traffic_allocation(
            self.experiment, results
        )
        # Treatment should get more traffic
        self.assertGreater(allocations[treatment_id], allocations[control_id])

    def test_optimize_traffic_empty_results(self):
        allocations = self.optimizer.optimize_traffic_allocation(
            self.experiment, []
        )
        # Should return current allocations
        for v in self.experiment.variants:
            self.assertIn(v.id, allocations)

    def test_optimize_traffic_minimum_allocation(self):
        """All variants should get at least 10% for exploration."""
        results = self._make_results(control_conv=100, treatment_conv=500)
        allocations = self.optimizer.optimize_traffic_allocation(
            self.experiment, results
        )
        for vid, alloc in allocations.items():
            self.assertGreaterEqual(alloc, 10.0)

    # ------------------------------------------------------------------
    # Action types
    # ------------------------------------------------------------------

    def test_optimization_action_fields(self):
        action = OptimizationAction(
            action_type="promote_winner",
            reason="test",
            confidence=0.95,
            details={"winner_variant_id": "v1"},
        )
        self.assertEqual(action.action_type, "promote_winner")
        self.assertEqual(action.confidence, 0.95)
        self.assertFalse(action.applied)

    def test_optimization_action_apply(self):
        action = OptimizationAction(
            action_type="stop_experiment",
            reason="harm detected",
            confidence=0.99,
        )
        self.assertFalse(action.applied)
        action.applied = True
        self.assertTrue(action.applied)


# ======================================================================
# Integration Tests
# ======================================================================


class TestABTestingIntegration(unittest.TestCase):
    """End-to-end integration tests for the full A/B testing workflow."""

    def setUp(self):
        self.manager = ExperimentManager()
        self.splitter = TrafficSplitter()
        self.analyzer = StatisticalAnalyzer()
        self.reporter = ReportGenerator()
        self.optimizer = AutoOptimizer()

    def tearDown(self):
        self.manager.clear_all()
        self.splitter.clear_cache()

    def test_full_experiment_lifecycle(self):
        """Test the complete lifecycle from creation to report."""
        # 1. Create experiment
        exp = self.manager.create_experiment(
            name="lifecycle_test",
            variants=[
                make_variant("control", 50.0, is_control=True),
                make_variant("treatment", 50.0),
            ],
        )
        self.assertEqual(exp.status, ExperimentStatus.DRAFT)

        # 2. Start experiment
        self.manager.start_experiment(exp.id)
        exp = self.manager.get_experiment(exp.id)
        self.assertEqual(exp.status, ExperimentStatus.RUNNING)

        # 3. Assign users
        user_ids = [f"user_{i}" for i in range(1000)]
        assignments = self.splitter.assign_batch(exp, user_ids)
        self.assertEqual(len(assignments), 1000)

        # 4. Simulate results
        control_id = exp.control_variant.id
        treatment_id = exp.treatment_variants[0].id

        control_assignments = [a for a in assignments if a.variant_id == control_id]
        treatment_assignments = [a for a in assignments if a.variant_id == treatment_id]

        results = [
            make_result(
                control_id, "control",
                len(control_assignments),
                int(len(control_assignments) * 0.10),
            ),
            make_result(
                treatment_id, "treatment",
                len(treatment_assignments),
                int(len(treatment_assignments) * 0.12),
            ),
        ]

        # 5. Analyze
        analysis = self.analyzer.analyze_experiment(exp, results)
        self.assertIn(treatment_id, analysis)

        # 6. Generate report
        report = self.reporter.generate_report(exp, results)
        self.assertEqual(report.total_visitors, 1000)

        # 7. Get optimization recommendation
        action = self.optimizer.recommend_action(exp, results)
        self.assertIsInstance(action, OptimizationAction)

        # 8. Complete experiment
        self.manager.complete_experiment(exp.id)
        exp = self.manager.get_experiment(exp.id)
        self.assertEqual(exp.status, ExperimentStatus.COMPLETED)

    def test_multi_variant_experiment(self):
        """Test with 3+ variants."""
        variants = [
            make_variant("control", 34.0, is_control=True),
            make_variant("treatment_A", 33.0),
            make_variant("treatment_B", 33.0),
        ]
        exp = self.manager.create_experiment(
            name="multi_variant",
            variants=variants,
        )
        self.manager.start_experiment(exp.id)

        # Assign users
        user_ids = [f"mv_user_{i}" for i in range(3000)]
        assignments = self.splitter.assign_batch(exp, user_ids)

        # All three variants should have assignments
        variant_ids = set(a.variant_id for a in assignments)
        self.assertEqual(len(variant_ids), 3)

        # Generate results for all variants
        results = []
        for i, v in enumerate(exp.variants):
            count = sum(1 for a in assignments if a.variant_id == v.id)
            results.append(make_result(v.id, v.name, count, int(count * (0.10 + i * 0.02))))

        # Report should have 3 variants and 2 comparisons
        report = self.reporter.generate_report(exp, results)
        self.assertEqual(len(report.variants), 3)
        self.assertEqual(len(report.comparisons), 2)

    def test_traffic_rebalance_after_optimization(self):
        """Test that traffic is rebalanced after optimization."""
        exp = self.manager.create_experiment(
            name="rebalance_test",
            variants=[
                make_variant("control", 50.0, is_control=True),
                make_variant("treatment", 50.0),
            ],
        )
        self.manager.start_experiment(exp.id)

        control_id = exp.control_variant.id
        treatment_id = exp.treatment_variants[0].id

        results = [
            make_result(control_id, "control", 1000, 50),
            make_result(treatment_id, "treatment", 1000, 150),
        ]

        # Auto-optimize with apply
        action = self.optimizer.auto_optimize(exp, results, apply=True)

        if action.action_type == "promote_winner":
            # Traffic should have been rebalanced
            total = exp.total_traffic_allocation
            self.assertAlmostEqual(total, 100.0, delta=0.1)


# ======================================================================
# Model Tests
# ======================================================================


class TestModels(unittest.TestCase):
    """Tests for data model validation and properties."""

    def test_variant_validation(self):
        with self.assertRaises(ValueError):
            Variant(name="", traffic_allocation=50.0)

    def test_variant_traffic_allocation_bounds(self):
        with self.assertRaises(ValueError):
            Variant(name="test", traffic_allocation=-1.0)
        with self.assertRaises(ValueError):
            Variant(name="test", traffic_allocation=101.0)

    def test_experiment_validation(self):
        with self.assertRaises(ValueError):
            Experiment(name="")

    def test_experiment_min_variants(self):
        with self.assertRaises(ValueError):
            Experiment(
                name="test",
                variants=[make_variant("only", 100.0, is_control=True)],
            )

    def test_experiment_confidence_level(self):
        with self.assertRaises(ValueError):
            Experiment(
                name="test",
                variants=[
                    make_variant("A", 50.0, is_control=True),
                    make_variant("B", 50.0),
                ],
                confidence_level=0.0,
            )
        with self.assertRaises(ValueError):
            Experiment(
                name="test",
                variants=[
                    make_variant("A", 50.0, is_control=True),
                    make_variant("B", 50.0),
                ],
                confidence_level=1.0,
            )

    def test_experiment_control_variant(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = Experiment(name="test", variants=variants)
        self.assertEqual(exp.control_variant.name, "A")

    def test_experiment_treatment_variants(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = Experiment(name="test", variants=variants)
        self.assertEqual(len(exp.treatment_variants), 1)
        self.assertEqual(exp.treatment_variants[0].name, "B")

    def test_experiment_total_traffic_allocation(self):
        variants = [
            make_variant("A", 34.0, is_control=True),
            make_variant("B", 33.0),
            make_variant("C", 33.0),
        ]
        exp = Experiment(name="test", variants=variants)
        self.assertAlmostEqual(exp.total_traffic_allocation, 100.0)

    def test_experiment_validate_traffic_allocation(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = Experiment(name="test", variants=variants)
        self.assertTrue(exp.validate_traffic_allocation())

    def test_experiment_get_variant(self):
        variants = [
            make_variant("A", 50.0, is_control=True),
            make_variant("B", 50.0),
        ]
        exp = Experiment(name="test", variants=variants)
        found = exp.get_variant(variants[0].id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "A")
        not_found = exp.get_variant("nonexistent")
        self.assertIsNone(not_found)

    def test_experiment_result_conversion_rate(self):
        result = make_result(visitors=1000, conversions=100)
        self.assertAlmostEqual(result.conversion_rate, 0.10)

    def test_experiment_result_revenue_per_visitor(self):
        result = make_result(visitors=1000, revenue=500.0)
        self.assertAlmostEqual(result.revenue_per_visitor, 0.50)

    def test_experiment_result_click_rate(self):
        result = make_result(visitors=1000, clicks=200)
        self.assertAlmostEqual(result.click_rate, 0.20)

    def test_experiment_result_zero_visitors(self):
        result = make_result(visitors=0, conversions=0)
        self.assertEqual(result.conversion_rate, 0.0)
        self.assertEqual(result.revenue_per_visitor, 0.0)
        self.assertEqual(result.click_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
