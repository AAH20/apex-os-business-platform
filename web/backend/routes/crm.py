"""CRM Lead CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str = "new"
    source: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str
    source: Optional[str] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str


# Synthetic in-memory data store
_leads: List[dict] = [
    {
        "id": 1,
        "name": "Alice Johnson",
        "email": "alice@acme.com",
        "phone": "+1-555-0101",
        "company": "Acme Corp",
        "status": "new",
        "source": "website",
        "notes": "Interested in enterprise plan",
        "created_at": "2026-09-01T10:00:00",
        "updated_at": "2026-09-01T10:00:00",
    },
    {
        "id": 2,
        "name": "Bob Smith",
        "email": "bob@globex.com",
        "phone": "+1-555-0102",
        "company": "Globex Inc",
        "status": "contacted",
        "source": "referral",
        "notes": "Follow up next week",
        "created_at": "2026-09-02T14:30:00",
        "updated_at": "2026-09-05T09:15:00",
    },
    {
        "id": 3,
        "name": "Carol Davis",
        "email": "carol@initech.com",
        "phone": "+1-555-0103",
        "company": "Initech",
        "status": "qualified",
        "source": "webinar",
        "notes": "Budget approved, ready for demo",
        "created_at": "2026-09-03T11:00:00",
        "updated_at": "2026-09-10T16:45:00",
    },
    {
        "id": 4,
        "name": "David Lee",
        "email": "david@umbrella.com",
        "phone": "+1-555-0104",
        "company": "Umbrella Corp",
        "status": "new",
        "source": "cold_call",
        "notes": "Left voicemail",
        "created_at": "2026-09-04T08:20:00",
        "updated_at": "2026-09-04T08:20:00",
    },
    {
        "id": 5,
        "name": "Eve Martinez",
        "email": "eve@stark.com",
        "phone": "+1-555-0105",
        "company": "Stark Industries",
        "status": "converted",
        "source": "website",
        "notes": "Signed annual contract",
        "created_at": "2026-08-28T13:00:00",
        "updated_at": "2026-09-15T10:30:00",
    },
]
_next_id = 6


@router.get("/", response_model=dict)
def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
):
    """List all leads with pagination and optional status filter."""
    filtered = _leads
    if status:
        filtered = [lead for lead in filtered if lead["status"] == status]
    start = (page - 1) * per_page
    end = start + per_page
    items = filtered[start:end]
    return {
        "items": items,
        "total": len(filtered),
        "page": page,
        "per_page": per_page,
        "pages": (len(filtered) + per_page - 1) // per_page,
    }


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int):
    """Get a single lead by ID."""
    for lead in _leads:
        if lead["id"] == lead_id:
            return lead
    raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")


@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(lead: LeadCreate):
    """Create a new lead."""
    global _next_id
    now = datetime.utcnow().isoformat()
    new_lead = {
        "id": _next_id,
        **lead.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _leads.append(new_lead)
    _next_id += 1
    return new_lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, lead: LeadUpdate):
    """Update an existing lead."""
    for i, existing in enumerate(_leads):
        if existing["id"] == lead_id:
            updates = lead.model_dump(exclude_unset=True)
            _leads[i].update(updates)
            _leads[i]["updated_at"] = datetime.utcnow().isoformat()
            return _leads[i]
    raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int):
    """Delete a lead by ID."""
    for i, lead in enumerate(_leads):
        if lead["id"] == lead_id:
            _leads.pop(i)
            return
    raise HTTPException(status_code=404, detail=f"Lead {lead_id} not found")
