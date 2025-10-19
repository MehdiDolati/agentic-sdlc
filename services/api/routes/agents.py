# services/api/routes/agents.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import AgentsRepoDB, AgentRunsRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/agents", tags=["agents"])

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    agent_type: str
    config: Dict[str, Any]
    capabilities: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = False

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    agent_type: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None

class Agent(BaseModel):
    id: str
    name: str
    description: str
    agent_type: str
    config: Dict[str, Any]
    status: str
    last_heartbeat: Optional[str] = None
    capabilities: Optional[Dict[str, Any]] = None
    owner: str
    is_public: bool
    created_at: str
    updated_at: str

class AgentRunCreate(BaseModel):
    agent_id: str
    project_id: Optional[str] = None
    plan_id: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None

class AgentRun(BaseModel):
    id: str
    agent_id: str
    project_id: Optional[str] = None
    plan_id: Optional[str] = None
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: str

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.post("", response_model=Agent, status_code=201)
def create_agent(
    agent_data: AgentCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new agent."""
    try:
        engine = _get_engine()
        agents_repo = AgentsRepoDB(engine)
        
        agent_dict = {
            "id": uuid4().hex[:8],
            "name": agent_data.name,
            "description": agent_data.description or "",
            "agent_type": agent_data.agent_type,
            "config": agent_data.config,
            "status": "inactive",
            "capabilities": agent_data.capabilities or {},
            "owner": user.get("id", "public"),
            "is_public": agent_data.is_public or False
        }
        
        created_agent = agents_repo.create(agent_dict)
        stored = agents_repo.get(created_agent["id"])
        
        # Convert datetime objects to ISO format strings
        created_at = stored.get("created_at")
        if created_at and isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        elif not created_at:
            created_at = datetime.now().isoformat()
            
        updated_at = stored.get("updated_at")
        if updated_at and isinstance(updated_at, datetime):
            updated_at = updated_at.isoformat()
        elif not updated_at:
            updated_at = datetime.now().isoformat()
        
        return Agent(
            id=stored["id"],
            name=stored["name"],
            description=stored.get("description", ""),
            agent_type=stored["agent_type"],
            config=stored["config"],
            status=stored.get("status", "inactive"),
            last_heartbeat=stored.get("last_heartbeat"),
            capabilities=stored.get("capabilities", {}),
            owner=stored.get("owner", "public"),
            is_public=stored.get("is_public", False),
            created_at=created_at,  # Use the converted string
            updated_at=updated_at   # Use the converted string
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")
        
@router.get("", response_model=List[Agent])
def list_agents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    agent_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    include_public: Optional[bool] = Query(default=True),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List agents with filtering and pagination."""
    try:
        engine = _get_engine()
        agents_repo = AgentsRepoDB(engine)
        
        user_id = user.get("id", "public")
        
        # Use the repository's actual parameters
        # Note: The current AgentsRepoDB doesn't support owner/is_public filtering,
        # so we'll just use the basic filters it supports
        agents, total = agents_repo.list(
            limit=limit,
            offset=offset,
            agent_type=agent_type,
            status=status
        )
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        out = []
        for agent in agents:
            # Map 'type' field from DB to 'agent_type' for the response
            out.append(Agent(
                id=str(agent["id"]),
                name=agent["name"],
                description=agent.get("description", ""),
                agent_type=agent.get("type", agent.get("agent_type", "unknown")),
                config=agent.get("config", {}),
                status=agent.get("status", "inactive"),
                last_heartbeat=_iso(agent.get("last_heartbeat")),
                capabilities=agent.get("capabilities", {}),
                owner=agent.get("owner", "public"),
                is_public=agent.get("is_public", False),
                created_at=_iso(agent.get("created_at")),
                updated_at=_iso(agent.get("updated_at"))
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")
        
@router.get("/{agent_id}", response_model=Agent)
def get_agent(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific agent by ID."""
    try:
        engine = _get_engine()
        agents_repo = AgentsRepoDB(engine)
        
        agent = agents_repo.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Check ownership or public access
        if agent.get("owner") != user.get("id", "public") and not agent.get("is_public", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        return Agent(
            id=agent["id"],
            name=agent["name"],
            description=agent.get("description", ""),
            agent_type=agent["agent_type"],
            config=agent["config"],
            status=agent.get("status", "inactive"),
            last_heartbeat=_iso(agent.get("last_heartbeat")),
            capabilities=agent.get("capabilities", {}),
            owner=agent.get("owner", "public"),
            is_public=agent.get("is_public", False),
            created_at=_iso(agent.get("created_at")),
            updated_at=_iso(agent.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")

@router.put("/{agent_id}", response_model=Agent)
def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update an agent."""
    try:
        engine = _get_engine()
        agents_repo = AgentsRepoDB(engine)
        
        # Check if agent exists and user has access
        existing_agent = agents_repo.get(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if existing_agent.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update fields
        update_fields = {}
        if agent_data.name is not None:
            update_fields["name"] = agent_data.name
        if agent_data.description is not None:
            update_fields["description"] = agent_data.description
        if agent_data.agent_type is not None:
            update_fields["agent_type"] = agent_data.agent_type
        if agent_data.config is not None:
            update_fields["config"] = agent_data.config
        if agent_data.status is not None:
            update_fields["status"] = agent_data.status
        if agent_data.capabilities is not None:
            update_fields["capabilities"] = agent_data.capabilities
        if agent_data.is_public is not None:
            update_fields["is_public"] = agent_data.is_public
        
        if not update_fields:
            # No changes requested, return existing agent
            def _iso(v):
                return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
            return Agent(
                id=existing_agent["id"],
                name=existing_agent["name"],
                description=existing_agent.get("description", ""),
                agent_type=existing_agent["agent_type"],
                config=existing_agent["config"],
                status=existing_agent.get("status", "inactive"),
                last_heartbeat=_iso(existing_agent.get("last_heartbeat")),
                capabilities=existing_agent.get("capabilities", {}),
                owner=existing_agent.get("owner", "public"),
                is_public=existing_agent.get("is_public", False),
                created_at=_iso(existing_agent.get("created_at")),
                updated_at=_iso(existing_agent.get("updated_at"))
            )
        
        updated_agent = agents_repo.update(agent_id, update_fields)
        if not updated_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        return Agent(
            id=updated_agent["id"],
            name=updated_agent["name"],
            description=updated_agent.get("description", ""),
            agent_type=updated_agent["agent_type"],
            config=updated_agent["config"],
            status=updated_agent.get("status", "inactive"),
            last_heartbeat=_iso(updated_agent.get("last_heartbeat")),
            capabilities=updated_agent.get("capabilities", {}),
            owner=updated_agent.get("owner", "public"),
            is_public=updated_agent.get("is_public", False),
            created_at=_iso(updated_agent.get("created_at")),
            updated_at=_iso(updated_agent.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")

@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete an agent."""
    try:
        engine = _get_engine()
        agents_repo = AgentsRepoDB(engine)
        
        # Check if agent exists and user has access
        existing_agent = agents_repo.get(agent_id)
        if not existing_agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if existing_agent.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = agents_repo.delete(agent_id)
        if not success:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")

# Agent Runs endpoints
@router.post("/runs", response_model=AgentRun, status_code=201)
def create_agent_run(
    run_data: AgentRunCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new agent run."""
    try:
        engine = _get_engine()
        agent_runs_repo = AgentRunsRepoDB(engine)
        agents_repo = AgentsRepoDB(engine)
        
        # Verify agent exists and user has access
        agent = agents_repo.get(run_data.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        if agent.get("owner") != user.get("id", "public") and not agent.get("is_public", False):
            raise HTTPException(status_code=403, detail="Access denied")
        
        run_dict = {
            "id": uuid4().hex[:8],
            "agent_id": run_data.agent_id,
            "project_id": run_data.project_id,
            "plan_id": run_data.plan_id,
            "status": "queued",
            "input_data": run_data.input_data or {}
        }
        
        created_run = agent_runs_repo.create(run_dict)
        stored = agent_runs_repo.get(created_run["id"])
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        return AgentRun(
            id=stored["id"],
            agent_id=stored["agent_id"],
            project_id=stored.get("project_id"),
            plan_id=stored.get("plan_id"),
            status=stored.get("status", "queued"),
            input_data=stored.get("input_data"),
            output_data=stored.get("output_data"),
            started_at=_iso(stored.get("started_at")),
            completed_at=_iso(stored.get("completed_at")),
            error_message=stored.get("error_message"),
            created_at=_iso(stored.get("created_at")),
            updated_at=_iso(stored.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent run: {str(e)}")

@router.get("/runs", response_model=List[AgentRun])
def list_agent_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    agent_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    plan_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List agent runs with filtering and pagination."""
    try:
        engine = _get_engine()
        agent_runs_repo = AgentRunsRepoDB(engine)
        
        filters = {}
        if agent_id:
            filters["agent_id"] = agent_id
        if project_id:
            filters["project_id"] = project_id
        if plan_id:
            filters["plan_id"] = plan_id
        if status:
            filters["status"] = status
        
        runs, total = agent_runs_repo.list(limit=limit, offset=offset, **filters)
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        out = []
        for run in runs:
            out.append(AgentRun(
                id=run["id"],
                agent_id=run["agent_id"],
                project_id=run.get("project_id"),
                plan_id=run.get("plan_id"),
                status=run.get("status", "queued"),
                input_data=run.get("input_data"),
                output_data=run.get("output_data"),
                started_at=_iso(run.get("started_at")),
                completed_at=_iso(run.get("completed_at")),
                error_message=run.get("error_message"),
                created_at=_iso(run.get("created_at")),
                updated_at=_iso(run.get("updated_at"))
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agent runs: {str(e)}")