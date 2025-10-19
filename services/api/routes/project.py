from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from services.api.core.db import get_db
from services.api.core.repos.project import ProjectRepository
from services.api.core.repos.project_agent import ProjectAgentRepository
from services.api.models.project import Project, ProjectCreate, ProjectUpdate, ProjectAgent, ProjectAgentCreate

router = APIRouter()

@router.post("/projects", response_model=Project)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    return repo.create(project)

@router.get("/projects", response_model=List[Project])
def list_projects(db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    return repo.list_all()

@router.get("/projects/{project_id}", response_model=Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    project = repo.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.put("/projects/{project_id}", response_model=Project)
def update_project(project_id: int, project: ProjectUpdate, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    updated = repo.update(project_id, project.dict(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return updated

@router.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    repo = ProjectRepository(db)
    if not repo.delete(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}

# Project Agents endpoints
@router.post("/projects/{project_id}/agents", response_model=ProjectAgent)
def add_project_agent(project_id: int, agent: ProjectAgentCreate, db: Session = Depends(get_db)):
    # Verify project exists
    project_repo = ProjectRepository(db)
    if not project_repo.get(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    
    agent_repo = ProjectAgentRepository(db)
    return agent_repo.create(project_id, agent)

@router.get("/projects/{project_id}/agents", response_model=List[ProjectAgent])
def list_project_agents(project_id: int, db: Session = Depends(get_db)):
    agent_repo = ProjectAgentRepository(db)
    return agent_repo.get_by_project(project_id)

@router.delete("/projects/{project_id}/agents/{agent_id}")
def remove_project_agent(project_id: int, agent_id: int, db: Session = Depends(get_db)):
    agent_repo = ProjectAgentRepository(db)
    if not agent_repo.delete(agent_id):
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True}