"""Cost optimization engine."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.cost_management.models import (
    CostCategory,
    CostEntry,
    OptimizationSuggestion,
    OptimizationType,
)


class CostOptimizer:
    """Analyzes costs and generates optimization suggestions."""

    def __init__(self):
        self._suggestions: Dict[str, OptimizationSuggestion] = {}

    def add_suggestion(self, suggestion: OptimizationSuggestion) -> OptimizationSuggestion:
        """Add an optimization suggestion."""
        self._suggestions[suggestion.id] = suggestion
        return suggestion

    def create_suggestion(
        self,
        type: OptimizationType,
        title: str,
        description: str,
        potential_savings: float,
        currency: str = "USD",
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
        priority: int = 5,
    ) -> OptimizationSuggestion:
        """Create and add a new optimization suggestion."""
        suggestion = OptimizationSuggestion.create(
            type=type,
            title=title,
            description=description,
            potential_savings=potential_savings,
            currency=currency,
            category=category,
            department_id=department_id,
            priority=priority,
        )
        return self.add_suggestion(suggestion)

    def get_suggestion(self, suggestion_id: str) -> Optional[OptimizationSuggestion]:
        """Get a suggestion by ID."""
        return self._suggestions.get(suggestion_id)

    def get_all_suggestions(self) -> List[OptimizationSuggestion]:
        """Get all suggestions."""
        return list(self._suggestions.values())

    def get_suggestions_by_type(self, type: OptimizationType) -> List[OptimizationSuggestion]:
        """Get suggestions filtered by type."""
        return [s for s in self._suggestions.values() if s.type == type]

    def get_suggestions_by_category(self, category: CostCategory) -> List[OptimizationSuggestion]:
        """Get suggestions filtered by category."""
        return [s for s in self._suggestions.values() if s.category == category]

    def get_suggestions_by_department(self, department_id: str) -> List[OptimizationSuggestion]:
        """Get suggestions filtered by department."""
        return [s for s in self._suggestions.values() if s.department_id == department_id]

    def get_pending_suggestions(self) -> List[OptimizationSuggestion]:
        """Get all pending (not implemented) suggestions."""
        return [s for s in self._suggestions.values() if not s.implemented]

    def get_implemented_suggestions(self) -> List[OptimizationSuggestion]:
        """Get all implemented suggestions."""
        return [s for s in self._suggestions.values() if s.implemented]

    def get_high_priority_suggestions(self, threshold: int = 3) -> List[OptimizationSuggestion]:
        """Get high priority suggestions (priority <= threshold)."""
        return [s for s in self._suggestions.values() if s.priority <= threshold]

    def mark_implemented(self, suggestion_id: str) -> OptimizationSuggestion:
        """Mark a suggestion as implemented."""
        suggestion = self._suggestions.get(suggestion_id)
        if not suggestion:
            raise ValueError(f"Suggestion not found: {suggestion_id}")
        suggestion.mark_implemented()
        return suggestion

    def remove_suggestion(self, suggestion_id: str) -> bool:
        """Remove a suggestion."""
        if suggestion_id in self._suggestions:
            del self._suggestions[suggestion_id]
            return True
        return False

    def get_total_potential_savings(
        self,
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
    ) -> float:
        """Get total potential savings with optional filters."""
        suggestions = self._suggestions.values()
        if category:
            suggestions = [s for s in suggestions if s.category == category]
        if department_id:
            suggestions = [s for s in suggestions if s.department_id == department_id]
        return sum(s.potential_savings for s in suggestions)

    def get_total_realized_savings(self) -> float:
        """Get total savings from implemented suggestions."""
        return sum(
            s.potential_savings
            for s in self._suggestions.values()
            if s.implemented
        )

    def analyze_costs(
        self,
        entries: List[CostEntry],
        department_costs: Optional[Dict[str, float]] = None,
    ) -> List[OptimizationSuggestion]:
        """Analyze cost entries and generate optimization suggestions."""
        suggestions = []

        # Analyze by category for high spending
        category_totals: Dict[CostCategory, float] = {}
        for entry in entries:
            category_totals[entry.category] = (
                category_totals.get(entry.category, 0.0) + entry.amount
            )

        # Suggest reductions for categories with high spend
        for category, total in category_totals.items():
            if total > 10000:
                suggestion = self.create_suggestion(
                    type=OptimizationType.REDUCE,
                    title=f"Reduce {category.value} costs",
                    description=f"High spending detected in {category.value}: ${total:,.2f}. Consider cost reduction strategies.",
                    potential_savings=total * 0.1,
                    category=category,
                    priority=2,
                )
                suggestions.append(suggestion)

        # Suggest consolidation for departments with many small entries
        if department_costs:
            for dept_id, total in department_costs.items():
                if total > 5000:
                    suggestion = self.create_suggestion(
                        type=OptimizationType.CONSOLIDATE,
                        title=f"Consolidate spending in {dept_id}",
                        description=f"Department {dept_id} has ${total:,.2f} in costs. Consolidate vendors and contracts.",
                        potential_savings=total * 0.15,
                        department_id=dept_id,
                        priority=3,
                    )
                    suggestions.append(suggestion)

        # Suggest automation for personnel costs
        personnel_total = category_totals.get(CostCategory.PERSONNEL, 0.0)
        if personnel_total > 20000:
            suggestion = self.create_suggestion(
                type=OptimizationType.AUTOMATE,
                title="Automate manual processes",
                description=f"High personnel costs (${personnel_total:,.2f}). Identify automation opportunities.",
                potential_savings=personnel_total * 0.2,
                category=CostCategory.PERSONNEL,
                priority=1,
            )
            suggestions.append(suggestion)

        return suggestions

    def get_savings_by_type(self) -> Dict[OptimizationType, float]:
        """Get potential savings grouped by optimization type."""
        result: Dict[OptimizationType, float] = {}
        for suggestion in self._suggestions.values():
            result[suggestion.type] = (
                result.get(suggestion.type, 0.0) + suggestion.potential_savings
            )
        return result

    def clear(self) -> None:
        """Clear all suggestions."""
        self._suggestions.clear()
