"""Journal Entry CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

router = APIRouter(prefix="/api/journal-entries", tags=["journal-entries"])

# Synthetic in-memory store
_journal_entries: dict[int, dict] = {
    1: {"id": 1, "date": "2026-09-01", "description": "Office supplies purchase",
        "debit_account": "6100", "credit_account": "1000", "amount": 250.00,
        "reference": "INV-001", "status": "posted"},
    2: {"id": 2, "date": "2026-09-05", "description": "Client payment received",
        "debit_account": "1000", "credit_account": "4000", "amount": 5000.00,
        "reference": "PMT-042", "status": "posted"},
    3: {"id": 3, "date": "2026-09-10", "description": "Monthly rent expense",
        "debit_account": "6200", "credit_account": "1000", "amount": 1200.00,
        "reference": "RENT-SEP", "status": "draft"},
}
_next_id = 4


class JournalEntryCreate(BaseModel):
    date: date
    description: str = Field(..., min_length=1, max_length=255)
    debit_account: str = Field(..., min_length=1, max_length=20)
    credit_account: str = Field(..., min_length=1, max_length=20)
    amount: float = Field(..., gt=0)
    reference: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field("draft", pattern="^(draft|posted|void)$")


class JournalEntryUpdate(BaseModel):
    date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=1, max_length=255)
    debit_account: Optional[str] = Field(None, min_length=1, max_length=20)
    credit_account: Optional[str] = Field(None, min_length=1, max_length=20)
    amount: Optional[float] = Field(None, gt=0)
    reference: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(draft|posted|void)$")


class JournalEntryResponse(BaseModel):
    id: int
    date: date
    description: str
    debit_account: str
    credit_account: str
    amount: float
    reference: Optional[str] = None
    status: str


@router.get("/", response_model=List[JournalEntryResponse])
async def list_journal_entries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
 -> List[JournalEntryResponse]:
    """List all journal entries with pagination."""
    try:
        entries = list(_journal_entries.values())
        start = (page - 1) * page_size
        return entries[start : start + page_size]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entry_id}", response_model=JournalEntryResponse)
async def get_journal_entry(entry_id: int):
    """Get a single journal entry by ID."""
    try:
        if entry_id not in _journal_entries:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        return _journal_entries[entry_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=JournalEntryResponse, status_code=201)
async def create_journal_entry(entry: JournalEntryCreate):
    """Create a new journal entry."""
    try:
        global _next_id
        new_entry = entry.model_dump()
        new_entry["id"] = _next_id
        _journal_entries[_next_id] = new_entry
        _next_id += 1
        return new_entry
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{entry_id}", response_model=JournalEntryResponse)
async def update_journal_entry(entry_id: int, entry: JournalEntryUpdate):
    """Update an existing journal entry."""
    try:
        if entry_id not in _journal_entries:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        stored = _journal_entries[entry_id]
        for field, value in entry.model_dump(exclude_unset=True).items( -> JournalEntryResponse:
            stored[field] = value
        return stored
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{entry_id}", status_code=204)
async def delete_journal_entry(entry_id: int):
    """Delete a journal entry."""
    try:
        if entry_id not in _journal_entries:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        del _journal_entries[entry_id]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
