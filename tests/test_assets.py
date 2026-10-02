"""Tests for asset management system."""
import pytest
from datetime import date, timedelta

from apex_os_bp.assets.models import (
    Asset,
    AssetCategory,
    AssetStatus,
    DepreciationMethod,
    DepreciationRecord,
    DisposalMethod,
    DisposalRecord,
    MaintenanceRecord,
    MaintenanceStatus,
    MaintenanceType,
    ValuationRecord,
)
from apex_os_bp.assets.tracker import AssetTracker
from apex_os_bp.assets.depreciation import DepreciationCalculator
from apex_os_bp.assets.maintenance import MaintenanceScheduler
from apex_os_bp.assets.valuation import AssetValuator
from apex_os_bp.assets.disposal import AssetDisposal


# =============================================================================
# Test Asset Models
# =============================================================================

class TestAssetModel:
    """Test asset data model."""

    def test_asset_creation(self):
        """Asset can be created with required fields."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            salvage_value=200.0,
            useful_life_years=3,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        assert asset.id == "asset-1"
        assert asset.name == "Laptop"
        assert asset.category == AssetCategory.ELECTRONICS
        assert asset.status == AssetStatus.ACTIVE
        assert asset.purchase_cost == 1200.0
        assert asset.salvage_value == 200.0
        assert asset.useful_life_years == 3

    def test_asset_negative_cost_raises(self):
        """Negative purchase cost raises ValueError."""
        with pytest.raises(ValueError, match="Purchase cost cannot be negative"):
            Asset(
                id="asset-1",
                name="Laptop",
                category=AssetCategory.ELECTRONICS,
                status=AssetStatus.ACTIVE,
                purchase_date=date(2024, 1, 15),
                purchase_cost=-100.0,
                salvage_value=0.0,
                useful_life_years=3,
                depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            )

    def test_asset_negative_salvage_raises(self):
        """Negative salvage value raises ValueError."""
        with pytest.raises(ValueError, match="Salvage value cannot be negative"):
            Asset(
                id="asset-1",
                name="Laptop",
                category=AssetCategory.ELECTRONICS,
                status=AssetStatus.ACTIVE,
                purchase_date=date(2024, 1, 15),
                purchase_cost=1000.0,
                salvage_value=-50.0,
                useful_life_years=3,
                depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            )

    def test_asset_zero_life_raises(self):
        """Zero useful life raises ValueError."""
        with pytest.raises(ValueError, match="Useful life must be positive"):
            Asset(
                id="asset-1",
                name="Laptop",
                category=AssetCategory.ELECTRONICS,
                status=AssetStatus.ACTIVE,
                purchase_date=date(2024, 1, 15),
                purchase_cost=1000.0,
                salvage_value=0.0,
                useful_life_years=0,
                depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            )

    def test_asset_salvage_exceeds_cost_raises(self):
        """Salvage value exceeding purchase cost raises ValueError."""
        with pytest.raises(ValueError, match="Salvage value cannot exceed purchase cost"):
            Asset(
                id="asset-1",
                name="Laptop",
                category=AssetCategory.ELECTRONICS,
                status=AssetStatus.ACTIVE,
                purchase_date=date(2024, 1, 15),
                purchase_cost=1000.0,
                salvage_value=1500.0,
                useful_life_years=3,
                depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            )

    def test_asset_with_optional_fields(self):
        """Asset can be created with optional fields."""
        asset = Asset(
            id="asset-1",
            name="Company Car",
            category=AssetCategory.VEHICLE,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 15),
            purchase_cost=30000.0,
            salvage_value=5000.0,
            useful_life_years=5,
            depreciation_method=DepreciationMethod.DECLINING_BALANCE,
            location="Building A",
            assigned_to="John Doe",
            serial_number="VIN123456",
            description="Company sedan",
            metadata={"color": "blue", "make": "Toyota"},
        )
        assert asset.location == "Building A"
        assert asset.assigned_to == "John Doe"
        assert asset.serial_number == "VIN123456"
        assert asset.description == "Company sedan"
        assert asset.metadata["color"] == "blue"


# =============================================================================
# Test Asset Tracker
# =============================================================================

class TestAssetTracker:
    """Test asset tracking functionality."""

    def test_register_asset(self):
        """Asset can be registered."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            salvage_value=200.0,
            useful_life_years=3,
        )
        assert asset.id is not None
        assert asset.name == "Laptop"
        assert asset.status == AssetStatus.ACTIVE
        assert tracker.get_asset_count() == 1

    def test_get_asset(self):
        """Asset can be retrieved by ID."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        retrieved = tracker.get_asset(asset.id)
        assert retrieved is not None
        assert retrieved.id == asset.id
        assert retrieved.name == "Laptop"

    def test_get_nonexistent_asset(self):
        """Getting nonexistent asset returns None."""
        tracker = AssetTracker()
        assert tracker.get_asset("nonexistent") is None

    def test_get_all_assets(self):
        """All assets can be retrieved."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        assert len(tracker.get_all_assets()) == 2

    def test_get_assets_by_category(self):
        """Assets can be filtered by category."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        electronics = tracker.get_assets_by_category(AssetCategory.ELECTRONICS)
        assert len(electronics) == 1
        assert electronics[0].name == "Laptop"

    def test_get_assets_by_status(self):
        """Assets can be filtered by status."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.set_asset_status(asset.id, AssetStatus.IDLE)
        idle_assets = tracker.get_assets_by_status(AssetStatus.IDLE)
        assert len(idle_assets) == 1
        assert idle_assets[0].status == AssetStatus.IDLE

    def test_get_assets_by_location(self):
        """Assets can be filtered by location."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            location="Building A",
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
            location="Building B",
        )
        building_a = tracker.get_assets_by_location("Building A")
        assert len(building_a) == 1
        assert building_a[0].name == "Laptop"

    def test_get_assets_by_assignee(self):
        """Assets can be filtered by assignee."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            assigned_to="John",
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
            assigned_to="Jane",
        )
        john_assets = tracker.get_assets_by_assignee("John")
        assert len(john_assets) == 1
        assert john_assets[0].name == "Laptop"

    def test_update_asset(self):
        """Asset can be updated."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        updated = tracker.update_asset(asset.id, name="Gaming Laptop", location="Office 101")
        assert updated.name == "Gaming Laptop"
        assert updated.location == "Office 101"

    def test_update_nonexistent_asset_raises(self):
        """Updating nonexistent asset raises ValueError."""
        tracker = AssetTracker()
        with pytest.raises(ValueError, match="Asset not found"):
            tracker.update_asset("nonexistent", name="New Name")

    def test_assign_asset(self):
        """Asset can be assigned to a person."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.assign_asset(asset.id, "John Doe")
        assert tracker.get_asset(asset.id).assigned_to == "John Doe"

    def test_relocate_asset(self):
        """Asset can be relocated."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            location="Building A",
        )
        tracker.relocate_asset(asset.id, "Building B")
        assert tracker.get_asset(asset.id).location == "Building B"

    def test_set_asset_status(self):
        """Asset status can be set."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.set_asset_status(asset.id, AssetStatus.IN_MAINTENANCE)
        assert tracker.get_asset(asset.id).status == AssetStatus.IN_MAINTENANCE

    def test_remove_asset(self):
        """Asset can be removed."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.remove_asset(asset.id)
        assert tracker.get_asset(asset.id) is None
        assert tracker.get_asset_count() == 0

    def test_remove_nonexistent_asset_raises(self):
        """Removing nonexistent asset raises ValueError."""
        tracker = AssetTracker()
        with pytest.raises(ValueError, match="Asset not found"):
            tracker.remove_asset("nonexistent")

    def test_get_total_asset_value(self):
        """Total asset value can be calculated."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        assert tracker.get_total_asset_value() == 1700.0

    def test_get_asset_count_by_category(self):
        """Asset count by category can be retrieved."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Monitor",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 20),
            purchase_cost=300.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        counts = tracker.get_asset_count_by_category()
        assert counts[AssetCategory.ELECTRONICS] == 2
        assert counts[AssetCategory.FURNITURE] == 1

    def test_get_asset_count_by_status(self):
        """Asset count by status can be retrieved."""
        tracker = AssetTracker()
        asset1 = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        tracker.set_asset_status(asset1.id, AssetStatus.IDLE)
        counts = tracker.get_asset_count_by_status()
        assert counts[AssetStatus.ACTIVE] == 1
        assert counts[AssetStatus.IDLE] == 1

    def test_search_assets(self):
        """Assets can be searched."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="MacBook Pro",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=2000.0,
            serial_number="MBP123",
        )
        tracker.register_asset(
            name="Dell Monitor",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 20),
            purchase_cost=400.0,
            serial_number="DELL456",
        )
        results = tracker.search_assets("macbook")
        assert len(results) == 1
        assert results[0].name == "MacBook Pro"

    def test_search_by_serial_number(self):
        """Assets can be searched by serial number."""
        tracker = AssetTracker()
        tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
            serial_number="SN12345",
        )
        results = tracker.search_assets("SN12345")
        assert len(results) == 1

    def test_get_depreciable_assets(self):
        """Depreciable assets can be retrieved."""
        tracker = AssetTracker()
        asset1 = tracker.register_asset(
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 15),
            purchase_cost=1200.0,
        )
        tracker.register_asset(
            name="Desk",
            category=AssetCategory.FURNITURE,
            purchase_date=date(2024, 2, 1),
            purchase_cost=500.0,
        )
        tracker.set_asset_status(asset1.id, AssetStatus.DISPOSED)
        depreciable = tracker.get_depreciable_assets()
        assert len(depreciable) == 1
        assert depreciable[0].name == "Desk"


