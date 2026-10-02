"""Traffic splitting: deterministic, consistent-hashing based assignment."""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from .models import Assignment, Experiment, ExperimentStatus, Variant


class TrafficSplitter:
    """Assigns users to experiment variants using consistent hashing.

    Uses MD5-based bucketing for deterministic, uniform assignment.
    The same user always gets the same variant for a given experiment,
    ensuring a consistent experience across sessions.
    """

    NUM_BUCKETS = 10_000  # 0-9999 for fine-grained allocation

    def __init__(self) -> None:
        self._assignment_cache: Dict[str, Assignment] = {}

    # ------------------------------------------------------------------
    # Core assignment
    # ------------------------------------------------------------------

    def _compute_bucket(self, experiment_id: str, user_id: str) -> int:
        """Compute a deterministic hash bucket (0 to NUM_BUCKETS-1)."""
        key = f"{experiment_id}:{user_id}"
        hash_bytes = hashlib.md5(key.encode("utf-8")).digest()
        # Use first 4 bytes as an unsigned int, then mod NUM_BUCKETS
        hash_int = int.from_bytes(hash_bytes[:4], byteorder="big")
        return hash_int % self.NUM_BUCKETS

    def _variant_for_bucket(
        self,
        variants: List[Variant],
        bucket: int,
    ) -> Optional[Variant]:
        """Map a hash bucket to a variant based on traffic allocation.

        Variants are assigned contiguous ranges of buckets proportional
        to their traffic allocation percentages.
        """
        if not variants:
            return None

        # Sort variants for deterministic ordering
        sorted_variants = sorted(variants, key=lambda v: v.name)

        cumulative = 0.0
        for variant in sorted_variants:
            cumulative += variant.traffic_allocation
            threshold = int(cumulative / 100.0 * self.NUM_BUCKETS)
            if bucket < threshold:
                return variant

        # Fallback: last variant (handles floating-point edge cases)
        return sorted_variants[-1]

    def assign(
        self,
        experiment: Experiment,
        user_id: str,
        use_cache: bool = True,
    ) -> Assignment:
        """Assign a user to a variant in the experiment.

        Args:
            experiment: The experiment to assign against.
            user_id: Unique identifier for the user.
            use_cache: Whether to use the assignment cache.

        Returns:
            An Assignment record.

        Raises:
            ValueError: If the experiment is not running or has no variants.
        """
        if experiment.status != ExperimentStatus.RUNNING:
            raise ValueError(
                f"Experiment '{experiment.name}' is not running "
                f"(status: {experiment.status.value})"
            )

        if not experiment.variants:
                raise ValueError("Experiment has no variants")

        cache_key = f"{experiment.id}:{user_id}"
        if use_cache and cache_key in self._assignment_cache:
            return self._assignment_cache[cache_key]

        bucket = self._compute_bucket(experiment.id, user_id)
        variant = self._variant_for_bucket(experiment.variants, bucket)

        if variant is None:
            raise ValueError("No variant available for assignment")

        assignment = Assignment(
            experiment_id=experiment.id,
            user_id=user_id,
            variant_id=variant.id,
            variant_name=variant.name,
            bucket=bucket,
        )

        if use_cache:
            self._assignment_cache[cache_key] = assignment

        return assignment

    def assign_batch(
        self,
        experiment: Experiment,
        user_ids: List[str],
    ) -> List[Assignment]:
        """Assign multiple users to variants efficiently.

        Returns:
            List of Assignment records in the same order as user_ids.
        """
        return [self.assign(experiment, uid) for uid in user_ids]

    # ------------------------------------------------------------------
    # Distribution analysis
    # ------------------------------------------------------------------

    def get_assignment_distribution(
        self,
        experiment: Experiment,
        user_ids: List[str],
    ) -> Dict[str, int]:
        """Get the distribution of assignments across variants.

        Returns:
            Dict mapping variant_id to count of assigned users.
        """
        distribution: Dict[str, int] = {v.id: 0 for v in experiment.variants}
        for uid in user_ids:
            assignment = self.assign(experiment, uid)
            distribution[assignment.variant_id] = (
                distribution.get(assignment.variant_id, 0) + 1
            )
        return distribution

    def get_assignment_percentages(
        self,
        experiment: Experiment,
        user_ids: List[str],
    ) -> Dict[str, float]:
        """Get assignment percentages for each variant.

        Returns:
            Dict mapping variant_id to percentage (0-100).
        """
        distribution = self.get_assignment_distribution(experiment, user_ids)
        total = sum(distribution.values())
        if total == 0:
            return {v.id: 0.0 for v in experiment.variants}
        return {
            vid: (count / total) * 100.0
            for vid, count in distribution.items()
        }

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def clear_cache(self) -> None:
        """Clear the assignment cache."""
        self._assignment_cache.clear()

    def clear_cache_for_experiment(self, experiment_id: str) -> None:
        """Clear cached assignments for a specific experiment."""
        keys_to_remove = [
            key for key in self._assignment_cache
            if key.startswith(f"{experiment_id}:")
        ]
        for key in keys_to_remove:
            del self._assignment_cache[key]

    def get_cache_size(self) -> int:
        """Return the number of cached assignments."""
        return len(self._assignment_cache)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_split(
        self,
        experiment: Experiment,
        user_ids: List[str],
        tolerance: float = 5.0,
    ) -> Tuple[bool, Dict[str, float]]:
        """Validate that actual split matches expected allocation.

        Args:
            experiment: The experiment to validate.
            user_ids: Sample of user IDs to test.
            tolerance: Maximum allowed deviation in percentage points.

        Returns:
            Tuple of (is_valid, actual_percentages).
        """
        actual = self.get_assignment_percentages(experiment, user_ids)
        expected = {v.id: v.traffic_allocation for v in experiment.variants}

        for variant in experiment.variants:
            deviation = abs(actual.get(variant.id, 0.0) - expected.get(variant.id, 0.0))
            if deviation > tolerance:
                return False, actual

        return True, actual
