"""Tests for manufacturing module."""
import pytest
from datetime import datetime, timedelta

from apex_os_bp.manufacturing.bom import BOM, BOMItem, BOMEngine, BOMError, BOMStatus
from apex_os_bp.manufacturing.production_planning import (
    ProductionOrder,
    ProductionPlanner,
    WorkCenter,
    PlanningError,
    OrderStatus,
    WorkCenterType,
)
from apex_os_bp.manufacturing.quality_control import (
    Inspection,
    Measurement,
    NonConformance,
    QualityControl,
    QualityError,
    InspectionResult,
    DefectSeverity,
    Disposition,
)
from apex_os_bp.manufacturing.shop_floor import (
    Operation,
    WorkOrder,
    ShopFloor,
    ShopFloorError,
    WorkOrderStatus,
    OperationStatus,
)
from apex_os_bp.manufacturing.maintenance import (
    Asset,
    MaintenanceOrder,
    MaintenancePlanner,
    MaintenanceError,
    AssetStatus,
    MaintenanceType,
    MaintenancePriority,
    MaintenanceOrderStatus,
)


# ─── BOM Tests ───────────────────────────────────────────────────────────────


class TestBOMItem:
    """Test BOM item data structure."""

    def test_bom_item_creation(self):
        """BOM item can be created."""
        item = BOMItem(
            component_id="comp-1",
            component_name="Steel Plate",
            quantity=2.0,
            unit="kg",
        )
        assert item.component_id == "comp-1"
        assert item.component_name == "Steel Plate"
        assert item.quantity == 2.0
        assert item.unit == "kg"
        assert item.scrap_factor == 0.0

    def test_bom_item_effective_quantity_no_scrap(self):
        """Effective quantity equals quantity when no scrap."""
        item = BOMItem(
            component_id="comp-1",
            component_name="Bolt",
            quantity=10.0,
            scrap_factor=0.0,
        )
        assert item.effective_quantity() == 10.0

    def test_bom_item_effective_quantity_with_scrap(self):
        """Effective quantity includes scrap factor."""
        item = BOMItem(
            component_id="comp-1",
            component_name="Bolt",
            quantity=10.0,
            scrap_factor=0.1,
        )
        assert item.effective_quantity() == 11.0


