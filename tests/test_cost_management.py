"""Tests for cost management module."""
import pytest
from datetime import datetime, timedelta

from apex_os_bp.cost_management.models import (
    CostCategory,
    CostEntry,
    CostStatus,
    AllocationMethod,
    AllocationRule,
    AllocationResult,
    BudgetPeriod,
    BudgetStatus,
    Budget,
    BudgetAlert,
    ForecastMethod,
    ForecastResult,
    OptimizationSuggestion,
    OptimizationType,
)
from apex_os_bp.cost_management.tracking import CostTracker
from apex_os_bp.cost_management.allocation import CostAllocator
from apex_os_bp.cost_management.optimization import CostOptimizer
from apex_os_bp.cost_management.budget import BudgetManager
from apex_os_bp.cost_management.forecasting import CostForecaster


# ============================================================================
# Model Tests
# ============================================================================

class TestCostEntry:
    """Test cost entry model."""

    def test_create(self):
        """Cost entry can be created with required fields."""
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Server costs",
        )
        assert entry.category == CostCategory.INFRASTRUCTURE
        assert entry.amount == 1000.0
        assert entry.currency == "USD"
        assert entry.description == "Server costs"
        assert entry.id is not None
        assert entry.status == CostStatus.PENDING

    def test_create_with_optional_fields(self):
        """Cost entry supports optional fields."""
        entry = CostEntry.create(
            category=CostCategory.PERSONNEL,
            amount=5000.0,
            currency="EUR",
            description="Salary",
            department_id="dept-1",
            project_id="proj-1",
            vendor_id="vendor-1",
            tags=["recurring", "monthly"],
        )
        assert entry.department_id == "dept-1"
        assert entry.project_id == "proj-1"
        assert entry.vendor_id == "vendor-1"
        assert "recurring" in entry.tags

    def test_approve(self):
        """Cost entry can be approved."""
        entry = CostEntry.create(
            category=CostCategory.OPERATIONS,
            amount=100.0,
            currency="USD",
            description="Office supplies",
        )
        entry.approve()
        assert entry.status == CostStatus.APPROVED
        assert entry.approved_date is not None

    def test_reject(self):
        """Cost entry can be rejected."""
        entry = CostEntry.create(
            category=CostCategory.MISCELLANEOUS,
            amount=50.0,
            currency="USD",
            description="Misc",
        )
        entry.reject()
        assert entry.status == CostStatus.REJECTED

    def test_mark_paid(self):
        """Cost entry can be marked as paid."""
        entry = CostEntry.create(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
        )
        entry.mark_paid()
        assert entry.status == CostStatus.PAID

    def test_cancel(self):
        """Cost entry can be cancelled."""
        entry = CostEntry.create(
            category=CostCategory.TRAVEL,
            amount=300.0,
            currency="USD",
            description="Flight",
        )
        entry.cancel()
        assert entry.status == CostStatus.CANCELLED


class TestAllocationRule:
    """Test allocation rule model."""

    def test_create(self):
        """Allocation rule can be created."""
        rule = AllocationRule.create(
            name="IT Cost Split",
            source_department_id="it-dept",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.EQUAL,
        )
        assert rule.name == "IT Cost Split"
        assert rule.source_department_id == "it-dept"
        assert len(rule.target_department_ids) == 2
        assert rule.method == AllocationMethod.EQUAL
        assert rule.active is True

    def test_create_with_percentages(self):
        """Allocation rule supports percentage-based allocation."""
        rule = AllocationRule.create(
            name="Revenue Split",
            source_department_id="corp",
            target_department_ids=["sales", "marketing"],
            method=AllocationMethod.PERCENTAGE,
            percentages={"sales": 60.0, "marketing": 40.0},
        )
        assert rule.percentages["sales"] == 60.0
        assert rule.percentages["marketing"] == 40.0

    def test_create_with_category_filter(self):
        """Allocation rule supports category filtering."""
        rule = AllocationRule.create(
            name="Infra Split",
            source_department_id="it",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
            category_filter=[CostCategory.INFRASTRUCTURE],
        )
        assert rule.category_filter == [CostCategory.INFRASTRUCTURE]


class TestAllocationResult:
    """Test allocation result model."""

    def test_create(self):
        """Allocation result can be created."""
        result = AllocationResult.create(
            rule_id="rule-1",
            source_cost_id="cost-1",
            allocations={"dept-a": 600.0, "dept-b": 400.0},
        )
        assert result.rule_id == "rule-1"
        assert result.source_cost_id == "cost-1"
        assert result.total_allocated == 1000.0
        assert result.allocations["dept-a"] == 600.0


