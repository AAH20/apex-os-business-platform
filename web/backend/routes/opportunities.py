"""Opportunity CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

_opportunities_db = {
    1: {"id": 1, "title": "Enterprise Deal - Acme Corp", "value": 50000.0,
        "stage": "qualification", "probability": 0.3, "contact_email": "buyer@acme.com",
        "is_active": True, "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "title": "Expansion - Globex Inc", "value": 25000.0,
        "stage": "proposal", "probability": 0.6, "contact_email": "cto@globex.com",
        "is_active": True, "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "title": "New Logo - Initech", "value": 15000.0,
        "stage": "closed_won", "probability": 1.0, "contact_email": "vp@initech.com",
        "is_active": True, "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "title": "Renewal - Umbrella Co", "value": 30000.0,
        "stage": "negotiation", "probability": 0.8, "contact_email": "ops@umbrella.com",
        "is_active": True, "created_at": "2024-04-05T16:45:00"},
    5: {"id": 5, "title": "Pilot - Stark Industries", "value": 10000.0,
        "stage": "closed_lost", "probability": 0.0, "contact_email": "procurement@stark.com",
        "is_active": False, "created_at": "2024-05-12T11:20:00"},
}
_next_id = 6


class OpportunityCreate(BaseModel):
    title: str
    value: float
    stage: str = "qualification"
    probability: float = 0.0
    contact_email: str = ""
    is_active: bool = True


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    value: Optional[float] = None
    stage: Optional[str] = None
    probability: Optional[float] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None


class OpportunityResponse(BaseModel):
    id: int
    title: str
    value: float
    stage: str
    probability: float
    contact_email: str
    is_active: bool
    created_at: str


@router.get("/", response_model=list[OpportunityResponse])
async def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    stage: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all opportunities with pagination and optional filters."""
    opps = list(_opportunities_db.values())
    if stage:
        opps = [o for o in opps if o["stage"] == stage]
    if is_active is not None:
        opps = [o for o in opps if o["is_active"] == is_active]
    return opps[skip : skip + limit]


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: int):
    """Get a single opportunity by ID."""
    opp = _opportunities_db.get(opportunity_id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")
    return opp


@router.post("/", response_model=OpportunityResponse, status_code=201)
async def create_opportunity(opportunity: OpportunityCreate):
    """Create a new opportunity."""
    global _next_id
    new_opp = {
        "id": _next_id,
        "title": opportunity.title,
        "value": opportunity.value,
        "stage": opportunity.stage,
        "probability": opportunity.probability,
        "contact_email": opportunity.contact_email,
        "is_active": opportunity.is_active,
        "created_at": datetime.utcnow().isoformat(),
    }
    _opportunities_db[_next_id] = new_opp
    _next_id += 1
    return new_opp


@router.put("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(opportunity_id: int, opportunity: OpportunityUpdate):
    """Update an existing opportunity."""
    existing = _opportunities_db.get(opportunity_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")
    for field, value in opportunity.model_dump(exclude_unset=True).items():
        existing[field] = value
    return existing


@router.delete("/{opportunity_id}", status_code=204)
async def delete_opportunity(opportunity_id: int):
    """Delete an opportunity by ID."""
    if opportunity_id not in _opportunities_db:
        raise HTTPException(status_code=404, detail=f"Opportunity {opportunity_id} not found")
    del _opportunities_db[opportunity_id]
