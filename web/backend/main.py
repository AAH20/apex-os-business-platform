"""APEX-OS Business Platform - FastAPI Backend with CRUD API."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import importlib
import os

app = FastAPI(title="APEX-OS Business Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request validation
class ItemCreate(BaseModel):
    data: Dict[str, Any]


class ItemUpdate(BaseModel):
    data: Dict[str, Any]


# In-memory data stores
stores: Dict[str, List[Dict[str, Any]]] = {}


def parse_request_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Parse request body - handle both raw objects and {"data": {...}} wrapper."""
    if "data" in body and isinstance(body["data"], dict):
        return body["data"]
    return body


def get_store(name: str) -> List[Dict[str, Any]]:
    if name not in stores:
        stores[name] = []
    return stores[name]


def find_by_id(store: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    return next((item for item in store if item.get("id") == item_id), None)


# Error handlers
@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


# Health check
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# CRUD route factory - fixed closure bug with default args
def add_crud_routes(resource: str, route: str):
    @app.get(f"/api/{route}")
    def list_items(resource=resource):
        return get_store(resource)

    @app.get(f"/api/{route}/{{item_id}}")
    def get_item(item_id: str, resource=resource):
        item = find_by_id(get_store(resource), item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
        return item

    @app.post(f"/api/{route}", status_code=201)
    def create_item(body: Dict[str, Any], resource=resource):
        store = get_store(resource)
        item = parse_request_body(body)
        item.setdefault("id", f"{resource}-{len(store) + 1:04d}")
        store.append(item)
        return item

    @app.put(f"/api/{route}/{{item_id}}")
    def update_item(item_id: str, body: Dict[str, Any], resource=resource):
        item = find_by_id(get_store(resource), item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
        item.update(parse_request_body(body))
        return item

    @app.delete(f"/api/{route}/{{item_id}}")
    def delete_item(item_id: str, resource=resource):
        store = get_store(resource)
        item = find_by_id(store, item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Item '{item_id}' not found")
        store.remove(item)
        return {"deleted": True, "id": item_id}


# Register CRUD routes for all 8 pages
RESOURCES = [
    ("dashboard", "dashboard"),
    ("accounting", "accounting"),
    ("crm", "crm"),
    ("analytics", "analytics"),
    ("agent_reach", "agent-reach"),
    ("bigdata", "bigdata"),
    ("datascience", "datascience"),
    ("continuous_bi", "continuous-bi"),
]

for resource, route in RESOURCES:
    add_crud_routes(resource, route)


# Register route modules from routes/ directory
def register_route_modules():
    routes_dir = os.path.join(os.path.dirname(__file__), "routes")
    if not os.path.exists(routes_dir):
        return
    for filename in os.listdir(routes_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                module = importlib.import_module(f"routes.{module_name}")
                if hasattr(module, "router"):
                    app.include_router(module.router, tags=[module_name])
            except Exception:
                pass


register_route_modules()


# Initialize synthetic data
def init_data():
    stores["dashboard"] = [{"id": "dash-001", "metrics": [
        {"name": "Total Revenue", "value": 2400000, "change": 12.3, "trend": "up"},
        {"name": "Active Users", "value": 14832, "change": 8.7, "trend": "up"},
        {"name": "Conversion Rate", "value": 3.24, "change": 0.5, "trend": "up"},
        {"name": "Avg Order Value", "value": 127.50, "change": -2.1, "trend": "down"},
    ], "revenue_trend": [120, 135, 148, 162, 178, 195, 210, 225, 240, 255, 270, 285],
        "user_growth": [8200, 9100, 10200, 11400, 12300, 13100, 13800, 14200, 14500, 14700, 14800, 14832],
        "recent_activity": [
            {"action": "New order #12847", "user": "john@example.com", "time": "2 min ago"},
            {"action": "Payment received", "user": "jane@example.com", "time": "5 min ago"},
            {"action": "New user registered", "user": "bob@example.com", "time": "12 min ago"},
            {"action": "Report generated", "user": "system", "time": "18 min ago"},
        ]}]

    stores["accounting"] = [{"id": "acc-001", "accounts": [
        {"id": "1000", "name": "Cash", "type": "Asset", "balance": 125000.00},
        {"id": "1100", "name": "Accounts Receivable", "type": "Asset", "balance": 87500.00},
        {"id": "2000", "name": "Accounts Payable", "type": "Liability", "balance": 45000.00},
        {"id": "3000", "name": "Equity", "type": "Equity", "balance": 167500.00},
        {"id": "4000", "name": "Revenue", "type": "Revenue", "balance": 2400000.00},
        {"id": "5000", "name": "COGS", "type": "Expense", "balance": 960000.00},
    ], "journal_entries": [
        {"id": "JE001", "date": "2026-10-01", "debit": "Cash", "credit": "Revenue", "amount": 15000.00,
         "description": "Product sales"},
        {"id": "JE002", "date": "2026-10-01", "debit": "COGS", "credit": "Inventory", "amount": 6000.00,
         "description": "Cost of goods sold"},
        {"id": "JE003", "date": "2026-10-02", "debit": "Accounts Receivable", "credit": "Revenue", "amount": 25000.00,
         "description": "Invoice #1001"},
    ], "trial_balance": {"debits": 2400000.00, "credits": 2400000.00, "balanced": True}}]

    stores["crm"] = [{"id": "crm-001", "leads": [
        {"id": "L001", "name": "Acme Corp", "status": "Qualified", "score": 85, "value": 50000},
        {"id": "L002", "name": "TechStart Inc", "status": "Contacted", "score": 72, "value": 35000},
        {"id": "L003", "name": "Global Systems", "status": "New", "score": 45, "value": 75000},
        {"id": "L004", "name": "DataFlow LLC", "status": "Qualified", "score": 91, "value": 120000},
    ], "opportunities": [
        {"id": "OPP001", "name": "Enterprise License", "stage": "Negotiation", "value": 250000, "probability": 75},
        {"id": "OPP002", "name": "Team Expansion", "stage": "Proposal", "value": 85000, "probability": 50},
        {"id": "OPP003", "name": "Renewal", "stage": "Qualification", "value": 45000, "probability": 90},
    ], "forecast": {"q1": 380000, "q2": 420000, "q3": 475000, "q4": 510000}}]

    stores["analytics"] = [{"id": "ana-001", "kpis": [
        {"name": "Customer Acquisition Cost", "value": 45.20, "target": 50.00, "status": "good"},
        {"name": "Lifetime Value", "value": 1250, "target": 1000, "status": "good"},
        {"name": "Churn Rate", "value": 2.1, "target": 3.0, "status": "good"},
        {"name": "NPS Score", "value": 72, "target": 70, "status": "good"},
    ], "anomalies": [
        {"metric": "Revenue", "date": "2026-10-15", "expected": 280000, "actual": 320000, "deviation": "+14.3%"},
        {"metric": "Users", "date": "2026-10-20", "expected": 14500, "actual": 12800, "deviation": "-11.7%"},
    ], "forecasts": [
        {"metric": "Revenue", "current": 2400000, "forecast_30d": 2650000, "forecast_90d": 3100000},
        {"metric": "Users", "current": 14832, "forecast_30d": 16200, "forecast_90d": 18500},
    ]}]

    stores["agent_reach"] = [{"id": "ar-001", "agents": [
        {"id": "agent-001", "name": "Data Processor", "status": "active", "messages_processed": 15420,
         "latency_ms": 12},
        {"id": "agent-002", "name": "Report Generator", "status": "active", "messages_processed": 8930,
         "latency_ms": 45},
        {"id": "agent-003", "name": "Alert Manager", "status": "idle", "messages_processed": 3210, "latency_ms": 8},
        {"id": "agent-004", "name": "ML Predictor", "status": "active", "messages_processed": 22100,
         "latency_ms": 120},
    ], "channels": [
        {"id": "ch-001", "name": "Orders", "type": "pubsub", "throughput": 1250},
        {"id": "ch-002", "name": "Notifications", "type": "pubsub", "throughput": 3400},
        {"id": "ch-003", "name": "ML Pipeline", "type": "stream", "throughput": 890},
    ], "routes": [
        {"source": "agent-001", "target": "agent-002", "messages": 5420, "success_rate": 99.8},
        {"source": "agent-002", "target": "agent-004", "messages": 3210, "success_rate": 99.5},
        {"source": "agent-003", "target": "agent-001", "messages": 1890, "success_rate": 99.9},
    ]}]

    stores["bigdata"] = [{"id": "bd-001", "datasets": [
        {"name": "transactions", "size": "2.4 TB", "rows": 15000000000, "format": "Parquet"},
        {"name": "user_events", "size": "890 GB", "rows": 45000000000, "format": "Delta Lake"},
        {"name": "product_catalog", "size": "12 GB", "rows": 5000000, "format": "Iceberg"},
    ], "queries": [
        {"id": "Q001", "type": "SELECT", "duration_ms": 245, "rows_scanned": 1500000, "status": "completed"},
        {"id": "Q002", "type": "JOIN", "duration_ms": 1890, "rows_scanned": 50000000, "status": "completed"},
        {"id": "Q003", "type": "AGGREGATE", "duration_ms": 567, "rows_scanned": 2500000, "status": "running"},
    ], "storage": {"total_tb": 3.3, "used_tb": 2.1, "compression_ratio": 4.2}}]

    stores["datascience"] = [{"id": "ds-001", "models": [
        {"name": "revenue_forecaster", "type": "XGBoost", "accuracy": 0.94, "last_trained": "2026-10-01",
         "status": "production"},
        {"name": "churn_predictor", "type": "LightGBM", "accuracy": 0.89, "last_trained": "2026-09-28",
         "status": "production"},
        {"name": "recommendation_engine", "type": "Neural CF", "accuracy": 0.82, "last_trained": "2026-09-25",
         "status": "staging"},
    ], "experiments": [
        {"id": "EXP001", "name": "Feature Engineering v2", "status": "running", "progress": 67},
        {"id": "EXP002", "name": "Hyperparameter Tuning", "status": "completed",
         "best_params": {"lr": 0.01, "epochs": 100}},
        {"id": "EXP003", "name": "A/B Test: New UI", "status": "running", "progress": 45},
    ], "features": [
        {"name": "user_age_days", "type": "numeric", "importance": 0.15},
        {"name": "purchase_frequency", "type": "numeric", "importance": 0.28},
        {"name": "avg_order_value", "type": "numeric", "importance": 0.22},
        {"name": "days_since_last_purchase", "type": "numeric", "importance": 0.18},
    ]}]

    stores["continuous_bi"] = [{"id": "cbi-001", "dashboards": [
        {"name": "Executive Summary", "widgets": 8, "refresh_rate": "5s", "viewers": 45},
        {"name": "Sales Performance", "widgets": 12, "refresh_rate": "10s", "viewers": 128},
        {"name": "Marketing Analytics", "widgets": 6, "refresh_rate": "30s", "viewers": 67},
        {"name": "Operations Monitor", "widgets": 15, "refresh_rate": "1s", "viewers": 23},
    ], "alerts": [
        {"name": "Revenue Drop", "condition": "revenue < 90% of forecast", "severity": "critical", "enabled": True},
        {"name": "User Spike", "condition": "new_users > 150% of average", "severity": "warning", "enabled": True},
        {"name": "System Latency", "condition": "p99_latency > 500ms", "severity": "warning", "enabled": True},
    ], "data_freshness": {"last_update": "2026-10-02T22:55:00Z", "lag_seconds": 3, "status": "healthy"}}]


init_data()


@app.get("/api/all")
def get_all_data():
    return {key: get_store(key) for key in stores}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
