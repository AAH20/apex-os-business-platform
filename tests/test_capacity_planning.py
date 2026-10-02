"""Tests for the capacity planning system."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.capacity_planning.forecasting import forecast_demand, ForecastResult
from apex_os_bp.capacity_planning.modeling import (
    ResourceCapacity,
    CapacityReport,
    utilization_rate,
    headroom,
    analyze_capacity,
)
from apex_os_bp.capacity_planning.scaling import (
    ScalingRecommendation,
    recommend_scaling,
    calculate_required_capacity,
)
from apex_os_bp.capacity_planning.cost_optimization import (
    CostItem,
    CostOptimizationResult,
    calculate_total_cost,
    optimize_costs,
    rightsizing_savings,
)
from apex_os_bp.capacity_planning.alerts import (
    AlertSeverity,
    CapacityAlert,
    check_capacity_alerts,
    format_alert,
)


# ============================================================
# Forecasting Tests
# ============================================================


class TestForecasting:
    """Tests for resource demand forecasting."""

    def test_linear_forecast_basic(self):
        """Test basic linear forecasting with clear trend."""
        data = [10, 20, 30, 40, 50]
        result = forecast_demand(data, periods=3, method="linear")
        assert isinstance(result, ForecastResult)
        assert len(result.values) == 3
        assert result.method == "linear"
        assert result.values[0] > 50
        assert result.values[1] > result.values[0]
        assert result.values[2] > result.values[1]

    def test_linear_forecast_confidence_intervals(self):
        """Test that confidence intervals are generated."""
        data = [10, 20, 30, 40, 50]
        result = forecast_demand(data, periods=3, method="linear")
        assert len(result.confidence_lower) == 3
        assert len(result.confidence_upper) == 3
        for i in range(3):
            assert result.confidence_lower[i] <= result.values[i]
            assert result.confidence_upper[i] >= result.values[i]

    def test_moving_average_forecast(self):
        """Test moving average forecasting."""
        data = [10, 20, 30, 40, 50]
        result = forecast_demand(data, periods=3, method="moving_average")
        assert isinstance(result, ForecastResult)
        assert len(result.values) == 3
        assert result.method == "moving_average"

    def test_exponential_smoothing_forecast(self):
        """Test exponential smoothing forecasting."""
        data = [10, 20, 30, 40, 50]
        result = forecast_demand(data, periods=3, method="exponential_smoothing")
        assert isinstance(result, ForecastResult)
        assert len(result.values) == 3
        assert result.method == "exponential_smoothing"

    def test_forecast_empty_data_raises(self):
        """Test that empty historical data raises ValueError."""
        with pytest.raises(ValueError, match="Historical data cannot be empty"):
            forecast_demand([], periods=3)

    def test_forecast_zero_periods_raises(self):
        """Test that zero periods raises ValueError."""
        with pytest.raises(ValueError, match="Periods must be positive"):
            forecast_demand([10, 20], periods=0)

    def test_forecast_negative_periods_raises(self):
        """Test that negative periods raises ValueError."""
        with pytest.raises(ValueError, match="Periods must be positive"):
            forecast_demand([10, 20], periods=-1)

    def test_forecast_unknown_method_raises(self):
        """Test that unknown method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown forecasting method"):
            forecast_demand([10, 20], periods=3, method="unknown")

    def test_forecast_single_data_point(self):
        """Test forecasting with a single data point."""
        data = [42]
        result = forecast_demand(data, periods=3, method="linear")
        assert len(result.values) == 3
        for v in result.values:
            assert v == pytest.approx(42.0)

    def test_forecast_flat_data(self):
        """Test forecasting with flat data."""
        data = [50, 50, 50, 50]
        result = forecast_demand(data, periods=3, method="linear")
        for v in result.values:
            assert v == pytest.approx(50.0)

    def test_forecast_downward_trend(self):
        """Test forecasting with downward trend."""
        data = [50, 40, 30, 20, 10]
        result = forecast_demand(data, periods=3, method="linear")
        assert result.values[0] < 10
        assert result.values[1] < result.values[0]


# ============================================================
# Modeling Tests
# ============================================================


