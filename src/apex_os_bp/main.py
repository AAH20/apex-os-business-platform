"""APEX-OS Business Platform — Main Application."""
from __future__ import annotations

import logging
from typing import Optional

from apex_os_bp.core.config import Config
from apex_os_bp.core.event_bus import EventBus
from apex_os_bp.accounting.engine import AccountingEngine
from apex_os_bp.crm.engine import CRMEngine
from apex_os_bp.analytics.engine import AnalyticsEngine
from apex_os_bp.integration.gateway import APIGateway, RateLimiter
from apex_os_bp.integration.workflow import WorkflowEngine
from apex_os_bp.security.auth import Authenticator
from apex_os_bp.security.vault import SecretVault
from apex_os_bp.workflow.engine import WorkflowEngine as WorkflowEngineV2

logger = logging.getLogger(__name__)


class ApexOSBusinessPlatform:
    """APEX-OS Business Platform — Unified business operations platform."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.event_bus = EventBus()
        self.accounting = AccountingEngine()
        self.crm = CRMEngine()
        self.analytics = AnalyticsEngine()
        self.api_gateway = APIGateway()
        self.workflow_engine = WorkflowEngine()
        self.auth = Authenticator()
        self.vault = SecretVault()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the platform."""
        logging.basicConfig(
            level=self.config.get("logging.level", "INFO"),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        logger.info("APEX-OS Business Platform initializing...")
        logger.info(f"Version: {self.config.get('app.version')}")
        self._setup_default_routes()
        self._setup_default_workflows()
        self._initialized = True
        logger.info("APEX-OS Business Platform initialized successfully")

    def _setup_default_routes(self) -> None:
        """Setup default API routes."""
        from apex_os_bp.integration.gateway import Route
        routes = [
            Route(path="/api/v1/accounting/invoices", method="GET", handler="list_invoices"),
            Route(path="/api/v1/accounting/invoices", method="POST", handler="create_invoice"),
            Route(path="/api/v1/crm/contacts", method="GET", handler="list_contacts"),
            Route(path="/api/v1/crm/contacts", method="POST", handler="create_contact"),
            Route(path="/api/v1/crm/deals", method="GET", handler="list_deals"),
            Route(path="/api/v1/analytics/metrics", method="GET", handler="get_metrics"),
            Route(path="/api/v1/health", method="GET", handler="health_check"),
        ]
        for route in routes:
            self.api_gateway.add_route(route)

    def _setup_default_workflows(self) -> None:
        """Setup default workflows."""
        from apex_os_bp.integration.workflow import WorkflowStep
        lead_to_cash = self.workflow_engine.create_workflow("lead_to_cash")
        lead_to_cash.add_step(WorkflowStep(name="capture_lead", action="crm.create_contact"))
        lead_to_cash.add_step(WorkflowStep(name="qualify_lead", action="crm.advance_stage"))
        lead_to_cash.add_step(WorkflowStep(name="create_deal", action="crm.create_deal"))
        lead_to_cash.add_step(WorkflowStep(name="generate_invoice", action="accounting.create_invoice"))
        lead_to_cash.add_step(WorkflowStep(name="track_revenue", action="analytics.track"))

    def health_check(self) -> dict:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": self.config.get("app.version"),
            "initialized": self._initialized,
            "components": {
                "accounting": self.accounting is not None,
                "crm": self.crm is not None,
                "analytics": self.analytics is not None,
                "api_gateway": self.api_gateway is not None,
                "workflow_engine": self.workflow_engine is not None,
                "auth": self.auth is not None,
                "vault": self.vault is not None,
            },
        }

    def shutdown(self) -> None:
        """Shutdown the platform."""
        logger.info("APEX-OS Business Platform shutting down...")
        self._initialized = False
        logger.info("APEX-OS Business Platform shutdown complete")


def create_app(config: Optional[Config] = None) -> ApexOSBusinessPlatform:
    """Application factory."""
    app = ApexOSBusinessPlatform(config)
    app.initialize()
    return app


if __name__ == "__main__":
    app = create_app()
    print(f"APEX-OS Business Platform v{app.config.get('app.version')}")
    print(f"Health: {app.health_check()}")
