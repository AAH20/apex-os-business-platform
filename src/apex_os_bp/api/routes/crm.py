"""CRM routes — contacts and deals."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from apex_os_bp.api.models import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    DealCreate,
    DealResponse,
    DealStage,
    DealUpdate,
    PipelineResponse,
)
from apex_os_bp.crm.engine import CRMEngine
from apex_os_bp.crm.models import Contact, Deal

router = APIRouter(prefix="/crm", tags=["CRM"])


def get_crm_engine(request: Request) -> CRMEngine:
    """Get the CRM engine from the app state."""
    return request.app.state.crm_engine


def _contact_to_response(contact: Contact) -> ContactResponse:
    """Convert a Contact model to a response."""
    return ContactResponse(
        id=contact.id,
        name=contact.name,
        email=contact.email,
        phone=contact.phone,
        company=contact.company,
        metadata=contact.metadata,
    )


def _deal_to_response(deal: Deal) -> DealResponse:
    """Convert a Deal model to a response."""
    return DealResponse(
        id=deal.id,
        title=deal.title,
        value=deal.value,
        stage=deal.stage.value,
        contact_id=deal.contact_id,
        metadata=deal.metadata,
    )


# ─── Contacts ─────────────────────────────────────────────────────────────────

@router.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    engine: CRMEngine = Depends(get_crm_engine),
) -> List[ContactResponse]:
    """List all contacts."""
    return [_contact_to_response(c) for c in engine.get_contacts()]


@router.post("/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(
    body: ContactCreate,
    engine: CRMEngine = Depends(get_crm_engine),
) -> ContactResponse:
    """Create a new contact."""
    contact = engine.create_contact(
        name=body.name,
        email=body.email,
        phone=body.phone,
        company=body.company,
        metadata=body.metadata,
    )
    return _contact_to_response(contact)


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    engine: CRMEngine = Depends(get_crm_engine),
) -> ContactResponse:
    """Get a contact by ID."""
    contact = engine.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact not found: {contact_id}",
        )
    return _contact_to_response(contact)


@router.put("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    body: ContactUpdate,
    engine: CRMEngine = Depends(get_crm_engine),
) -> ContactResponse:
    """Update a contact."""
    contact = engine.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact not found: {contact_id}",
        )
    if body.name is not None:
        contact.name = body.name
    if body.email is not None:
        contact.email = body.email
    if body.phone is not None:
        contact.phone = body.phone
    if body.company is not None:
        contact.company = body.company
    if body.metadata is not None:
        contact.metadata = body.metadata
    return _contact_to_response(contact)


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: str,
    engine: CRMEngine = Depends(get_crm_engine),
) -> None:
    """Delete a contact."""
    contact = engine.get_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact not found: {contact_id}",
        )
    del engine._contacts[contact_id]


# ─── Deals ────────────────────────────────────────────────────────────────────

@router.get("/deals", response_model=List[DealResponse])
async def list_deals(
    engine: CRMEngine = Depends(get_crm_engine),
) -> List[DealResponse]:
    """List all deals."""
    return [_deal_to_response(d) for d in engine.get_deals()]


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal(
    body: DealCreate,
    engine: CRMEngine = Depends(get_crm_engine),
) -> DealResponse:
    """Create a new deal."""
    deal = engine.create_deal(
        title=body.title,
        value=body.value,
        contact_id=body.contact_id,
        metadata=body.metadata,
    )
    if body.stage != DealStage.LEAD:
        deal.stage = DealStage(body.stage.value)
    return _deal_to_response(deal)


@router.get("/deals/{deal_id}", response_model=DealResponse)
async def get_deal(
    deal_id: str,
    engine: CRMEngine = Depends(get_crm_engine),
) -> DealResponse:
    """Get a deal by ID."""
    deal = engine.get_deal(deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal not found: {deal_id}",
        )
    return _deal_to_response(deal)


@router.put("/deals/{deal_id}", response_model=DealResponse)
async def update_deal(
    deal_id: str,
    body: DealUpdate,
    engine: CRMEngine = Depends(get_crm_engine),
) -> DealResponse:
    """Update a deal."""
    deal = engine.get_deal(deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal not found: {deal_id}",
        )
    if body.title is not None:
        deal.title = body.title
    if body.value is not None:
        deal.value = body.value
    if body.stage is not None:
        deal.stage = DealStage(body.stage.value)
    if body.contact_id is not None:
        deal.contact_id = body.contact_id
    if body.metadata is not None:
        deal.metadata = body.metadata
    return _deal_to_response(deal)


@router.delete("/deals/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: str,
    engine: CRMEngine = Depends(get_crm_engine),
) -> None:
    """Delete a deal."""
    deal = engine.get_deal(deal_id)
    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deal not found: {deal_id}",
        )
    del engine._deals[deal_id]
    # Also remove from pipeline
    engine._pipeline.deals = [d for d in engine._pipeline.deals if d.id != deal_id]


# ─── Pipeline ─────────────────────────────────────────────────────────────────

@router.get("/pipeline", response_model=PipelineResponse)
async def get_pipeline(
    engine: CRMEngine = Depends(get_crm_engine),
) -> PipelineResponse:
    """Get pipeline report."""
    report = engine.pipeline_report()
    return PipelineResponse(
        total_deals=report["total_deals"],
        total_value=report["total_value"],
        deals_by_stage=report["deals_by_stage"],
    )
