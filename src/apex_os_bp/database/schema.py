"""APEX-OS Business Platform — SQLAlchemy 2.0 relational schema."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint, Index, CheckConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AuditMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


# ── 1. Auth / RBAC ──────────────────────────────────────────────
class User(Base, AuditMixin):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime)
    roles: Mapped[list["Role"]] = relationship("Role", secondary="user_roles", back_populates="users")


class Role(Base, AuditMixin):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    users: Mapped[list["User"]] = relationship("User", secondary="user_roles", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship("Permission", secondary="role_permissions", back_populates="roles")


class Permission(Base, AuditMixin):
    __tablename__ = "permissions"
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    roles: Mapped[list["Role"]] = relationship("Role", secondary="role_permissions", back_populates="permissions")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


# ── 2. Accounting ───────────────────────────────────────────────
class Account(Base, AuditMixin):
    __tablename__ = "accounts"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    account_number: Mapped[str | None] = mapped_column(String(50), unique=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)


class JournalEntry(Base, AuditMixin):
    __tablename__ = "journal_entries"
    entry_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    total_debit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class JournalEntryLine(Base, AuditMixin):
    __tablename__ = "journal_entry_lines"
    entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False, index=True)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    debit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    credit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class Invoice(Base, AuditMixin):
    __tablename__ = "invoices"
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)


class Payment(Base, AuditMixin):
    __tablename__ = "payments"
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))


class TaxRate(Base, AuditMixin):
    __tablename__ = "tax_rates"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ── 3. CRM ──────────────────────────────────────────────────────
class Lead(Base, AuditMixin):
    __tablename__ = "leads"
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    source: Mapped[str | None] = mapped_column(String(50))


class Contact(Base, AuditMixin):
    __tablename__ = "contacts"
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str | None] = mapped_column(String(100))


class Opportunity(Base, AuditMixin):
    __tablename__ = "opportunities"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    stage: Mapped[str] = mapped_column(String(50), default="prospecting", nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    probability: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    close_date: Mapped[datetime | None] = mapped_column(DateTime)


class Activity(Base, AuditMixin):
    __tablename__ = "activities"
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True)


class Campaign(Base, AuditMixin):
    __tablename__ = "campaigns"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime | None] = mapped_column(DateTime)
    end_date: Mapped[datetime | None] = mapped_column(DateTime)
    budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="planned", nullable=False)


# ── 4. Dashboards & Reports ─────────────────────────────────────
class Dashboard(Base, AuditMixin):
    __tablename__ = "dashboards"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    layout: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Widget(Base, AuditMixin):
    __tablename__ = "widgets"
    dashboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dashboards.id"), nullable=False, index=True)
    widget_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    config: Mapped[str | None] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Report(Base, AuditMixin):
    __tablename__ = "reports"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    query: Mapped[str | None] = mapped_column(Text)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)


class ReportFilter(Base, AuditMixin):
    __tablename__ = "report_filters"
    report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("reports.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str | None] = mapped_column(String(500))


# ── 5. Agent / Messaging ────────────────────────────────────────
class Agent(Base, AuditMixin):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="idle", nullable=False)
    config: Mapped[str | None] = mapped_column(Text)


class Channel(Base, AuditMixin):
    __tablename__ = "channels"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Message(Base, AuditMixin):
    __tablename__ = "messages"
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Route(Base, AuditMixin):
    __tablename__ = "routes"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    target_agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AgentLog(Base, AuditMixin):
    __tablename__ = "agent_logs"
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text)


# ── 6. Data Catalog ─────────────────────────────────────────────
class Dataset(Base, AuditMixin):
    __tablename__ = "datasets"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    location: Mapped[str | None] = mapped_column(String(500))


class DataTable(Base, AuditMixin):
    __tablename__ = "data_tables"
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    schema_name: Mapped[str | None] = mapped_column(String(100))


class DataColumn(Base, AuditMixin):
    __tablename__ = "data_columns"
    table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_tables.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Partition(Base, AuditMixin):
    __tablename__ = "partitions"
    table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_tables.id"), nullable=False, index=True)
    partition_key: Mapped[str] = mapped_column(String(100), nullable=False)
    partition_value: Mapped[str] = mapped_column(String(200), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)


class Query(Base, AuditMixin):
    __tablename__ = "queries"
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)


class QueryResult(Base, AuditMixin):
    __tablename__ = "query_results"
    query_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False, index=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_data: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)


# ── 7. ML / AI ──────────────────────────────────────────────────
class Model(Base, AuditMixin):
    __tablename__ = "models"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(String(500))


class Experiment(Base, AuditMixin):
    __tablename__ = "experiments"
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)


class Feature(Base, AuditMixin):
    __tablename__ = "features"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    feature_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class FeatureValue(Base, AuditMixin):
    __tablename__ = "feature_values"
    feature_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("features.id"), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Prediction(Base, AuditMixin):
    __tablename__ = "predictions"
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False, index=True)
    input_data: Mapped[str | None] = mapped_column(Text)
    output_data: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ModelMetric(Base, AuditMixin):
    __tablename__ = "model_metrics"
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


# ── 8. Alerts & Notifications ───────────────────────────────────
class Alert(Base, AuditMixin):
    __tablename__ = "alerts"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    message: Mapped[str | None] = mapped_column(Text)


class AlertRule(Base, AuditMixin):
    __tablename__ = "alert_rules"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertHistory(Base, AuditMixin):
    __tablename__ = "alert_history"
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False, index=True)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    details: Mapped[str | None] = mapped_column(Text)


class Notification(Base, AuditMixin):
    __tablename__ = "notifications"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)


# ── 9. Audit & Sessions ─────────────────────────────────────────
class AuditLog(Base, AuditMixin):
    __tablename__ = "audit_logs"
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100))
    old_values: Mapped[str | None] = mapped_column(Text)
    new_values: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(45))


class Session(Base, AuditMixin):
    __tablename__ = "sessions"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))


class ApiKey(Base, AuditMixin):
    __tablename__ = "api_keys"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    scopes: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
