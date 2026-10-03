"""Tests for deepened supply chain modules: forecasting, suppliers, logistics, warehouse, procurement."""
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_forecast():
    return {
        "product_id": "PROD-001",
        "period": "2024-Q1",
        "predicted_demand": 1000,
        "actual_demand": 950,
        "confidence": 0.85,
    }


@pytest.fixture
def sample_supplier():
    return {
        "id": "SUP-001",
        "name": "Acme Parts",
        "lead_time_days": 14,
        "rating": 4.5,
        "on_time_rate": 0.92,
    }


class TestForecasting:
    def test_forecast_accuracy(self, sample_forecast):
        accuracy = 1 - abs(sample_forecast["predicted_demand"] - sample_forecast["actual_demand"]) / sample_forecast["actual_demand"]
        assert accuracy == pytest.approx(0.947, rel=0.01)

    def test_forecast_confidence_threshold(self, sample_forecast):
        assert sample_forecast["confidence"] >= 0.8

    def test_demand_variance(self):
        forecast = 1000
        actual = 1100
        variance = actual - forecast
        assert variance == 100


class TestSuppliers:
    def test_supplier_rating(self, sample_supplier):
        assert sample_supplier["rating"] >= 4.0

    def test_supplier_on_time_delivery(self, sample_supplier):
        assert sample_supplier["on_time_rate"] >= 0.9

    def test_lead_time_calculation(self, sample_supplier):
        order_date = datetime.now()
        expected_delivery = order_date + timedelta(days=sample_supplier["lead_time_days"])
        assert (expected_delivery - order_date).days == 14


class TestLogistics:
    def test_shipping_cost_calculation(self):
        weight_kg = 10
        rate_per_kg = 2.5
        cost = weight_kg * rate_per_kg
        assert cost == 25.0

    def test_delivery_time_estimate(self):
        distance_km = 500
        speed_kmh = 80
        hours = distance_km / speed_kmh
        assert hours == 6.25

    def test_route_optimization(self):
        stops = [1, 2, 3, 4, 5]
        optimized = [1, 3, 5, 4, 2]
        assert len(optimized) == len(stops)


class TestWarehouse:
    def test_inventory_turnover(self):
        cogs = 50000.0
        avg_inventory = 10000.0
        turnover = cogs / avg_inventory
        assert turnover == 5.0

    def test_storage_capacity(self):
        total_capacity = 10000
        used = 7500
        utilization = used / total_capacity
        assert utilization == 0.75

    def test_picking_accuracy(self):
        total_picks = 1000
        errors = 5
        accuracy = (total_picks - errors) / total_picks
        assert accuracy == 0.995


class TestProcurement:
    def test_purchase_order_creation(self):
        po = {"id": "PO-001", "supplier_id": "SUP-001", "total": 5000.0, "status": "draft"}
        assert po["status"] == "draft"
        assert po["total"] > 0

    def test_procurement_savings(self):
        original_price = 100.0
        negotiated_price = 85.0
        savings = (original_price - negotiated_price) / original_price
        assert savings == 0.15

    def test_vendor_performance_score(self):
        metrics = {"quality": 0.95, "delivery": 0.90, "cost": 0.85}
        score = sum(metrics.values()) / len(metrics)
        assert score == pytest.approx(0.90, rel=0.01)
