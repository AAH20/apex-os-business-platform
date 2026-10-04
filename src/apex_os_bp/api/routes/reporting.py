"""Reporting routes — reports endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/reporting/reports/")
async def list_reports():
    return {"data": [], "count": 0}
