"""Assets routes — assets endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/assets/assets/")
async def list_assets():
    return {"data": [], "count": 0}