class TestModeling:
    """Tests for capacity modeling."""

    def test_utilization_rate_basic(self):
        """Test basic utilization rate calculation."""
        assert utilization_rate(50, 100) == pytest.approx(0.5)

    def test_utilization_rate_full(self):
        """Test 100% utilization."""
        assert utilization_rate(100, 100) == pytest.approx(1.0)

    def test_utilization_rate_zero(self):
        """Test 0% utilization."""
        assert utilization_rate(0, 100) == pytest.approx(0.0)

    def test_utilization_rate_zero_total_raises(self):
        """Test that zero total raises ValueError."""
        with pytest.raises(ValueError, match="Total capacity must be positive"):
            utilization_rate(50, 0)

    def test_utilization_rate_negative_used_raises(self):
        """Test that negative used raises ValueError."""
        with pytest.raises(ValueError, match="Used capacity cannot be negative"):
            utilization_rate(-10, 100)

    def test_headroom_basic(self):
        """Test basic headroom calculation."""
        assert headroom(100, 30) == pytest.approx(70)

    def test_headroom_full(self):
        """Test headroom when fully utilized."""
        assert headroom(100, 100) == pytest.approx(0)

    def test_headroom_overutilized(self):
        """Test headroom when over-utilized (should be 0)."""
        assert headroom(100, 120) == pytest.approx(0)

    def test_headroom_negative_total_raises(self):
        """Test that negative total raises ValueError."""
        with pytest.raises(ValueError):
            headroom(-10, 5)

    def test_resource_capacity_creation(self):
        """Test ResourceCapacity dataclass creation."""
        rc = ResourceCapacity(name="CPU", total=100, used=60, unit="cores")
        assert rc.name == "CPU"
        assert rc.total == 100
        assert rc.used == 60
        assert rc.unit == "cores"

    def test_resource_capacity_invalid_total(self):
        """Test that invalid total raises ValueError."""
        with pytest.raises(ValueError):
            ResourceCapacity(name="CPU", total=0, used=0)

    def test_resource_capacity_negative_used(self):
        """Test that negative used raises ValueError."""
        with pytest.raises(ValueError):
            ResourceCapacity(name="CPU", total=100, used=-5)

    def test_resource_capacity_used_exceeds_total(self):
        """Test that used > total raises ValueError."""
        with pytest.raises(ValueError):
            ResourceCapacity(name="CPU", total=100, used=150)

    def test_analyze_capacity_basic(self):
        """Test basic capacity analysis."""
        resources = [
            ResourceCapacity(name="CPU", total=100, used=80),
            ResourceCapacity(name="Memory", total=256, used=128),
            ResourceCapacity(name="Disk", total=1000, used=300),
        ]
        report = analyze_capacity(resources)
        assert isinstance(report, CapacityReport)
        assert len(report.resources) == 3
        assert report.overall_utilization == pytest.approx(508 / 1356, rel=0.01)
        assert "CPU" in report.bottlenecks
        assert "Memory" not in report.bottlenecks
        assert "Disk" not in report.bottlenecks

    def test_analyze_capacity_empty_raises(self):
        """Test that empty resources raises ValueError."""
        with pytest.raises(ValueError, match="Resources list cannot be empty"):
            analyze_capacity([])

    def test_analyze_capacity_custom_threshold(self):
        """Test capacity analysis with custom bottleneck threshold."""
        resources = [
            ResourceCapacity(name="CPU", total=100, used=70),
        ]
        report = analyze_capacity(resources, bottleneck_threshold=0.6)
        assert "CPU" in report.bottlenecks

    def test_analyze_capacity_headroom(self):
        """Test that headroom is correctly calculated."""
        resources = [
            ResourceCapacity(name="CPU", total=100, used=60),
        ]
        report = analyze_capacity(resources)
        assert report.headroom["CPU"] == pytest.approx(40)


# ============================================================
# Scaling Tests
# ============================================================