# =============================================================================
# Test Depreciation Calculator
# =============================================================================

class TestDepreciationCalculator:
    """Test depreciation calculations."""

    def test_straight_line_basic(self):
        """Straight-line depreciation is calculated correctly."""
        dep = DepreciationCalculator.straight_line(1000.0, 200.0, 4)
        assert dep == 200.0

    def test_straight_line_zero_life(self):
        """Straight-line with zero life returns 0."""
        dep = DepreciationCalculator.straight_line(1000.0, 200.0, 0)
        assert dep == 0.0

    def test_declining_balance_year1(self):
        """Declining balance first year is calculated correctly."""
        dep = DepreciationCalculator.declining_balance(1000.0, 200.0, 4, 1)
        assert dep == 500.0  # 1000 * 2/4

    def test_declining_balance_year2(self):
        """Declining balance second year is calculated correctly."""
        dep = DepreciationCalculator.declining_balance(1000.0, 200.0, 4, 2)
        assert dep == 250.0  # (1000 - 500) * 2/4

    def test_declining_balance_respects_salvage(self):
        """Declining balance does not go below salvage value."""
        dep = DepreciationCalculator.declining_balance(1000.0, 900.0, 4, 1)
        assert dep == 100.0  # Limited to 1000 - 900

    def test_declining_balance_invalid_year(self):
        """Declining balance with invalid year returns 0."""
        dep = DepreciationCalculator.declining_balance(1000.0, 200.0, 4, 5)
        assert dep == 0.0

    def test_sum_of_years_digits_year1(self):
        """Sum-of-years-digits first year is calculated correctly."""
        dep = DepreciationCalculator.sum_of_years_digits(1000.0, 200.0, 4, 1)
        assert dep == 320.0  # (1000-200) * 4/10

    def test_sum_of_years_digits_year2(self):
        """Sum-of-years-digits second year is calculated correctly."""
        dep = DepreciationCalculator.sum_of_years_digits(1000.0, 200.0, 4, 2)
        assert dep == 240.0  # (1000-200) * 3/10

    def test_sum_of_years_digits_last_year(self):
        """Sum-of-years-digits last year is calculated correctly."""
        dep = DepreciationCalculator.sum_of_years_digits(1000.0, 200.0, 4, 4)
        assert dep == 80.0  # (1000-200) * 1/10

    def test_sum_of_years_digits_invalid_year(self):
        """Sum-of-years-digits with invalid year returns 0."""
        dep = DepreciationCalculator.sum_of_years_digits(1000.0, 200.0, 4, 5)
        assert dep == 0.0

    def test_units_of_production(self):
        """Units-of-production depreciation is calculated correctly."""
        dep = DepreciationCalculator.units_of_production(1000.0, 200.0, 10000.0, 500.0)
        assert dep == 40.0  # (1000-200)/10000 * 500

    def test_units_of_production_zero_total(self):
        """Units-of-production with zero total units returns 0."""
        dep = DepreciationCalculator.units_of_production(1000.0, 200.0, 0.0, 500.0)
        assert dep == 0.0

    def test_calculate_schedule_straight_line(self):
        """Full depreciation schedule for straight-line method."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        schedule = DepreciationCalculator.calculate_schedule(asset)
        assert len(schedule) == 4
        assert schedule[0].depreciation_amount == 200.0
        assert schedule[0].accumulated_depreciation == 200.0
        assert schedule[0].book_value == 800.0
        assert schedule[3].book_value == 200.0  # salvage value

    def test_calculate_schedule_declining_balance(self):
        """Full depreciation schedule for declining balance method."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=100.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.DECLINING_BALANCE,
        )
        schedule = DepreciationCalculator.calculate_schedule(asset)
        assert len(schedule) == 4
        assert schedule[0].depreciation_amount == 500.0
        assert schedule[0].book_value == 500.0
        # Final book value should not go below salvage
        assert schedule[-1].book_value >= 100.0

    def test_calculate_schedule_sum_of_years(self):
        """Full depreciation schedule for sum-of-years-digits method."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.SUM_OF_YEARS_DIGITS,
        )
        schedule = DepreciationCalculator.calculate_schedule(asset)
        assert len(schedule) == 4
        assert schedule[0].depreciation_amount == 320.0
        assert schedule[1].depreciation_amount == 240.0
        assert schedule[2].depreciation_amount == 160.0
        assert schedule[3].depreciation_amount == 80.0
        assert schedule[-1].book_value == 200.0

    def test_calculate_schedule_units_of_production(self):
        """Full depreciation schedule for units-of-production method."""
        asset = Asset(
            id="asset-1",
            name="Machine",
            category=AssetCategory.MACHINERY,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.UNITS_OF_PRODUCTION,
        )
        schedule = DepreciationCalculator.calculate_schedule(asset, total_units=10000.0)
        assert len(schedule) == 4
        # Each year: (1000-200)/10000 * 2500 = 200
        assert schedule[0].depreciation_amount == 200.0

    def test_calculate_schedule_units_of_production_requires_total(self):
        """Units-of-production schedule requires total_units."""
        asset = Asset(
            id="asset-1",
            name="Machine",
            category=AssetCategory.MACHINERY,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.UNITS_OF_PRODUCTION,
        )
        with pytest.raises(ValueError, match="total_units required"):
            DepreciationCalculator.calculate_schedule(asset)

    def test_get_book_value(self):
        """Book value can be calculated as of a date."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        # After 2 years: 1000 - 2*200 = 600
        book_value = DepreciationCalculator.get_book_value(asset, date(2026, 1, 1))
        assert book_value == 600.0

    def test_get_book_value_before_purchase(self):
        """Book value before purchase date is purchase cost."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        book_value = DepreciationCalculator.get_book_value(asset, date(2023, 1, 1))
        assert book_value == 1000.0

    def test_get_accumulated_depreciation(self):
        """Accumulated depreciation can be calculated as of a date."""
        asset = Asset(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        # After 2 years: 2 * 200 = 400
        accumulated = DepreciationCalculator.get_accumulated_depreciation(asset, date(2026, 1, 1))
        assert accumulated == 400.0


# =============================================================================
# Test Maintenance Scheduler
# =============================================================================

class TestMaintenanceScheduler:
    """Test maintenance scheduling functionality."""

    def test_schedule_maintenance(self):
        """Maintenance can be scheduled."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
            description="Annual checkup",
            technician="Tech Bob",
            cost=150.0,
        )
        assert record.id is not None
        assert record.asset_id == "asset-1"
        assert record.status == MaintenanceStatus.SCHEDULED
        assert record.scheduled_date == date(2024, 6, 1)

    def test_start_maintenance(self):
        """Maintenance can be started."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        started = scheduler.start_maintenance(record.id)
        assert started.status == MaintenanceStatus.IN_PROGRESS

    def test_start_nonexistent_maintenance_raises(self):
        """Starting nonexistent maintenance raises ValueError."""
        scheduler = MaintenanceScheduler()
        with pytest.raises(ValueError, match="Maintenance record not found"):
            scheduler.start_maintenance("nonexistent")

    def test_start_already_started_raises(self):
        """Starting already started maintenance raises ValueError."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.start_maintenance(record.id)
        with pytest.raises(ValueError, match="Cannot start maintenance"):
            scheduler.start_maintenance(record.id)

    def test_complete_maintenance(self):
        """Maintenance can be completed."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.start_maintenance(record.id)
        completed = scheduler.complete_maintenance(record.id, notes="All good")
        assert completed.status == MaintenanceStatus.COMPLETED
        assert completed.completed_date is not None
        assert completed.notes == "All good"

    def test_complete_nonexistent_maintenance_raises(self):
        """Completing nonexistent maintenance raises ValueError."""
        scheduler = MaintenanceScheduler()
        with pytest.raises(ValueError, match="Maintenance record not found"):
            scheduler.complete_maintenance("nonexistent")

    def test_complete_without_start_raises(self):
        """Completing maintenance without starting raises ValueError."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        with pytest.raises(ValueError, match="Cannot complete maintenance"):
            scheduler.complete_maintenance(record.id)

    def test_cancel_maintenance(self):
        """Maintenance can be cancelled."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        cancelled = scheduler.cancel_maintenance(record.id, reason="No longer needed")
        assert cancelled.status == MaintenanceStatus.CANCELLED
        assert cancelled.notes == "No longer needed"

    def test_cancel_nonexistent_maintenance_raises(self):
        """Cancelling nonexistent maintenance raises ValueError."""
        scheduler = MaintenanceScheduler()
        with pytest.raises(ValueError, match="Maintenance record not found"):
            scheduler.cancel_maintenance("nonexistent")

    def test_cancel_completed_raises(self):
        """Cancelling completed maintenance raises ValueError."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.start_maintenance(record.id)
        scheduler.complete_maintenance(record.id)
        with pytest.raises(ValueError, match="Cannot cancel maintenance"):
            scheduler.cancel_maintenance(record.id)

    def test_get_record(self):
        """Maintenance record can be retrieved."""
        scheduler = MaintenanceScheduler()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        retrieved = scheduler.get_record(record.id)
        assert retrieved is not None
        assert retrieved.id == record.id

    def test_get_nonexistent_record(self):
        """Getting nonexistent record returns None."""
        scheduler = MaintenanceScheduler()
        assert scheduler.get_record("nonexistent") is None

    def test_get_records_for_asset(self):
        """Maintenance records can be filtered by asset."""
        scheduler = MaintenanceScheduler()
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.CORRECTIVE,
            scheduled_date=date(2024, 7, 1),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-2",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 15),
        )
        records = scheduler.get_records_for_asset("asset-1")
        assert len(records) == 2

    def test_get_upcoming_maintenance(self):
        """Upcoming maintenance can be retrieved."""
        scheduler = MaintenanceScheduler()
        today = date.today()
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=today + timedelta(days=10),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-2",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=today + timedelta(days=60),
        )
        upcoming = scheduler.get_upcoming_maintenance(days=30)
        assert len(upcoming) == 1
        assert upcoming[0].asset_id == "asset-1"

    def test_get_overdue_maintenance(self):
        """Overdue maintenance can be retrieved."""
        scheduler = MaintenanceScheduler()
        today = date.today()
        record = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=today - timedelta(days=5),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-2",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=today + timedelta(days=5),
        )
        overdue = scheduler.get_overdue_maintenance()
        assert len(overdue) == 1
        assert overdue[0].status == MaintenanceStatus.OVERDUE

    def test_get_maintenance_cost(self):
        """Total maintenance cost can be calculated."""
        scheduler = MaintenanceScheduler()
        record1 = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
            cost=100.0,
        )
        record2 = scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.CORRECTIVE,
            scheduled_date=date(2024, 7, 1),
            cost=200.0,
        )
        scheduler.schedule_maintenance(
            asset_id="asset-2",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 15),
            cost=50.0,
        )
        # Complete two records for asset-1
        scheduler.start_maintenance(record1.id)
        scheduler.complete_maintenance(record1.id)
        scheduler.start_maintenance(record2.id)
        scheduler.complete_maintenance(record2.id)
        assert scheduler.get_maintenance_cost("asset-1") == 300.0

    def test_get_maintenance_history(self):
        """Maintenance history can be retrieved."""
        scheduler = MaintenanceScheduler()
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.CORRECTIVE,
            scheduled_date=date(2024, 7, 1),
        )
        history = scheduler.get_maintenance_history("asset-1")
        assert len(history) == 2
        # Most recent first
        assert history[0].scheduled_date == date(2024, 7, 1)

    def test_get_maintenance_history_filtered(self):
        """Maintenance history can be filtered by type."""
        scheduler = MaintenanceScheduler()
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
        )
        scheduler.schedule_maintenance(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.CORRECTIVE,
            scheduled_date=date(2024, 7, 1),
        )
        preventive = scheduler.get_maintenance_history(
            "asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
        )
        assert len(preventive) == 1
        assert preventive[0].maintenance_type == MaintenanceType.PREVENTIVE

    def test_schedule_recurring(self):
        """Recurring maintenance can be scheduled."""
        scheduler = MaintenanceScheduler()
        records = scheduler.schedule_recurring(
            asset_id="asset-1",
            maintenance_type=MaintenanceType.PREVENTIVE,
            first_date=date(2024, 1, 1),
            interval_days=90,
            occurrences=4,
            description="Quarterly checkup",
        )
        assert len(records) == 4
        assert records[0].scheduled_date == date(2024, 1, 1)
        assert records[1].scheduled_date == date(2024, 3, 31)
        assert records[3].scheduled_date == date(2024, 9, 27)


