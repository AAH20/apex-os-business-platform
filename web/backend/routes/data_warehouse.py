"""Data Warehouse module CRUD API endpoints for data sources, ETL jobs, data marts, and data models."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/data-warehouse", tags=["data-warehouse"])


# ── Data Sources ──────────────────────────────────────────────────────────────

class DataSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: str = Field(default="postgresql", pattern="^(postgresql|mysql|s3|kafka|api|csv|bigquery|redshift)$")
    connection_string: Optional[str] = None
    status: str = Field(default="active", pattern="^(active|inactive|error|pending)$")
    tags: List[str] = Field(default_factory=list)


class DataSourceCreate(DataSourceBase):
    pass


class DataSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    source_type: Optional[str] = Field(None, pattern="^(postgresql|mysql|s3|kafka|api|csv|bigquery|redshift)$")
    connection_string: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|error|pending)$")
    tags: Optional[List[str]] = None


class DataSource(DataSourceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── ETL Jobs ──────────────────────────────────────────────────────────────────

class ETLJobBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    source_id: Optional[int] = None
    target_type: str = Field(default="data_mart", pattern="^(data_mart|data_model|table|view)$")
    schedule: Optional[str] = None
    status: str = Field(default="pending", pattern="^(pending|running|completed|failed|paused)$")
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    row_count: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)


class ETLJobCreate(ETLJobBase):
    pass


class ETLJobUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    source_id: Optional[int] = None
    target_type: Optional[str] = Field(None, pattern="^(data_mart|data_model|table|view)$")
    schedule: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|running|completed|failed|paused)$")
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    row_count: Optional[int] = Field(None, ge=0)
    duration_ms: Optional[int] = Field(None, ge=0)


class ETLJob(ETLJobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Data Marts ────────────────────────────────────────────────────────────────

class DataMartBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    schema_name: Optional[str] = None
    mart_type: str = Field(default="star", pattern="^(star|snowflake|flat|denormalized)$")
    status: str = Field(default="active", pattern="^(active|inactive|building|deprecated)$")
    table_count: int = Field(default=0, ge=0)
    size_bytes: int = Field(default=0, ge=0)
    tags: List[str] = Field(default_factory=list)


class DataMartCreate(DataMartBase):
    pass


class DataMartUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    schema_name: Optional[str] = None
    mart_type: Optional[str] = Field(None, pattern="^(star|snowflake|flat|denormalized)$")
    status: Optional[str] = Field(None, pattern="^(active|inactive|building|deprecated)$")
    table_count: Optional[int] = Field(None, ge=0)
    size_bytes: Optional[int] = Field(None, ge=0)
    tags: Optional[List[str]] = None


class DataMart(DataMartBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Data Models ───────────────────────────────────────────────────────────────

class DataModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    model_type: str = Field(default="table", pattern="^(table|view|materialized_view|external)$")
    mart_id: Optional[int] = None
    columns: List[str] = Field(default_factory=list)
    primary_key: Optional[str] = None
    indexes: List[str] = Field(default_factory=list)
    status: str = Field(default="active", pattern="^(active|inactive|draft|deprecated)$")
    row_count: int = Field(default=0, ge=0)
    size_bytes: int = Field(default=0, ge=0)


class DataModelCreate(DataModelBase):
    pass


class DataModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    model_type: Optional[str] = Field(None, pattern="^(table|view|materialized_view|external)$")
    mart_id: Optional[int] = None
    columns: Optional[List[str]] = None
    primary_key: Optional[str] = None
    indexes: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive|draft|deprecated)$")
    row_count: Optional[int] = Field(None, ge=0)
    size_bytes: Optional[int] = Field(None, ge=0)


class DataModel(DataModelBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Synthetic in-memory data stores ───────────────────────────────────────────

_DATA_SOURCES: List[dict] = [
    {
        "id": i,
        "name": f"source_{i}",
        "description": f"Data source number {i}",
        "source_type": ["postgresql", "mysql", "s3", "kafka", "api", "csv", "bigquery", "redshift"][i % 8],
        "connection_string": f"conn://host/{i}",
        "status": ["active", "inactive", "error", "pending"][i % 4],
        "tags": ["synthetic", f"tag_{i % 3}"],
        "created_at": datetime(2024, 1, i + 1),
        "updated_at": datetime(2024, 1, i + 1),
    }
    for i in range(1, 11)
]

_ETL_JOBS: List[dict] = [
    {
        "id": i,
        "name": f"etl_job_{i}",
        "description": f"ETL job number {i}",
        "source_id": (i % 10) + 1,
        "target_type": ["data_mart", "data_model", "table", "view"][i % 4],
        "schedule": f"0 {i % 24} * * *",
        "status": ["pending", "running", "completed", "failed", "paused"][i % 5],
        "last_run": datetime(2024, 6, i, i % 24, 0, 0),
        "next_run": datetime(2024, 7, i, i % 24, 0, 0),
        "row_count": 10000 * i,
        "duration_ms": 5000 * i,
        "created_at": datetime(2024, 1, i + 1),
        "updated_at": datetime(2024, 6, i),
    }
    for i in range(1, 16)
]

_DATA_MARTS: List[dict] = [
    {
        "id": i,
        "name": f"mart_{i}",
        "description": f"Data mart number {i}",
        "schema_name": f"schema_{i}",
        "mart_type": ["star", "snowflake", "flat", "denormalized"][i % 4],
        "status": ["active", "inactive", "building", "deprecated"][i % 4],
        "table_count": 5 + i,
        "size_bytes": 1024 * 1024 * (i + 1),
        "tags": ["synthetic", f"domain_{i % 3}"],
        "created_at": datetime(2024, 1, i + 1),
        "updated_at": datetime(2024, 1, i + 1),
    }
    for i in range(1, 9)
]

_DATA_MODELS: List[dict] = [
    {
        "id": i,
        "name": f"model_{i}",
        "description": f"Data model number {i}",
        "model_type": ["table", "view", "materialized_view", "external"][i % 4],
        "mart_id": (i % 8) + 1,
        "columns": [f"col_{j}" for j in range(1, 6)],
        "primary_key": "id",
        "indexes": [f"idx_{j}" for j in range(1, 3)],
        "status": ["active", "inactive", "draft", "deprecated"][i % 4],
        "row_count": 50000 * i,
        "size_bytes": 512 * 1024 * (i + 1),
        "created_at": datetime(2024, 1, i + 1),
        "updated_at": datetime(2024, 1, i + 1),
    }
    for i in range(1, 13)
]

_next_ids = {"data_sources": 11, "etl_jobs": 16, "data_marts": 9, "data_models": 13}


# ── Data Source endpoints ─────────────────────────────────────────────────────

@router.get("/data-sources", response_model=List[DataSource])
async def list_data_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all data sources with pagination."""
    return _DATA_SOURCES[skip : skip + limit]


