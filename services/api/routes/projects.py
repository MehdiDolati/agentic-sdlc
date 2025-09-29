# services/api/routes/projects.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import ProjectsRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    status: Optional[str] = "planning"

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
            "status": project_data.status or "planning"
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


