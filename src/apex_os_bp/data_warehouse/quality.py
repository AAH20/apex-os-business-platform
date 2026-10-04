"""Data quality module for data warehouse.

Provides quality rules, validation engine, and quality reporting
for ensuring data integrity and reliability.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Types of data quality rules."""

    COMPLETENESS = "completeness"
    UNIQUENESS = "uniqueness"
    VALIDITY = "validity"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    INTEGRITY = "integrity"
    ACCURACY = "accuracy"
    CUSTOM = "custom"


@dataclass
class QualityRule:
    """Represents a data quality rule."""

    name: str
    rule_type: RuleType
    column: Optional[str] = None
    table: Optional[str] = None
    description: str = ""
    severity: str = "error"  # error, warning, info
    validator: Optional[Callable[[Any], bool]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, value: Any) -> bool:
        """Evaluate the rule against a value."""
        if not self.enabled:
            return True
        if self.validator:
            return self.validator(value)
        return True

    def evaluate_batch(self, values: List[Any]) -> Tuple[int, int]:
        """Evaluate the rule against a batch of values. Returns (passed, failed)."""
        passed = 0
        failed = 0
        for value in values:
            if self.evaluate(value):
                passed += 1
            else:
                failed += 1
        return passed, failed


@dataclass
class QualityCheckResult:
    """Result of a quality check."""

    rule_name: str
    rule_type: RuleType
    passed: bool
    total_records: int
    passed_records: int
    failed_records: int
    severity: str
    details: List[str] = field(default_factory=list)
    column: Optional[str] = None
    table: Optional[str] = None

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_records == 0:
            return 100.0
        return (self.passed_records / self.total_records) * 100.0

    @property
    def failed(self) -> bool:
        """Check if the quality check failed."""
        return not self.passed


