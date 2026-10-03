"""AgentReach CRUD API endpoints."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

router = APIRouter(prefix="/api/agents", tags=["agents"])


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    agent_type: str = Field(..., min_length=1, max_length=50)
    status: str = Field(default="active", pattern="^(active|inactive|paused)$")
    config: Optional[dict] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    agent_type: Optional[str] = Field(None, min_length=1, max_length=50)
    status: Optional[str] = Field(None, pattern="^(active|inactive|paused)$")
    config: Optional[dict] = None


class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    agent_type: str
    status: str
    config: Optional[dict] = None
    created_at: str
    updated_at: str


# Synthetic in-memory data store
_agents: List[dict] = [
    {
        "id": i,
        "name": f"Agent {i}",
        "description": f"Synthetic agent number {i}",
        "agent_type": ["chatbot", "analyzer", "executor"][i % 3],
        "status": ["active", "inactive", "paused"][i % 3],
        "config": {"model": "gpt-4", "temperature": 0.7},
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
    for i in range(1, 26)
]
_next_id = 26


@router.get("/", response_model=dict)
def list_agents(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """List all agents with pagination."""
    start = (page - 1) * page_size
    end = start + page_size
    items = _agents[start:end]
    return {
        "items": items,
        "total": len(_agents),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int):
    """Get a single agent by ID."""
    for agent in _agents:
        if agent["id"] == agent_id:
            return agent
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")


@router.post("/", response_model=AgentResponse, status_code=201)
def create_agent(body: AgentCreate):
    """Create a new agent."""
    global _next_id
    now = datetime.utcnow().isoformat()
    agent = {
        "id": _next_id,
        **body.model_dump(),
        "created_at": now,
        "updated_at": now,
    }
    _agents.append(agent)
    _next_id += 1
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: int, body: AgentUpdate):
    """Update an existing agent."""
    for idx, agent in enumerate(_agents):
        if agent["id"] == agent_id:
            updates = body.model_dump(exclude_unset=True)
            _agents[idx].update(updates)
            _agents[idx]["updated_at"] = datetime.utcnow().isoformat()
            return _agents[idx]
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: int):
    """Delete an agent."""
    for idx, agent in enumerate(_agents):
        if agent["id"] == agent_id:
            _agents.pop(idx)
            return
    raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
