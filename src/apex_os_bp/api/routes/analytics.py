"""Analytics routes — metrics and dashboards."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apex_os_bp.analytics.engine import AnalyticsEngine, Metric
from apex_os_bp.api.models import (
    AnalyticsReportResponse,
    DashboardCreate,
    DashboardResponse,
    MetricCreate,
    MetricResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def get_analytics_engine(request: Request) -> AnalyticsEngine:
    """Get the analytics engine from the app state."""
    return request.app.state.analytics_engine


def _metric_to_response(metric: Metric) -> MetricResponse:
    """Convert a Metric model to a response."""
    return MetricResponse(
        name=metric.name,
        value=metric.value,
        unit=metric.unit,
        tags=metric.tags,
        timestamp=metric.timestamp,
        metadata=metric.metadata,
    )


@router.get("/metrics", response_model=List[MetricResponse])
async def list_metrics(
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> List[MetricResponse]:
    """List all tracked metrics (latest value per metric name)."""
    results = []
    for name in engine._metrics:
        metric = engine._metrics[name][-1] if engine._metrics[name] else None
        if metric:
            results.append(_metric_to_response(metric))
    return results


@router.post("/metrics", response_model=MetricResponse, status_code=status.HTTP_201_CREATED)
async def track_metric(
    body: MetricCreate,
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> MetricResponse:
    """Track a new metric value."""
    metric = engine.track(
        name=body.name,
        value=body.value,
        unit=body.unit,
        tags=body.tags,
        metadata=body.metadata,
    )
    return _metric_to_response(metric)


@router.get("/metrics/{name}", response_model=List[MetricResponse])
async def get_metric_history(
    name: str,
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> List[MetricResponse]:
    """Get the time series for a metric."""
    series = engine.time_series(name)
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric not found: {name}",
        )
    return [_metric_to_response(m) for m in series]


@router.get("/report", response_model=AnalyticsReportResponse)
async def get_report(
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> AnalyticsReportResponse:
    """Generate an analytics report."""
    return AnalyticsReportResponse(metrics=engine.report())


# ─── Dashboards ───────────────────────────────────────────────────────────────

@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> List[DashboardResponse]:
    """List all dashboards."""
    return [DashboardResponse(**d.summary()) for d in engine._dashboards.values()]


@router.post("/dashboards", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    body: DashboardCreate,
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> DashboardResponse:
    """Create a new dashboard."""
    dashboard = engine.create_dashboard(name=body.name, metadata=body.metadata)
    return DashboardResponse(**dashboard.summary())


@router.get("/dashboards/{name}", response_model=DashboardResponse)
async def get_dashboard(
    name: str,
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> DashboardResponse:
    """Get a dashboard by name."""
    dashboard = engine.get_dashboard(name)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard not found: {name}",
        )
    return DashboardResponse(**dashboard.summary())


@router.post("/dashboards/{name}/metrics", response_model=DashboardResponse)
async def add_metric_to_dashboard(
    name: str,
    body: MetricCreate,
    engine: AnalyticsEngine = Depends(get_analytics_engine),
) -> DashboardResponse:
    """Add a metric to a dashboard."""
    dashboard = engine.get_dashboard(name)
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard not found: {name}",
        )
    metric = Metric(
        name=body.name,
        value=body.value,
        unit=body.unit,
        tags=body.tags,
        metadata=body.metadata,
    )
    engine.add_metric_to_dashboard(name, metric)
    return DashboardResponse(**dashboard.summary())