@dataclass
class QualityReport:
    """Aggregated quality report for a dataset."""

    dataset_name: str
    timestamp: str = ""
    results: List[QualityCheckResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_checks(self) -> int:
        """Total number of checks performed."""
        return len(self.results)

    @property
    def passed_checks(self) -> int:
        """Number of checks that passed."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_checks(self) -> int:
        """Number of checks that failed."""
        return sum(1 for r in self.results if not r.passed)

    @property
    def overall_pass_rate(self) -> float:
        """Overall pass rate across all checks."""
        if not self.results:
            return 100.0
        return (self.passed_checks / self.total_checks) * 100.0

    @property
    def is_healthy(self) -> bool:
        """Check if all error-severity checks passed."""
        return all(r.passed for r in self.results if r.severity == "error")

    def get_failures(self) -> List[QualityCheckResult]:
        """Get all failed checks."""
        return [r for r in self.results if not r.passed]

    def get_by_type(self, rule_type: RuleType) -> List[QualityCheckResult]:
        """Get results filtered by rule type."""
        return [r for r in self.results if r.rule_type == rule_type]

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "timestamp": self.timestamp,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "overall_pass_rate": self.overall_pass_rate,
            "is_healthy": self.is_healthy,
            "results": [
                {
                    "rule_name": r.rule_name,
                    "rule_type": r.rule_type.value,
                    "passed": r.passed,
                    "total_records": r.total_records,
                    "passed_records": r.passed_records,
                    "failed_records": r.failed_records,
                    "pass_rate": r.pass_rate,
                    "severity": r.severity,
                    "column": r.column,
                    "table": r.table,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


class DataQualityEngine:
    """Engine for executing data quality checks."""

    def __init__(self):
        self._rules: List[QualityRule] = []
        self._custom_validators: Dict[str, Callable] = {}

    def add_rule(self, rule: QualityRule) -> None:
        """Add a quality rule."""
        self._rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a quality rule by name."""
        for i, rule in enumerate(self._rules):
            if rule.name == name:
                self._rules.pop(i)
                return True
        return False

    def register_validator(self, name: str, validator: Callable[[Any], bool]) -> None:
        """Register a custom validator function."""
        self._custom_validators[name] = validator

    def check_completeness(
        self,
        data: List[Dict[str, Any]],
        column: str,
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check for null/empty values in a column."""
        total = len(data)
        passed = sum(1 for row in data if row.get(column) is not None and row.get(column) != "")
        failed = total - passed
        return QualityCheckResult(
            rule_name=rule_name or f"completeness_{column}",
            rule_type=RuleType.COMPLETENESS,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} null/empty values in '{column}'"] if failed > 0 else [],
        )

    def check_uniqueness(
        self,
        data: List[Dict[str, Any]],
        column: str,
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check for duplicate values in a column."""
        total = len(data)
        values = [row.get(column) for row in data if row.get(column) is not None]
        unique_values = set(values)
        passed = len(unique_values)
        failed = total - passed
        return QualityCheckResult(
            rule_name=rule_name or f"uniqueness_{column}",
            rule_type=RuleType.UNIQUENESS,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} duplicate values in '{column}'"] if failed > 0 else [],
        )

    def check_validity(
        self,
        data: List[Dict[str, Any]],
        column: str,
        validator: Callable[[Any], bool],
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check values against a validity function."""
        total = len(data)
        passed = 0
        failed = 0
        for row in data:
            value = row.get(column)
            if value is None:
                continue
            if validator(value):
                passed += 1
            else:
                failed += 1
        return QualityCheckResult(
            rule_name=rule_name or f"validity_{column}",
            rule_type=RuleType.VALIDITY,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} invalid values in '{column}'"] if failed > 0 else [],
        )

    def check_range(
        self,
        data: List[Dict[str, Any]],
        column: str,
        min_val: Optional[Any] = None,
        max_val: Optional[Any] = None,
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check numeric values are within a range."""
        total = len(data)
        passed = 0
        failed = 0
        for row in data:
            value = row.get(column)
            if value is None:
                continue
            try:
                if min_val is not None and value < min_val:
                    failed += 1
                elif max_val is not None and value > max_val:
                    failed += 1
                else:
                    passed += 1
            except TypeError:
                failed += 1
        return QualityCheckResult(
            rule_name=rule_name or f"range_{column}",
            rule_type=RuleType.VALIDITY,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} out-of-range values in '{column}'"] if failed > 0 else [],
        )

    def check_pattern(
        self,
        data: List[Dict[str, Any]],
        column: str,
        pattern: str,
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check string values match a regex pattern."""
        total = len(data)
        passed = 0
        failed = 0
        compiled = re.compile(pattern)
        for row in data:
            value = row.get(column)
            if value is None:
                continue
            if compiled.match(str(value)):
                passed += 1
            else:
                failed += 1
        return QualityCheckResult(
            rule_name=rule_name or f"pattern_{column}",
            rule_type=RuleType.VALIDITY,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} values not matching pattern in '{column}'"] if failed > 0 else [],
        )

    def check_referential_integrity(
        self,
        data: List[Dict[str, Any]],
        column: str,
        reference_set: Set[Any],
        rule_name: Optional[str] = None
    ) -> QualityCheckResult:
        """Check foreign key values exist in reference set."""
        total = len(data)
        passed = 0
        failed = 0
        for row in data:
            value = row.get(column)
            if value is None:
                continue
            if value in reference_set:
                passed += 1
            else:
                failed += 1
        return QualityCheckResult(
            rule_name=rule_name or f"referential_integrity_{column}",
            rule_type=RuleType.INTEGRITY,
            passed=failed == 0,
            total_records=total,
            passed_records=passed,
            failed_records=failed,
            severity="error",
            column=column,
            details=[f"Found {failed} orphaned references in '{column}'"] if failed > 0 else [],
        )

    def run_rules(self, data: List[Dict[str, Any]], dataset_name: str = "dataset") -> QualityReport:
        """Run all registered rules against the data."""
        from datetime import datetime, timezone

        results: List[QualityCheckResult] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if rule.column is None:
                continue
            values = [row.get(rule.column) for row in data]
            passed, failed = rule.evaluate_batch(values)
            results.append(QualityCheckResult(
                rule_name=rule.name,
                rule_type=rule.rule_type,
                passed=failed == 0,
                total_records=len(data),
                passed_records=passed,
                failed_records=failed,
                severity=rule.severity,
                column=rule.column,
                details=[f"Found {failed} violations"] if failed > 0 else [],
            ))
        return QualityReport(
            dataset_name=dataset_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results,
        )

    def run_all_checks(
        self,
        data: List[Dict[str, Any]],
        columns: List[str],
        dataset_name: str = "dataset"
    ) -> QualityReport:
        """Run all standard checks on specified columns."""
        from datetime import datetime, timezone

        results: List[QualityCheckResult] = []
        for col in columns:
            results.append(self.check_completeness(data, col))
            results.append(self.check_uniqueness(data, col))
        return QualityReport(
            dataset_name=dataset_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=results,
        )
