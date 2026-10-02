"""A/B testing engine with statistical significance."""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from apex_os_bp.marketing.models import (
    ABTest,
    ABVariant,
    TestStatus,
)


class ABTestingEngine:
    """A/B testing with variant management and statistical analysis."""

    def __init__(self):
        self._tests: Dict[str, ABTest] = {}

    def create_test(
        self,
        name: str,
        confidence_level: float = 0.95,
        metadata: Optional[Dict] = None,
    ) -> ABTest:
        """Create a new A/B test."""
        test = ABTest(
            id=str(uuid.uuid4()),
            name=name,
            confidence_level=confidence_level,
            metadata=metadata or {},
        )
        self._tests[test.id] = test
        return test

    def add_variant(
        self,
        test_id: str,
        name: str,
        subject: str,
        body: str,
        traffic_allocation: float = 0.5,
    ) -> ABVariant:
        """Add a variant to an A/B test."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        if test.status != TestStatus.DRAFT:
            raise ValueError(f"Cannot add variants to a {test.status.value} test")

        variant = ABVariant(
            id=str(uuid.uuid4()),
            test_id=test_id,
            name=name,
            subject=subject,
            body=body,
            traffic_allocation=traffic_allocation,
        )
        test.variants.append(variant)
        return variant

    def start_test(self, test_id: str) -> None:
        """Start an A/B test."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        if len(test.variants) < 2:
            raise ValueError("Test must have at least 2 variants")
        test.status = TestStatus.RUNNING
        test.start_date = datetime.now()

    def stop_test(self, test_id: str) -> None:
        """Stop an A/B test."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        test.status = TestStatus.COMPLETED
        test.end_date = datetime.now()

    def track_event(self, test_id: str, variant_id: str, event_type: str) -> None:
        """Track an event for a specific variant."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        variant = None
        for v in test.variants:
            if v.id == variant_id:
                variant = v
                break
        if not variant:
            raise ValueError(f"Variant not found: {variant_id}")

        metrics = variant.metrics
        if event_type == "open":
            metrics.opened += 1
        elif event_type == "click":
            metrics.clicked += 1
        elif event_type == "conversion":
            metrics.converted += 1
        elif event_type == "bounce":
            metrics.bounced += 1
        elif event_type == "unsubscribe":
            metrics.unsubscribed += 1
        else:
            raise ValueError(f"Unknown event type: {event_type}")

    def get_variant_performance(self, test_id: str, variant_id: str) -> Dict:
        """Get performance metrics for a variant."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        for variant in test.variants:
            if variant.id == variant_id:
                return {
                    "variant_id": variant.id,
                    "name": variant.name,
                    "metrics": variant.metrics.to_dict(),
                    "traffic_allocation": variant.traffic_allocation,
                }
        raise ValueError(f"Variant not found: {variant_id}")

    def _normal_cdf(self, x: float) -> float:
        """Approximation of the standard normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _z_test_proportions(
        self,
        conversions_a: int,
        total_a: int,
        conversions_b: int,
        total_b: int,
    ) -> Tuple[float, float]:
        """Two-proportion z-test. Returns (z_score, p_value)."""
        if total_a == 0 or total_b == 0:
            return 0.0, 1.0

        p_a = conversions_a / total_a
        p_b = conversions_b / total_b
        p_pool = (conversions_a + conversions_b) / (total_a + total_b)

        if p_pool == 0 or p_pool == 1:
            return 0.0, 1.0

        se = math.sqrt(p_pool * (1 - p_pool) * (1 / total_a + 1 / total_b))
        if se == 0:
            return 0.0, 1.0

        z = (p_a - p_b) / se
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        return z, p_value

    def is_statistically_significant(self, test_id: str) -> bool:
        """Check if the test results are statistically significant."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        if len(test.variants) < 2:
            return False

        v1, v2 = test.variants[0], test.variants[1]
        _, p_value = self._z_test_proportions(
            v1.metrics.converted,
            v1.metrics.delivered,
            v2.metrics.converted,
            v2.metrics.delivered,
        )
        return p_value < (1 - test.confidence_level)

    def determine_winner(self, test_id: str) -> Optional[str]:
        """Determine the winning variant based on conversion rate."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")
        if len(test.variants) < 2:
            return None

        best_variant = None
        best_rate = -1.0
        for variant in test.variants:
            rate = variant.metrics.conversion_rate
            if rate > best_rate:
                best_rate = rate
                best_variant = variant

        if best_variant:
            test.winner_variant_id = best_variant.id
        return best_variant.id if best_variant else None

    def get_test_report(self, test_id: str) -> Dict:
        """Generate a comprehensive A/B test report."""
        test = self._tests.get(test_id)
        if not test:
            raise ValueError(f"Test not found: {test_id}")

        variants_report = []
        for variant in test.variants:
            variants_report.append(
                {
                    "variant_id": variant.id,
                    "name": variant.name,
                    "metrics": variant.metrics.to_dict(),
                    "traffic_allocation": variant.traffic_allocation,
                }
            )

        significance = None
        if len(test.variants) >= 2:
            v1, v2 = test.variants[0], test.variants[1]
            z, p_value = self._z_test_proportions(
                v1.metrics.converted,
                v1.metrics.delivered,
                v2.metrics.converted,
                v2.metrics.delivered,
            )
            significance = {
                "z_score": z,
                "p_value": p_value,
                "is_significant": p_value < (1 - test.confidence_level),
                "confidence_level": test.confidence_level,
            }

        return {
            "test_id": test.id,
            "name": test.name,
            "status": test.status.value,
            "variants": variants_report,
            "winner_variant_id": test.winner_variant_id,
            "statistical_significance": significance,
            "start_date": test.start_date.isoformat() if test.start_date else None,
            "end_date": test.end_date.isoformat() if test.end_date else None,
        }

    def list_tests(self, status: Optional[TestStatus] = None) -> List[ABTest]:
        """List all tests, optionally filtered by status."""
        tests = list(self._tests.values())
        if status:
            tests = [t for t in tests if t.status == status]
        return tests