class TestBudget:
    """Test budget model."""

    def test_create(self):
        """Budget can be created."""
        budget = Budget.create(
            name="Q1 Budget",
            department_id="dept-1",
            amount=50000.0,
            currency="USD",
            period=BudgetPeriod.QUARTERLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 3, 31),
        )
        assert budget.name == "Q1 Budget"
        assert budget.amount == 50000.0
        assert budget.period == BudgetPeriod.QUARTERLY
        assert budget.status == BudgetStatus.DRAFT
        assert budget.spent == 0.0

    def test_remaining(self):
        """Budget remaining is computed correctly."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        budget.add_spend(3000.0)
        assert budget.remaining == 7000.0

    def test_utilization_rate(self):
        """Budget utilization rate is computed correctly."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        budget.add_spend(7500.0)
        assert budget.utilization_rate == 0.75

    def test_is_exceeded(self):
        """Budget exceeded detection works."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        assert not budget.is_exceeded
        budget.add_spend(1500.0)
        assert budget.is_exceeded
        assert budget.status == BudgetStatus.EXCEEDED

    def test_is_near_limit(self):
        """Budget near-limit detection works."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            alert_threshold=0.8,
        )
        assert not budget.is_near_limit
        budget.add_spend(850.0)
        assert budget.is_near_limit

    def test_activate(self):
        """Budget can be activated."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        budget.activate()
        assert budget.status == BudgetStatus.ACTIVE

    def test_freeze(self):
        """Budget can be frozen."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        budget.freeze()
        assert budget.status == BudgetStatus.FROZEN

    def test_close(self):
        """Budget can be closed."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        budget.close()
        assert budget.status == BudgetStatus.CLOSED


class TestBudgetAlert:
    """Test budget alert model."""

    def test_create(self):
        """Budget alert can be created."""
        alert = BudgetAlert.create(
            budget_id="budget-1",
            message="Budget exceeded",
            severity="critical",
        )
        assert alert.budget_id == "budget-1"
        assert alert.severity == "critical"
        assert alert.acknowledged is False

    def test_acknowledge(self):
        """Alert can be acknowledged."""
        alert = BudgetAlert.create(
            budget_id="budget-1",
            message="Warning",
        )
        alert.acknowledge()
        assert alert.acknowledged is True


class TestForecastResult:
    """Test forecast result model."""

    def test_create(self):
        """Forecast result can be created."""
        result = ForecastResult.create(
            method=ForecastMethod.MOVING_AVERAGE,
            forecast_periods=[100.0, 110.0, 120.0],
            confidence_interval_lower=[90.0, 100.0, 110.0],
            confidence_interval_upper=[110.0, 120.0, 130.0],
        )
        assert result.method == ForecastMethod.MOVING_AVERAGE
        assert len(result.forecast_periods) == 3
        assert result.total_forecast == 330.0

    def test_create_with_filters(self):
        """Forecast result supports category and department filters."""
        result = ForecastResult.create(
            method=ForecastMethod.LINEAR_REGRESSION,
            forecast_periods=[100.0],
            confidence_interval_lower=[90.0],
            confidence_interval_upper=[110.0],
            category=CostCategory.INFRASTRUCTURE,
            department_id="dept-1",
        )
        assert result.category == CostCategory.INFRASTRUCTURE
        assert result.department_id == "dept-1"


class TestOptimizationSuggestion:
    """Test optimization suggestion model."""

    def test_create(self):
        """Optimization suggestion can be created."""
        suggestion = OptimizationSuggestion.create(
            type=OptimizationType.REDUCE,
            title="Reduce cloud costs",
            description="Switch to reserved instances",
            potential_savings=5000.0,
        )
        assert suggestion.type == OptimizationType.REDUCE
        assert suggestion.potential_savings == 5000.0
        assert suggestion.implemented is False

    def test_mark_implemented(self):
        """Suggestion can be marked as implemented."""
        suggestion = OptimizationSuggestion.create(
            type=OptimizationType.ELIMINATE,
            title="Remove unused services",
            description="Decommission old servers",
            potential_savings=2000.0,
        )
        suggestion.mark_implemented()
        assert suggestion.implemented is True


# ============================================================================
# Cost Tracking Tests
# ============================================================================

class TestCostTracker:
    """Test cost tracking engine."""

    def setup_method(self):
        self.tracker = CostTracker()

    def test_add_entry(self):
        """Entry can be added to tracker."""
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Server",
        )
        self.tracker.add_entry(entry)
        assert self.tracker.get_entry_count() == 1

    def test_create_entry(self):
        """Entry can be created directly in tracker."""
        entry = self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=500.0,
            currency="USD",
            description="License",
        )
        assert entry.id is not None
        assert self.tracker.get_entry(entry.id) == entry

    def test_get_entry(self):
        """Entry can be retrieved by ID."""
        entry = self.tracker.create_entry(
            category=CostCategory.OPERATIONS,
            amount=200.0,
            currency="USD",
            description="Ops",
        )
        retrieved = self.tracker.get_entry(entry.id)
        assert retrieved == entry

    def test_get_all_entries(self):
        """All entries can be retrieved."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
        )
        assert len(self.tracker.get_all_entries()) == 2

    def test_get_entries_by_category(self):
        """Entries can be filtered by category."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
        )
        infra = self.tracker.get_entries_by_category(CostCategory.INFRASTRUCTURE)
        assert len(infra) == 1
        assert infra[0].amount == 100.0

    def test_get_entries_by_department(self):
        """Entries can be filtered by department."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
            department_id="dept-1",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
            department_id="dept-2",
        )
        dept1 = self.tracker.get_entries_by_department("dept-1")
        assert len(dept1) == 1

    def test_get_entries_by_project(self):
        """Entries can be filtered by project."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
            project_id="proj-1",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
            project_id="proj-2",
        )
        proj1 = self.tracker.get_entries_by_project("proj-1")
        assert len(proj1) == 1

    def test_get_entries_by_status(self):
        """Entries can be filtered by status."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
        )
        pending = self.tracker.get_entries_by_status(CostStatus.PENDING)
        assert len(pending) == 2
        self.tracker.approve_entry(entry.id)
        approved = self.tracker.get_entries_by_status(CostStatus.APPROVED)
        assert len(approved) == 1

    def test_get_entries_by_date_range(self):
        """Entries can be filtered by date range."""
        old_entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Old",
            incurred_date=datetime(2025, 1, 1),
        )
        new_entry = CostEntry.create(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="New",
            incurred_date=datetime(2026, 6, 1),
        )
        self.tracker.add_entry(old_entry)
        self.tracker.add_entry(new_entry)
        results = self.tracker.get_entries_by_date_range(
            datetime(2026, 1, 1),
            datetime(2026, 12, 31),
        )
        assert len(results) == 1
        assert results[0].description == "New"

    def test_get_entries_by_vendor(self):
        """Entries can be filtered by vendor."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
            vendor_id="aws",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
            vendor_id="microsoft",
        )
        aws = self.tracker.get_entries_by_vendor("aws")
        assert len(aws) == 1

    def test_get_entries_by_tags(self):
        """Entries can be filtered by tags."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
            tags=["cloud", "aws"],
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="License",
            tags=["subscription"],
        )
        cloud = self.tracker.get_entries_by_tags(["cloud"])
        assert len(cloud) == 1

    def test_approve_entry(self):
        """Entry can be approved."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.approve_entry(entry.id)
        assert entry.status == CostStatus.APPROVED

    def test_reject_entry(self):
        """Entry can be rejected."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.reject_entry(entry.id)
        assert entry.status == CostStatus.REJECTED

    def test_mark_paid(self):
        """Entry can be marked as paid."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.mark_paid(entry.id)
        assert entry.status == CostStatus.PAID

    def test_cancel_entry(self):
        """Entry can be cancelled."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        self.tracker.cancel_entry(entry.id)
        assert entry.status == CostStatus.CANCELLED

    def test_delete_entry(self):
        """Entry can be deleted."""
        entry = self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Server",
        )
        assert self.tracker.delete_entry(entry.id) is True
        assert self.tracker.get_entry(entry.id) is None

    def test_get_total_cost(self):
        """Total cost can be computed."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
        )
        assert self.tracker.get_total_cost() == 300.0

    def test_get_total_cost_with_filters(self):
        """Total cost respects filters."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
            department_id="dept-1",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
            department_id="dept-2",
        )
        assert self.tracker.get_total_cost(department_id="dept-1") == 100.0
        assert self.tracker.get_total_cost(category=CostCategory.SOFTWARE) == 200.0

    def test_get_cost_by_category(self):
        """Cost can be grouped by category."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
        )
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=200.0,
            currency="USD",
            description="B",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=300.0,
            currency="USD",
            description="C",
        )
        by_cat = self.tracker.get_cost_by_category()
        assert by_cat[CostCategory.INFRASTRUCTURE] == 300.0
        assert by_cat[CostCategory.SOFTWARE] == 300.0

    def test_get_cost_by_department(self):
        """Cost can be grouped by department."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
            department_id="dept-1",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
            department_id="dept-1",
        )
        self.tracker.create_entry(
            category=CostCategory.OPERATIONS,
            amount=300.0,
            currency="USD",
            description="C",
            department_id="dept-2",
        )
        by_dept = self.tracker.get_cost_by_department()
        assert by_dept["dept-1"] == 300.0
        assert by_dept["dept-2"] == 300.0

    def test_get_cost_by_project(self):
        """Cost can be grouped by project."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
            project_id="proj-1",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
            project_id="proj-2",
        )
        by_proj = self.tracker.get_cost_by_project()
        assert by_proj["proj-1"] == 100.0
        assert by_proj["proj-2"] == 200.0

    def test_get_cost_by_vendor(self):
        """Cost can be grouped by vendor."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
            vendor_id="aws",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="B",
            vendor_id="aws",
        )
        by_vendor = self.tracker.get_cost_by_vendor()
        assert by_vendor["aws"] == 300.0

    def test_get_monthly_cost(self):
        """Monthly cost can be computed."""
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
            incurred_date=datetime(2026, 6, 15),
        )
        self.tracker.add_entry(entry)
        assert self.tracker.get_monthly_cost(2026, 6) == 100.0
        assert self.tracker.get_monthly_cost(2026, 7) == 0.0

    def test_get_cost_trend(self):
        """Cost trend can be computed."""
        for i in range(3):
            entry = CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Entry {i}",
                incurred_date=datetime.now() - timedelta(days=i * 30),
            )
            self.tracker.add_entry(entry)
        trend = self.tracker.get_cost_trend(periods=3, period_days=30)
        assert len(trend) == 3
        assert trend[0]["total_cost"] > 0

    def test_search_entries(self):
        """Entries can be searched."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="AWS Server costs",
        )
        self.tracker.create_entry(
            category=CostCategory.SOFTWARE,
            amount=200.0,
            currency="USD",
            description="Office supplies",
        )
        results = self.tracker.search_entries("AWS")
        assert len(results) == 1
        assert results[0].description == "AWS Server costs"

    def test_clear(self):
        """All entries can be cleared."""
        self.tracker.create_entry(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="A",
        )
        self.tracker.clear()
        assert self.tracker.get_entry_count() == 0


# ============================================================================
# Cost Allocation Tests
# ============================================================================

class TestCostAllocator:
    """Test cost allocation engine."""

    def setup_method(self):
        self.allocator = CostAllocator()

    def test_add_rule(self):
        """Rule can be added."""
        rule = AllocationRule.create(
            name="Test",
            source_department_id="src",
            target_department_ids=["tgt1", "tgt2"],
            method=AllocationMethod.EQUAL,
        )
        self.allocator.add_rule(rule)
        assert self.allocator.get_rule(rule.id) == rule

    def test_create_rule(self):
        """Rule can be created directly."""
        rule = self.allocator.create_rule(
            name="Test",
            source_department_id="src",
            target_department_ids=["tgt1", "tgt2"],
            method=AllocationMethod.EQUAL,
        )
        assert rule.id is not None
        assert len(self.allocator.get_all_rules()) == 1

    def test_get_all_rules(self):
        """All rules can be retrieved."""
        self.allocator.create_rule(
            name="Rule 1",
            source_department_id="src",
            target_department_ids=["tgt1"],
            method=AllocationMethod.EQUAL,
        )
        self.allocator.create_rule(
            name="Rule 2",
            source_department_id="src",
            target_department_ids=["tgt2"],
            method=AllocationMethod.PERCENTAGE,
        )
        assert len(self.allocator.get_all_rules()) == 2

    def test_get_active_rules(self):
        """Active rules can be filtered."""
        rule = self.allocator.create_rule(
            name="Rule 1",
            source_department_id="src",
            target_department_ids=["tgt1"],
            method=AllocationMethod.EQUAL,
        )
        self.allocator.toggle_rule(rule.id)
        assert len(self.allocator.get_active_rules()) == 0
        self.allocator.toggle_rule(rule.id)
        assert len(self.allocator.get_active_rules()) == 1

    def test_remove_rule(self):
        """Rule can be removed."""
        rule = self.allocator.create_rule(
            name="Rule 1",
            source_department_id="src",
            target_department_ids=["tgt1"],
            method=AllocationMethod.EQUAL,
        )
        assert self.allocator.remove_rule(rule.id) is True
        assert self.allocator.get_rule(rule.id) is None

    def test_toggle_rule(self):
        """Rule can be toggled."""
        rule = self.allocator.create_rule(
            name="Rule 1",
            source_department_id="src",
            target_department_ids=["tgt1"],
            method=AllocationMethod.EQUAL,
        )
        assert rule.active is True
        self.allocator.toggle_rule(rule.id)
        assert rule.active is False

    def test_allocate_equal(self):
        """Equal allocation distributes evenly."""
        rule = self.allocator.create_rule(
            name="Equal Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b", "dept-c"],
            method=AllocationMethod.EQUAL,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=300.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(rule.id, entry)
        assert result.allocations["dept-a"] == 100.0
        assert result.allocations["dept-b"] == 100.0
        assert result.allocations["dept-c"] == 100.0
        assert result.total_allocated == 300.0

    def test_allocate_percentage(self):
        """Percentage allocation distributes by percentage."""
        rule = self.allocator.create_rule(
            name="Pct Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.PERCENTAGE,
            percentages={"dept-a": 70.0, "dept-b": 30.0},
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(rule.id, entry)
        assert result.allocations["dept-a"] == 700.0
        assert result.allocations["dept-b"] == 300.0

    def test_allocate_usage_based(self):
        """Usage-based allocation distributes by usage."""
        rule = self.allocator.create_rule(
            name="Usage Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.USAGE_BASED,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(
            rule.id, entry, usage_data={"dept-a": 75.0, "dept-b": 25.0}
        )
        assert result.allocations["dept-a"] == 750.0
        assert result.allocations["dept-b"] == 250.0

    def test_allocate_headcount(self):
        """Headcount allocation distributes by headcount."""
        rule = self.allocator.create_rule(
            name="Headcount Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.HEADCOUNT,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(
            rule.id, entry, headcount_data={"dept-a": 10, "dept-b": 30}
        )
        assert result.allocations["dept-a"] == 250.0
        assert result.allocations["dept-b"] == 750.0

    def test_allocate_revenue_based(self):
        """Revenue-based allocation distributes by revenue."""
        rule = self.allocator.create_rule(
            name="Revenue Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.REVENUE_BASED,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(
            rule.id, entry, revenue_data={"dept-a": 200000.0, "dept-b": 300000.0}
        )
        assert result.allocations["dept-a"] == 400.0
        assert result.allocations["dept-b"] == 600.0

    def test_allocate_custom(self):
        """Custom allocation uses custom percentages."""
        rule = self.allocator.create_rule(
            name="Custom Split",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.CUSTOM,
            percentages={"dept-a": 50.0, "dept-b": 50.0},
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Shared cost",
        )
        result = self.allocator.allocate(rule.id, entry)
        assert result.allocations["dept-a"] == 500.0
        assert result.allocations["dept-b"] == 500.0

    def test_allocate_with_category_filter(self):
        """Category filter restricts which costs can be allocated."""
        rule = self.allocator.create_rule(
            name="Infra Only",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
            category_filter=[CostCategory.INFRASTRUCTURE],
        )
        entry = CostEntry.create(
            category=CostCategory.SOFTWARE,
            amount=1000.0,
            currency="USD",
            description="Software cost",
        )
        with pytest.raises(ValueError, match="not in rule's filter"):
            self.allocator.allocate(rule.id, entry)

    def test_allocate_inactive_rule_raises(self):
        """Allocating with inactive rule raises error."""
        rule = self.allocator.create_rule(
            name="Inactive",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
        )
        self.allocator.toggle_rule(rule.id)
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Cost",
        )
        with pytest.raises(ValueError, match="not active"):
            self.allocator.allocate(rule.id, entry)

    def test_get_result(self):
        """Allocation result can be retrieved."""
        rule = self.allocator.create_rule(
            name="Test",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Cost",
        )
        result = self.allocator.allocate(rule.id, entry)
        retrieved = self.allocator.get_result(result.id)
        assert retrieved == result

    def test_get_all_results(self):
        """All results can be retrieved."""
        rule = self.allocator.create_rule(
            name="Test",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
        )
        for i in range(3):
            entry = CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0,
                currency="USD",
                description=f"Cost {i}",
            )
            self.allocator.allocate(rule.id, entry)
        assert len(self.allocator.get_all_results()) == 3

    def test_get_results_by_rule(self):
        """Results can be filtered by rule."""
        rule1 = self.allocator.create_rule(
            name="Rule 1",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
        )
        rule2 = self.allocator.create_rule(
            name="Rule 2",
            source_department_id="src",
            target_department_ids=["dept-b"],
            method=AllocationMethod.EQUAL,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Cost",
        )
        self.allocator.allocate(rule1.id, entry)
        self.allocator.allocate(rule2.id, entry)
        results = self.allocator.get_results_by_rule(rule1.id)
        assert len(results) == 1

    def test_get_total_allocated(self):
        """Total allocated amount can be computed."""
        rule = self.allocator.create_rule(
            name="Test",
            source_department_id="src",
            target_department_ids=["dept-a", "dept-b"],
            method=AllocationMethod.EQUAL,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=1000.0,
            currency="USD",
            description="Cost",
        )
        self.allocator.allocate(rule.id, entry)
        assert self.allocator.get_total_allocated() == 1000.0
        assert self.allocator.get_total_allocated("dept-a") == 500.0

    def test_clear(self):
        """All rules and results can be cleared."""
        rule = self.allocator.create_rule(
            name="Test",
            source_department_id="src",
            target_department_ids=["dept-a"],
            method=AllocationMethod.EQUAL,
        )
        entry = CostEntry.create(
            category=CostCategory.INFRASTRUCTURE,
            amount=100.0,
            currency="USD",
            description="Cost",
        )
        self.allocator.allocate(rule.id, entry)
        self.allocator.clear()
        assert len(self.allocator.get_all_rules()) == 0
        assert len(self.allocator.get_all_results()) == 0


# ============================================================================
# Cost Optimization Tests
# ============================================================================

class TestCostOptimizer:
    """Test cost optimization engine."""

    def setup_method(self):
        self.optimizer = CostOptimizer()

    def test_add_suggestion(self):
        """Suggestion can be added."""
        suggestion = OptimizationSuggestion.create(
            type=OptimizationType.REDUCE,
            title="Reduce costs",
            description="Test",
            potential_savings=1000.0,
        )
        self.optimizer.add_suggestion(suggestion)
        assert self.optimizer.get_suggestion(suggestion.id) == suggestion

    def test_create_suggestion(self):
        """Suggestion can be created directly."""
        suggestion = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="Reduce costs",
            description="Test",
            potential_savings=1000.0,
        )
        assert suggestion.id is not None
        assert len(self.optimizer.get_all_suggestions()) == 1

    def test_get_all_suggestions(self):
        """All suggestions can be retrieved."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
        )
        assert len(self.optimizer.get_all_suggestions()) == 2

    def test_get_suggestions_by_type(self):
        """Suggestions can be filtered by type."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
        )
        reduce_suggestions = self.optimizer.get_suggestions_by_type(OptimizationType.REDUCE)
        assert len(reduce_suggestions) == 1

    def test_get_suggestions_by_category(self):
        """Suggestions can be filtered by category."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
            category=CostCategory.INFRASTRUCTURE,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
            category=CostCategory.SOFTWARE,
        )
        infra = self.optimizer.get_suggestions_by_category(CostCategory.INFRASTRUCTURE)
        assert len(infra) == 1

    def test_get_suggestions_by_department(self):
        """Suggestions can be filtered by department."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
            department_id="dept-1",
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
            department_id="dept-2",
        )
        dept1 = self.optimizer.get_suggestions_by_department("dept-1")
        assert len(dept1) == 1

    def test_get_pending_suggestions(self):
        """Pending suggestions can be filtered."""
        s1 = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
        )
        self.optimizer.mark_implemented(s1.id)
        pending = self.optimizer.get_pending_suggestions()
        assert len(pending) == 1

    def test_get_implemented_suggestions(self):
        """Implemented suggestions can be filtered."""
        s1 = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
        )
        self.optimizer.mark_implemented(s1.id)
        implemented = self.optimizer.get_implemented_suggestions()
        assert len(implemented) == 1

    def test_get_high_priority_suggestions(self):
        """High priority suggestions can be filtered."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
            priority=1,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=200.0,
            priority=5,
        )
        high = self.optimizer.get_high_priority_suggestions(threshold=3)
        assert len(high) == 1

    def test_mark_implemented(self):
        """Suggestion can be marked as implemented."""
        suggestion = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.mark_implemented(suggestion.id)
        assert suggestion.implemented is True

    def test_remove_suggestion(self):
        """Suggestion can be removed."""
        suggestion = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        assert self.optimizer.remove_suggestion(suggestion.id) is True
        assert self.optimizer.get_suggestion(suggestion.id) is None

    def test_get_total_potential_savings(self):
        """Total potential savings can be computed."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=1000.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=2000.0,
        )
        assert self.optimizer.get_total_potential_savings() == 3000.0

    def test_get_total_potential_savings_with_filters(self):
        """Total potential savings respects filters."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=1000.0,
            category=CostCategory.INFRASTRUCTURE,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=2000.0,
            category=CostCategory.SOFTWARE,
        )
        assert self.optimizer.get_total_potential_savings(
            category=CostCategory.INFRASTRUCTURE
        ) == 1000.0

    def test_get_total_realized_savings(self):
        """Total realized savings can be computed."""
        s1 = self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=1000.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="B",
            description="Test",
            potential_savings=2000.0,
        )
        self.optimizer.mark_implemented(s1.id)
        assert self.optimizer.get_total_realized_savings() == 1000.0

    def test_analyze_costs(self):
        """Cost analysis generates suggestions."""
        entries = []
        for i in range(5):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=3000.0,
                currency="USD",
                description=f"Server {i}",
            ))
        suggestions = self.optimizer.analyze_costs(entries)
        assert len(suggestions) > 0

    def test_analyze_costs_with_department_data(self):
        """Cost analysis with department data generates more suggestions."""
        entries = [
            CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=15000.0,
                currency="USD",
                description="Server",
                department_id="dept-1",
            ),
        ]
        dept_costs = {"dept-1": 15000.0}
        suggestions = self.optimizer.analyze_costs(entries, department_costs=dept_costs)
        assert len(suggestions) > 0

    def test_get_savings_by_type(self):
        """Savings can be grouped by type."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=1000.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="B",
            description="Test",
            potential_savings=500.0,
        )
        self.optimizer.create_suggestion(
            type=OptimizationType.ELIMINATE,
            title="C",
            description="Test",
            potential_savings=2000.0,
        )
        by_type = self.optimizer.get_savings_by_type()
        assert by_type[OptimizationType.REDUCE] == 1500.0
        assert by_type[OptimizationType.ELIMINATE] == 2000.0

    def test_clear(self):
        """All suggestions can be cleared."""
        self.optimizer.create_suggestion(
            type=OptimizationType.REDUCE,
            title="A",
            description="Test",
            potential_savings=100.0,
        )
        self.optimizer.clear()
        assert len(self.optimizer.get_all_suggestions()) == 0


# ============================================================================
# Budget Management Tests
# ============================================================================

class TestBudgetManager:
    """Test budget management engine."""

    def setup_method(self):
        self.manager = BudgetManager()

    def test_add_budget(self):
        """Budget can be added."""
        budget = Budget.create(
            name="Test",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.add_budget(budget)
        assert self.manager.get_budget(budget.id) == budget

    def test_create_budget(self):
        """Budget can be created directly."""
        budget = self.manager.create_budget(
            name="Test",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        assert budget.id is not None
        assert len(self.manager.get_all_budgets()) == 1

    def test_get_all_budgets(self):
        """All budgets can be retrieved."""
        self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.QUARTERLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 3, 31),
        )
        assert len(self.manager.get_all_budgets()) == 2

    def test_get_budgets_by_department(self):
        """Budgets can be filtered by department."""
        self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        dept1 = self.manager.get_budgets_by_department("dept-1")
        assert len(dept1) == 1

    def test_get_budgets_by_category(self):
        """Budgets can be filtered by category."""
        self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            category=CostCategory.INFRASTRUCTURE,
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            category=CostCategory.SOFTWARE,
        )
        infra = self.manager.get_budgets_by_category(CostCategory.INFRASTRUCTURE)
        assert len(infra) == 1

    def test_get_budgets_by_status(self):
        """Budgets can be filtered by status."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        active = self.manager.get_budgets_by_status(BudgetStatus.ACTIVE)
        assert len(active) == 1

    def test_get_active_budgets(self):
        """Active budgets can be filtered."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        active = self.manager.get_active_budgets()
        assert len(active) == 1

    def test_get_exceeded_budgets(self):
        """Exceeded budgets can be filtered."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        self.manager.record_spend(b1.id, 1500.0)
        exceeded = self.manager.get_exceeded_budgets()
        assert len(exceeded) == 1

    def test_get_near_limit_budgets(self):
        """Near-limit budgets can be filtered."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            alert_threshold=0.8,
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            alert_threshold=0.8,
        )
        self.manager.activate_budget(b1.id)
        self.manager.activate_budget(b1.id)
        self.manager.record_spend(b1.id, 850.0)
        near_limit = self.manager.get_near_limit_budgets()
        assert len(near_limit) == 1

    def test_remove_budget(self):
        """Budget can be removed."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        assert self.manager.remove_budget(budget.id) is True
        assert self.manager.get_budget(budget.id) is None

    def test_activate_budget(self):
        """Budget can be activated."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        assert budget.status == BudgetStatus.ACTIVE

    def test_freeze_budget(self):
        """Budget can be frozen."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.freeze_budget(budget.id)
        assert budget.status == BudgetStatus.FROZEN

    def test_close_budget(self):
        """Budget can be closed."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.close_budget(budget.id)
        assert budget.status == BudgetStatus.CLOSED

    def test_record_spend(self):
        """Spending can be recorded against a budget."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 3000.0)
        assert budget.spent == 3000.0
        assert budget.remaining == 7000.0

    def test_record_spend_frozen_raises(self):
        """Recording spend on frozen budget raises error."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.freeze_budget(budget.id)
        with pytest.raises(ValueError, match="frozen"):
            self.manager.record_spend(budget.id, 100.0)

    def test_record_spend_closed_raises(self):
        """Recording spend on closed budget raises error."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.close_budget(budget.id)
        with pytest.raises(ValueError, match="closed"):
            self.manager.record_spend(budget.id, 100.0)

    def test_budget_alerts_on_exceed(self):
        """Alert is generated when budget is exceeded."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        alerts = self.manager.get_alerts_by_budget(budget.id)
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    def test_budget_alerts_on_near_limit(self):
        """Alert is generated when budget is near limit."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
            alert_threshold=0.8,
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 850.0)
        alerts = self.manager.get_alerts_by_budget(budget.id)
        assert len(alerts) == 1
        assert alerts[0].severity == "warning"

    def test_get_alert(self):
        """Alert can be retrieved by ID."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        alerts = self.manager.get_alerts_by_budget(budget.id)
        alert = self.manager.get_alert(alerts[0].id)
        assert alert is not None

    def test_get_all_alerts(self):
        """All alerts can be retrieved."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        b2 = self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        self.manager.activate_budget(b2.id)
        self.manager.record_spend(b1.id, 1500.0)
        self.manager.record_spend(b2.id, 1500.0)
        assert len(self.manager.get_all_alerts()) == 2

    def test_get_unacknowledged_alerts(self):
        """Unacknowledged alerts can be filtered."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        assert len(self.manager.get_unacknowledged_alerts()) == 1
        alerts = self.manager.get_alerts_by_budget(budget.id)
        self.manager.acknowledge_alert(alerts[0].id)
        assert len(self.manager.get_unacknowledged_alerts()) == 0

    def test_get_critical_alerts(self):
        """Critical alerts can be filtered."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        critical = self.manager.get_critical_alerts()
        assert len(critical) == 1

    def test_acknowledge_alert(self):
        """Alert can be acknowledged."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        alerts = self.manager.get_alerts_by_budget(budget.id)
        self.manager.acknowledge_alert(alerts[0].id)
        assert alerts[0].acknowledged is True

    def test_acknowledge_all_alerts(self):
        """All alerts can be acknowledged at once."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        b2 = self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        self.manager.activate_budget(b2.id)
        self.manager.record_spend(b1.id, 1500.0)
        self.manager.record_spend(b2.id, 1500.0)
        count = self.manager.acknowledge_all_alerts()
        assert count == 2

    def test_get_budget_summary(self):
        """Budget summary can be retrieved."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 3000.0)
        summary = self.manager.get_budget_summary(budget.id)
        assert summary["amount"] == 10000.0
        assert summary["spent"] == 3000.0
        assert summary["remaining"] == 7000.0
        assert summary["utilization_rate"] == 0.3

    def test_get_total_budget(self):
        """Total budget across all budgets can be computed."""
        self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=20000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        assert self.manager.get_total_budget() == 30000.0

    def test_get_total_spent(self):
        """Total spent across all budgets can be computed."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        b2 = self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=20000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        self.manager.activate_budget(b2.id)
        self.manager.record_spend(b1.id, 3000.0)
        self.manager.record_spend(b2.id, 5000.0)
        assert self.manager.get_total_spent() == 8000.0

    def test_get_department_spending(self):
        """Department spending can be computed."""
        b1 = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=10000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        b2 = self.manager.create_budget(
            name="B",
            department_id="dept-2",
            amount=20000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(b1.id)
        self.manager.activate_budget(b2.id)
        self.manager.record_spend(b1.id, 3000.0)
        self.manager.record_spend(b2.id, 5000.0)
        spending = self.manager.get_department_spending()
        assert spending["dept-1"] == 3000.0
        assert spending["dept-2"] == 5000.0

    def test_get_period_budgets(self):
        """Budgets can be filtered by period."""
        self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.create_budget(
            name="B",
            department_id="dept-1",
            amount=2000.0,
            currency="USD",
            period=BudgetPeriod.QUARTERLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 3, 31),
        )
        monthly = self.manager.get_period_budgets(BudgetPeriod.MONTHLY)
        assert len(monthly) == 1

    def test_clear(self):
        """All budgets and alerts can be cleared."""
        budget = self.manager.create_budget(
            name="A",
            department_id="dept-1",
            amount=1000.0,
            currency="USD",
            period=BudgetPeriod.MONTHLY,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )
        self.manager.activate_budget(budget.id)
        self.manager.record_spend(budget.id, 1500.0)
        self.manager.clear()
        assert len(self.manager.get_all_budgets()) == 0
        assert len(self.manager.get_all_alerts()) == 0


