"""DataScience module CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/models", tags=["datascience"])

# Synthetic in-memory data store
_models_db = [
    {"id": 1, "name": "Sales Forecaster", "type": "regression", "version": "1.0.0",
     "status": "active", "accuracy": 0.92, "created_at": "2025-01-15T10:00:00"},
    {"id": 2, "name": "Churn Predictor", "type": "classification", "version": "2.1.0",
     "status": "active", "accuracy": 0.87, "created_at": "2025-02-20T14:30:00"},
    {"id": 3, "name": "Anomaly Detector", "type": "anomaly_detection", "version": "1.5.2",
     "status": "training", "accuracy": 0.78, "created_at": "2025-03-10T09:15:00"},
    {"id": 4, "name": "Recommendation Engine", "type": "recommendation", "version": "3.0.1",
     "status": "active", "accuracy": 0.85, "created_at": "2025-04-05T16:45:00"},
    {"id": 5, "name": "NLP Sentiment Analyzer", "type": "nlp", "version": "1.2.0",
     "status": "deprecated", "accuracy": 0.81, "created_at": "2024-12-01T11:00:00"},
]
_next_id = 6


class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str = Field(..., min_length=1, max_length=64)
    version: str = Field(default="1.0.0", max_length=32)
    status: str = Field(default="training", max_length=32)
    accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ModelUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=128)
    type: Optional[str] = Field(default=None, min_length=1, max_length=64)
    version: Optional[str] = Field(default=None, max_length=32)
    status: Optional[str] = Field(default=None, max_length=32)
    accuracy: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ModelResponse(BaseModel):
    id: int
    name: str
    type: str
    version: str
    status: str
    accuracy: Optional[float] = None
    created_at: str


@router.get("", response_model=List[ModelResponse])
async def list_models(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    status: Optional[str] = None,
 -> List[ModelResponse]:
    """List all models with optional pagination and status filter."""
    try:
        results = _models_db
        if status:
            results = [m for m in results if m["status"] == status]
        return results[skip : skip + limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: int):
    """Get a single model by ID."""
    try:
        for m in _models_db:
            if m["id"] == model_id:
                return m
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(payload: ModelCreate):
    """Create a new model."""
    try:
        global _next_id
        model = payload.model_dump()
        model["id"] = _next_id
        model["created_at"] = datetime.utcnow().isoformat()
        _models_db.append(model)
        _next_id += 1
        return model
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(model_id: int, payload: ModelUpdate):
    """Update an existing model."""
    try:
        for i, m in enumerate(_models_db -> ModelResponse:
            if m["id"] == model_id:
                updates = payload.model_dump(exclude_unset=True)
                _models_db[i].update(updates)
                return _models_db[i]
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: int):
    """Delete a model by ID."""
    try:
        for i, m in enumerate(_models_db -> None:
            if m["id"] == model_id:
                _models_db.pop(i)
                return
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
