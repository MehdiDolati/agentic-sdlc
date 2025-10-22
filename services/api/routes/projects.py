# services/api/routes/projects.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import ProjectsRepoDB
from services.api.auth.routes import get_current_user
from services.api.models.project import ProjectAgent, ProjectAgentCreate

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "new"

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class Project(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    status: str
    createdAt: str
    updatedAt: str

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.post("", response_model=Project, status_code=201)
def create_project(
    project_data: ProjectCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new project."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        project_id = uuid4().hex[:8]
        project_dict = {
            "id": project_id,
            "title": project_data.title,
            "description": project_data.description or "",
            "owner": user.get("id", "public"),
            "status": "new"  # Always start new projects with "new" status
        }
        
        projects_repo.create(project_dict)
        # Fetch back to include DB-populated timestamps
        stored = projects_repo.get(project_id) or project_dict
        
        return Project(
            id=stored["id"],
            title=stored.get("title", project_dict["title"]),
            description=stored.get("description", project_dict["description"]),
            owner=stored.get("owner", project_dict["owner"]),
            status=stored.get("status", project_dict["status"]),
            createdAt=(stored.get("created_at") or datetime.now().isoformat()),
            updatedAt=(stored.get("updated_at") or datetime.now().isoformat())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@router.get("", response_model=List[Project])
def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default="created_at"),
    order: Optional[str] = Query(default="desc"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List projects with filtering and pagination."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Build filters
        filters = {
            "owner": user.get("id", "public")
        }
        if q:
            filters["q"] = q
        if status:
            filters["status"] = status
        if sort:
            filters["sort"] = sort
        if order:
            filters["order"] = order
        
        projects, total = projects_repo.list(limit=limit, offset=offset, **filters)
        
        def _iso(v):
            from datetime import datetime
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        out = []
        for p in projects:
            out.append(Project(
                id=p["id"],
                title=p["title"],
                description=p.get("description", ""),
                owner=p.get("owner", "public"),
                status=p.get("status", "planning"),
                createdAt=_iso(p.get("created_at")),
                updatedAt=_iso(p.get("updated_at")),
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

@router.get("/{project_id}", response_model=Project)
def get_project(
    project_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific project by ID."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        project = projects_repo.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check ownership (for now, allow access to all projects - can be enhanced with proper permissions)
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        return Project(
            id=project["id"],
            title=project["title"],
            description=project.get("description", ""),
            owner=project.get("owner", "public"),
            status=project.get("status", "planning"),
            createdAt=_iso(project.get("created_at")),
            updatedAt=_iso(project.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")

@router.put("/{project_id}", response_model=Project)
def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a project."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Check if project exists
        existing_project = projects_repo.get(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check ownership (for now, allow updates to all projects - can be enhanced with proper permissions)
        
        # Build update fields
        update_fields = {}
        if project_data.title is not None:
            update_fields["title"] = project_data.title
        if project_data.description is not None:
            update_fields["description"] = project_data.description
        if project_data.status is not None:
            update_fields["status"] = project_data.status
        
        if not update_fields:
            # No changes requested, return existing project
            def _iso(v):
                return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
            return Project(
                id=existing_project["id"],
                title=existing_project["title"],
                description=existing_project.get("description", ""),
                owner=existing_project.get("owner", "public"),
                status=existing_project.get("status", "planning"),
                createdAt=_iso(existing_project.get("created_at")),
                updatedAt=_iso(existing_project.get("updated_at"))
            )
        
        updated_project = projects_repo.update(project_id, update_fields)
        if not updated_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        return Project(
            id=updated_project["id"],
            title=updated_project["title"],
            description=updated_project.get("description", ""),
            owner=updated_project.get("owner", "public"),
            status=updated_project.get("status", "planning"),
            createdAt=_iso(updated_project.get("created_at")),
            updatedAt=_iso(updated_project.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")

@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a project."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Check if project exists
        existing_project = projects_repo.get(project_id)
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check ownership (for now, allow deletion of all projects - can be enhanced with proper permissions)
        
        # Note: The current ProjectsRepoDB doesn't have a delete method
        # This would need to be implemented in the repository class
        raise HTTPException(status_code=501, detail="Project deletion not yet implemented")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


# Project Agents endpoints
@router.post("/{project_id}/agents", response_model=ProjectAgent, status_code=201)
def add_project_agent(
    project_id: str,
    agent_data: ProjectAgentCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Add an agent to a project."""
    try:
        from services.api.core.db import project_agents, agent_templates
        from sqlalchemy import select, insert
        from sqlalchemy.orm import Session
        import json
        
        engine = _get_engine()
        
        # Verify project exists
        projects_repo = ProjectsRepoDB(engine)
        if not projects_repo.get(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        
        with Session(engine) as session:
            # Fetch agent template to get default name/type if not provided
            stmt = select(agent_templates).where(agent_templates.c.id == agent_data.agent_template_id)
            template = session.execute(stmt).first()
            
            if not template:
                raise HTTPException(status_code=404, detail="Agent template not found")
            
            # Use template values as defaults
            agent_name = agent_data.name or template.name
            agent_type = agent_data.type or template.type
            agent_config = agent_data.config or template.config or {}
            
            insert_data = {
                "project_id": project_id,
                "agent_template_id": agent_data.agent_template_id,
                "name": agent_name,
                "type": agent_type,
                "description": agent_data.description or template.description or "",
                "config": json.dumps(agent_config) if isinstance(agent_config, dict) else agent_config,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC)
            }
            
            result = session.execute(
                insert(project_agents).values(**insert_data)
            )
            session.commit()
            
            # Fetch created agent
            agent_id = result.inserted_primary_key[0]
            stmt = select(project_agents).where(project_agents.c.id == agent_id)
            row = session.execute(stmt).first()
            
            config = row.config
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except:
                    config = {}
            
            return ProjectAgent(
                id=row.id,
                project_id=row.project_id,
                agent_template_id=row.agent_template_id,
                name=row.name,
                type=row.type,
                description=row.description or "",
                config=config,
                created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at)
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add project agent: {str(e)}")

@router.get("/{project_id}/agents", response_model=List[ProjectAgent])
def list_project_agents(
    project_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List all agents assigned to a project."""
    try:
        from services.api.core.db import project_agents
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        import json
        
        engine = _get_engine()
        
        # Verify project exists
        projects_repo = ProjectsRepoDB(engine)
        if not projects_repo.get(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        
        with Session(engine) as session:
            stmt = select(project_agents).where(project_agents.c.project_id == project_id)
            results = session.execute(stmt).fetchall()
            
            agents = []
            for row in results:
                config = row.config
                if isinstance(config, str):
                    try:
                        config = json.loads(config)
                    except:
                        config = {}
                
                agents.append(ProjectAgent(
                    id=row.id,
                    project_id=row.project_id,
                    agent_template_id=row.agent_template_id,
                    name=row.name,
                    type=row.type,
                    description=row.description or "",
                    config=config,
                    created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                    updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at)
                ))
            return agents
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list project agents: {str(e)}")

@router.delete("/{project_id}/agents/{agent_id}", status_code=204)
def remove_project_agent(
    project_id: str,
    agent_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Remove an agent from a project."""
    try:
        from services.api.core.db import project_agents
        from sqlalchemy import select, delete
        from sqlalchemy.orm import Session
        
        engine = _get_engine()
        
        with Session(engine) as session:
            # Check if agent exists and belongs to this project
            stmt = select(project_agents).where(
                (project_agents.c.id == agent_id) & 
                (project_agents.c.project_id == project_id)
            )
            existing = session.execute(stmt).first()
            
            if not existing:
                raise HTTPException(status_code=404, detail="Project agent not found")
            
            # Delete
            stmt = delete(project_agents).where(project_agents.c.id == agent_id)
            session.execute(stmt)
            session.commit()
            
            return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove project agent: {str(e)}")