class TestScaling:
    """Tests for scaling recommendations."""

    def test_calculate_required_capacity_basic(self):
        """Test basic required capacity calculation."""
        assert calculate_required_capacity(70, 0.7) == pytest.approx(100)

    def test_calculate_required_capacity_default_utilization(self):
        """Test with default target utilization."""
        assert calculate_required_capacity(70) == pytest.approx(100)

    def test_calculate_required_capacity_zero_demand(self):
        """Test with zero demand."""
        assert calculate_required_capacity(0, 0.7) == pytest.approx(0)

    def test_calculate_required_capacity_negative_demand_raises(self):
        """Test that negative demand raises ValueError."""
        with pytest.raises(ValueError, match="Demand cannot be negative"):
            calculate_required_capacity(-10, 0.7)

    def test_calculate_required_capacity_invalid_utilization_raises(self):
        """Test that invalid utilization raises ValueError."""
        with pytest.raises(ValueError, match="Target utilization must be between 0 and 1"):
            calculate_required_capacity(70, 0)
        with pytest.raises(ValueError, match="Target utilization must be between 0 and 1"):
            calculate_required_capacity(70, 1.5)

    def test_recommend_scaling_scale_up(self):
        """Test scale-up recommendation when utilization is high."""
        rec = recommend_scaling(current_capacity=100, forecasted_demand=90)
        assert rec.action == "scale_up"
        assert rec.current_capacity == 100
        assert rec.recommended_capacity > 100
        assert rec.urgency in ("medium", "high")

    def test_recommend_scaling_scale_down(self):
        """Test scale-down recommendation when utilization is low."""
        rec = recommend_scaling(current_capacity=100, forecasted_demand=20)
        assert rec.action == "scale_down"
        assert rec.current_capacity == 100
        assert rec.recommended_capacity < 100

    def test_recommend_scaling_maintain(self):
        """Test maintain recommendation when utilization is in range."""
        rec = recommend_scaling(current_capacity=100, forecasted_demand=50)
        assert rec.action == "maintain"
        assert rec.current_capacity == 100
        assert rec.recommended_capacity == 100

    def test_recommend_scaling_high_urgency(self):
        """Test high urgency when utilization is critical."""
        rec = recommend_scaling(current_capacity=100, forecasted_demand=98)
        assert rec.action == "scale_up"
        assert rec.urgency == "high"

    def test_recommend_scaling_zero_capacity_raises(self):
        """Test that zero current capacity raises ValueError."""
        with pytest.raises(ValueError, match="Current capacity must be positive"):
            recommend_scaling(current_capacity=0, forecasted_demand=50)

    def test_recommend_scaling_negative_demand_raises(self):
        """Test that negative demand raises ValueError."""
        with pytest.raises(ValueError, match="Forecasted demand cannot be negative"):
            recommend_scaling(current_capacity=100, forecasted_demand=-10)

    def test_recommend_scaling_custom_thresholds(self):
        """Test with custom thresholds."""
        rec = recommend_scaling(
            current_capacity=100,
            forecasted_demand=75,
            scale_up_threshold=0.7,
            scale_down_threshold=0.2,
        )
        assert rec.action == "scale_up"


# ============================================================
# Cost Optimization Tests
# ============================================================


class TestCostOptimization:
    """Tests for cost optimization."""

    def test_calculate_total_cost_basic(self):
        """Test basic total cost calculation."""
        items = [
            CostItem(resource="CPU", quantity=10, unit_cost=0.5),
            CostItem(resource="Memory", quantity=20, unit_cost=0.3),
        ]
        assert calculate_total_cost(items) == pytest.approx(10 * 0.5 + 20 * 0.3)

    def test_calculate_total_cost_empty(self):
        """Test total cost with empty list."""
        assert calculate_total_cost([]) == pytest.approx(0)

    def test_cost_item_creation(self):
        """Test CostItem dataclass creation."""
        item = CostItem(resource="CPU", quantity=10, unit_cost=0.5)
        assert item.resource == "CPU"
        assert item.quantity == 10
        assert item.unit_cost == 0.5

    def test_cost_item_negative_quantity_raises(self):
        """Test that negative quantity raises ValueError."""
        with pytest.raises(ValueError):
            CostItem(resource="CPU", quantity=-5, unit_cost=0.5)

    def test_cost_item_negative_unit_cost_raises(self):
        """Test that negative unit cost raises ValueError."""
        with pytest.raises(ValueError):
            CostItem(resource="CPU", quantity=5, unit_cost=-0.5)

    def test_optimize_costs_overprovisioned(self):
        """Test optimization when over-provisioned."""
        items = [
            CostItem(resource="CPU", quantity=100, unit_cost=1.0),
            CostItem(resource="Memory", quantity=200, unit_cost=0.5),
        ]
        result = optimize_costs(items, demand_forecast=50)
        assert isinstance(result, CostOptimizationResult)
        assert result.current_cost == pytest.approx(200.0)
        assert result.optimized_cost < result.current_cost
        assert result.savings > 0
        assert result.savings_percent > 0
        assert len(result.recommendations) > 0

    def test_optimize_costs_well_matched(self):
        """Test optimization when well-matched."""
        items = [
            CostItem(resource="CPU", quantity=100, unit_cost=1.0),
        ]
        result = optimize_costs(items, demand_forecast=85)
        assert result.current_cost == pytest.approx(100.0)
        assert result.optimized_cost == pytest.approx(100.0)
        assert result.savings == pytest.approx(0.0)
        assert len(result.recommendations) > 0

    def test_optimize_costs_empty_raises(self):
        """Test that empty items raises ValueError."""
        with pytest.raises(ValueError, match="Current items cannot be empty"):
            optimize_costs([], demand_forecast=50)

    def test_optimize_costs_negative_demand_raises(self):
        """Test that negative demand raises ValueError."""
        items = [CostItem(resource="CPU", quantity=10, unit_cost=1.0)]
        with pytest.raises(ValueError, match="Demand forecast cannot be negative"):
            optimize_costs(items, demand_forecast=-10)

    def test_rightsizing_savings(self):
        """Test rightsizing savings calculation."""
        current = [
            CostItem(resource="CPU", quantity=100, unit_cost=1.0),
        ]
        recommended = [
            CostItem(resource="CPU", quantity=80, unit_cost=1.0),
        ]
        savings = rightsizing_savings(current, recommended)
        assert savings == pytest.approx(20.0)

    def test_rightsizing_savings_no_savings(self):
        """Test rightsizing when recommended costs more."""
        current = [
            CostItem(resource="CPU", quantity=80, unit_cost=1.0),
        ]
        recommended = [
            CostItem(resource="CPU", quantity=100, unit_cost=1.0),
        ]
        savings = rightsizing_savings(current, recommended)
        assert savings == pytest.approx(0.0)


