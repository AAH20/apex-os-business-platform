"""Cost allocation engine."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.cost_management.models import (
    AllocationMethod,
    AllocationResult,
    AllocationRule,
    CostCategory,
    CostEntry,
)


class CostAllocator:
    """Allocates costs across departments using configurable rules."""

    def __init__(self):
        self._rules: Dict[str, AllocationRule] = {}
        self._results: Dict[str, AllocationResult] = {}

    def add_rule(self, rule: AllocationRule) -> AllocationRule:
        """Add an allocation rule."""
        self._rules[rule.id] = rule
        return rule

    def create_rule(
        self,
        name: str,
        source_department_id: str,
        target_department_ids: List[str],
        method: AllocationMethod,
        percentages: Optional[Dict[str, float]] = None,
        category_filter: Optional[List[CostCategory]] = None,
    ) -> AllocationRule:
        """Create and add a new allocation rule."""
        rule = AllocationRule.create(
            name=name,
            source_department_id=source_department_id,
            target_department_ids=target_department_ids,
            method=method,
            percentages=percentages,
            category_filter=category_filter,
        )
        return self.add_rule(rule)

    def get_rule(self, rule_id: str) -> Optional[AllocationRule]:
        """Get an allocation rule by ID."""
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AllocationRule]:
        """Get all allocation rules."""
        return list(self._rules.values())

    def get_active_rules(self) -> List[AllocationRule]:
        """Get all active allocation rules."""
        return [r for r in self._rules.values() if r.active]

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an allocation rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def toggle_rule(self, rule_id: str) -> AllocationRule:
        """Toggle a rule's active status."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Allocation rule not found: {rule_id}")
        rule.active = not rule.active
        return rule

    def allocate(
        self,
        rule_id: str,
        cost_entry: CostEntry,
        usage_data: Optional[Dict[str, float]] = None,
        headcount_data: Optional[Dict[str, int]] = None,
        revenue_data: Optional[Dict[str, float]] = None,
    ) -> AllocationResult:
        """Allocate a cost entry using the specified rule."""
        rule = self._rules.get(rule_id)
        if not rule:
            raise ValueError(f"Allocation rule not found: {rule_id}")
        if not rule.active:
            raise ValueError(f"Allocation rule is not active: {rule_id}")

        # Check category filter
        if rule.category_filter and cost_entry.category not in rule.category_filter:
            raise ValueError(
                f"Cost category {cost_entry.category} not in rule's filter"
            )

        allocations = self._compute_allocations(
            rule, cost_entry.amount, usage_data, headcount_data, revenue_data
        )
        result = AllocationResult.create(
            rule_id=rule_id,
            source_cost_id=cost_entry.id,
            allocations=allocations,
        )
        self._results[result.id] = result
        return result

    def _compute_allocations(
        self,
        rule: AllocationRule,
        amount: float,
        usage_data: Optional[Dict[str, float]] = None,
        headcount_data: Optional[Dict[str, int]] = None,
        revenue_data: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """Compute allocation amounts based on the rule's method."""
        targets = rule.target_department_ids

        if rule.method == AllocationMethod.EQUAL:
            share = amount / len(targets)
            return {dept: share for dept in targets}

        elif rule.method == AllocationMethod.PERCENTAGE:
            if not rule.percentages:
                raise ValueError("Percentage method requires percentages")
            return {
                dept: amount * (rule.percentages.get(dept, 0.0) / 100.0)
                for dept in targets
            }

        elif rule.method == AllocationMethod.USAGE_BASED:
            if not usage_data:
                raise ValueError("Usage-based method requires usage_data")
            total_usage = sum(usage_data.get(dept, 0.0) for dept in targets)
            if total_usage == 0:
                share = amount / len(targets)
                return {dept: share for dept in targets}
            return {
                dept: amount * (usage_data.get(dept, 0.0) / total_usage)
                for dept in targets
            }

        elif rule.method == AllocationMethod.HEADCOUNT:
            if not headcount_data:
                raise ValueError("Headcount method requires headcount_data")
            total_headcount = sum(headcount_data.get(dept, 0) for dept in targets)
            if total_headcount == 0:
                share = amount / len(targets)
                return {dept: share for dept in targets}
            return {
                dept: amount * (headcount_data.get(dept, 0) / total_headcount)
                for dept in targets
            }

        elif rule.method == AllocationMethod.REVENUE_BASED:
            if not revenue_data:
                raise ValueError("Revenue-based method requires revenue_data")
            total_revenue = sum(revenue_data.get(dept, 0.0) for dept in targets)
            if total_revenue == 0:
                share = amount / len(targets)
                return {dept: share for dept in targets}
            return {
                dept: amount * (revenue_data.get(dept, 0.0) / total_revenue)
                for dept in targets
            }

        elif rule.method == AllocationMethod.CUSTOM:
            if not rule.percentages:
                raise ValueError("Custom method requires percentages")
            return {
                dept: amount * (rule.percentages.get(dept, 0.0) / 100.0)
                for dept in targets
            }

        else:
            raise ValueError(f"Unknown allocation method: {rule.method}")

    def get_result(self, result_id: str) -> Optional[AllocationResult]:
        """Get an allocation result by ID."""
        return self._results.get(result_id)

    def get_all_results(self) -> List[AllocationResult]:
        """Get all allocation results."""
        return list(self._results.values())

    def get_results_by_rule(self, rule_id: str) -> List[AllocationResult]:
        """Get results filtered by rule ID."""
        return [r for r in self._results.values() if r.rule_id == rule_id]

    def get_total_allocated(
        self,
        department_id: Optional[str] = None,
    ) -> float:
        """Get total allocated amount, optionally filtered by department."""
        total = 0.0
        for result in self._results.values():
            if department_id:
                total += result.allocations.get(department_id, 0.0)
            else:
                total += result.total_allocated
        return total

    def clear(self) -> None:
        """Clear all rules and results."""
        self._rules.clear()
        self._results.clear()
