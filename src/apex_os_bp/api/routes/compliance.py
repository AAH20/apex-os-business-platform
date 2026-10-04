"""Compliance routes — frameworks endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/compliance/frameworks/")
async def list_frameworks():
    return {"data": [], "count": 0}
