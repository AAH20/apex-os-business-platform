"""Notification templates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class NotificationTemplate:
    """A notification template with variable substitution."""
    id: str
    name: str
    title_template: str
    body_template: str
    channels: List[str] = field(default_factory=list)
    default_priority: str = "normal"
    description: str = ""

    def render(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Render template with data."""
        return {
            "title": self._render_string(self.title_template, data),
            "body": self._render_string(self.body_template, data),
        }

    def _render_string(self, template: str, data: Dict[str, Any]) -> str:
        """Render a template string with variable substitution."""
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in data:
                return str(data[var_name])
            return match.group(0)

        return re.sub(r"\{\{\s*(\w+)\s*\}\}", replace_var, template)


class TemplateRegistry:
    """Registry of notification templates."""

    def __init__(self):
        self._templates: Dict[str, NotificationTemplate] = {}
        self._register_defaults()

    def register(self, template: NotificationTemplate) -> None:
        """Register a template."""
        self._templates[template.id] = template

    def get(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self) -> List[NotificationTemplate]:
        """List all registered templates."""
        return list(self._templates.values())

    def remove(self, template_id: str) -> bool:
        """Remove a template."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def render(self, template_id: str, data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Render a template by ID."""
        template = self.get(template_id)
        if template:
            return template.render(data)
        return None

    def _register_defaults(self) -> None:
        """Register default templates."""
        defaults = [
            NotificationTemplate(
                id="welcome",
                name="Welcome",
                title_template="Welcome, {{name}}!",
                body_template="Hi {{name}}, welcome to APEX-OS Business Platform.",
                channels=["email"],
                description="Sent when a new user registers",
            ),
            NotificationTemplate(
                id="password_reset",
                name="Password Reset",
                title_template="Password Reset Request",
                body_template="Hi {{name}}, click here to reset your password: {{reset_url}}",
                channels=["email"],
                description="Sent when user requests password reset",
            ),
            NotificationTemplate(
                id="order_confirmation",
                name="Order Confirmation",
                title_template="Order #{{order_id}} Confirmed",
                body_template="Hi {{name}}, your order #{{order_id}} for {{amount}} has been confirmed.",
                channels=["email", "push"],
                description="Sent when an order is confirmed",
            ),
            NotificationTemplate(
                id="payment_received",
                name="Payment Received",
                title_template="Payment Received - {{amount}}",
                body_template="Hi {{name}}, we received your payment of {{amount}} for invoice #{{invoice_id}}.",
                channels=["email"],
                description="Sent when a payment is received",
            ),
            NotificationTemplate(
                id="alert",
                name="System Alert",
                title_template="Alert: {{alert_type}}",
                body_template="System alert: {{message}}. Severity: {{severity}}.",
                channels=["email", "sms", "push"],
                description="System alert notification",
            ),
            NotificationTemplate(
                id="task_assigned",
                name="Task Assigned",
                title_template="New Task: {{task_name}}",
                body_template="Hi {{name}}, you have been assigned task: {{task_name}}. Due: {{due_date}}.",
                channels=["email", "push"],
                description="Sent when a task is assigned",
            ),
            NotificationTemplate(
                id="meeting_reminder",
                name="Meeting Reminder",
                title_template="Meeting Reminder: {{meeting_title}}",
                body_template="Reminder: {{meeting_title}} starts at {{start_time}}.",
                channels=["email", "push"],
                description="Meeting reminder notification",
            ),
            NotificationTemplate(
                id="invoice_overdue",
                name="Invoice Overdue",
                title_template="Invoice #{{invoice_id}} Overdue",
                body_template="Hi {{name}}, invoice #{{invoice_id}} for {{amount}} is overdue. Please pay by {{due_date}}.",
                channels=["email", "sms"],
                description="Sent when an invoice is overdue",
            ),
            NotificationTemplate(
                id="system_maintenance",
                name="System Maintenance",
                title_template="Scheduled Maintenance",
                body_template="System maintenance scheduled for {{maintenance_time}}. Duration: {{duration}}.",
                channels=["email", "push", "webhook"],
                description="System maintenance notification",
            ),
            NotificationTemplate(
                id="security_alert",
                name="Security Alert",
                title_template="Security Alert: {{alert_type}}",
                body_template="Security alert: {{message}}. If this wasn't you, contact support immediately.",
                channels=["email", "sms", "push"],
                description="Security-related alerts",
            ),
        ]
        for template in defaults:
            self.register(template)
