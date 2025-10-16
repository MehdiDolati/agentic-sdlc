# services/api/routes/repositories.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import RepositoriesRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

class RepositoryCreate(BaseModel):
    name: str
    url: str
    description: Optional[str] = ""
    type: Optional[str] = "git"
    branch: Optional[str] = "main"
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None

class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    branch: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    last_sync_status: Optional[str] = None

class Repository(BaseModel):
    id: str
    name: str
    url: str
    description: str
    type: str
    branch: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    owner: str
    is_active: bool
    last_sync_status: Optional[str] = None
    last_sync_at: Optional[str] = None
    created_at: str
    updated_at: str

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.post("", response_model=Repository, status_code=201)
def create_repository(
    repo_data: RepositoryCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new repository configuration."""
    try:
        engine = _get_engine()
        repos_repo = RepositoriesRepoDB(engine)
        
        repo_dict = {
            "id": uuid4().hex[:8],
            "name": repo_data.name,
            "url": repo_data.url,
            "description": repo_data.description or "",
            "type": repo_data.type or "git",
            "branch": repo_data.branch,
            "auth_type": repo_data.auth_type,
            "auth_config": repo_data.auth_config,
            "owner": user.get("id", "public"),
            "is_active": True
        }
        
        created_repo = repos_repo.create(repo_dict)
        stored = repos_repo.get(created_repo["id"])
        
        return Repository(
            id=stored["id"],
            name=stored["name"],
            url=stored["url"],
            description=stored.get("description", ""),
            type=stored.get("type", "git"),
            branch=stored.get("branch"),
            auth_type=stored.get("auth_type"),
            auth_config=stored.get("auth_config"),
            owner=stored.get("owner", "public"),
            is_active=stored.get("is_active", True),
            last_sync_status=stored.get("last_sync_status"),
            last_sync_at=stored.get("last_sync_at"),
            created_at=stored.get("created_at", datetime.now().isoformat()),
            updated_at=stored.get("updated_at", datetime.now().isoformat())
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create repository: {str(e)}")

@router.get("", response_model=List[Repository])
def list_repositories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List repositories with filtering and pagination."""
    try:
        engine = _get_engine()
        repos_repo = RepositoriesRepoDB(engine)
        
        filters = {
            "owner": user.get("id", "public")
        }
        if type:
            filters["type"] = type
        if is_active is not None:
            filters["is_active"] = is_active
        
        repositories, total = repos_repo.list(limit=limit, offset=offset, **filters)
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        out = []
        for repo in repositories:
            out.append(Repository(
                id=repo["id"],
                name=repo["name"],
                url=repo["url"],
                description=repo.get("description", ""),
                type=repo.get("type", "git"),
                branch=repo.get("branch"),
                auth_type=repo.get("auth_type"),
                auth_config=repo.get("auth_config"),
                owner=repo.get("owner", "public"),
                is_active=repo.get("is_active", True),
                last_sync_status=repo.get("last_sync_status"),
                last_sync_at=_iso(repo.get("last_sync_at")),
                created_at=_iso(repo.get("created_at")),
                updated_at=_iso(repo.get("updated_at"))
            ))
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list repositories: {str(e)}")

@router.get("/{repo_id}", response_model=Repository)
def get_repository(
    repo_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific repository by ID."""
    try:
        engine = _get_engine()
        repos_repo = RepositoriesRepoDB(engine)
        
        repository = repos_repo.get(repo_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check ownership
        if repository.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        return Repository(
            id=repository["id"],
            name=repository["name"],
            url=repository["url"],
            description=repository.get("description", ""),
            type=repository.get("type", "git"),
            branch=repository.get("branch"),
            auth_type=repository.get("auth_type"),
            auth_config=repository.get("auth_config"),
            owner=repository.get("owner", "public"),
            is_active=repository.get("is_active", True),
            last_sync_status=repository.get("last_sync_status"),
            last_sync_at=_iso(repository.get("last_sync_at")),
            created_at=_iso(repository.get("created_at")),
            updated_at=_iso(repository.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get repository: {str(e)}")

@router.put("/{repo_id}", response_model=Repository)
def update_repository(
    repo_id: str,
    repo_data: RepositoryUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update a repository."""
    try:
        engine = _get_engine()
        repos_repo = RepositoriesRepoDB(engine)
        
        # Check if repository exists and user has access
        existing_repo = repos_repo.get(repo_id)
        if not existing_repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if existing_repo.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update fields
        update_fields = {}
        if repo_data.name is not None:
            update_fields["name"] = repo_data.name
        if repo_data.url is not None:
            update_fields["url"] = repo_data.url
        if repo_data.description is not None:
            update_fields["description"] = repo_data.description
        if repo_data.type is not None:
            update_fields["type"] = repo_data.type
        if repo_data.branch is not None:
            update_fields["branch"] = repo_data.branch
        if repo_data.auth_type is not None:
            update_fields["auth_type"] = repo_data.auth_type
        if repo_data.auth_config is not None:
            update_fields["auth_config"] = repo_data.auth_config
        if repo_data.is_active is not None:
            update_fields["is_active"] = repo_data.is_active
        if repo_data.last_sync_status is not None:
            update_fields["last_sync_status"] = repo_data.last_sync_status
        
        if not update_fields:
            # No changes requested, return existing repository
            def _iso(v):
                return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
            return Repository(
                id=existing_repo["id"],
                name=existing_repo["name"],
                url=existing_repo["url"],
                description=existing_repo.get("description", ""),
                type=existing_repo.get("type", "git"),
                branch=existing_repo.get("branch"),
                auth_type=existing_repo.get("auth_type"),
                auth_config=existing_repo.get("auth_config"),
                owner=existing_repo.get("owner", "public"),
                is_active=existing_repo.get("is_active", True),
                last_sync_status=existing_repo.get("last_sync_status"),
                last_sync_at=_iso(existing_repo.get("last_sync_at")),
                created_at=_iso(existing_repo.get("created_at")),
                updated_at=_iso(existing_repo.get("updated_at"))
            )
        
        updated_repo = repos_repo.update(repo_id, update_fields)
        if not updated_repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        def _iso(v):
            return v.isoformat() if hasattr(v, "isoformat") else (v or datetime.now().isoformat())
        
        return Repository(
            id=updated_repo["id"],
            name=updated_repo["name"],
            url=updated_repo["url"],
            description=updated_repo.get("description", ""),
            type=updated_repo.get("type", "git"),
            branch=updated_repo.get("branch"),
            auth_type=updated_repo.get("auth_type"),
            auth_config=updated_repo.get("auth_config"),
            owner=updated_repo.get("owner", "public"),
            is_active=updated_repo.get("is_active", True),
            last_sync_status=updated_repo.get("last_sync_status"),
            last_sync_at=_iso(updated_repo.get("last_sync_at")),
            created_at=_iso(updated_repo.get("created_at")),
            updated_at=_iso(updated_repo.get("updated_at"))
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update repository: {str(e)}")

@router.delete("/{repo_id}", status_code=204)
def delete_repository(
    repo_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a repository."""
    try:
        engine = _get_engine()
        repos_repo = RepositoriesRepoDB(engine)
        
        # Check if repository exists and user has access
        existing_repo = repos_repo.get(repo_id)
        if not existing_repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        if existing_repo.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        success = repos_repo.delete(repo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete repository: {str(e)}")