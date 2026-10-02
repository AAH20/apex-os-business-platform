"""FastAPI application factory for APEX-OS Business Platform."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from apex_os_bp.api.middleware.auth import AuthMiddleware
from apex_os_bp.api.middleware.rate_limit import RateLimitMiddleware
from apex_os_bp.api.routes import accounting, analytics, auth, crm, health, workflow
from apex_os_bp.core.config import Config
from apex_os_bp.security.auth import Authenticator

logger = logging.getLogger(__name__)


def create_api_app(config: Optional[Config] = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Optional configuration object.

    Returns:
        Configured FastAPI application.
    """
    config = config or Config()

    app = FastAPI(
        title="APEX-OS Business Platform API",
        description="REST API for the APEX-OS Business Platform",
        version=config.get("app.version", "0.1.0"),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Store config and version in app state
    app.state.version = config.get("app.version", "0.1.0")
    app.state.initialized = True

    # Initialize platform components
    from apex_os_bp.accounting.engine import AccountingEngine
    from apex_os_bp.analytics.engine import AnalyticsEngine
    from apex_os_bp.crm.engine import CRMEngine
    from apex_os_bp.workflow.engine import WorkflowEngine

    app.state.accounting_engine = AccountingEngine()
    app.state.crm_engine = CRMEngine()
    app.state.analytics_engine = AnalyticsEngine()
    app.state.workflow_engine = WorkflowEngine()
    app.state.authenticator = Authenticator()

    # Setup default accounting accounts
    from apex_os_bp.accounting.ledger import Account, AccountType
    import uuid

    ar_account = Account(
        id=str(uuid.uuid4()),
        name="Accounts Receivable",
        type=AccountType.ASSET,
    )
    revenue_account = Account(
        id=str(uuid.uuid4()),
        name="Revenue",
        type=AccountType.INCOME,
    )
    app.state.accounting_engine.add_account(ar_account)
    app.state.accounting_engine.add_account(revenue_account)

    # Setup default admin user
    admin_user = app.state.authenticator.register("admin", "admin@apex-os.local", "admin12345")
    app.state.authenticator.assign_role(admin_user.id, "admin")

    # Add middleware (order matters: rate limit first, then auth)
    # Note: add_middleware prepends to the stack, so we add auth first, then rate limit
    # This means rate limit runs first (outermost), then auth (innermost)
    app.add_middleware(
        AuthMiddleware,
        authenticator=app.state.authenticator,
        secret=config.get("security.jwt_secret", "change-me-in-production"),
    )
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=config.get("api.rate_limit.max_requests", 100),
        window_seconds=config.get("api.rate_limit.window_seconds", 60),
    )

    # Store auth middleware reference for token management
    # The middleware instance is stored in the class-level registry
    app.state.auth_middleware = AuthMiddleware.get_instance()

    # Include routers
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(crm.router, prefix="/api/v1")
    app.include_router(accounting.router, prefix="/api/v1")
    app.include_router(analytics.router, prefix="/api/v1")
    app.include_router(workflow.router, prefix="/api/v1")

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": errors,
                "status_code": 422,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected errors."""
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "status_code": 500,
            },
        )

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        """Initialize the application on startup."""
        logger.info("APEX-OS Business Platform API starting up...")

    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("APEX-OS Business Platform API shutting down...")

    return app
