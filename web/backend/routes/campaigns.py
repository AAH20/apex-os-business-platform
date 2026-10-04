"""Campaign CRUD API endpoints for APEX-OS Business Platform."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_campaigns_db = {
    1: {"id": 1, "name": "Q1 Product Launch", "channel": "email", "status": "active",
        "budget": 10000.0, "start_date": "2024-01-01", "end_date": "2024-03-31",
        "is_active": True, "created_at": "2024-01-15T10:30:00"},
    2: {"id": 2, "name": "Spring Webinar Series", "channel": "webinar", "status": "completed",
        "budget": 5000.0, "start_date": "2024-02-01", "end_date": "2024-04-30",
        "is_active": True, "created_at": "2024-02-20T14:00:00"},
    3: {"id": 3, "name": "Summer Sale Promo", "channel": "social", "status": "draft",
        "budget": 8000.0, "start_date": "2024-06-01", "end_date": "2024-08-31",
        "is_active": True, "created_at": "2024-03-10T09:15:00"},
    4: {"id": 4, "name": "Partner Outreach", "channel": "email", "status": "paused",
        "budget": 3000.0, "start_date": "2024-04-01", "end_date": "2024-06-30",
        "is_active": False, "created_at": "2024-04-05T16:45:00"},
    5: {"id": 5, "name": "Year-End Conference", "channel": "event", "status": "active",
        "budget": 25000.0, "start_date": "2024-10-01", "end_date": "2024-12-15",
        "is_active": True, "created_at": "2024-05-12T11:20:00"},
}
_next_id = 6


class CampaignCreate(BaseModel):
    name: str
    channel: str
    status: str = "draft"
    budget: float = 0.0
    start_date: str = ""
    end_date: str = ""
    is_active: bool = True


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    budget: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    channel: str
    status: str
    budget: float
    start_date: str
    end_date: str
    is_active: bool
    created_at: str


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> list[CampaignResponse]:
    """List all campaigns with pagination and optional filters."""
    try:
        campaigns = list(_campaigns_db.values())
        if status:
            campaigns = [c for c in campaigns if c["status"] == status]
        if channel:
            campaigns = [c for c in campaigns if c["channel"] == channel]
        if is_active is not None:
            campaigns = [c for c in campaigns if c["is_active"] == is_active]
        return campaigns[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: int) -> CampaignResponse:
    """Get a single campaign by ID."""
    try:
        campaign = _campaigns_db.get(campaign_id)
        if not campaign:
            raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
        return campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(campaign: CampaignCreate) -> CampaignResponse:
    """Create a new campaign."""
    try:
        global _next_id
        new_campaign = {
            "id": _next_id,
            "name": campaign.name,
            "channel": campaign.channel,
            "status": campaign.status,
            "budget": campaign.budget,
            "start_date": campaign.start_date,
            "end_date": campaign.end_date,
            "is_active": campaign.is_active,
            "created_at": datetime.utcnow().isoformat(),
        }
        _campaigns_db[_next_id] = new_campaign
        _next_id += 1
        return new_campaign
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: int, campaign: CampaignUpdate) -> CampaignResponse:
    """Update an existing campaign."""
    try:
        existing = _campaigns_db.get(campaign_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
        for field, value in campaign.model_dump(exclude_unset=True).items():
            existing[field] = value
        return existing
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(campaign_id: int) -> None:
    """Delete a campaign by ID."""
    try:
        if campaign_id not in _campaigns_db:
            raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")
        del _campaigns_db[campaign_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
