# services/api/routes/projects.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, UTC
from pathlib import Path
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
    repository_id: Optional[str] = None

class Project(BaseModel):
    id: str
    title: str
    description: str
    owner: str
    status: str
    createdAt: str
    updatedAt: str

class DocumentStatus(BaseModel):
    """Document status for a project."""
    prd: bool = False
    architecture: bool = False
    userStories: bool = False
    apis: bool = False
    plans: bool = False
    adr: bool = False

class ProjectWithDetails(BaseModel):
    """Extended project model with repository and agents."""
    id: str
    title: str
    description: str
    owner: str
    status: str
    createdAt: str
    updatedAt: str
    repository_id: Optional[str] = None
    agents: List[ProjectAgent] = []

class ProjectWithDocuments(BaseModel):
    """Project model with document status for dashboard."""
    id: str
    title: str
    description: str
    owner: str
    status: str
    createdAt: str
    updatedAt: str
    documents: DocumentStatus

def _check_plan_exists(project_id: str) -> bool:
    """Check if a plan exists for the project via API."""
    try:
        import urllib.request
        import urllib.error
        
        # Extract plan ID from project ID (project ID format: proj-{plan_id})
        if project_id.startswith("proj-"):
            plan_id = project_id[5:]  # Remove "proj-" prefix
        else:
            plan_id = project_id
        
        # Debug logging
        print(f"Checking plan existence for project_id: {project_id}, extracted plan_id: {plan_id}")
        
        # Check if plan exists by trying to access features endpoint
        # This is a more reliable check than the plan endpoint itself
        url = f"http://localhost:8000/plans/{plan_id}/features"
        print(f"Checking plan at URL: {url}")
        
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                result = response.status == 200
                print(f"Plan check result for {plan_id}: {result}")
                return result
        except urllib.error.HTTPError as e:
            print(f"HTTP Error checking plan {plan_id}: {e.code}")
            return False
    except Exception as e:
        print(f"Error checking plan existence: {e}")
        return False

def _check_document_status(project_id: str, project_title: str) -> DocumentStatus:
    """Check which documents exist for a specific project."""
    try:
        repo_root = _repo_root()
        
        # Main document directories to check
        docs_dirs = [
            Path(repo_root) / "docs",
            Path(repo_root) / "data" / "docs"
        ]
        
        # Document type mappings to directory/file patterns
        doc_patterns = {
            "prd": ["prd"],
            "architecture": ["tech", "architecture"], 
            "userStories": ["stories", "features"],
            "apis": ["api", "openapi"],
            "plans": ["plans"],
            "adr": ["adr"]
        }
        
        status = DocumentStatus()
        
        # Check each document type
        for doc_type, patterns in doc_patterns.items():
            found = False
            
            # Special handling for plans - check database first
            if doc_type == "plans":
                found = _check_plan_exists(project_id)
            
            # If not found and not plans, or if plans check failed, check filesystem
            if not found:
                for docs_dir in docs_dirs:
                    if found:
                        break
                    
                    if not docs_dir.exists():
                        continue
                        
                    # Check each pattern directory
                    for pattern in patterns:
                        try:
                            pattern_dir = docs_dir / pattern
                            if pattern_dir.exists() and pattern_dir.is_dir():
                                # Look for project-specific files - prioritize exact project ID match
                                files = list(pattern_dir.glob("*"))
                                for file_path in files:
                                    if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.json', '.yaml', '.yml']:
                                        file_name_lower = file_path.name.lower()
                                        
                                        # First priority: Exact project ID match
                                        if project_id.lower() in file_name_lower:
                                            found = True
                                            break
                                
                                if found:
                                    break
                        except Exception as e:
                            continue
                    
                    if found:
                        break
            
            # Set the status for this document type
            setattr(status, doc_type, found)
        
        return status
        
    except Exception as e:
        # Return empty status on error
        return DocumentStatus()

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

