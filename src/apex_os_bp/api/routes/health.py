"""Health check routes."""
from __future__ import annotations

from fastapi import APIRouter, Request

from apex_os_bp.api.models import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check endpoint."""
    app = request.app
    return HealthResponse(
        status="healthy",
        version=getattr(app.state, "version", "0.1.0"),
        initialized=getattr(app.state, "initialized", False),
        components={
            "accounting": getattr(app.state, "accounting_engine", None) is not None,
            "crm": getattr(app.state, "crm_engine", None) is not None,
            "analytics": getattr(app.state, "analytics_engine", None) is not None,
            "workflow": getattr(app.state, "workflow_engine", None) is not None,
            "auth": getattr(app.state, "authenticator", None) is not None,
        },
    )
