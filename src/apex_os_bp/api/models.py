"""Pydantic models for API request/response validation."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Auth Models ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1, max_length=256)


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class RegisterRequest(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: str
    roles: List[str] = []


# ─── CRM Models ───────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    """Contact creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    email: EmailStr
    phone: str = Field(default="", max_length=64)
    company: str = Field(default="", max_length=256)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContactUpdate(BaseModel):
    """Contact update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=64)
    company: Optional[str] = Field(default=None, max_length=256)
    metadata: Optional[Dict[str, Any]] = None


class ContactResponse(BaseModel):
    """Contact response model."""
    id: str
    name: str
    email: str
    phone: str = ""
    company: str = ""
    metadata: Dict[str, Any] = {}


class DealStage(str, Enum):
    """Deal stage enum."""
    LEAD = "lead"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class DealCreate(BaseModel):
    """Deal creation request."""
    title: str = Field(..., min_length=1, max_length=512)
    value: float = Field(..., gt=0)
    stage: DealStage = DealStage.LEAD
    contact_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DealUpdate(BaseModel):
    """Deal update request."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    value: Optional[float] = Field(default=None, gt=0)
    stage: Optional[DealStage] = None
    contact_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DealResponse(BaseModel):
    """Deal response model."""
    id: str
    title: str
    value: float
    stage: str
    contact_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PipelineResponse(BaseModel):
    """Pipeline response model."""
    total_deals: int
    total_value: float
    deals_by_stage: Dict[str, int]


# ─── Accounting Models ────────────────────────────────────────────────────────

class AccountType(str, Enum):
    """Account type enum."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    INCOME = "income"
    EXPENSE = "expense"


class AccountCreate(BaseModel):
    """Account creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    type: AccountType
    balance: float = 0.0


class AccountUpdate(BaseModel):
    """Account update request."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=256)
    type: Optional[AccountType] = None
    balance: Optional[float] = None


class AccountResponse(BaseModel):
    """Account response model."""
    id: str
    name: str
    type: str
    balance: float


class InvoiceItem(BaseModel):
    """Invoice line item."""
    description: str = Field(..., min_length=1, max_length=512)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)

    @property
    def amount(self) -> float:
        return self.quantity * self.unit_price


class InvoiceCreate(BaseModel):
    """Invoice creation request."""
    customer_id: str = Field(..., min_length=1, max_length=128)
    items: List[InvoiceItem] = Field(..., min_length=1)


class InvoiceResponse(BaseModel):
    """Invoice response model."""
    id: str
    customer_id: str
    items: List[Dict[str, Any]]
    total: float
    status: str


class JournalEntryLineCreate(BaseModel):
    """Journal entry line creation request."""
    account_id: str = Field(..., min_length=1, max_length=128)
    debit: float = Field(default=0.0, ge=0)
    credit: float = Field(default=0.0, ge=0)


class JournalEntryCreate(BaseModel):
    """Journal entry creation request."""
    description: str = Field(..., min_length=1, max_length=512)
    lines: List[JournalEntryLineCreate] = Field(..., min_length=2)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JournalEntryResponse(BaseModel):
    """Journal entry response model."""
    id: str
    description: str
    lines: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


class TrialBalanceResponse(BaseModel):
    """Trial balance response model."""
    trial_balance: float
    is_balanced: bool


# ─── Analytics Models ─────────────────────────────────────────────────────────

class MetricCreate(BaseModel):
    """Metric creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    value: float
    unit: str = Field(..., min_length=1, max_length=64)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricResponse(BaseModel):
    """Metric response model."""
    name: str
    value: float
    unit: str
    tags: List[str] = []
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DashboardCreate(BaseModel):
    """Dashboard creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DashboardResponse(BaseModel):
    """Dashboard response model."""
    name: str
    total_metrics: int
    metrics: List[Dict[str, Any]]


class AnalyticsReportResponse(BaseModel):
    """Analytics report response model."""
    metrics: Dict[str, Optional[float]]


# ─── Workflow Models ──────────────────────────────────────────────────────────

class WorkflowStepCreate(BaseModel):
    """Workflow step creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    action: str = Field(..., min_length=1, max_length=256)
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCreate(BaseModel):
    """Workflow creation request."""
    name: str = Field(..., min_length=1, max_length=256)
    steps: List[WorkflowStepCreate] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    """Workflow response model."""
    name: str
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any] = {}


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response model."""
    workflow: str
    status: str
    steps: List[Dict[str, Any]]


# ─── Health Models ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    version: str
    initialized: bool
    components: Dict[str, bool]


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str
    status_code: int
