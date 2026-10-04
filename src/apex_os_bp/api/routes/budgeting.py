"""Budgeting routes — budgets endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/budgeting/budgets/")
async def list_budgets():
    return {"data": [], "count": 0}
