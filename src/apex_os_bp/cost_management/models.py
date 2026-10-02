"""Cost management data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional


class CostCategory(Enum):
    """Cost category types."""
    INFRASTRUCTURE = "infrastructure"
    PERSONNEL = "personnel"
    MARKETING = "marketing"
    OPERATIONS = "operations"
    RESEARCH = "research"
    SALES = "sales"
    ADMINISTRATIVE = "administrative"
    UTILITIES = "utilities"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    TRAVEL = "travel"
    TRAINING = "training"
    MISCELLANEOUS = "miscellaneous"


class CostStatus(Enum):
    """Cost entry status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class AllocationMethod(Enum):
    """Cost allocation methods."""
    EQUAL = "equal"
    PERCENTAGE = "percentage"
    USAGE_BASED = "usage_based"
    HEADCOUNT = "headcount"
    REVENUE_BASED = "revenue_based"
    CUSTOM = "custom"


class BudgetPeriod(Enum):
    """Budget period types."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetStatus(Enum):
    """Budget status."""
    DRAFT = "draft"
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"
    EXCEEDED = "exceeded"


class ForecastMethod(Enum):
    """Cost forecasting methods."""
    MOVING_AVERAGE = "moving_average"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    SEASONAL = "seasonal"


class OptimizationType(Enum):
    """Cost optimization suggestion types."""
    REDUCE = "reduce"
    ELIMINATE = "eliminate"
    CONSOLIDATE = "consolidate"
    RENEGOTIATE = "renegotiate"
    AUTOMATE = "automate"
    OUTSOURCE = "outsource"


@dataclass
class CostEntry:
    """Individual cost entry."""
    id: str
    category: CostCategory
    amount: float
    currency: str
    description: str
    department_id: Optional[str] = None
    project_id: Optional[str] = None
    vendor_id: Optional[str] = None
    status: CostStatus = CostStatus.PENDING
    incurred_date: datetime = field(default_factory=datetime.now)
    approved_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        category: CostCategory,
        amount: float,
        currency: str,
        description: str,
        department_id: Optional[str] = None,
        project_id: Optional[str] = None,
        vendor_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ) -> CostEntry:
        """Create a new cost entry."""
        return cls(
            id=str(uuid.uuid4()),
            category=category,
            amount=amount,
            currency=currency,
            description=description,
            department_id=department_id,
            project_id=project_id,
            vendor_id=vendor_id,
            tags=tags or [],
            metadata=metadata or {},
        )

    def approve(self) -> None:
        """Approve the cost entry."""
        self.status = CostStatus.APPROVED
        self.approved_date = datetime.now()

    def reject(self) -> None:
        """Reject the cost entry."""
        self.status = CostStatus.REJECTED

    def mark_paid(self) -> None:
        """Mark the cost entry as paid."""
        self.status = CostStatus.PAID

    def cancel(self) -> None:
        """Cancel the cost entry."""
        self.status = CostStatus.CANCELLED


@dataclass
class AllocationRule:
    """Cost allocation rule."""
    id: str
    name: str
    source_department_id: str
    target_department_ids: List[str]
    method: AllocationMethod
    percentages: Dict[str, float] = field(default_factory=dict)
    category_filter: Optional[List[CostCategory]] = None
    active: bool = True

    @classmethod
    def create(
        cls,
        name: str,
        source_department_id: str,
        target_department_ids: List[str],
        method: AllocationMethod,
        percentages: Optional[Dict[str, float]] = None,
        category_filter: Optional[List[CostCategory]] = None,
    ) -> AllocationRule:
        """Create a new allocation rule."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            source_department_id=source_department_id,
            target_department_ids=target_department_ids,
            method=method,
            percentages=percentages or {},
            category_filter=category_filter,
        )


@dataclass
class AllocationResult:
    """Result of a cost allocation."""
    id: str
    rule_id: str
    source_cost_id: str
    allocations: Dict[str, float]
    total_allocated: float
    allocated_date: datetime = field(default_factory=datetime.now)

    @classmethod
    def create(
        cls,
        rule_id: str,
        source_cost_id: str,
        allocations: Dict[str, float],
    ) -> AllocationResult:
        """Create a new allocation result."""
        return cls(
            id=str(uuid.uuid4()),
            rule_id=rule_id,
            source_cost_id=source_cost_id,
            allocations=allocations,
            total_allocated=sum(allocations.values()),
        )


