"""Project management routes — projects endpoint."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/project-mgmt/projects/")
async def list_projects():
    return {"data": [], "count": 0}
