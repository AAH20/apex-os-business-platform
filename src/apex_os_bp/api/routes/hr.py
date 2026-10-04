"""HR routes — employees endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/hr/employees/")
async def list_employees():
    return {"data": [], "count": 0}
