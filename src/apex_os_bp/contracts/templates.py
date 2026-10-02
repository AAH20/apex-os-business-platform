"""Contract templates feature."""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from .models import ContractParty, ContractType


@dataclass
class ContractTemplate:
    """A reusable contract template."""
    name: str
    contract_type: ContractType
    description: str = ""
    default_terms: list[str] = field(default_factory=list)
    default_clauses: dict[str, str] = field(default_factory=dict)
    default_value: float = 0.0
    default_currency: str = "USD"
    default_duration_days: int = 365
    default_auto_renew: bool = False
    default_renewal_notice_days: int = 30
    required_party_roles: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    is_active: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "contract_type": self.contract_type.value,
            "description": self.description,
            "default_terms": self.default_terms,
            "default_clauses": self.default_clauses,
            "default_value": self.default_value,
            "default_currency": self.default_currency,
            "default_duration_days": self.default_duration_days,
            "default_auto_renew": self.default_auto_renew,
            "default_renewal_notice_days": self.default_renewal_notice_days,
            "required_party_roles": self.required_party_roles,
            "tags": self.tags,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContractTemplate:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            contract_type=ContractType(data["contract_type"]),
            description=data.get("description", ""),
            default_terms=data.get("default_terms", []),
            default_clauses=data.get("default_clauses", {}),
            default_value=data.get("default_value", 0.0),
            default_currency=data.get("default_currency", "USD"),
            default_duration_days=data.get("default_duration_days", 365),
            default_auto_renew=data.get("default_auto_renew", False),
            default_renewal_notice_days=data.get("default_renewal_notice_days", 30),
            required_party_roles=data.get("required_party_roles", []),
            tags=data.get("tags", []),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", date.today().isoformat()),
        )


class TemplateManager:
    """Manages contract templates."""

    def __init__(self) -> None:
        self._templates: dict[str, ContractTemplate] = {}

    def create_template(
        self,
        name: str,
        contract_type: ContractType,
        description: str = "",
        default_terms: Optional[list[str]] = None,
        default_clauses: Optional[dict[str, str]] = None,
        default_value: float = 0.0,
        default_currency: str = "USD",
        default_duration_days: int = 365,
        default_auto_renew: bool = False,
        default_renewal_notice_days: int = 30,
        required_party_roles: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> ContractTemplate:
        """Create a new template."""
        template = ContractTemplate(
            name=name,
            contract_type=contract_type,
            description=description,
            default_terms=list(default_terms) if default_terms else [],
            default_clauses=dict(default_clauses) if default_clauses else {},
            default_value=default_value,
            default_currency=default_currency,
            default_duration_days=default_duration_days,
            default_auto_renew=default_auto_renew,
            default_renewal_notice_days=default_renewal_notice_days,
            required_party_roles=list(required_party_roles) if required_party_roles else [],
            tags=list(tags) if tags else [],
        )
        self._templates[template.id] = template
        return template

    def get_template(self, template_id: str) -> Optional[ContractTemplate]:
        """Retrieve a template by ID."""
        return self._templates.get(template_id)

    def get_templates_by_type(self, contract_type: ContractType) -> list[ContractTemplate]:
        """Get all active templates for a given contract type."""
        return [t for t in self._templates.values() if t.contract_type == contract_type and t.is_active]

    def list_templates(self, include_inactive: bool = False) -> list[ContractTemplate]:
        """List all templates."""
        if include_inactive:
            return list(self._templates.values())
        return [t for t in self._templates.values() if t.is_active]

    def update_template(self, template_id: str, **kwargs: Any) -> ContractTemplate:
        """Update template fields."""
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found.")
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template. Returns True if deleted."""
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def deactivate_template(self, template_id: str) -> ContractTemplate:
        """Deactivate a template (soft delete)."""
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found.")
        template.is_active = False
        return template

    def clone_template(self, template_id: str, new_name: str) -> ContractTemplate:
        """Clone an existing template with a new name."""
        original = self._templates.get(template_id)
        if original is None:
            raise ValueError(f"Template {template_id} not found.")
        cloned = copy.deepcopy(original)
        cloned.id = str(uuid.uuid4())
        cloned.name = new_name
        cloned.created_at = date.today().isoformat()
        self._templates[cloned.id] = cloned
        return cloned

    def apply_template(
        self,
        template_id: str,
        title: str,
        parties: list[ContractParty],
        start_date: date,
        value: Optional[float] = None,
        currency: Optional[str] = None,
        description: str = "",
        extra_terms: Optional[list[str]] = None,
        extra_clauses: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Apply a template to generate contract parameters."""
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found.")
        if not template.is_active:
            raise ValueError(f"Template {template_id} is inactive.")

        end_date = date.fromordinal(start_date.toordinal() + template.default_duration_days)

        terms = list(template.default_terms)
        if extra_terms:
            terms.extend(extra_terms)

        clauses = dict(template.default_clauses)
        if extra_clauses:
            clauses.update(extra_clauses)

        return {
            "title": title,
            "contract_type": template.contract_type,
            "parties": parties,
            "start_date": start_date,
            "end_date": end_date,
            "value": value if value is not None else template.default_value,
            "currency": currency if currency else template.default_currency,
            "description": description or template.description,
            "terms": terms,
            "clauses": clauses,
            "auto_renew": template.default_auto_renew,
            "renewal_notice_days": template.default_renewal_notice_days,
            "tags": list(template.tags),
        }

    def validate_parties_against_template(
        self, template_id: str, parties: list[ContractParty]
    ) -> list[str]:
        """Validate that parties satisfy the template's required roles."""
        template = self._templates.get(template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found.")
        errors: list[str] = []
        party_roles = {p.role for p in parties}
        for required_role in template.required_party_roles:
            if required_role not in party_roles:
                errors.append(f"Missing required party role: {required_role}")
        return errors