class TestBOM:
    """Test BOM data structure."""

    def test_bom_creation(self):
        """BOM can be created."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        assert bom.product_id == "prod-1"
        assert bom.product_name == "Widget"
        assert bom.version == "1.0"
        assert bom.status == BOMStatus.DRAFT
        assert len(bom.items) == 0

    def test_bom_add_item(self):
        """Items can be added to BOM."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        item = BOMItem(component_id="comp-1", component_name="Steel", quantity=1.0)
        bom.add_item(item)
        assert len(bom.items) == 1
        assert bom.items[0].component_id == "comp-1"

    def test_bom_remove_item(self):
        """Items can be removed from BOM."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        bom.add_item(BOMItem(component_id="comp-1", component_name="Steel", quantity=1.0))
        bom.add_item(BOMItem(component_id="comp-2", component_name="Bolt", quantity=4.0))
        result = bom.remove_item("comp-1")
        assert result is True
        assert len(bom.items) == 1
        assert bom.items[0].component_id == "comp-2"

    def test_bom_remove_nonexistent_item(self):
        """Removing non-existent item returns False."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        result = bom.remove_item("nonexistent")
        assert result is False

    def test_bom_total_component_quantity(self):
        """Total component quantity is calculated correctly."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="A", quantity=2.0))
        bom.add_item(BOMItem(component_id="c2", component_name="B", quantity=3.0))
        assert bom.total_component_quantity() == 5.0

    def test_bom_total_effective_quantity(self):
        """Total effective quantity includes scrap."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="A", quantity=2.0, scrap_factor=0.1))
        bom.add_item(BOMItem(component_id="c2", component_name="B", quantity=3.0, scrap_factor=0.0))
        assert bom.total_effective_quantity() == pytest.approx(5.2)

    def test_bom_activate(self):
        """BOM can be activated."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="A", quantity=1.0))
        bom.activate()
        assert bom.status == BOMStatus.ACTIVE

    def test_bom_activate_empty_raises(self):
        """Activating empty BOM raises error."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        with pytest.raises(BOMError):
            bom.activate()

    def test_bom_obsolete(self):
        """BOM can be marked obsolete."""
        bom = BOM(product_id="prod-1", product_name="Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="A", quantity=1.0))
        bom.activate()
        bom.obsolete()
        assert bom.status == BOMStatus.OBSOLETE


class TestBOMEngine:
    """Test BOM engine."""

    def test_create_bom(self):
        """BOM can be created via engine."""
        engine = BOMEngine()
        bom = engine.create_bom("prod-1", "Widget")
        assert bom.product_id == "prod-1"
        assert bom.product_name == "Widget"
        assert bom.id in [b.id for b in engine.list_boms()]

    def test_get_bom(self):
        """BOM can be retrieved by ID."""
        engine = BOMEngine()
        bom = engine.create_bom("prod-1", "Widget")
        retrieved = engine.get_bom(bom.id)
        assert retrieved is not None
        assert retrieved.id == bom.id

    def test_get_bom_not_found(self):
        """Getting non-existent BOM returns None."""
        engine = BOMEngine()
        assert engine.get_bom("nonexistent") is None

    def test_find_by_product(self):
        """BOMs can be found by product ID."""
        engine = BOMEngine()
        engine.create_bom("prod-1", "Widget A")
        engine.create_bom("prod-1", "Widget B")
        engine.create_bom("prod-2", "Gadget")
        results = engine.find_by_product("prod-1")
        assert len(results) == 2

    def test_explode(self):
        """BOM explosion returns component requirements."""
        engine = BOMEngine()
        bom = engine.create_bom("prod-1", "Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="Steel", quantity=2.0))
        bom.add_item(BOMItem(component_id="c2", component_name="Bolt", quantity=4.0, scrap_factor=0.1))
        bom.activate()
        reqs = engine.explode(bom.id, quantity=1.0)
        assert len(reqs) == 2
        assert reqs[0]["component_id"] == "c1"
        assert reqs[0]["quantity"] == 2.0
        assert reqs[1]["quantity"] == pytest.approx(4.4)

    def test_explode_inactive_raises(self):
        """Exploding inactive BOM raises error."""
        engine = BOMEngine()
        bom = engine.create_bom("prod-1", "Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="Steel", quantity=1.0))
        with pytest.raises(BOMError):
            engine.explode(bom.id)

    def test_explode_not_found_raises(self):
        """Exploding non-existent BOM raises error."""
        engine = BOMEngine()
        with pytest.raises(BOMError):
            engine.explode("nonexistent")

    def test_explode_multi_level(self):
        """Multi-level BOM explosion works."""
        engine = BOMEngine()
        sub_bom = engine.create_bom("sub-1", "Sub-Assembly")
        sub_bom.add_item(BOMItem(component_id="raw-1", component_name="Raw Material", quantity=1.0))
        sub_bom.activate()

        top_bom = engine.create_bom("prod-1", "Widget")
        top_bom.add_item(BOMItem(component_id="sub-1", component_name="Sub-Assembly", quantity=2.0))
        top_bom.activate()

        reqs = engine.explode_multi_level(top_bom.id, quantity=1.0)
        assert len(reqs) == 1
        assert reqs[0]["component_id"] == "raw-1"
        assert reqs[0]["quantity"] == 2.0

    def test_calculate_cost(self):
        """BOM cost calculation works."""
        engine = BOMEngine()
        bom = engine.create_bom("prod-1", "Widget")
        bom.add_item(BOMItem(component_id="c1", component_name="Steel", quantity=2.0))
        bom.add_item(BOMItem(component_id="c2", component_name="Bolt", quantity=4.0))
        costs = {"c1": 10.0, "c2": 0.5}
        total = engine.calculate_cost(bom.id, costs)
        assert total == 22.0

    def test_list_boms(self):
        """All BOMs can be listed."""
        engine = BOMEngine()
        engine.create_bom("prod-1", "Widget")
        engine.create_bom("prod-2", "Gadget")
        assert len(engine.list_boms()) == 2


# ─── Production Planning Tests ───────────────────────────────────────────────


class TestWorkCenter:
    """Test work center data structure."""

    def test_work_center_creation(self):
        """Work center can be created."""
        wc = WorkCenter(name="CNC-1", work_center_type=WorkCenterType.MACHINING)
        assert wc.name == "CNC-1"
        assert wc.work_center_type == WorkCenterType.MACHINING
        assert wc.capacity_per_hour == 1.0
        assert wc.efficiency == 1.0
        assert wc.is_active is True

    def test_available_capacity(self):
        """Available capacity is calculated correctly."""
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0, efficiency=0.8)
        assert wc.available_capacity() == 8.0

    def test_allocate(self):
        """Capacity can be allocated."""
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        assert wc.allocate(5.0) is True
        assert wc.current_load == 5.0
        assert wc.available_capacity() == 5.0

    def test_allocate_exceeds_capacity(self):
        """Allocation beyond capacity fails."""
        wc = WorkCenter(name="CNC-1", capacity_per_hour=5.0)
        assert wc.allocate(10.0) is False
        assert wc.current_load == 0.0

    def test_release(self):
        """Allocated capacity can be released."""
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        wc.allocate(5.0)
        wc.release(3.0)
        assert wc.current_load == 2.0

    def test_release_below_zero(self):
        """Release doesn't go below zero."""
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        wc.allocate(2.0)
        wc.release(5.0)
        assert wc.current_load == 0.0


class TestProductionOrder:
    """Test production order data structure."""

    def test_production_order_creation(self):
        """Production order can be created."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        assert order.product_id == "prod-1"
        assert order.product_name == "Widget"
        assert order.quantity == 100.0
        assert order.status == OrderStatus.PLANNED
        assert order.priority == 5

    def test_release(self):
        """Order can be released."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.release()
        assert order.status == OrderStatus.RELEASED

    def test_release_wrong_status_raises(self):
        """Releasing non-planned order raises error."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.release()
        with pytest.raises(PlanningError):
            order.release()

    def test_start(self):
        """Order can be started."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.release()
        order.start()
        assert order.status == OrderStatus.IN_PROGRESS
        assert order.actual_start is not None

    def test_complete(self):
        """Order can be completed."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.release()
        order.start()
        order.complete()
        assert order.status == OrderStatus.COMPLETED
        assert order.actual_end is not None

    def test_cancel(self):
        """Order can be cancelled."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.cancel()
        assert order.status == OrderStatus.CANCELLED

    def test_cancel_completed_raises(self):
        """Cancelling completed order raises error."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        order.release()
        order.start()
        order.complete()
        with pytest.raises(PlanningError):
            order.cancel()

    def test_is_overdue(self):
        """Overdue check works."""
        past = datetime.now() - timedelta(days=1)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=past,
        )
        assert order.is_overdue() is True

    def test_is_not_overdue(self):
        """Non-overdue check works."""
        future = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=future,
        )
        assert order.is_overdue() is False

    def test_lead_time_hours(self):
        """Lead time is calculated correctly."""
        due = datetime.now() + timedelta(days=7)
        order = ProductionOrder(
            product_id="prod-1",
            product_name="Widget",
            quantity=100.0,
            due_date=due,
        )
        start = datetime.now()
        end = start + timedelta(hours=8.0)
        order.scheduled_start = start
        order.scheduled_end = end
        assert order.lead_time_hours() == pytest.approx(8.0)


class TestProductionPlanner:
    """Test production planner engine."""

    def test_add_work_center(self):
        """Work center can be added."""
        planner = ProductionPlanner()
        wc = WorkCenter(name="CNC-1")
        planner.add_work_center(wc)
        assert planner.get_work_center(wc.id) is not None

    def test_create_order(self):
        """Production order can be created."""
        planner = ProductionPlanner()
        due = datetime.now() + timedelta(days=7)
        order = planner.create_order("prod-1", "Widget", 100.0, due)
        assert order.product_id == "prod-1"
        assert order.quantity == 100.0

    def test_get_order(self):
        """Order can be retrieved."""
        planner = ProductionPlanner()
        due = datetime.now() + timedelta(days=7)
        order = planner.create_order("prod-1", "Widget", 100.0, due)
        assert planner.get_order(order.id) is not None

    def test_schedule_order(self):
        """Order can be scheduled on a work center."""
        planner = ProductionPlanner()
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        planner.add_work_center(wc)
        due = datetime.now() + timedelta(days=7)
        order = planner.create_order("prod-1", "Widget", 100.0, due)
        start = datetime.now()
        result = planner.schedule_order(order.id, wc.id, start, 4.0)
        assert result is True
        assert order.work_center_id == wc.id
        assert order.scheduled_start == start

    def test_schedule_order_insufficient_capacity(self):
        """Scheduling fails when capacity is insufficient."""
        planner = ProductionPlanner()
        wc = WorkCenter(name="CNC-1", capacity_per_hour=2.0)
        planner.add_work_center(wc)
        due = datetime.now() + timedelta(days=7)
        order = planner.create_order("prod-1", "Widget", 100.0, due)
        start = datetime.now()
        result = planner.schedule_order(order.id, wc.id, start, 10.0)
        assert result is False

    def test_get_orders_by_status(self):
        """Orders can be filtered by status."""
        planner = ProductionPlanner()
        due = datetime.now() + timedelta(days=7)
        o1 = planner.create_order("prod-1", "Widget", 100.0, due)
        o2 = planner.create_order("prod-2", "Gadget", 50.0, due)
        o2.release()
        planned = planner.get_orders_by_status(OrderStatus.PLANNED)
        released = planner.get_orders_by_status(OrderStatus.RELEASED)
        assert len(planned) == 1
        assert len(released) == 1

    def test_get_overdue_orders(self):
        """Overdue orders can be retrieved."""
        planner = ProductionPlanner()
        past = datetime.now() - timedelta(days=1)
        future = datetime.now() + timedelta(days=7)
        planner.create_order("prod-1", "Widget", 100.0, past)
        planner.create_order("prod-2", "Gadget", 50.0, future)
        overdue = planner.get_overdue_orders()
        assert len(overdue) == 1
        assert overdue[0].product_id == "prod-1"

    def test_capacity_check(self):
        """Capacity check works."""
        planner = ProductionPlanner()
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        planner.add_work_center(wc)
        assert planner.capacity_check(wc.id, 5.0) is True
        assert planner.capacity_check(wc.id, 15.0) is False

    def test_utilization_rate(self):
        """Utilization rate is calculated correctly."""
        planner = ProductionPlanner()
        wc = WorkCenter(name="CNC-1", capacity_per_hour=10.0)
        planner.add_work_center(wc)
        wc.allocate(5.0)
        assert planner.utilization_rate(wc.id) == pytest.approx(0.5)

    def test_list_orders(self):
        """All orders can be listed."""
        planner = ProductionPlanner()
        due = datetime.now() + timedelta(days=7)
        planner.create_order("prod-1", "Widget", 100.0, due)
        planner.create_order("prod-2", "Gadget", 50.0, due)
        assert len(planner.list_orders()) == 2

    def test_list_work_centers(self):
        """All work centers can be listed."""
        planner = ProductionPlanner()
        planner.add_work_center(WorkCenter(name="CNC-1"))
        planner.add_work_center(WorkCenter(name="CNC-2"))
        assert len(planner.list_work_centers()) == 2


# ─── Quality Control Tests ───────────────────────────────────────────────────


class TestMeasurement:
    """Test measurement data structure."""

    def test_measurement_creation(self):
        """Measurement can be created."""
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=100.1,
            tolerance_min=99.0,
            tolerance_max=101.0,
            unit="mm",
        )
        assert m.parameter == "length"
        assert m.nominal_value == 100.0
        assert m.actual_value == 100.1

    def test_is_within_tolerance(self):
        """Within tolerance check works."""
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=100.5,
            tolerance_min=99.0,
            tolerance_max=101.0,
        )
        assert m.is_within_tolerance() is True

    def test_is_outside_tolerance(self):
        """Outside tolerance check works."""
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=102.0,
            tolerance_min=99.0,
            tolerance_max=101.0,
        )
        assert m.is_within_tolerance() is False

    def test_deviation(self):
        """Deviation is calculated correctly."""
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=100.5,
            tolerance_min=99.0,
            tolerance_max=101.0,
        )
        assert m.deviation() == pytest.approx(0.5)


class TestInspection:
    """Test inspection data structure."""

    def test_inspection_creation(self):
        """Inspection can be created."""
        insp = Inspection(
            product_id="prod-1",
            batch_id="batch-1",
            inspector="John",
            sample_size=50,
        )
        assert insp.product_id == "prod-1"
        assert insp.batch_id == "batch-1"
        assert insp.inspector == "John"
        assert insp.sample_size == 50
        assert insp.result == InspectionResult.PASS

    def test_add_measurement(self):
        """Measurement can be added to inspection."""
        insp = Inspection(product_id="prod-1", batch_id="batch-1", inspector="John")
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=100.5,
            tolerance_min=99.0,
            tolerance_max=101.0,
        )
        insp.add_measurement(m)
        assert len(insp.measurements) == 1
        assert insp.defects_found == 0

    def test_add_defective_measurement(self):
        """Defective measurement increments defect count."""
        insp = Inspection(product_id="prod-1", batch_id="batch-1", inspector="John")
        m = Measurement(
            parameter="length",
            nominal_value=100.0,
            actual_value=105.0,
            tolerance_min=99.0,
            tolerance_max=101.0,
        )
        insp.add_measurement(m)
        assert insp.defects_found == 1

    def test_first_pass_yield(self):
        """First pass yield is calculated correctly."""
        insp = Inspection(
            product_id="prod-1",
            batch_id="batch-1",
            inspector="John",
            sample_size=100,
            defects_found=5,
        )
        assert insp.first_pass_yield() == 95.0

    def test_first_pass_yield_zero_sample(self):
        """FPY is 0 when sample size is 0."""
        insp = Inspection(product_id="prod-1", batch_id="batch-1", inspector="John")
        assert insp.first_pass_yield() == 0.0

    def test_defect_rate(self):
        """Defect rate (DPPM) is calculated correctly."""
        insp = Inspection(
            product_id="prod-1",
            batch_id="batch-1",
            inspector="John",
            sample_size=10000,
            defects_found=3,
        )
        assert insp.defect_rate() == pytest.approx(300.0)


class TestNonConformance:
    """Test non-conformance data structure."""

    def test_non_conformance_creation(self):
        """Non-conformance can be created."""
        nc = NonConformance(
            product_id="prod-1",
            description="Surface scratch",
            severity=DefectSeverity.MINOR,
        )
        assert nc.product_id == "prod-1"
        assert nc.description == "Surface scratch"
        assert nc.severity == DefectSeverity.MINOR
        assert nc.disposition == Disposition.PENDING

    def test_set_disposition(self):
        """Disposition can be set."""
        nc = NonConformance(
            product_id="prod-1",
            description="Scratch",
            severity=DefectSeverity.MINOR,
        )
        nc.set_disposition(Disposition.REWORK)
        assert nc.disposition == Disposition.REWORK

    def test_close(self):
        """Non-conformance can be closed."""
        nc = NonConformance(
            product_id="prod-1",
            description="Scratch",
            severity=DefectSeverity.MINOR,
        )
        nc.close("Polished and re-inspected")
        assert nc.is_closed() is True
        assert nc.corrective_action == "Polished and re-inspected"
        assert nc.closed_date is not None

    def test_is_not_closed(self):
        """Open non-conformance is not closed."""
        nc = NonConformance(
            product_id="prod-1",
            description="Scratch",
            severity=DefectSeverity.MINOR,
        )
        assert nc.is_closed() is False


class TestQualityControl:
    """Test quality control engine."""

    def test_create_inspection(self):
        """Inspection can be created."""
        qc = QualityControl()
        insp = qc.create_inspection("prod-1", "batch-1", "John", sample_size=50)
        assert insp.product_id == "prod-1"
        assert insp.sample_size == 50

    def test_get_inspection(self):
        """Inspection can be retrieved."""
        qc = QualityControl()
        insp = qc.create_inspection("prod-1", "batch-1", "John")
        assert qc.get_inspection(insp.id) is not None

    def test_record_result(self):
        """Inspection result can be recorded."""
        qc = QualityControl()
        insp = qc.create_inspection("prod-1", "batch-1", "John")
        qc.record_result(insp.id, InspectionResult.FAIL)
        assert insp.result == InspectionResult.FAIL

    def test_record_result_not_found_raises(self):
        """Recording result for non-existent inspection raises error."""
        qc = QualityControl()
        with pytest.raises(QualityError):
            qc.record_result("nonexistent", InspectionResult.PASS)

    def test_create_non_conformance(self):
        """Non-conformance can be created."""
        qc = QualityControl()
        nc = qc.create_non_conformance(
            product_id="prod-1",
            description="Crack found",
            severity=DefectSeverity.CRITICAL,
        )
        assert nc.product_id == "prod-1"
        assert nc.severity == DefectSeverity.CRITICAL

    def test_get_non_conformance(self):
        """Non-conformance can be retrieved."""
        qc = QualityControl()
        nc = qc.create_non_conformance("prod-1", "Crack", DefectSeverity.CRITICAL)
        assert qc.get_non_conformance(nc.id) is not None

    def test_get_inspections_by_product(self):
        """Inspections can be filtered by product."""
        qc = QualityControl()
        qc.create_inspection("prod-1", "batch-1", "John")
        qc.create_inspection("prod-1", "batch-2", "Jane")
        qc.create_inspection("prod-2", "batch-3", "John")
        results = qc.get_inspections_by_product("prod-1")
        assert len(results) == 2

    def test_get_open_non_conformances(self):
        """Open non-conformances can be retrieved."""
        qc = QualityControl()
        nc1 = qc.create_non_conformance("prod-1", "Issue A", DefectSeverity.MAJOR)
        qc.create_non_conformance("prod-2", "Issue B", DefectSeverity.MINOR)
        nc1.close("Fixed")
        open_ncs = qc.get_open_non_conformances()
        assert len(open_ncs) == 1

    def test_get_non_conformances_by_severity(self):
        """Non-conformances can be filtered by severity."""
        qc = QualityControl()
        qc.create_non_conformance("prod-1", "Critical issue", DefectSeverity.CRITICAL)
        qc.create_non_conformance("prod-2", "Minor issue", DefectSeverity.MINOR)
        qc.create_non_conformance("prod-3", "Another critical", DefectSeverity.CRITICAL)
        critical = qc.get_non_conformances_by_severity(DefectSeverity.CRITICAL)
        assert len(critical) == 2

    def test_overall_quality_score(self):
        """Overall quality score is calculated correctly."""
        qc = QualityControl()
        insp1 = qc.create_inspection("prod-1", "batch-1", "John", sample_size=100)
        insp1.defects_found = 2
        insp2 = qc.create_inspection("prod-1", "batch-2", "Jane", sample_size=100)
        insp2.defects_found = 3
        score = qc.overall_quality_score("prod-1")
        assert score == pytest.approx(97.5)

    def test_overall_quality_score_no_inspections(self):
        """Quality score is 100 when no inspections."""
        qc = QualityControl()
        assert qc.overall_quality_score("prod-1") == 100.0

    def test_list_inspections(self):
        """All inspections can be listed."""
        qc = QualityControl()
        qc.create_inspection("prod-1", "batch-1", "John")
        qc.create_inspection("prod-2", "batch-2", "Jane")
        assert len(qc.list_inspections()) == 2

    def test_list_non_conformances(self):
        """All non-conformances can be listed."""
        qc = QualityControl()
        qc.create_non_conformance("prod-1", "Issue A", DefectSeverity.MAJOR)
        qc.create_non_conformance("prod-2", "Issue B", DefectSeverity.MINOR)
        assert len(qc.list_non_conformances()) == 2


# ─── Shop Floor Tests ────────────────────────────────────────────────────────


class TestOperation:
    """Test operation data structure."""

    def test_operation_creation(self):
        """Operation can be created."""
        op = Operation(
            sequence=10,
            description="Mill surface",
            work_center_id="wc-1",
            setup_time_minutes=30.0,
            run_time_minutes=60.0,
        )
        assert op.sequence == 10
        assert op.description == "Mill surface"
        assert op.status == OperationStatus.PENDING

    def test_total_standard_time(self):
        """Total standard time is calculated correctly."""
        op = Operation(
            sequence=10,
            description="Mill",
            work_center_id="wc-1",
            setup_time_minutes=30.0,
            run_time_minutes=60.0,
        )
        assert op.total_standard_time() == 90.0

    def test_total_actual_time(self):
        """Total actual time is calculated correctly."""
        op = Operation(
            sequence=10,
            description="Mill",
            work_center_id="wc-1",
            actual_setup_minutes=25.0,
            actual_run_minutes=55.0,
        )
        assert op.total_actual_time() == 80.0

    def test_efficiency(self):
        """Efficiency is calculated correctly."""
        op = Operation(
            sequence=10,
            description="Mill",
            work_center_id="wc-1",
            setup_time_minutes=30.0,
            run_time_minutes=60.0,
            actual_setup_minutes=30.0,
            actual_run_minutes=60.0,
        )
        assert op.efficiency() == pytest.approx(1.0)

    def test_efficiency_zero_standard(self):
        """Efficiency is 1.0 when standard time is 0."""
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        assert op.efficiency() == 1.0

    def test_start(self):
        """Operation can be started."""
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op.start()
        assert op.status == OperationStatus.IN_PROGRESS

    def test_start_wrong_status_raises(self):
        """Starting non-pending operation raises error."""
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op.start()
        with pytest.raises(ShopFloorError):
            op.start()

    def test_complete(self):
        """Operation can be completed."""
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op.start()
        op.complete(completed_qty=100.0, defect_qty=2.0)
        assert op.status == OperationStatus.COMPLETED
        assert op.completed_quantity == 100.0
        assert op.defect_quantity == 2.0

    def test_complete_wrong_status_raises(self):
        """Completing non-in-progress operation raises error."""
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        with pytest.raises(ShopFloorError):
            op.complete(completed_qty=100.0)


class TestWorkOrder:
    """Test work order data structure."""

    def test_work_order_creation(self):
        """Work order can be created."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        assert wo.product_id == "prod-1"
        assert wo.product_name == "Widget"
        assert wo.quantity == 100.0
        assert wo.status == WorkOrderStatus.CREATED

    def test_add_operation(self):
        """Operation can be added to work order."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        wo.add_operation(op)
        assert len(wo.operations) == 1

    def test_add_operation_sorted(self):
        """Operations are sorted by sequence."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op2 = Operation(sequence=20, description="Drill", work_center_id="wc-1")
        op1 = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        wo.add_operation(op2)
        wo.add_operation(op1)
        assert wo.operations[0].sequence == 10
        assert wo.operations[1].sequence == 20

    def test_dispatch(self):
        """Work order can be dispatched."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        wo.dispatch()
        assert wo.status == WorkOrderStatus.DISPATCHED
        assert wo.dispatch_date is not None

    def test_dispatch_wrong_status_raises(self):
        """Dispatching non-created work order raises error."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        wo.dispatch()
        with pytest.raises(ShopFloorError):
            wo.dispatch()

    def test_start(self):
        """Work order can be started."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        wo.dispatch()
        wo.start()
        assert wo.status == WorkOrderStatus.IN_PROGRESS
        assert wo.start_date is not None

    def test_complete(self):
        """Work order can be completed."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        wo.dispatch()
        wo.start()
        wo.complete(completed_qty=98.0, defect_qty=2.0)
        assert wo.status == WorkOrderStatus.COMPLETED
        assert wo.completed_quantity == 98.0
        assert wo.defect_quantity == 2.0

    def test_close(self):
        """Work order can be closed."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        wo.dispatch()
        wo.start()
        wo.complete(100.0)
        wo.close()
        assert wo.status == WorkOrderStatus.CLOSED

    def test_close_wrong_status_raises(self):
        """Closing non-completed work order raises error."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        with pytest.raises(ShopFloorError):
            wo.close()

    def test_current_operation(self):
        """Current operation is returned correctly."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op1 = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op2 = Operation(sequence=20, description="Drill", work_center_id="wc-1")
        wo.add_operation(op1)
        wo.add_operation(op2)
        current = wo.current_operation()
        assert current is not None
        assert current.sequence == 10

    def test_current_operation_all_completed(self):
        """No current operation when all completed."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op.status = OperationStatus.COMPLETED
        wo.add_operation(op)
        assert wo.current_operation() is None

    def test_completion_percentage(self):
        """Completion percentage is calculated correctly."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op1 = Operation(sequence=10, description="Mill", work_center_id="wc-1")
        op2 = Operation(sequence=20, description="Drill", work_center_id="wc-1")
        op1.status = OperationStatus.COMPLETED
        wo.add_operation(op1)
        wo.add_operation(op2)
        assert wo.completion_percentage() == pytest.approx(50.0)

    def test_total_standard_time(self):
        """Total standard time for all operations."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op1 = Operation(sequence=10, description="Mill", work_center_id="wc-1",
                        setup_time_minutes=10.0, run_time_minutes=20.0)
        op2 = Operation(sequence=20, description="Drill", work_center_id="wc-1",
                        setup_time_minutes=5.0, run_time_minutes=15.0)
        wo.add_operation(op1)
        wo.add_operation(op2)
        assert wo.total_standard_time() == 50.0

    def test_total_actual_time(self):
        """Total actual time for all operations."""
        wo = WorkOrder(product_id="prod-1", product_name="Widget", quantity=100.0)
        op1 = Operation(sequence=10, description="Mill", work_center_id="wc-1",
                        actual_setup_minutes=10.0, actual_run_minutes=20.0)
        op2 = Operation(sequence=20, description="Drill", work_center_id="wc-1",
                        actual_setup_minutes=5.0, actual_run_minutes=15.0)
        wo.add_operation(op1)
        wo.add_operation(op2)
        assert wo.total_actual_time() == 50.0


class TestShopFloor:
    """Test shop floor engine."""

    def test_create_work_order(self):
        """Work order can be created."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        assert wo.product_id == "prod-1"
        assert wo.quantity == 100.0

    def test_get_work_order(self):
        """Work order can be retrieved."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        assert sf.get_work_order(wo.id) is not None

    def test_dispatch_work_order(self):
        """Work order can be dispatched."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        sf.dispatch_work_order(wo.id)
        assert wo.status == WorkOrderStatus.DISPATCHED

    def test_start_work_order(self):
        """Work order can be started."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        sf.dispatch_work_order(wo.id)
        sf.start_work_order(wo.id)
        assert wo.status == WorkOrderStatus.IN_PROGRESS

    def test_complete_work_order(self):
        """Work order can be completed."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        sf.dispatch_work_order(wo.id)
        sf.start_work_order(wo.id)
        sf.complete_work_order(wo.id, 98.0, 2.0)
        assert wo.status == WorkOrderStatus.COMPLETED
        assert wo.completed_quantity == 98.0

    def test_close_work_order(self):
        """Work order can be closed."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        sf.dispatch_work_order(wo.id)
        sf.start_work_order(wo.id)
        sf.complete_work_order(wo.id, 100.0)
        sf.close_work_order(wo.id)
        assert wo.status == WorkOrderStatus.CLOSED

    def test_get_work_orders_by_status(self):
        """Work orders can be filtered by status."""
        sf = ShopFloor()
        sf.create_work_order("prod-1", "Widget", 100.0)
        sf.create_work_order("prod-2", "Gadget", 50.0)
        created = sf.get_work_orders_by_status(WorkOrderStatus.CREATED)
        assert len(created) == 2

    def test_get_active_work_orders(self):
        """Active work orders can be retrieved."""
        sf = ShopFloor()
        wo1 = sf.create_work_order("prod-1", "Widget", 100.0)
        sf.create_work_order("prod-2", "Gadget", 50.0)
        sf.dispatch_work_order(wo1.id)
        sf.start_work_order(wo1.id)
        active = sf.get_active_work_orders()
        assert len(active) == 1

    def test_get_work_orders_by_product(self):
        """Work orders can be filtered by product."""
        sf = ShopFloor()
        sf.create_work_order("prod-1", "Widget", 100.0)
        sf.create_work_order("prod-1", "Widget", 200.0)
        sf.create_work_order("prod-2", "Gadget", 50.0)
        results = sf.get_work_orders_by_product("prod-1")
        assert len(results) == 2

    def test_average_efficiency(self):
        """Average efficiency is calculated correctly."""
        sf = ShopFloor()
        wo = sf.create_work_order("prod-1", "Widget", 100.0)
        op = Operation(sequence=10, description="Mill", work_center_id="wc-1",
                        setup_time_minutes=10.0, run_time_minutes=20.0,
                        actual_setup_minutes=10.0, actual_run_minutes=20.0)
        wo.add_operation(op)
        assert sf.average_efficiency() == pytest.approx(1.0)

    def test_list_work_orders(self):
        """All work orders can be listed."""
        sf = ShopFloor()
        sf.create_work_order("prod-1", "Widget", 100.0)
        sf.create_work_order("prod-2", "Gadget", 50.0)
        assert len(sf.list_work_orders()) == 2


# ─── Maintenance Tests ───────────────────────────────────────────────────────


class TestAsset:
    """Test asset data structure."""

    def test_asset_creation(self):
        """Asset can be created."""
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        assert asset.name == "CNC Mill"
        assert asset.asset_type == "Machine"
        assert asset.location == "Building A"
        assert asset.status == AssetStatus.OPERATIONAL

    def test_is_due_for_maintenance_no_schedule(self):
        """Asset not due when no schedule set."""
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        assert asset.is_due_for_maintenance() is False

    def test_is_due_for_maintenance_past_date(self):
        """Asset due when scheduled date is past."""
        asset = Asset(
            name="CNC Mill",
            asset_type="Machine",
            location="Building A",
            next_scheduled_maintenance=datetime.now() - timedelta(days=1),
        )
        assert asset.is_due_for_maintenance() is True

    def test_is_due_for_maintenance_future_date(self):
        """Asset not due when scheduled date is future."""
        asset = Asset(
            name="CNC Mill",
            asset_type="Machine",
            location="Building A",
            next_scheduled_maintenance=datetime.now() + timedelta(days=30),
        )
        assert asset.is_due_for_maintenance() is False

    def test_record_maintenance(self):
        """Maintenance can be recorded."""
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        asset.record_maintenance(2.0)
        assert asset.last_maintenance_date is not None
        assert asset.next_scheduled_maintenance is not None
        assert asset.status == AssetStatus.OPERATIONAL

    def test_add_operating_hours(self):
        """Operating hours can be added."""
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        asset.add_operating_hours(100.0)
        assert asset.total_operating_hours == 100.0
        asset.add_operating_hours(50.0)
        assert asset.total_operating_hours == 150.0

    def test_set_status(self):
        """Asset status can be set."""
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        asset.set_status(AssetStatus.DOWN)
        assert asset.status == AssetStatus.DOWN


class TestMaintenanceOrder:
    """Test maintenance order data structure."""

    def test_maintenance_order_creation(self):
        """Maintenance order can be created."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Replace spindle bearing",
        )
        assert order.asset_id == "asset-1"
        assert order.maintenance_type == MaintenanceType.PREVENTIVE
        assert order.priority == MaintenancePriority.HIGH
        assert order.status == MaintenanceOrderStatus.OPEN

    def test_schedule(self):
        """Order can be scheduled."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        date = datetime.now() + timedelta(days=3)
        order.schedule(date, technician="Mike")
        assert order.status == MaintenanceOrderStatus.SCHEDULED
        assert order.scheduled_date == date
        assert order.assigned_technician == "Mike"

    def test_schedule_wrong_status_raises(self):
        """Scheduling non-open order raises error."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        order.schedule(datetime.now() + timedelta(days=1))
        with pytest.raises(MaintenanceError):
            order.schedule(datetime.now() + timedelta(days=2))

    def test_start(self):
        """Order can be started."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        order.schedule(datetime.now() + timedelta(days=1))
        order.start()
        assert order.status == MaintenanceOrderStatus.IN_PROGRESS
        assert order.started_date is not None

    def test_complete(self):
        """Order can be completed."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        order.schedule(datetime.now() + timedelta(days=1))
        order.start()
        order.complete(actual_hours=3.0, downtime_hours=4.0)
        assert order.status == MaintenanceOrderStatus.COMPLETED
        assert order.actual_hours == 3.0
        assert order.downtime_hours == 4.0

    def test_cancel(self):
        """Order can be cancelled."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        order.cancel()
        assert order.status == MaintenanceOrderStatus.CANCELLED

    def test_cancel_completed_raises(self):
        """Cancelling completed order raises error."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
        )
        order.schedule(datetime.now() + timedelta(days=1))
        order.start()
        order.complete(2.0)
        with pytest.raises(MaintenanceError):
            order.cancel()

    def test_total_cost(self):
        """Total cost is calculated correctly."""
        order = MaintenanceOrder(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Routine check",
            parts_cost=150.0,
            labor_cost=200.0,
        )
        assert order.total_cost() == 350.0


class TestMaintenancePlanner:
    """Test maintenance planner engine."""

    def test_add_asset(self):
        """Asset can be added."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        assert planner.get_asset(asset.id) is not None

    def test_create_order(self):
        """Maintenance order can be created."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        order = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Replace bearing",
        )
        assert order.asset_id == asset.id
        assert order.maintenance_type == MaintenanceType.PREVENTIVE

    def test_create_order_asset_not_found_raises(self):
        """Creating order for non-existent asset raises error."""
        planner = MaintenancePlanner()
        with pytest.raises(MaintenanceError):
            planner.create_order(
                asset_id="nonexistent",
                maintenance_type=MaintenanceType.PREVENTIVE,
                priority=MaintenancePriority.HIGH,
                description="Test",
            )

    def test_get_order(self):
        """Order can be retrieved."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        order = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Test",
        )
        assert planner.get_order(order.id) is not None

    def test_schedule_order(self):
        """Order can be scheduled."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        order = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Test",
        )
        date = datetime.now() + timedelta(days=3)
        planner.schedule_order(order.id, date, technician="Mike")
        assert order.status == MaintenanceOrderStatus.SCHEDULED

    def test_start_order(self):
        """Order can be started."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        order = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Test",
        )
        planner.schedule_order(order.id, datetime.now() + timedelta(days=1))
        planner.start_order(order.id)
        assert order.status == MaintenanceOrderStatus.IN_PROGRESS
        assert asset.status == AssetStatus.UNDER_MAINTENANCE

    def test_complete_order(self):
        """Order can be completed."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        order = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Test",
        )
        planner.schedule_order(order.id, datetime.now() + timedelta(days=1))
        planner.start_order(order.id)
        planner.complete_order(order.id, actual_hours=3.0, downtime_hours=4.0)
        assert order.status == MaintenanceOrderStatus.COMPLETED
        assert asset.status == AssetStatus.OPERATIONAL

    def test_get_orders_by_status(self):
        """Orders can be filtered by status."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC Mill", asset_type="Machine", location="Building A")
        planner.add_asset(asset)
        o1 = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            priority=MaintenancePriority.HIGH,
            description="Test A",
        )
        o2 = planner.create_order(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.CORRECTIVE,
            priority=MaintenancePriority.MEDIUM,
            description="Test B",
        )
        o2.schedule(datetime.now() + timedelta(days=1))
        open_orders = planner.get_orders_by_status(MaintenanceOrderStatus.OPEN)
        scheduled = planner.get_orders_by_status(MaintenanceOrderStatus.SCHEDULED)
        assert len(open_orders) == 1
        assert len(scheduled) == 1

    def test_get_orders_by_asset(self):
        """Orders can be filtered by asset."""
        planner = MaintenancePlanner()
        a1 = Asset(name="CNC-1", asset_type="Machine", location="A")
        a2 = Asset(name="CNC-2", asset_type="Machine", location="B")
        planner.add_asset(a1)
        planner.add_asset(a2)
        planner.create_order(a1.id, MaintenanceType.PREVENTIVE, MaintenancePriority.HIGH, "Fix A")
        planner.create_order(a2.id, MaintenanceType.CORRECTIVE, MaintenancePriority.LOW, "Fix B")
        results = planner.get_orders_by_asset(a1.id)
        assert len(results) == 1

    def test_get_orders_by_type(self):
        """Orders can be filtered by type."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC-1", asset_type="Machine", location="A")
        planner.add_asset(asset)
        planner.create_order(asset.id, MaintenanceType.PREVENTIVE, MaintenancePriority.HIGH, "PM")
        planner.create_order(asset.id, MaintenanceType.CORRECTIVE, MaintenancePriority.LOW, "CM")
        preventive = planner.get_orders_by_type(MaintenanceType.PREVENTIVE)
        assert len(preventive) == 1

    def test_get_open_orders(self):
        """Open orders can be retrieved."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC-1", asset_type="Machine", location="A")
        planner.add_asset(asset)
        o1 = planner.create_order(asset.id, MaintenanceType.PREVENTIVE, MaintenancePriority.HIGH, "PM")
        o2 = planner.create_order(asset.id, MaintenanceType.CORRECTIVE, MaintenancePriority.LOW, "CM")
        o2.schedule(datetime.now() + timedelta(days=1))
        open_orders = planner.get_open_orders()
        assert len(open_orders) == 2

    def test_get_due_preventive_maintenance(self):
        """Assets due for maintenance can be retrieved."""
        planner = MaintenancePlanner()
        a1 = Asset(
            name="CNC-1",
            asset_type="Machine",
            location="A",
            next_scheduled_maintenance=datetime.now() - timedelta(days=1),
        )
        a2 = Asset(
            name="CNC-2",
            asset_type="Machine",
            location="B",
            next_scheduled_maintenance=datetime.now() + timedelta(days=30),
        )
        planner.add_asset(a1)
        planner.add_asset(a2)
        due = planner.get_due_preventive_maintenance()
        assert len(due) == 1
        assert due[0].name == "CNC-1"

    def test_get_asset_uptime(self):
        """Asset uptime is calculated correctly."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC-1", asset_type="Machine", location="A")
        asset.total_operating_hours = 1000.0
        planner.add_asset(asset)
        order = planner.create_order(
            asset.id,
            MaintenanceType.PREVENTIVE,
            MaintenancePriority.HIGH,
            "PM",
        )
        planner.schedule_order(order.id, datetime.now() + timedelta(days=1))
        planner.start_order(order.id)
        planner.complete_order(order.id, actual_hours=2.0, downtime_hours=4.0)
        uptime = planner.get_asset_uptime(asset.id)
        assert uptime == pytest.approx(99.6)

    def test_total_maintenance_cost(self):
        """Total maintenance cost is calculated correctly."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC-1", asset_type="Machine", location="A")
        planner.add_asset(asset)
        o1 = planner.create_order(asset.id, MaintenanceType.PREVENTIVE, MaintenancePriority.HIGH, "PM")
        o1.parts_cost = 100.0
        o1.labor_cost = 200.0
        o2 = planner.create_order(asset.id, MaintenanceType.CORRECTIVE, MaintenancePriority.LOW, "CM")
        o2.parts_cost = 50.0
        o2.labor_cost = 75.0
        assert planner.total_maintenance_cost() == 425.0

    def test_list_assets(self):
        """All assets can be listed."""
        planner = MaintenancePlanner()
        planner.add_asset(Asset(name="CNC-1", asset_type="Machine", location="A"))
        planner.add_asset(Asset(name="CNC-2", asset_type="Machine", location="B"))
        assert len(planner.list_assets()) == 2

    def test_list_orders(self):
        """All orders can be listed."""
        planner = MaintenancePlanner()
        asset = Asset(name="CNC-1", asset_type="Machine", location="A")
        planner.add_asset(asset)
        planner.create_order(asset.id, MaintenanceType.PREVENTIVE, MaintenancePriority.HIGH, "PM")
        planner.create_order(asset.id, MaintenanceType.CORRECTIVE, MaintenancePriority.LOW, "CM")
        assert len(planner.list_orders()) == 2