# ============================================================
# Alerts Tests
# ============================================================


class TestAlerts:
    """Tests for capacity alerts."""

    def test_check_alerts_no_breach(self):
        """Test no alerts when metrics are within thresholds."""
        metrics = {"cpu_utilization": 0.5}
        thresholds = {"cpu_utilization": {"warning": 0.8, "critical": 0.95}}
        alerts = check_capacity_alerts(metrics, thresholds)
        assert len(alerts) == 0

    def test_check_alerts_warning(self):
        """Test warning alert when metric exceeds warning threshold."""
        metrics = {"cpu_utilization": 0.85}
        thresholds = {"cpu_utilization": {"warning": 0.8, "critical": 0.95}}
        alerts = check_capacity_alerts(metrics, thresholds)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.WARNING
        assert alerts[0].resource == "cpu_utilization"
        assert alerts[0].current_value == pytest.approx(0.85)

    def test_check_alerts_critical(self):
        """Test critical alert when metric exceeds critical threshold."""
        metrics = {"cpu_utilization": 0.97}
        thresholds = {"cpu_utilization": {"warning": 0.8, "critical": 0.95}}
        alerts = check_capacity_alerts(metrics, thresholds)
        assert len(alerts) == 1
        assert alerts[0].severity == AlertSeverity.CRITICAL

    def test_check_alerts_multiple_metrics(self):
        """Test alerts for multiple metrics."""
        metrics = {
            "cpu_utilization": 0.85,
            "memory_utilization": 0.5,
            "disk_utilization": 0.97,
        }
        thresholds = {
            "cpu_utilization": {"warning": 0.8, "critical": 0.95},
            "memory_utilization": {"warning": 0.8, "critical": 0.95},
            "disk_utilization": {"warning": 0.8, "critical": 0.95},
        }
        alerts = check_capacity_alerts(metrics, thresholds)
        assert len(alerts) == 2
        severities = {a.severity for a in alerts}
        assert AlertSeverity.WARNING in severities
        assert AlertSeverity.CRITICAL in severities

    def test_check_alerts_unknown_metric_ignored(self):
        """Test that unknown metrics are ignored."""
        metrics = {"unknown_metric": 0.99}
        thresholds = {"cpu_utilization": {"warning": 0.8, "critical": 0.95}}
        alerts = check_capacity_alerts(metrics, thresholds)
        assert len(alerts) == 0

    def test_check_alerts_empty_metrics(self):
        """Test with empty metrics."""
        thresholds = {"cpu_utilization": {"warning": 0.8, "critical": 0.95}}
        alerts = check_capacity_alerts({}, thresholds)
        assert len(alerts) == 0

    def test_alert_to_dict(self):
        """Test alert serialization to dict."""
        alert = CapacityAlert(
            severity=AlertSeverity.WARNING,
            resource="cpu_utilization",
            message="Test alert",
            metric="cpu_utilization",
            threshold=0.8,
            current_value=0.85,
        )
        d = alert.to_dict()
        assert d["severity"] == "warning"
        assert d["resource"] == "cpu_utilization"
        assert d["current_value"] == pytest.approx(0.85)

    def test_format_alert(self):
        """Test alert formatting."""
        alert = CapacityAlert(
            severity=AlertSeverity.CRITICAL,
            resource="cpu_utilization",
            message="CRITICAL: cpu_utilization at 0.97",
            metric="cpu_utilization",
            threshold=0.95,
            current_value=0.97,
        )
        formatted = format_alert(alert)
        assert "CRITICAL" in formatted
        assert "cpu_utilization" in formatted

    def test_alert_severity_enum(self):
        """Test AlertSeverity enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"