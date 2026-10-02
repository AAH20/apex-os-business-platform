"""Contact deduplication engine for CRM.

Detects and merges duplicate contact records using fuzzy matching
on name, email, phone, and company fields.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any


@dataclass
class DuplicateGroup:
    """A group of contacts identified as duplicates."""

    group_id: str
    contact_ids: list[str]
    confidence: float  # 0.0 - 1.0
    match_reasons: list[str] = field(default_factory=list)
    canonical_id: str | None = None  # The "master" record to keep

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "contact_ids": self.contact_ids,
            "confidence": self.confidence,
            "match_reasons": self.match_reasons,
            "canonical_id": self.canonical_id,
        }


def _normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse spaces."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_email(email: str) -> str:
    """Normalize email: lowercase, strip whitespace."""
    return email.lower().strip() if email else ""


def _normalize_phone(phone: str) -> str:
    """Normalize phone: digits only."""
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def _similarity(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0 - 1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


class DeduplicationEngine:
    """Detects duplicate contacts using configurable field weights.

    Default weights:
        email: 0.40
        phone: 0.25
        name:  0.20
        company: 0.15
    """

    DEFAULT_WEIGHTS: dict[str, float] = {
        "email": 0.40,
        "phone": 0.25,
        "name": 0.20,
        "company": 0.15,
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        threshold: float = 0.75,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.threshold = threshold

    def _email_similarity(self, a: dict, b: dict) -> float:
        ea = _normalize_email(a.get("email", ""))
        eb = _normalize_email(b.get("email", ""))
        if not ea or not eb:
            return 0.0
        if ea == eb:
            return 1.0
        # Check local part similarity for typos
        local_a = ea.split("@")[0]
        local_b = eb.split("@")[0]
        return _similarity(local_a, local_b) * 0.8

    def _phone_similarity(self, a: dict, b: dict) -> float:
        pa = _normalize_phone(a.get("phone", ""))
        pb = _normalize_phone(b.get("phone", ""))
        if not pa or not pb:
            return 0.0
        if pa == pb:
            return 1.0
        # Check if one is a suffix of the other (missing country code)
        if pa.endswith(pb) or pb.endswith(pa):
            return 0.9
        return _similarity(pa, pb)

    def _name_similarity(self, a: dict, b: dict) -> float:
        na = _normalize(a.get("name", ""))
        nb = _normalize(b.get("name", ""))
        if not na or not nb:
            return 0.0
        if na == nb:
            return 1.0
        return _similarity(na, nb)

    def _company_similarity(self, a: dict, b: dict) -> float:
        ca = _normalize(a.get("company", ""))
        cb = _normalize(b.get("company", ""))
        if not ca or not cb:
            return 0.0
        if ca == cb:
            return 1.0
        return _similarity(ca, cb)

    def compute_similarity(self, contact_a: dict, contact_b: dict) -> tuple[float, list[str]]:
        """Compute weighted similarity between two contacts.

        Returns (score, match_reasons) where score is 0.0-1.0.
        """
        field_scores = {
            "email": self._email_similarity(contact_a, contact_b),
            "phone": self._phone_similarity(contact_a, contact_b),
            "name": self._name_similarity(contact_a, contact_b),
            "company": self._company_similarity(contact_a, contact_b),
        }

        total = 0.0
        reasons: list[str] = []
        for field_name, weight in self.weights.items():
            score = field_scores.get(field_name, 0.0)
            total += score * weight
            if score >= 0.85:
                reasons.append(f"{field_name}_match")
            elif score >= 0.6:
                reasons.append(f"{field_name}_partial")

        return round(total, 4), reasons

    def find_duplicates(
        self, contacts: list[dict]
    ) -> list[DuplicateGroup]:
        """Find all duplicate groups in a list of contacts.

        Each contact dict must have an 'id' key.
        """
        n = len(contacts)
        if n < 2:
            return []

        # Build similarity graph (adjacency list)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Compare all pairs
        pairs: list[tuple[int, int, float, list[str]]] = []
        for i in range(n):
            for j in range(i + 1, n):
                score, reasons = self.compute_similarity(contacts[i], contacts[j])
                if score >= self.threshold:
                    pairs.append((i, j, score, reasons))
                    union(i, j)

        # Group by connected components
        groups: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            groups.setdefault(root, []).append(i)

        # Build DuplicateGroup objects
        result: list[DuplicateGroup] = []
        for idx, (root, members) in enumerate(groups.items()):
            if len(members) < 2:
                continue

            # Compute average confidence within the group
            group_pairs = [
                (s, r) for (i, j, s, r) in pairs
                if i in members and j in members
            ]
            avg_confidence = (
                sum(s for s, _ in group_pairs) / len(group_pairs)
                if group_pairs else 0.0
            )

            # Collect all match reasons
            all_reasons: list[str] = []
            for _, reasons in group_pairs:
                for reason in reasons:
                    if reason not in all_reasons:
                        all_reasons.append(reason)

            # Pick canonical: most complete record (most non-empty fields)
            canonical_idx = max(
                members,
                key=lambda i: sum(
                    1 for v in contacts[i].values() if v
                ),
            )

            result.append(DuplicateGroup(
                group_id=f"dup_group_{idx}",
                contact_ids=[contacts[i]["id"] for i in members],
                confidence=round(avg_confidence, 4),
                match_reasons=all_reasons,
                canonical_id=contacts[canonical_idx]["id"],
            ))

        return sorted(result, key=lambda g: g.confidence, reverse=True)

    def merge_contacts(
        self, contacts: list[dict], group: DuplicateGroup
    ) -> dict:
        """Merge a group of duplicate contacts into one canonical record.

        Strategy: start with canonical, fill missing fields from others.
        """
        contact_map = {c["id"]: c for c in contacts}
        canonical = contact_map.get(group.canonical_id)
        if canonical is None:
            # Fallback to first contact in group
            canonical = contact_map[group.contact_ids[0]]

        merged = dict(canonical)
        merged["merged_from"] = list(group.contact_ids)
        merged["merge_confidence"] = group.confidence

        # Fill missing fields from other contacts
        for cid in group.contact_ids:
            if cid == group.canonical_id:
                continue
            other = contact_map.get(cid, {})
            for key, value in other.items():
                if key in ("id", "merged_from", "merge_confidence"):
                    continue
                if not merged.get(key) and value:
                    merged[key] = value

        return merged

    def deduplicate(
        self, contacts: list[dict]
    ) -> tuple[list[dict], list[DuplicateGroup]]:
        """Full deduplication pass.

        Returns (unique_contacts, duplicate_groups).
        Merged contacts replace their duplicates in the output.
        """
        groups = self.find_duplicates(contacts)
        if not groups:
            return list(contacts), []

        # Track which contact IDs have been merged away
        merged_ids: set[str] = set()
        merged_records: list[dict] = []

        for group in groups:
            merged = self.merge_contacts(contacts, group)
            merged_records.append(merged)
            for cid in group.contact_ids:
                if cid != group.canonical_id:
                    merged_ids.add(cid)

        # Keep contacts not merged away
        unique = [
            c for c in contacts
            if c["id"] not in merged_ids
        ]
        unique.extend(merged_records)

        return unique, groups