@dataclass
class Budget:
    """Budget definition."""
    id: str
    name: str
    department_id: str
    category: Optional[CostCategory]
    amount: float
    currency: str
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime
    status: BudgetStatus = BudgetStatus.DRAFT
    spent: float = 0.0
    alert_threshold: float = 0.8
    description: str = ""
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
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
        """Create a new budget."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            department_id=department_id,
            category=category,
            amount=amount,
            currency=currency,
            period=period,
            start_date=start_date,
            end_date=end_date,
            alert_threshold=alert_threshold,
            description=description,
        )

    @property
    def remaining(self) -> float:
        """Get remaining budget amount."""
        return self.amount - self.spent

    @property
    def utilization_rate(self) -> float:
        """Get budget utilization rate."""
        if self.amount == 0:
            return 0.0
        return self.spent / self.amount

    @property
    def is_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        return self.spent > self.amount

    @property
    def is_near_limit(self) -> bool:
        """Check if budget is near its limit."""
        return self.utilization_rate >= self.alert_threshold

    def add_spend(self, amount: float) -> None:
        """Add spend to the budget."""
        self.spent += amount
        if self.is_exceeded:
            self.status = BudgetStatus.EXCEEDED

    def activate(self) -> None:
        """Activate the budget."""
        self.status = BudgetStatus.ACTIVE

    def freeze(self) -> None:
        """Freeze the budget."""
        self.status = BudgetStatus.FROZEN

    def close(self) -> None:
        """Close the budget."""
        self.status = BudgetStatus.CLOSED


@dataclass
class BudgetAlert:
    """Budget alert."""
    id: str
    budget_id: str
    message: str
    severity: str
    triggered_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False

    @classmethod
    def create(
        cls,
        budget_id: str,
        message: str,
        severity: str = "warning",
    ) -> BudgetAlert:
        """Create a new budget alert."""
        return cls(
            id=str(uuid.uuid4()),
            budget_id=budget_id,
            message=message,
            severity=severity,
        )

    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.acknowledged = True


@dataclass
class ForecastResult:
    """Cost forecast result."""
    id: str
    method: ForecastMethod
    category: Optional[CostCategory]
    department_id: Optional[str]
    forecast_periods: List[float]
    confidence_interval_lower: List[float]
    confidence_interval_upper: List[float]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        method: ForecastMethod,
        forecast_periods: List[float],
        confidence_interval_lower: List[float],
        confidence_interval_upper: List[float],
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> ForecastResult:
        """Create a new forecast result."""
        return cls(
            id=str(uuid.uuid4()),
            method=method,
            category=category,
            department_id=department_id,
            forecast_periods=forecast_periods,
            confidence_interval_lower=confidence_interval_lower,
            confidence_interval_upper=confidence_interval_upper,
            metadata=metadata or {},
        )

    @property
    def total_forecast(self) -> float:
        """Get total forecasted cost."""
        return sum(self.forecast_periods)


@dataclass
class OptimizationSuggestion:
    """Cost optimization suggestion."""
    id: str
    type: OptimizationType
    title: str
    description: str
    potential_savings: float
    currency: str
    category: Optional[CostCategory] = None
    department_id: Optional[str] = None
    priority: int = 5
    implemented: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        type: OptimizationType,
        title: str,
        description: str,
        potential_savings: float,
        currency: str = "USD",
        category: Optional[CostCategory] = None,
        department_id: Optional[str] = None,
        priority: int = 5,
    ) -> OptimizationSuggestion:
        """Create a new optimization suggestion."""
        return cls(
            id=str(uuid.uuid4()),
            type=type,
            title=title,
            description=description,
            potential_savings=potential_savings,
            currency=currency,
            category=category,
            department_id=department_id,
            priority=priority,
        )

    def mark_implemented(self) -> None:
        """Mark the suggestion as implemented."""
        self.implemented = True