@router.get("", response_model=List[ProjectWithDocuments])
def list_projects(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    sort: Optional[str] = Query(default="created_at"),
    order: Optional[str] = Query(default="desc")
):
    """List projects with filtering and pagination."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Build filters (bypassing auth for now)
        filters = {
            "owner": "public"
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
            try:
                # Check document status for each project
                doc_status = _check_document_status(p["id"], p["title"])
                
                out.append(ProjectWithDocuments(
                    id=p["id"],
                    title=p["title"],
                    description=p.get("description", ""),
                    owner=p.get("owner", "public"),
                    status=p.get("status", "planning"),
                    createdAt=_iso(p.get("created_at")),
                    updatedAt=_iso(p.get("updated_at")),
                    documents=doc_status
                ))
            except Exception as e:
                print(f"Error processing project {p.get('id')}: {e}")
                # Fallback: add project without document status
                out.append(ProjectWithDocuments(
                    id=p["id"],
                    title=p["title"],
                    description=p.get("description", ""),
                    owner=p.get("owner", "public"),
                    status=p.get("status", "planning"),
                    createdAt=_iso(p.get("created_at")),
                    updatedAt=_iso(p.get("updated_at")),
                    documents=DocumentStatus()
                ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")

@router.get("/{project_id}", response_model=ProjectWithDetails)
def get_project(
    project_id: str,
    include_details: bool = Query(True, description="Include repository and agents"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific project by ID with optional details."""
    try:
        print(f"[GET PROJECT] Loading project {project_id}")
        from services.api.core.db import project_agents
        from sqlalchemy import select
        from sqlalchemy.orm import Session
        import json
        
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        print(f"[GET PROJECT] Calling projects_repo.get()")
        project = projects_repo.get(project_id)
        print(f"[GET PROJECT] Got project: {project}")
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check ownership (for now, allow access to all projects - can be enhanced with proper permissions)
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        # Get repository_id from project
        repository_id = project.get("repository_id")
        print(f"[GET PROJECT] repository_id: {repository_id}")
        
        # Get agents if include_details is True
        agents_list = []
        if include_details:
            print(f"[GET PROJECT] Loading agents for project {project_id}")
            try:
                with Session(engine) as session:
                    stmt = select(project_agents).where(project_agents.c.project_id == project_id)
                    print(f"[GET PROJECT] Executing agent query")
                    rows = session.execute(stmt).fetchall()
                    print(f"[GET PROJECT] Found {len(rows)} agents")
                    
                    for row in rows:
                        config = row.config
                        if isinstance(config, str):
                            try:
                                config = json.loads(config)
                            except:
                                config = {}
                        
                        agents_list.append(ProjectAgent(
                            id=row.id,
                            project_id=row.project_id,
                            agent_template_id=row.agent_template_id,
                            name=row.name,
                            type=row.type,
                            description=row.description or "",
                            config=config,
                            step_key=row.step_key,
                            created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                            updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at)
                        ))
            except Exception as e:
                print(f"Error loading agents: {e}")
                import traceback
                traceback.print_exc()
                # Continue without agents if there's an error
        
        print(f"[GET PROJECT] Building response with {len(agents_list)} agents")
        return ProjectWithDetails(
            id=project["id"],
            title=project["title"],
            description=project.get("description", ""),
            owner=project.get("owner", "public"),
            status=project.get("status", "planning"),
            createdAt=_iso(project.get("created_at")),
            updatedAt=_iso(project.get("updated_at")),
            repository_id=repository_id,
            agents=agents_list
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
        print(f"[UPDATE PROJECT] Received data: title={project_data.title}, desc={project_data.description}, status={project_data.status}, repo_id={project_data.repository_id}")
        if project_data.title is not None:
            update_fields["title"] = project_data.title
        if project_data.description is not None:
            update_fields["description"] = project_data.description
        if project_data.status is not None:
            update_fields["status"] = project_data.status
        # Always include repository_id if it was sent (even if null) to allow clearing it
        if hasattr(project_data, 'repository_id'):
            update_fields["repository_id"] = project_data.repository_id
        
        print(f"[UPDATE PROJECT] Update fields: {update_fields}")
        
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
@router.put("/{project_id}/agents", response_model=List[ProjectAgent])
def replace_project_agents(
    project_id: str,
    agents_data: List[ProjectAgentCreate],
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Replace all agents for a project (delete existing and add new ones)."""
    try:
        from services.api.core.db import project_agents, agent_templates
        from sqlalchemy import select, insert, delete
        from sqlalchemy.orm import Session
        import json
        
        engine = _get_engine()
        
        # Verify project exists
        projects_repo = ProjectsRepoDB(engine)
        project = projects_repo.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Only allow agent changes if status is 'new' or 'planning'
        current_status = project.get("status", "")
        if current_status not in {"new", "planning"}:
            raise HTTPException(
                status_code=403, 
                detail="Agent assignments can only be modified when project status is 'new' or 'planning'"
            )
        
        with Session(engine) as session:
            # Delete all existing agents for this project
            session.execute(
                delete(project_agents).where(project_agents.c.project_id == project_id)
            )
            
            # Add new agents
            created_agents = []
            for agent_data in agents_data:
                # Fetch agent template to get default name/type if not provided
                stmt = select(agent_templates).where(agent_templates.c.id == agent_data.agent_template_id)
                template = session.execute(stmt).first()
                
                if not template:
                    # Skip invalid template IDs
                    continue
                
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
                    "step_key": agent_data.step_key,
                }
                
                result = session.execute(
                    insert(project_agents).values(**insert_data)
                )
                
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
                
                created_agents.append(ProjectAgent(
                    id=row.id,
                    project_id=row.project_id,
                    agent_template_id=row.agent_template_id,
                    name=row.name,
                    type=row.type,
                    description=row.description or "",
                    config=config,
                    step_key=row.step_key,
                    created_at=row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                    updated_at=row.updated_at.isoformat() if hasattr(row.updated_at, 'isoformat') else str(row.updated_at)
                ))
            
            session.commit()
            return created_agents
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to replace project agents: {str(e)}")

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
        project = projects_repo.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Only allow agent changes if status is 'new' or 'planning'
        current_status = project.get("status", "")
        if current_status not in {"new", "planning"}:
            raise HTTPException(
                status_code=403, 
                detail="Agent assignments can only be modified when project status is 'new' or 'planning'"
            )
        
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
                "step_key": agent_data.step_key,  # Save the SDLC step
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
                step_key=row.step_key,
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
        
        # Verify project exists and check status
        projects_repo = ProjectsRepoDB(engine)
        project = projects_repo.get(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Only allow agent changes if status is 'new' or 'planning'
        current_status = project.get("status", "")
        if current_status not in {"new", "planning"}:
            raise HTTPException(
                status_code=403, 
                detail="Agent assignments can only be modified when project status is 'new' or 'planning'"
            )
        
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
