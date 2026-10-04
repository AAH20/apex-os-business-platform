"""BigData module CRUD API endpoints for datasets."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/datasets", tags=["bigdata"])


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source: Optional[str] = None
    format: str = Field(default="csv", pattern="^(csv|json|parquet|avro)$")
    size_bytes: int = Field(default=0, ge=0)
    row_count: int = Field(default=0, ge=0)
    tags: List[str] = Field(default_factory=list)


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    source: Optional[str] = None
    format: Optional[str] = Field(None, pattern="^(csv|json|parquet|avro)$")
    size_bytes: Optional[int] = Field(None, ge=0)
    row_count: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None


class Dataset(DatasetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Synthetic in-memory data store
_DATASETS: List[dict] = [
    {
        "id": i,
        "name": f"dataset_{i}",
        "description": f"Synthetic dataset number {i}",
        "source": f"s3://bucket/path/{i}",
        "format": ["csv", "json", "parquet", "avro"][i % 4],
        "size_bytes": 1024 * (i + 1),
        "row_count": 1000 * (i + 1),
        "tags": ["synthetic", f"tag_{i % 3}"],
        "created_at": datetime(2024, 1, i + 1),
        "updated_at": datetime(2024, 1, i + 1),
    }
    for i in range(1, 26)
]
_next_id = 26


@router.get("", response_model=List[Dataset])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all datasets with pagination."""
    return _DATASETS[skip : skip + limit]


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: int):
    """Get a single dataset by ID."""
    for ds in _DATASETS:
        if ds["id"] == dataset_id:
            return ds
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.post("", response_model=Dataset, status_code=201)
async def create_dataset(payload: DatasetCreate):
    """Create a new dataset."""
    global _next_id
    now = datetime.utcnow()
    ds = {
        "id": _next_id,
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _DATASETS.append(ds)
    _next_id += 1
    return ds


@router.put("/{dataset_id}", response_model=Dataset)
async def update_dataset(dataset_id: int, payload: DatasetUpdate):
    """Update an existing dataset."""
    for idx, ds in enumerate(_DATASETS):
        if ds["id"] == dataset_id:
            updates = payload.model_dump(exclude_unset=True)
            _DATASETS[idx].update(updates)
            _DATASETS[idx]["updated_at"] = datetime.utcnow()
            return _DATASETS[idx]
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: int):
    """Delete a dataset by ID."""
    for idx, ds in enumerate(_DATASETS):
        if ds["id"] == dataset_id:
            _DATASETS.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
