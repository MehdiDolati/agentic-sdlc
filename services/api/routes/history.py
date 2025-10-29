from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Any, Dict
from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import InteractionHistoryRepoDB

router = APIRouter(prefix="/api/history", tags=["history"])

def get_repo():
    engine = _create_engine(_database_url(_repo_root()))
    return InteractionHistoryRepoDB(engine)

class HistoryIn(BaseModel):
    project_id: Optional[str] = None
    prompt: str
    response: str
    role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    step: Optional[str] = None
    agent_type: Optional[str] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def log_interaction(entry: HistoryIn, repo=Depends(get_repo)):
    repo.add(entry.model_dump())
    return {"ok": True}

@router.get("/", response_model=list)
def list_all(repo=Depends(get_repo)):
    return repo.list_all()

@router.get("/project/{project_id}", response_model=list)
def list_by_project(project_id: str, repo=Depends(get_repo)):
    return repo.list_by_project(project_id)

@router.get("/project/{project_id}/step/{step}", response_model=list)
def list_by_project_and_step(project_id: str, step: str, repo=Depends(get_repo)):
    return repo.list_by_project_and_step(project_id, step)
