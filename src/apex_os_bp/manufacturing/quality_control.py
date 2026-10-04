"""Quality Control module."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class QualityError(Exception):
    """Quality control error."""


class InspectionResult(Enum):
    """Result of a quality inspection."""
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class DefectSeverity(Enum):
    """Severity of a quality defect."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class Disposition(Enum):
    """Disposition for non-conforming material."""
    REWORK = "rework"
    SCRAP = "scrap"
    USE_AS_IS = "use_as_is"
    RETURN_TO_VENDOR = "return_to_vendor"
    PENDING = "pending"


@dataclass
class Measurement:
    """A single measurement in an inspection."""
    parameter: str
    nominal_value: float
    actual_value: float
    tolerance_min: float
    tolerance_max: float
    unit: str = ""

    def is_within_tolerance(self) -> bool:
        """Check if measurement is within tolerance."""
        return self.tolerance_min <= self.actual_value <= self.tolerance_max

    def deviation(self) -> float:
        """Calculate deviation from nominal."""
        return self.actual_value - self.nominal_value


@dataclass
class Inspection:
    """A quality inspection record."""
    product_id: str
    batch_id: str
    inspector: str
    result: InspectionResult = InspectionResult.PASS
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    measurements: List[Measurement] = field(default_factory=list)
    sample_size: int = 0
    defects_found: int = 0
    notes: str = ""
    inspection_date: datetime = field(default_factory=datetime.now)
    production_order_id: str = ""

    def add_measurement(self, measurement: Measurement) -> None:
        """Add a measurement to the inspection."""
        self.measurements.append(measurement)
        if not measurement.is_within_tolerance():
            self.defects_found += 1

    def first_pass_yield(self) -> float:
        """Calculate first pass yield percentage."""
        if self.sample_size == 0:
            return 0.0
        good_units = self.sample_size - self.defects_found
        return (good_units / self.sample_size) * 100.0

    def defect_rate(self) -> float:
        """Calculate defect rate (DPPM)."""
        if self.sample_size == 0:
            return 0.0
        return (self.defects_found / self.sample_size) * 1_000_000.0


@dataclass
class NonConformance:
    """A non-conformance record."""
    product_id: str
    description: str
    severity: DefectSeverity
    disposition: Disposition = Disposition.PENDING
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str = ""
    quantity_affected: float = 0.0
    reported_by: str = ""
    reported_date: datetime = field(default_factory=datetime.now)
    root_cause: str = ""
    corrective_action: str = ""
    closed_date: Optional[datetime] = None
    inspection_id: str = ""

    def set_disposition(self, disposition: Disposition) -> None:
        """Set the disposition for this non-conformance."""
        self.disposition = disposition

    def close(self, corrective_action: str) -> None:
        """Close the non-conformance with corrective action."""
        self.corrective_action = corrective_action
        self.closed_date = datetime.now()

    def is_closed(self) -> bool:
        """Check if non-conformance is closed."""
        return self.closed_date is not None


class QualityControl:
    """Engine for quality control operations."""

    def __init__(self):
        self._inspections: Dict[str, Inspection] = {}
        self._non_conformances: Dict[str, NonConformance] = {}

    def create_inspection(
        self,
        product_id: str,
        batch_id: str,
        inspector: str,
        sample_size: int = 1,
        production_order_id: str = "",
    ) -> Inspection:
        """Create a new inspection."""
        inspection = Inspection(
            product_id=product_id,
            batch_id=batch_id,
            inspector=inspector,
            sample_size=sample_size,
            production_order_id=production_order_id,
        )
        self._inspections[inspection.id] = inspection
        return inspection

    def get_inspection(self, inspection_id: str) -> Optional[Inspection]:
        """Get an inspection by ID."""
        return self._inspections.get(inspection_id)

    def record_result(self, inspection_id: str, result: InspectionResult) -> None:
        """Record the final result of an inspection."""
        inspection = self._inspections.get(inspection_id)
        if not inspection:
            raise QualityError(f"Inspection not found: {inspection_id}")
        inspection.result = result

    def create_non_conformance(
        self,
        product_id: str,
        description: str,
        severity: DefectSeverity,
        batch_id: str = "",
        quantity_affected: float = 0.0,
        reported_by: str = "",
        inspection_id: str = "",
    ) -> NonConformance:
        """Create a non-conformance record."""
        nc = NonConformance(
            product_id=product_id,
            description=description,
            severity=severity,
            batch_id=batch_id,
            quantity_affected=quantity_affected,
            reported_by=reported_by,
            inspection_id=inspection_id,
        )
        self._non_conformances[nc.id] = nc
        return nc

    def get_non_conformance(self, nc_id: str) -> Optional[NonConformance]:
        """Get a non-conformance by ID."""
        return self._non_conformances.get(nc_id)

    def get_inspections_by_product(self, product_id: str) -> List[Inspection]:
        """Get all inspections for a product."""
        return [i for i in self._inspections.values() if i.product_id == product_id]

    def get_open_non_conformances(self) -> List[NonConformance]:
        """Get all open non-conformances."""
        return [nc for nc in self._non_conformances.values() if not nc.is_closed()]

    def get_non_conformances_by_severity(self, severity: DefectSeverity) -> List[NonConformance]:
        """Get non-conformances by severity."""
        return [nc for nc in self._non_conformances.values() if nc.severity == severity]

    def overall_quality_score(self, product_id: str) -> float:
        """Calculate overall quality score for a product (0-100)."""
        inspections = self.get_inspections_by_product(product_id)
        if not inspections:
            return 100.0

        total_fpy = sum(i.first_pass_yield() for i in inspections)
        return total_fpy / len(inspections)

    def list_inspections(self) -> List[Inspection]:
        """List all inspections."""
        return list(self._inspections.values())

    def list_non_conformances(self) -> List[NonConformance]:
        """List all non-conformances."""
        return list(self._non_conformances.values())
