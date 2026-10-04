"""Customer segmentation for CRM.

Segments customers using RFM analysis (Recency, Frequency, Monetary)
and behavioral/demographic grouping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SegmentType(str, Enum):
    RFM = "rfm"
    BEHAVIORAL = "behavioral"
    DEMOGRAPHIC = "demographic"
    CUSTOM = "custom"


@dataclass
class Segment:
    """A customer segment with criteria and members."""

    name: str
    segment_type: SegmentType
    criteria: dict[str, Any] = field(default_factory=dict)
    member_ids: list[str] = field(default_factory=list)
    segment_id: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not self.segment_id:
            import uuid
            self.segment_id = str(uuid.uuid4())[:8]

    @property
    def size(self) -> int:
        return len(self.member_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "name": self.name,
            "type": self.segment_type.value,
            "criteria": self.criteria,
            "member_ids": self.member_ids,
            "size": self.size,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }


class CustomerSegmentation:
    """RFM-based customer segmentation.

    Each customer dict should have:
        customer_id: str
        last_purchase_days: int (recency)
        purchase_count: int (frequency)
        total_spent: float (monetary)
    """

    # RFM score thresholds (1-5 scale)
    RFM_THRESHOLDS = {
        "recency": [7, 14, 30, 60, 90],      # days
        "frequency": [10, 5, 3, 2, 1],        # purchases
        "monetary": [10000, 5000, 1000, 500, 100],  # currency
    }

    # Segment definitions based on RFM scores
    SEGMENT_DEFINITIONS: dict[str, dict[str, Any]] = {
        "champions": {
            "description": "Best customers: high R, F, M",
            "rfm_range": {"r": (4, 5), "f": (4, 5), "m": (4, 5)},
        },
        "loyal_customers": {
            "description": "Regular buyers with good value",
            "rfm_range": {"r": (3, 5), "f": (3, 5), "m": (3, 5)},
        },
        "potential_loyalists": {
            "description": "Recent customers with potential",
            "rfm_range": {"r": (4, 5), "f": (1, 3), "m": (1, 3)},
        },
        "new_customers": {
            "description": "Very recent first-time buyers",
            "rfm_range": {"r": (4, 5), "f": (1, 1), "m": (1, 5)},
        },
        "promising": {
            "description": "Recent customers with low value",
            "rfm_range": {"r": (4, 5), "f": (1, 2), "m": (1, 2)},
        },
        "need_attention": {
            "description": "Customers who need attention",
            "rfm_range": {"r": (2, 3), "f": (2, 3), "m": (2, 3)},
        },
        "about_to_sleep": {
            "description": "Customers about to become inactive",
            "rfm_range": {"r": (2, 3), "f": (1, 2), "m": (1, 5)},
        },
        "at_risk": {
            "description": "Customers at risk of churning",
            "rfm_range": {"r": (1, 3), "f": (2, 5), "m": (2, 5)},
        },
        "cannot_lose": {
            "description": "High-value customers at risk",
            "rfm_range": {"r": (1, 2), "f": (4, 5), "m": (4, 5)},
        },
        "hibernating": {
            "description": "Inactive customers with low value",
            "rfm_range": {"r": (1, 2), "f": (1, 2), "m": (1, 2)},
        },
        "lost": {
            "description": "Lost customers",
            "rfm_range": {"r": (1, 1), "f": (1, 1), "m": (1, 1)},
        },
    }

    def __init__(self, reference_date: datetime | None = None):
        self.reference_date = reference_date or datetime.utcnow()
        self._segments: dict[str, Segment] = {}

    def _score_recency(self, days: int) -> int:
        """Score recency: lower days = higher score (1-5)."""
        thresholds = self.RFM_THRESHOLDS["recency"]
        for i, t in enumerate(thresholds):
            if days <= t:
                return 5 - i
        return 1

    def _score_frequency(self, count: int) -> int:
        """Score frequency: higher count = higher score (1-5)."""
        thresholds = self.RFM_THRESHOLDS["frequency"]
        for i, t in enumerate(thresholds):
            if count >= t:
                return 5 - i
        return 1

    def _score_monetary(self, amount: float) -> int:
        """Score monetary: higher amount = higher score (1-5)."""
        thresholds = self.RFM_THRESHOLDS["monetary"]
        for i, t in enumerate(thresholds):
            if amount >= t:
                return 5 - i
        return 1

    def compute_rfm(self, customer: dict) -> dict[str, int]:
        """Compute RFM scores for a customer."""
        r = self._score_recency(customer.get("last_purchase_days", 999))
        f = self._score_frequency(customer.get("purchase_count", 0))
        m = self._score_monetary(customer.get("total_spent", 0))
        return {"r": r, "f": f, "m": m}

    def _match_segment(self, rfm: dict[str, int]) -> str:
        """Find the best matching segment for RFM scores."""
        best_match = "hibernating"
        best_score = -1

        for seg_name, seg_def in self.SEGMENT_DEFINITIONS.items():
            r_range = seg_def["rfm_range"]["r"]
            f_range = seg_def["rfm_range"]["f"]
            m_range = seg_def["rfm_range"]["m"]

            score = 0
            if r_range[0] <= rfm["r"] <= r_range[1]:
                score += 1
            if f_range[0] <= rfm["f"] <= f_range[1]:
                score += 1
            if m_range[0] <= rfm["m"] <= m_range[1]:
                score += 1

            if score > best_score:
                best_score = score
                best_match = seg_name

        return best_match

    def segment_customers(
        self, customers: list[dict]
    ) -> dict[str, Segment]:
        """Segment a list of customers using RFM analysis.

        Returns dict mapping segment name to Segment object.
        """
        # Initialize segments
        for seg_name, seg_def in self.SEGMENT_DEFINITIONS.items():
            self._segments[seg_name] = Segment(
                name=seg_name,
                segment_type=SegmentType.RFM,
                criteria=seg_def["rfm_range"],
                description=seg_def["description"],
            )

        # Assign customers to segments
        for customer in customers:
            cid = customer.get("customer_id", "unknown")
            rfm = self.compute_rfm(customer)
            seg_name = self._match_segment(rfm)
            self._segments[seg_name].member_ids.append(cid)

        return self._segments

    def get_segment(self, name: str) -> Segment | None:
        return self._segments.get(name)

    def get_all_segments(self) -> list[Segment]:
        return list(self._segments.values())

    def get_segment_distribution(self) -> dict[str, int]:
        """Return count of customers per segment."""
        return {name: seg.size for name, seg in self._segments.items()}

    def get_segment_stats(self) -> dict[str, dict[str, Any]]:
        """Return statistics for each segment."""
        stats: dict[str, dict[str, Any]] = {}
        for name, seg in self._segments.items():
            stats[name] = {
                "size": seg.size,
                "percentage": 0.0,  # Will be filled if total known
                "description": seg.description,
            }
        total = sum(s["size"] for s in stats.values())
        if total > 0:
            for s in stats.values():
                s["percentage"] = round((s["size"] / total) * 100, 2)
        return stats

    def create_custom_segment(
        self,
        name: str,
        member_ids: list[str],
        description: str = "",
        criteria: dict[str, Any] | None = None,
    ) -> Segment:
        """Create a custom segment."""
        seg = Segment(
            name=name,
            segment_type=SegmentType.CUSTOM,
            criteria=criteria or {},
            member_ids=member_ids,
            description=description,
        )
        self._segments[name] = seg
        return seg

    def behavioral_segment(
        self,
        customers: list[dict],
        activity_key: str,
        thresholds: list[float],
        labels: list[str] | None = None,
    ) -> dict[str, Segment]:
        """Segment customers by an activity metric.

        Args:
            customers: List of customer dicts.
            activity_key: Key for the activity metric (e.g. "page_views").
            thresholds: Sorted list of threshold values.
            labels: Optional labels for each tier.
        """
        if labels is None:
            labels = [f"tier_{i}" for i in range(len(thresholds) + 1)]

        segments: dict[str, Segment] = {}
        for label in labels:
            segments[label] = Segment(
                name=label,
                segment_type=SegmentType.BEHAVIORAL,
                criteria={"activity_key": activity_key, "thresholds": thresholds},
            )

        for customer in customers:
            cid = customer.get("customer_id", "unknown")
            value = customer.get(activity_key, 0)
            assigned = False
            for i, threshold in enumerate(thresholds):
                if value <= threshold:
                    segments[labels[i]].member_ids.append(cid)
                    assigned = True
                    break
            if not assigned:
                segments[labels[-1]].member_ids.append(cid)

        self._segments.update(segments)
        return segments

    def demographic_segment(
        self,
        customers: list[dict],
        attribute: str,
    ) -> dict[str, Segment]:
        """Segment customers by a demographic attribute.

        Args:
            customers: List of customer dicts.
            attribute: Key for the demographic field (e.g. "country", "industry").
        """
        segments: dict[str, Segment] = {}

        for customer in customers:
            cid = customer.get("customer_id", "unknown")
            value = str(customer.get(attribute, "unknown"))
            if value not in segments:
                segments[value] = Segment(
                    name=f"{attribute}_{value}",
                    segment_type=SegmentType.DEMOGRAPHIC,
                    criteria={attribute: value},
                )
            segments[value].member_ids.append(cid)

        self._segments.update(segments)
        return segments