# ============================================================================
# Cost Forecasting Tests
# ============================================================================

class TestCostForecaster:
    """Test cost forecasting engine."""

    def setup_method(self):
        self.forecaster = CostForecaster()

    def test_add_result(self):
        """Forecast result can be added."""
        result = ForecastResult.create(
            method=ForecastMethod.MOVING_AVERAGE,
            forecast_periods=[100.0, 110.0],
            confidence_interval_lower=[90.0, 100.0],
            confidence_interval_upper=[110.0, 120.0],
        )
        self.forecaster.add_result(result)
        assert self.forecaster.get_result(result.id) == result

    def test_get_all_results(self):
        """All forecast results can be retrieved."""
        for i in range(3):
            result = ForecastResult.create(
                method=ForecastMethod.MOVING_AVERAGE,
                forecast_periods=[100.0 * (i + 1)],
                confidence_interval_lower=[90.0],
                confidence_interval_upper=[110.0],
            )
            self.forecaster.add_result(result)
        assert len(self.forecaster.get_all_results()) == 3

    def test_forecast_moving_average(self):
        """Moving average forecast can be generated."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Cost {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.MOVING_AVERAGE
        )
        assert result.method == ForecastMethod.MOVING_AVERAGE
        assert len(result.forecast_periods) == 6
        assert all(f > 0 for f in result.forecast_periods)

    def test_forecast_exponential_smoothing(self):
        """Exponential smoothing forecast can be generated."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Cost {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.EXPONENTIAL_SMOOTHING
        )
        assert result.method == ForecastMethod.EXPONENTIAL_SMOOTHING
        assert len(result.forecast_periods) == 6

    def test_forecast_linear_regression(self):
        """Linear regression forecast can be generated."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Cost {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.LINEAR_REGRESSION
        )
        assert result.method == ForecastMethod.LINEAR_REGRESSION
        assert len(result.forecast_periods) == 6

    def test_forecast_seasonal(self):
        """Seasonal forecast can be generated."""
        entries = []
        for i in range(12):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Cost {i}",
                incurred_date=datetime.now() - timedelta(days=(11 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.SEASONAL
        )
        assert result.method == ForecastMethod.SEASONAL
        assert len(result.forecast_periods) == 6

    def test_forecast_with_category_filter(self):
        """Forecast can be filtered by category."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0,
                currency="USD",
                description=f"Infra {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
            entries.append(CostEntry.create(
                category=CostCategory.SOFTWARE,
                amount=500.0,
                currency="USD",
                description=f"Software {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.MOVING_AVERAGE,
            category=CostCategory.INFRASTRUCTURE,
        )
        assert result.category == CostCategory.INFRASTRUCTURE

    def test_forecast_with_department_filter(self):
        """Forecast can be filtered by department."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0,
                currency="USD",
                description=f"Cost {i}",
                department_id="dept-1",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.MOVING_AVERAGE,
            department_id="dept-1",
        )
        assert result.department_id == "dept-1"

    def test_forecast_empty_data(self):
        """Forecast with no data returns zero forecast."""
        result = self.forecaster.forecast(
            [], periods=6, method=ForecastMethod.MOVING_AVERAGE
        )
        assert len(result.forecast_periods) == 6
        assert all(f == 0.0 for f in result.forecast_periods)

    def test_forecast_confidence_intervals(self):
        """Forecast includes confidence intervals."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0 * (i + 1),
                currency="USD",
                description=f"Cost {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        result = self.forecaster.forecast(
            entries, periods=6, method=ForecastMethod.MOVING_AVERAGE
        )
        assert len(result.confidence_interval_lower) == 6
        assert len(result.confidence_interval_upper) == 6
        for i in range(6):
            assert result.confidence_interval_lower[i] <= result.forecast_periods[i]
            assert result.forecast_periods[i] <= result.confidence_interval_upper[i]

    def test_forecast_by_category(self):
        """Forecast can be generated per category."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0,
                currency="USD",
                description=f"Infra {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
            entries.append(CostEntry.create(
                category=CostCategory.SOFTWARE,
                amount=200.0,
                currency="USD",
                description=f"Software {i}",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        results = self.forecaster.forecast_by_category(entries, periods=6)
        assert CostCategory.INFRASTRUCTURE in results
        assert CostCategory.SOFTWARE in results

    def test_forecast_by_department(self):
        """Forecast can be generated per department."""
        entries = []
        for i in range(6):
            entries.append(CostEntry.create(
                category=CostCategory.INFRASTRUCTURE,
                amount=100.0,
                currency="USD",
                description=f"Cost {i}",
                department_id="dept-1",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
            entries.append(CostEntry.create(
                category=CostCategory.SOFTWARE,
                amount=200.0,
                currency="USD",
                description=f"Cost {i}",
                department_id="dept-2",
                incurred_date=datetime.now() - timedelta(days=(5 - i) * 30),
            ))
        results = self.forecaster.forecast_by_department(entries, periods=6)
        assert "dept-1" in results
        assert "dept-2" in results

    def test_get_total_forecast(self):
        """Total forecast across all results can be computed."""
        for i in range(3):
            result = ForecastResult.create(
                method=ForecastMethod.MOVING_AVERAGE,
                forecast_periods=[100.0 * (i + 1)],
                confidence_interval_lower=[90.0],
                confidence_interval_upper=[110.0],
            )
            self.forecaster.add_result(result)
        assert self.forecaster.get_total_forecast() == 600.0

    def test_clear(self):
        """All forecast results can be cleared."""
        result = ForecastResult.create(
            method=ForecastMethod.MOVING_AVERAGE,
            forecast_periods=[100.0],
            confidence_interval_lower=[90.0],
            confidence_interval_upper=[110.0],
        )
        self.forecaster.add_result(result)
        self.forecaster.clear()
        assert len(self.forecaster.get_all_results()) == 0
