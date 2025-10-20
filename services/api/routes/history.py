from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Any, Dict
from sqlalchemy import create_engine, Engine
from pathlib import Path
import os
from services.api.core.repos import InteractionHistoryRepoDB

router = APIRouter(prefix="/api/history", tags=["history"])

def _database_url(repo_root: Path) -> str:
    """
    Prefer DATABASE_URL if set; otherwise use a local SQLite file under the repo root.
    Keep it simple and avoid additional helpers to prevent import churn.
    """
    env = os.getenv("DATABASE_URL")
    if env:
        return env
    db_path = (repo_root / "notes.db").resolve()
    return f"sqlite+pysqlite:///{db_path}"

def _create_engine(url: str) -> Engine:
    return create_engine(url, future=True, echo=False)

def _repo_root() -> Path:
    """Simple repo root function"""
    return Path.cwd()

def get_repo():
    try:
        repo_root = _repo_root()
        url = _database_url(repo_root)
        engine = _create_engine(url)
        return InteractionHistoryRepoDB(engine)
    except Exception as e:
        print(f"Error creating repo: {e}")
        raise

class HistoryIn(BaseModel):
    project_id: Optional[str] = None
    prompt: str
    response: str
    role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.post("/", status_code=status.HTTP_201_CREATED)
def log_interaction(entry: HistoryIn, repo=Depends(get_repo)):
    try:
        repo.add(entry.model_dump())
        return {"ok": True}
    except Exception as e:
        print(f"Error in log_interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to log interaction")

@router.get("/", response_model=list)
def list_all(repo=Depends(get_repo)):
    try:
        return repo.list_all()
    except Exception as e:
        print(f"Error in list_all: {e}")
        return []

@router.get("/project/{project_id}", response_model=list)
def list_by_project(project_id: str, repo=Depends(get_repo)):
    try:
        all_entries = repo.list_all()
        # Filter by project_id
        project_entries = [entry for entry in all_entries if entry.get('project_id') == project_id]
        return project_entries
    except Exception as e:
        print(f"Error in list_by_project: {e}")
        return []