# =============================================================================
# Test Asset Valuator
# =============================================================================

class TestAssetValuator:
    """Test asset valuation functionality."""

    def test_record_valuation(self):
        """Valuation can be recorded."""
        valuator = AssetValuator()
        record = valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
            appraiser="Appraiser Inc.",
        )
        assert record.id is not None
        assert record.asset_id == "asset-1"
        assert record.market_value == 800.0
        assert record.book_value == 600.0
        assert record.valuation_method == "market_comparison"

    def test_get_valuation(self):
        """Valuation can be retrieved by ID."""
        valuator = AssetValuator()
        record = valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
        )
        retrieved = valuator.get_valuation(record.id)
        assert retrieved is not None
        assert retrieved.id == record.id

    def test_get_nonexistent_valuation(self):
        """Getting nonexistent valuation returns None."""
        valuator = AssetValuator()
        assert valuator.get_valuation("nonexistent") is None

    def test_get_valuations_for_asset(self):
        """Valuations can be filtered by asset."""
        valuator = AssetValuator()
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
        )
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=750.0,
            book_value=550.0,
            valuation_method="market_comparison",
        )
        valuator.record_valuation(
            asset_id="asset-2",
            market_value=500.0,
            book_value=400.0,
            valuation_method="cost_approach",
        )
        valuations = valuator.get_valuations_for_asset("asset-1")
        assert len(valuations) == 2

    def test_get_latest_valuation(self):
        """Latest valuation can be retrieved."""
        valuator = AssetValuator()
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
            valuation_date=date(2024, 1, 1),
        )
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=750.0,
            book_value=550.0,
            valuation_method="market_comparison",
            valuation_date=date(2024, 6, 1),
        )
        latest = valuator.get_latest_valuation("asset-1")
        assert latest is not None
        assert latest.market_value == 750.0

    def test_get_latest_valuation_none(self):
        """Latest valuation returns None when no valuations exist."""
        valuator = AssetValuator()
        assert valuator.get_latest_valuation("nonexistent") is None

    def test_get_valuation_history(self):
        """Valuation history can be retrieved sorted by date."""
        valuator = AssetValuator()
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=750.0,
            book_value=550.0,
            valuation_method="market_comparison",
            valuation_date=date(2024, 6, 1),
        )
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
            valuation_date=date(2024, 1, 1),
        )
        history = valuator.get_valuation_history("asset-1")
        assert len(history) == 2
        assert history[0].valuation_date == date(2024, 1, 1)
        assert history[1].valuation_date == date(2024, 6, 1)

    def test_calculate_impairment(self):
        """Impairment loss can be calculated."""
        loss = AssetValuator.calculate_impairment(None, recoverable_amount=400.0, book_value=600.0)
        assert loss == 200.0

    def test_calculate_no_impairment(self):
        """No impairment when recoverable amount exceeds book value."""
        loss = AssetValuator.calculate_impairment(None, recoverable_amount=700.0, book_value=600.0)
        assert loss == 0.0

    def test_get_net_realizable_value(self):
        """Net realizable value can be calculated."""
        nrv = AssetValuator.get_net_realizable_value(None, estimated_selling_price=1000.0, selling_costs=100.0)
        assert nrv == 900.0

    def test_get_replacement_cost(self):
        """Replacement cost can be calculated."""
        rc = AssetValuator.get_replacement_cost(1000.0, inflation_rate=0.03, years=5)
        assert rc == pytest.approx(1159.27, rel=0.01)

    def test_get_depreciated_replacement_cost(self):
        """Depreciated replacement cost can be calculated."""
        drc = AssetValuator.get_depreciated_replacement_cost(
            replacement_cost=1000.0,
            age_years=2,
            useful_life_years=10,
        )
        assert drc == 800.0

    def test_get_total_valuation(self):
        """Total valuation for multiple assets can be calculated."""
        valuator = AssetValuator()
        valuator.record_valuation(
            asset_id="asset-1",
            market_value=800.0,
            book_value=600.0,
            valuation_method="market_comparison",
        )
        valuator.record_valuation(
            asset_id="asset-2",
            market_value=500.0,
            book_value=400.0,
            valuation_method="cost_approach",
        )
        total = valuator.get_total_valuation(["asset-1", "asset-2"])
        assert total["asset-1"] == 800.0
        assert total["asset-2"] == 500.0


