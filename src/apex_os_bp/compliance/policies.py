"""Policy management module."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .models import Policy


class PolicyManager:
    """Manages compliance policies."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}

    def create_policy(
        self,
        policy_id: str,
        title: str,
        version: str,
        content: str,
        category: str,
        author: str = "",
        approver: str = "",
        effective_date: date | None = None,
        review_date: date | None = None,
        tags: list[str] | None = None,
        related_regulations: list[str] | None = None,
    ) -> Policy:
        """Create a new policy."""
        policy = Policy(
            id=policy_id,
            title=title,
            version=version,
            content=content,
            category=category,
            author=author,
            approver=approver,
            effective_date=effective_date,
            review_date=review_date,
            status="draft",
            tags=tags or [],
            related_regulations=related_regulations or [],
        )
        self._policies[policy_id] = policy
        return policy

    def get_policy(self, policy_id: str) -> Policy | None:
        """Get a policy by ID."""
        return self._policies.get(policy_id)

    def update_policy(self, policy_id: str, **kwargs: Any) -> Policy | None:
        """Update policy fields."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return None
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        policy.updated_at = datetime.utcnow()
        return policy

    def approve_policy(self, policy_id: str, approver: str) -> Policy | None:
        """Approve a policy, making it active."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return None
        policy.approver = approver
        policy.status = "active"
        if policy.effective_date is None:
            policy.effective_date = date.today()
        policy.updated_at = datetime.utcnow()
        return policy

    def deprecate_policy(self, policy_id: str) -> Policy | None:
        """Deprecate a policy."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return None
        policy.status = "deprecated"
        policy.updated_at = datetime.utcnow()
        return policy

    def archive_policy(self, policy_id: str) -> Policy | None:
        """Archive a policy."""
        policy = self._policies.get(policy_id)
        if policy is None:
            return None
        policy.status = "archived"
        policy.updated_at = datetime.utcnow()
        return policy

    def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            return True
        return False

    def list_policies(
        self,
        status: str | None = None,
        category: str | None = None,
        tag: str | None = None,
    ) -> list[Policy]:
        """List policies with optional filters."""
        policies = list(self._policies.values())
        if status is not None:
            policies = [p for p in policies if p.status == status]
        if category is not None:
            policies = [p for p in policies if p.category == category]
        if tag is not None:
            policies = [p for p in policies if tag in p.tags]
        return policies

    def get_policies_by_category(self) -> dict[str, list[Policy]]:
        """Group policies by category."""
        grouped: dict[str, list[Policy]] = defaultdict(list)
        for policy in self._policies.values():
            grouped[policy.category].append(policy)
        return dict(grouped)

    def get_policies_by_regulation(self, regulation: str) -> list[Policy]:
        """Get policies related to a specific regulation."""
        return [
            p for p in self._policies.values()
            if regulation in p.related_regulations
        ]

    def get_policies_needing_review(self) -> list[Policy]:
        """Get active policies past their review date."""
        today = date.today()
        return [
            p for p in self._policies.values()
            if p.status == "active"
            and p.review_date is not None
            and p.review_date < today
        ]

    def search_policies(self, query: str) -> list[Policy]:
        """Search policies by title or content."""
        query_lower = query.lower()
        return [
            p for p in self._policies.values()
            if query_lower in p.title.lower() or query_lower in p.content.lower()
        ]

    def to_dict(self) -> dict[str, Any]:
        """Export all policies as a dictionary."""
        return {
            "policies": {k: v.to_dict() for k, v in self._policies.items()},
            "total": len(self._policies),
        }

    def __len__(self) -> int:
        return len(self._policies)
