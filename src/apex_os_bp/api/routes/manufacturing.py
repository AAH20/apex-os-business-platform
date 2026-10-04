"""Manufacturing routes — production-lines endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/manufacturing/production-lines/")
async def list_production_lines():
    return {"data": [], "count": 0}
