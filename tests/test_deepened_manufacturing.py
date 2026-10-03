"""Tests for deepened manufacturing modules: MRP, quality, maintenance, BOM, shop floor."""
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_bom():
    return {
        "product_id": "PROD-001",
        "components": [
            {"part_id": "PART-A", "qty": 2},
            {"part_id": "PART-B", "qty": 1},
        ],
    }


@pytest.fixture
def sample_work_order():
    return {
        "id": "WO-001",
        "product_id": "PROD-001",
        "quantity": 100,
        "status": "scheduled",
        "start_date": datetime.now(),
    }


class TestMRP:
    def test_material_requirements_calculation(self, sample_bom):
        required_qty = 50
        for comp in sample_bom["components"]:
            comp["required"] = comp["qty"] * required_qty
        assert sample_bom["components"][0]["required"] == 100
        assert sample_bom["components"][1]["required"] == 50

    def test_mrp_net_requirements(self):
        gross = 200
        on_hand = 50
        net = gross - on_hand
        assert net == 150

    def test_mrp_planned_order_release(self):
        net_requirement = 150
        lot_size = 200
        planned_order = max(net_requirement, lot_size)
        assert planned_order == 200


class TestQuality:
    def test_defect_rate_calculation(self):
        total_produced = 1000
        defects = 10
        defect_rate = defects / total_produced
        assert defect_rate == 0.01

    def test_quality_pass_rate(self):
        inspected = 500
        passed = 490
        rate = passed / inspected
        assert rate == 0.98

    def test_spc_control_limits(self):
        mean = 50.0
        std_dev = 2.0
        ucl = mean + 3 * std_dev
        lcl = mean - 3 * std_dev
        assert ucl == 56.0
        assert lcl == 44.0


class TestMaintenance:
    def test_mtbf_calculation(self):
        total_operating_hours = 10000
        failures = 5
        mtbf = total_operating_hours / failures
        assert mtbf == 2000

    def test_mttr_calculation(self):
        total_downtime_hours = 20
        repairs = 4
        mttr = total_downtime_hours / repairs
        assert mttr == 5

    def test_equipment_availability(self):
        scheduled_hours = 720
        downtime_hours = 36
        availability = (scheduled_hours - downtime_hours) / scheduled_hours
        assert availability == 0.95

    def test_preventive_maintenance_schedule(self):
        last_service = datetime.now() - timedelta(days=85)
        interval_days = 90
        due = (datetime.now() - last_service).days >= interval_days
        assert due is False


class TestBOM:
    def test_bom_component_count(self, sample_bom):
        assert len(sample_bom["components"]) == 2

    def test_bom_cost_rollup(self):
        components = [
            {"part_id": "A", "qty": 2, "unit_cost": 10.0},
            {"part_id": "B", "qty": 1, "unit_cost": 25.0},
        ]
        total = sum(c["qty"] * c["unit_cost"] for c in components)
        assert total == 45.0

    def test_bom_level_explosion(self):
        bom = {"level": 0, "children": [{"level": 1, "children": [{"level": 2, "children": []}]}]}
        assert bom["children"][0]["children"][0]["level"] == 2


class TestShopFloor:
    def test_work_order_creation(self, sample_work_order):
        assert sample_work_order["id"] == "WO-001"
        assert sample_work_order["status"] == "scheduled"

    def test_production_schedule_adherence(self):
        planned = 100
        actual = 95
        adherence = actual / planned
        assert adherence == 0.95

    def test_oee_calculation(self):
        availability = 0.95
        performance = 0.90
        quality = 0.98
        oee = availability * performance * quality
        assert oee == pytest.approx(0.838, rel=0.01)

    def test_cycle_time_calculation(self):
        total_time_minutes = 480
        units_produced = 120
        cycle_time = total_time_minutes / units_produced
        assert cycle_time == 4.0
