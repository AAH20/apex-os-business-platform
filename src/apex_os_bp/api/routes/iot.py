"""IoT routes — devices endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/iot/devices/")
async def list_devices():
    return {"data": [], "count": 0}
