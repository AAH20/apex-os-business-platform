"""Inventory routes — products endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/inventory/products/")
async def list_products():
    return {"data": [], "count": 0}