# =============================================================================
# Test Asset Disposal
# =============================================================================

class TestAssetDisposal:
    """Test asset disposal functionality."""

    def _make_asset(self, **kwargs):
        """Helper to create a test asset."""
        defaults = dict(
            id="asset-1",
            name="Laptop",
            category=AssetCategory.ELECTRONICS,
            status=AssetStatus.ACTIVE,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1000.0,
            salvage_value=200.0,
            useful_life_years=4,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        defaults.update(kwargs)
        return Asset(**defaults)

    def test_dispose_asset(self):
        """Asset can be disposed."""
        disposal = AssetDisposal()
        asset = self._make_asset()
        record = disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
            buyer="Buyer Corp",
            reason="End of life",
        )
        assert record.id is not None
        assert record.asset_id == "asset-1"
        assert record.disposal_method == DisposalMethod.SALE
        assert record.proceeds == 500.0
        assert record.book_value_at_disposal == 600.0
        assert record.gain_loss == -100.0  # Loss
        assert asset.status == AssetStatus.DISPOSED

    def test_dispose_already_disposed_raises(self):
        """Disposing already disposed asset raises ValueError."""
        disposal = AssetDisposal()
        asset = self._make_asset()
        disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        with pytest.raises(ValueError, match="already disposed"):
            disposal.dispose_asset(
                asset=asset,
                disposal_method=DisposalMethod.SCRAP,
                proceeds=0.0,
                book_value_at_disposal=600.0,
            )

    def test_get_disposal(self):
        """Disposal record can be retrieved."""
        disposal = AssetDisposal()
        asset = self._make_asset()
        record = disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        retrieved = disposal.get_disposal(record.id)
        assert retrieved is not None
        assert retrieved.id == record.id

    def test_get_nonexistent_disposal(self):
        """Getting nonexistent disposal returns None."""
        disposal = AssetDisposal()
        assert disposal.get_disposal("nonexistent") is None

    def test_get_disposals_for_asset(self):
        """Disposals can be filtered by asset."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SCRAP,
            proceeds=0.0,
            book_value_at_disposal=400.0,
        )
        disposals = disposal.get_disposals_for_asset("asset-1")
        assert len(disposals) == 1

    def test_get_disposal_history(self):
        """Disposal history can be retrieved."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
            disposal_date=date(2024, 6, 1),
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SCRAP,
            proceeds=0.0,
            book_value_at_disposal=400.0,
            disposal_date=date(2024, 3, 1),
        )
        history = disposal.get_disposal_history()
        assert len(history) == 2
        # Most recent first
        assert history[0].disposal_date == date(2024, 6, 1)

    def test_get_disposal_history_date_range(self):
        """Disposal history can be filtered by date range."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
            disposal_date=date(2024, 6, 1),
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SCRAP,
            proceeds=0.0,
            book_value_at_disposal=400.0,
            disposal_date=date(2024, 3, 1),
        )
        history = disposal.get_disposal_history(
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
        )
        assert len(history) == 1
        assert history[0].asset_id == "asset-1"

    def test_get_total_proceeds(self):
        """Total disposal proceeds can be calculated."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SALE,
            proceeds=300.0,
            book_value_at_disposal=400.0,
        )
        assert disposal.get_total_proceeds() == 800.0

    def test_get_total_gain_loss(self):
        """Total gain/loss can be calculated."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,  # -100 loss
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=400.0,  # +100 gain
        )
        assert disposal.get_total_gain_loss() == 0.0

    def test_get_disposals_by_method(self):
        """Disposals can be grouped by method."""
        disposal = AssetDisposal()
        asset1 = self._make_asset(id="asset-1")
        asset2 = self._make_asset(id="asset-2")
        asset3 = self._make_asset(id="asset-3")
        disposal.dispose_asset(
            asset=asset1,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        disposal.dispose_asset(
            asset=asset2,
            disposal_method=DisposalMethod.SALE,
            proceeds=300.0,
            book_value_at_disposal=400.0,
        )
        disposal.dispose_asset(
            asset=asset3,
            disposal_method=DisposalMethod.SCRAP,
            proceeds=0.0,
            book_value_at_disposal=200.0,
        )
        by_method = disposal.get_disposals_by_method()
        assert len(by_method[DisposalMethod.SALE]) == 2
        assert len(by_method[DisposalMethod.SCRAP]) == 1

    def test_calculate_gain_loss(self):
        """Gain/loss can be calculated."""
        gain = AssetDisposal.calculate_gain_loss(proceeds=700.0, book_value=600.0)
        assert gain == 100.0
        loss = AssetDisposal.calculate_gain_loss(proceeds=500.0, book_value=600.0)
        assert loss == -100.0

    def test_is_profitable_disposal(self):
        """Profitable disposal can be identified."""
        disposal = AssetDisposal()
        asset = self._make_asset()
        record = disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=700.0,
            book_value_at_disposal=600.0,
        )
        assert disposal.is_profitable_disposal(record) is True

    def test_is_not_profitable_disposal(self):
        """Non-profitable disposal can be identified."""
        disposal = AssetDisposal()
        asset = self._make_asset()
        record = disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=600.0,
        )
        assert disposal.is_profitable_disposal(record) is False


# =============================================================================
# Integration Tests
# =============================================================================

class TestAssetManagementIntegration:
    """Integration tests for the full asset management lifecycle."""

    def test_full_asset_lifecycle(self):
        """Test complete asset lifecycle from registration to disposal."""
        tracker = AssetTracker()
        scheduler = MaintenanceScheduler()
        valuator = AssetValuator()
        disposal = AssetDisposal()

        # 1. Register asset
        asset = tracker.register_asset(
            name="Company Laptop",
            category=AssetCategory.ELECTRONICS,
            purchase_date=date(2024, 1, 1),
            purchase_cost=1200.0,
            salvage_value=200.0,
            useful_life_years=3,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
            location="Office A",
            assigned_to="John Doe",
        )
        assert asset.status == AssetStatus.ACTIVE
        assert tracker.get_asset_count() == 1

        # 2. Schedule maintenance
        maint = scheduler.schedule_maintenance(
            asset_id=asset.id,
            maintenance_type=MaintenanceType.PREVENTIVE,
            scheduled_date=date(2024, 6, 1),
            description="Annual checkup",
            cost=100.0,
        )
        assert maint.status == MaintenanceStatus.SCHEDULED

        # 3. Complete maintenance
        scheduler.start_maintenance(maint.id)
        scheduler.complete_maintenance(maint.id)
        assert scheduler.get_record(maint.id).status == MaintenanceStatus.COMPLETED

        # 4. Record valuation
        valuation = valuator.record_valuation(
            asset_id=asset.id,
            market_value=800.0,
            book_value=800.0,
            valuation_method="market_comparison",
        )
        assert valuation.market_value == 800.0

        # 5. Dispose asset
        disposal_record = disposal.dispose_asset(
            asset=asset,
            disposal_method=DisposalMethod.SALE,
            proceeds=500.0,
            book_value_at_disposal=800.0,
            buyer="Employee",
        )
        assert disposal_record.gain_loss == -300.0
        assert asset.status == AssetStatus.DISPOSED

        # 6. Verify tracker reflects disposal
        disposed_assets = tracker.get_assets_by_status(AssetStatus.DISPOSED)
        assert len(disposed_assets) == 1

    def test_depreciation_affects_book_value(self):
        """Depreciation correctly reduces book value over time."""
        tracker = AssetTracker()
        asset = tracker.register_asset(
            name="Vehicle",
            category=AssetCategory.VEHICLE,
            purchase_date=date(2020, 1, 1),
            purchase_cost=20000.0,
            salvage_value=2000.0,
            useful_life_years=5,
            depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        )
        # After 2 years: 20000 - 2*3600 = 12800
        book_value = tracker.get_total_book_value()
        assert book_value < 20000.0

    def test_multiple_assets_tracking(self):
        """Multiple assets can be tracked simultaneously."""
        tracker = AssetTracker()
        for i in range(5):
            tracker.register_asset(
                name=f"Asset {i}",
                category=AssetCategory.ELECTRONICS,
                purchase_date=date(2024, 1, 1),
                purchase_cost=1000.0 * (i + 1),
            )
        assert tracker.get_asset_count() == 5
        assert tracker.get_total_asset_value() == 15000.0
