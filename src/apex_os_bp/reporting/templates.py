"""Report templates — pre-built report templates and template registry."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apex_os_bp.reporting.builder import (
    ReportColumn,
    ReportDefinition,
    ReportFilter,
    ReportType,
)


@dataclass
class ReportTemplate:
    """A reusable report template."""

    name: str
    description: str
    report_type: ReportType
    columns: list[ReportColumn]
    data_source: str
    default_filters: list[ReportFilter] = field(default_factory=list)
    default_group_by: list[str] = field(default_factory=list)
    default_order_by: list[str] = field(default_factory=list)
    default_limit: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1

    def instantiate(
        self,
        name: str | None = None,
        filters: list[ReportFilter] | None = None,
        group_by: list[str] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReportDefinition:
        """Create a report definition from this template."""
        merged_metadata = {**self.metadata, **(metadata or {})}
        return ReportDefinition(
            name=name or self.name,
            report_type=self.report_type,
            columns=list(self.columns),
            data_source=self.data_source,
            filters=filters if filters is not None else list(self.default_filters),
            group_by=group_by if group_by is not None else list(self.default_group_by),
            order_by=order_by if order_by is not None else list(self.default_order_by),
            limit=limit if limit is not None else self.default_limit,
            metadata=merged_metadata,
        )


class TemplateRegistry:
    """Registry of available report templates."""

    def __init__(self) -> None:
        self._templates: dict[str, ReportTemplate] = {}
        self._register_defaults()

    def register(self, template: ReportTemplate) -> None:
        """Register a template."""
        self._templates[template.id] = template

    def unregister(self, template_id: str) -> bool:
        """Remove a template from the registry."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def get(self, template_id: str) -> ReportTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def get_by_name(self, name: str) -> ReportTemplate | None:
        """Get a template by name."""
        for t in self._templates.values():
            if t.name == name:
                return t
        return None

    def list_templates(
        self, report_type: ReportType | None = None
    ) -> list[ReportTemplate]:
        """List all templates, optionally filtered by type."""
        templates = list(self._templates.values())
        if report_type is not None:
            templates = [t for t in templates if t.report_type == report_type]
        return templates

    def create_from_template(
        self,
        template_id: str,
        name: str | None = None,
        filters: list[ReportFilter] | None = None,
        group_by: list[str] | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReportDefinition | None:
        """Create a report definition from a registered template."""
        template = self._templates.get(template_id)
        if template is None:
            return None
        return template.instantiate(
            name=name,
            filters=filters,
            group_by=group_by,
            order_by=order_by,
            limit=limit,
            metadata=metadata,
        )

    def _register_defaults(self) -> None:
        """Register built-in default templates."""
        self.register(ReportTemplate(
            name="Sales Summary",
            description="Summary of sales by region and product",
            report_type=ReportType.SUMMARY,
            data_source="sales_db",
            columns=[
                ReportColumn("region", "Region", "string"),
                ReportColumn("product", "Product", "string"),
                ReportColumn("total_sales", "Total Sales", "number"),
                ReportColumn("order_count", "Order Count", "integer"),
                ReportColumn("avg_order_value", "Avg Order Value", "number"),
            ],
            default_group_by=["region", "product"],
            default_order_by=["-total_sales"],
            default_limit=100,
            metadata={"category": "sales", "icon": "chart-bar"},
        ))
        self.register(ReportTemplate(
            name="User Activity",
            description="User login and activity report",
            report_type=ReportType.ANALYTICS,
            data_source="user_db",
            columns=[
                ReportColumn("user_id", "User ID", "string"),
                ReportColumn("username", "Username", "string"),
                ReportColumn("login_count", "Login Count", "integer"),
                ReportColumn("last_login", "Last Login", "datetime"),
                ReportColumn("actions", "Actions", "integer"),
            ],
            default_order_by=["-login_count"],
            default_limit=500,
            metadata={"category": "users", "icon": "users"},
        ))
        self.register(ReportTemplate(
            name="Audit Trail",
            description="System audit trail report",
            report_type=ReportType.AUDIT,
            data_source="audit_log",
            columns=[
                ReportColumn("timestamp", "Timestamp", "datetime"),
                ReportColumn("user", "User", "string"),
                ReportColumn("action", "Action", "string"),
                ReportColumn("resource", "Resource", "string"),
                ReportColumn("details", "Details", "string"),
                ReportColumn("ip_address", "IP Address", "string"),
            ],
            default_order_by=["-timestamp"],
            default_limit=1000,
            metadata={"category": "security", "icon": "shield"},
        ))
        self.register(ReportTemplate(
            name="Revenue Detail",
            description="Detailed revenue breakdown",
            report_type=ReportType.DETAIL,
            data_source="finance_db",
            columns=[
                ReportColumn("date", "Date", "date"),
                ReportColumn("revenue", "Revenue", "number"),
                ReportColumn("expenses", "Expenses", "number"),
                ReportColumn("profit", "Profit", "number"),
                ReportColumn("margin", "Margin %", "number"),
            ],
            default_order_by=["-date"],
            default_limit=365,
            metadata={"category": "finance", "icon": "dollar"},
        ))
        self.register(ReportTemplate(
            name="Inventory Status",
            description="Current inventory levels and alerts",
            report_type=ReportType.SUMMARY,
            data_source="inventory_db",
            columns=[
                ReportColumn("sku", "SKU", "string"),
                ReportColumn("product_name", "Product Name", "string"),
                ReportColumn("quantity", "Quantity", "integer"),
                ReportColumn("reorder_level", "Reorder Level", "integer"),
                ReportColumn("status", "Status", "string"),
            ],
            default_filters=[
                ReportFilter("status", "in", ["low", "out_of_stock"]),
            ],
            default_order_by=["quantity"],
            default_limit=200,
            metadata={"category": "inventory", "icon": "box"},
        ))
