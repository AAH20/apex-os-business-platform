"""Supply chain routes — suppliers endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/supply-chain/suppliers/")
async def list_suppliers():
    return {"data": [], "count": 0}