@router.get("/data-sources/{source_id}", response_model=DataSource)
async def get_data_source(source_id: int):
    """Get a single data source by ID."""
    for ds in _DATA_SOURCES:
        if ds["id"] == source_id:
            return ds
    raise HTTPException(status_code=404, detail=f"Data source {source_id} not found")


@router.post("/data-sources", response_model=DataSource, status_code=201)
async def create_data_source(payload: DataSourceCreate):
    """Create a new data source."""
    global _next_ids
    now = datetime.utcnow()
    ds = {
        "id": _next_ids["data_sources"],
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _DATA_SOURCES.append(ds)
    _next_ids["data_sources"] += 1
    return ds


@router.put("/data-sources/{source_id}", response_model=DataSource)
async def update_data_source(source_id: int, payload: DataSourceUpdate):
    """Update an existing data source."""
    for idx, ds in enumerate(_DATA_SOURCES):
        if ds["id"] == source_id:
            updates = payload.model_dump(exclude_unset=True)
            _DATA_SOURCES[idx].update(updates)
            _DATA_SOURCES[idx]["updated_at"] = datetime.utcnow()
            return _DATA_SOURCES[idx]
    raise HTTPException(status_code=404, detail=f"Data source {source_id} not found")


@router.delete("/data-sources/{source_id}", status_code=204)
async def delete_data_source(source_id: int):
    """Delete a data source by ID."""
    for idx, ds in enumerate(_DATA_SOURCES):
        if ds["id"] == source_id:
            _DATA_SOURCES.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Data source {source_id} not found")


# ── ETL Job endpoints ─────────────────────────────────────────────────────────

@router.get("/etl-jobs", response_model=List[ETLJob])
async def list_etl_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all ETL jobs with pagination."""
    return _ETL_JOBS[skip : skip + limit]


@router.get("/etl-jobs/{job_id}", response_model=ETLJob)
async def get_etl_job(job_id: int):
    """Get a single ETL job by ID."""
    for job in _ETL_JOBS:
        if job["id"] == job_id:
            return job
    raise HTTPException(status_code=404, detail=f"ETL job {job_id} not found")


@router.post("/etl-jobs", response_model=ETLJob, status_code=201)
async def create_etl_job(payload: ETLJobCreate):
    """Create a new ETL job."""
    global _next_ids
    now = datetime.utcnow()
    job = {
        "id": _next_ids["etl_jobs"],
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _ETL_JOBS.append(job)
    _next_ids["etl_jobs"] += 1
    return job


@router.put("/etl-jobs/{job_id}", response_model=ETLJob)
async def update_etl_job(job_id: int, payload: ETLJobUpdate):
    """Update an existing ETL job."""
    for idx, job in enumerate(_ETL_JOBS):
        if job["id"] == job_id:
            updates = payload.model_dump(exclude_unset=True)
            _ETL_JOBS[idx].update(updates)
            _ETL_JOBS[idx]["updated_at"] = datetime.utcnow()
            return _ETL_JOBS[idx]
    raise HTTPException(status_code=404, detail=f"ETL job {job_id} not found")


@router.delete("/etl-jobs/{job_id}", status_code=204)
async def delete_etl_job(job_id: int):
    """Delete an ETL job by ID."""
    for idx, job in enumerate(_ETL_JOBS):
        if job["id"] == job_id:
            _ETL_JOBS.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"ETL job {job_id} not found")


# ── Data Mart endpoints ───────────────────────────────────────────────────────

@router.get("/data-marts", response_model=List[DataMart])
async def list_data_marts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all data marts with pagination."""
    return _DATA_MARTS[skip : skip + limit]


@router.get("/data-marts/{mart_id}", response_model=DataMart)
async def get_data_mart(mart_id: int):
    """Get a single data mart by ID."""
    for mart in _DATA_MARTS:
        if mart["id"] == mart_id:
            return mart
    raise HTTPException(status_code=404, detail=f"Data mart {mart_id} not found")


@router.post("/data-marts", response_model=DataMart, status_code=201)
async def create_data_mart(payload: DataMartCreate):
    """Create a new data mart."""
    global _next_ids
    now = datetime.utcnow()
    mart = {
        "id": _next_ids["data_marts"],
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _DATA_MARTS.append(mart)
    _next_ids["data_marts"] += 1
    return mart


@router.put("/data-marts/{mart_id}", response_model=DataMart)
async def update_data_mart(mart_id: int, payload: DataMartUpdate):
    """Update an existing data mart."""
    for idx, mart in enumerate(_DATA_MARTS):
        if mart["id"] == mart_id:
            updates = payload.model_dump(exclude_unset=True)
            _DATA_MARTS[idx].update(updates)
            _DATA_MARTS[idx]["updated_at"] = datetime.utcnow()
            return _DATA_MARTS[idx]
    raise HTTPException(status_code=404, detail=f"Data mart {mart_id} not found")


@router.delete("/data-marts/{mart_id}", status_code=204)
async def delete_data_mart(mart_id: int):
    """Delete a data mart by ID."""
    for idx, mart in enumerate(_DATA_MARTS):
        if mart["id"] == mart_id:
            _DATA_MARTS.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Data mart {mart_id} not found")


# ── Data Model endpoints ──────────────────────────────────────────────────────

@router.get("/data-models", response_model=List[DataModel])
async def list_data_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """List all data models with pagination."""
    return _DATA_MODELS[skip : skip + limit]


@router.get("/data-models/{model_id}", response_model=DataModel)
async def get_data_model(model_id: int):
    """Get a single data model by ID."""
    for model in _DATA_MODELS:
        if model["id"] == model_id:
            return model
    raise HTTPException(status_code=404, detail=f"Data model {model_id} not found")


@router.post("/data-models", response_model=DataModel, status_code=201)
async def create_data_model(payload: DataModelCreate):
    """Create a new data model."""
    global _next_ids
    now = datetime.utcnow()
    model = {
        "id": _next_ids["data_models"],
        **payload.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _DATA_MODELS.append(model)
    _next_ids["data_models"] += 1
    return model


@router.put("/data-models/{model_id}", response_model=DataModel)
async def update_data_model(model_id: int, payload: DataModelUpdate):
    """Update an existing data model."""
    for idx, model in enumerate(_DATA_MODELS):
        if model["id"] == model_id:
            updates = payload.model_dump(exclude_unset=True)
            _DATA_MODELS[idx].update(updates)
            _DATA_MODELS[idx]["updated_at"] = datetime.utcnow()
            return _DATA_MODELS[idx]
    raise HTTPException(status_code=404, detail=f"Data model {model_id} not found")


@router.delete("/data-models/{model_id}", status_code=204)
async def delete_data_model(model_id: int):
    """Delete a data model by ID."""
    for idx, model in enumerate(_DATA_MODELS):
        if model["id"] == model_id:
            _DATA_MODELS.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Data model {model_id} not found")
