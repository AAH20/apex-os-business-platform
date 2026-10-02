"""Budget management engine."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from apex_os_bp.cost_management.models import (
    Budget,
    BudgetAlert,
    BudgetPeriod,
    BudgetStatus,
    CostCategory,
)


class BudgetManager:
    """Manages budgets, tracks spending, and generates alerts."""

    def __init__(self):
        self._budgets: Dict[str, Budget] = {}
        self._alerts: Dict[str, BudgetAlert] = {}

    def add_budget(self, budget: Budget) -> Budget:
        """Add a budget."""
        self._budgets[budget.id] = budget
        return budget

    def create_budget(
        self,
        name: str,
        department_id: str,
        amount: float,
        currency: str,
        period: BudgetPeriod,
        start_date: datetime,
        end_date: datetime,
        category: Optional[CostCategory] = None,
        alert_threshold: float = 0.8,
        description: str = "",
    ) -> Budget:
        """Create and add a new budget."""
        budget = Budget.create(
            name=name,
            department_id=department_id,
            amount=amount,
            currency=currency,
            period=period,
            start_date=start_date,
            end_date=end_date,
            category=category,
            alert_threshold=alert_threshold,
            description=description,
        )
        return self.add_budget(budget)

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Get a budget by ID."""
        return self._budgets.get(budget_id)

    def get_all_budgets(self) -> List[Budget]:
        """Get all budgets."""
        return list(self._budgets.values())

    def get_budgets_by_department(self, department_id: str) -> List[Budget]:
        """Get budgets filtered by department."""
        return [b for b in self._budgets.values() if b.department_id == department_id]

    def get_budgets_by_category(self, category: CostCategory) -> List[Budget]:
        """Get budgets filtered by category."""
        return [b for b in self._budgets.values() if b.category == category]

    def get_budgets_by_status(self, status: BudgetStatus) -> List[Budget]:
        """Get budgets filtered by status."""
        return [b for b in self._budgets.values() if b.status == status]

    def get_active_budgets(self) -> List[Budget]:
        """Get all active budgets."""
        return [b for b in self._budgets.values() if b.status == BudgetStatus.ACTIVE]

    def get_exceeded_budgets(self) -> List[Budget]:
        """Get all exceeded budgets."""
        return [b for b in self._budgets.values() if b.is_exceeded]

    def get_near_limit_budgets(self) -> List[Budget]:
        """Get all budgets near their limit."""
        return [b for b in self._budgets.values() if b.is_near_limit and not b.is_exceeded]

    def remove_budget(self, budget_id: str) -> bool:
        """Remove a budget."""
        if budget_id in self._budgets:
            del self._budgets[budget_id]
            return True
        return False

    def activate_budget(self, budget_id: str) -> Budget:
        """Activate a budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        budget.activate()
        return budget

    def freeze_budget(self, budget_id: str) -> Budget:
        """Freeze a budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        budget.freeze()
        return budget

    def close_budget(self, budget_id: str) -> Budget:
        """Close a budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        budget.close()
        return budget

    def record_spend(
        self,
        budget_id: str,
        amount: float,
    ) -> Budget:
        """Record spending against a budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        if budget.status == BudgetStatus.FROZEN:
            raise ValueError(f"Budget is frozen: {budget_id}")
        if budget.status == BudgetStatus.CLOSED:
            raise ValueError(f"Budget is closed: {budget_id}")
        budget.add_spend(amount)
        self._check_alerts(budget)
        return budget

    def _check_alerts(self, budget: Budget) -> None:
        """Check and generate alerts for a budget."""
        if budget.is_exceeded:
            alert = BudgetAlert.create(
                budget_id=budget.id,
                message=f"Budget '{budget.name}' exceeded: ${budget.spent:,.2f} / ${budget.amount:,.2f}",
                severity="critical",
            )
            self._alerts[alert.id] = alert
        elif budget.is_near_limit:
            alert = BudgetAlert.create(
                budget_id=budget.id,
                message=f"Budget '{budget.name}' near limit: {budget.utilization_rate:.1%} utilized",
                severity="warning",
            )
            self._alerts[alert.id] = alert

    def get_alert(self, alert_id: str) -> Optional[BudgetAlert]:
        """Get an alert by ID."""
        return self._alerts.get(alert_id)

    def get_all_alerts(self) -> List[BudgetAlert]:
        """Get all alerts."""
        return list(self._alerts.values())

    def get_alerts_by_budget(self, budget_id: str) -> List[BudgetAlert]:
        """Get alerts filtered by budget."""
        return [a for a in self._alerts.values() if a.budget_id == budget_id]

    def get_unacknowledged_alerts(self) -> List[BudgetAlert]:
        """Get all unacknowledged alerts."""
        return [a for a in self._alerts.values() if not a.acknowledged]

    def get_critical_alerts(self) -> List[BudgetAlert]:
        """Get all critical alerts."""
        return [a for a in self._alerts.values() if a.severity == "critical"]

    def acknowledge_alert(self, alert_id: str) -> BudgetAlert:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if not alert:
            raise ValueError(f"Alert not found: {alert_id}")
        alert.acknowledge()
        return alert

    def acknowledge_all_alerts(self) -> int:
        """Acknowledge all alerts. Returns count."""
        count = 0
        for alert in self._alerts.values():
            if not alert.acknowledged:
                alert.acknowledge()
                count += 1
        return count

    def get_budget_summary(self, budget_id: str) -> Dict:
        """Get a summary of a budget's status."""
        budget = self._budgets.get(budget_id)
        if not budget:
            raise ValueError(f"Budget not found: {budget_id}")
        return {
            "id": budget.id,
            "name": budget.name,
            "amount": budget.amount,
            "spent": budget.spent,
            "remaining": budget.remaining,
            "utilization_rate": budget.utilization_rate,
            "status": budget.status.value,
            "is_exceeded": budget.is_exceeded,
            "is_near_limit": budget.is_near_limit,
        }

    def get_total_budget(self) -> float:
        """Get total budget amount across all budgets."""
        return sum(b.amount for b in self._budgets.values())

    def get_total_spent(self) -> float:
        """Get total spent across all budgets."""
        return sum(b.spent for b in self._budgets.values())

    def get_department_spending(self) -> Dict[str, float]:
        """Get total spending grouped by department."""
        result: Dict[str, float] = {}
        for budget in self._budgets.values():
            result[budget.department_id] = (
                result.get(budget.department_id, 0.0) + budget.spent
            )
        return result

    def get_period_budgets(self, period: BudgetPeriod) -> List[Budget]:
        """Get budgets filtered by period."""
        return [b for b in self._budgets.values() if b.period == period]

    def clear(self) -> None:
        """Clear all budgets and alerts."""
        self._budgets.clear()
        self._alerts.clear()
