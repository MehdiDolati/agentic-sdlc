# services/api/routes/repositories.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4
from sqlalchemy.orm import Session

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import RepositoriesRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

class RepositoryCreate(BaseModel):
    name: str
    url: str
    api_url: Optional[str] = None
    description: Optional[str] = ""
    type: Optional[str] = "git"
    branch: Optional[str] = "main"
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None

class RepositoryUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_url: Optional[str] = None
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
    api_url: Optional[str] = None
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

def _get_session():
    engine = _get_engine()
    return Session(engine)

def _dict_to_repository(repo_dict: Dict[str, Any]) -> Repository:
    """Convert a repository dictionary to a Repository model."""
    # Convert datetime objects to strings
    created_at = repo_dict.get("created_at")
    updated_at = repo_dict.get("updated_at")
    last_sync_at = repo_dict.get("last_sync_at")
    
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()
    elif created_at:
        created_at = str(created_at)
        
    if isinstance(updated_at, datetime):
        updated_at = updated_at.isoformat()
    elif updated_at:
        updated_at = str(updated_at)
        
    if last_sync_at:
        if isinstance(last_sync_at, datetime):
            last_sync_at = last_sync_at.isoformat()
        else:
            last_sync_at = str(last_sync_at)
    
    # Convert URL to string if needed
    url = repo_dict.get("url", "")
    if hasattr(url, "__str__") and not isinstance(url, str):
        url = str(url)
    
    return Repository(
        id=str(repo_dict.get("id", "")),
        name=str(repo_dict.get("name", "")),
        url=url,
        api_url=repo_dict.get("api_url"),
        description=str(repo_dict.get("description", "")),
        type=str(repo_dict.get("type", "git")),
        branch=repo_dict.get("branch"),
        auth_type=repo_dict.get("auth_type"),
        auth_config=repo_dict.get("auth_config"),
        owner=str(repo_dict.get("owner", "")),
        is_active=bool(repo_dict.get("is_active", True)),
        last_sync_status=repo_dict.get("last_sync_status"),
        last_sync_at=last_sync_at,
        created_at=created_at,
        updated_at=updated_at
    )

@router.post("", response_model=Repository, status_code=201)
def create_repository(
    repo_data: RepositoryCreate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new repository configuration."""
    try:
        session = _get_session()
        repos_repo = RepositoriesRepoDB(session)
        
        # Generate ID and create repository data dict
        repo_dict = {
            "id": str(uuid4())[:8],
            "name": repo_data.name,
            "url": str(repo_data.url),
            "api_url": repo_data.api_url,
            "description": repo_data.description or "",
            "type": repo_data.type or "git",
            "branch": repo_data.branch or "main",
            "auth_type": repo_data.auth_type,
            "auth_config": repo_data.auth_config,
            "owner": user.get("id", "public"),
            "is_active": True,
            "is_public": False
        }
        
        created_repo_dict = repos_repo.create(repo_dict)
        return _dict_to_repository(created_repo_dict)
    except Exception as e:
        import traceback
        error_detail = f"Failed to create repository: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("", response_model=List[Repository])
def list_repositories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    type: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    user: Dict[str, Any] = Depends(get_current_user),
    include_public: Optional[bool] = Query(default=True),
):
    """List repositories with filtering and pagination."""
    try:
        session = _get_session()
        repos_repo = RepositoriesRepoDB(session)
        
        # Get repositories with filtering
        filters = {}
        if type is not None:
            filters["type"] = type
        if is_active is not None:
            filters["is_active"] = is_active
            
        repositories, total = repos_repo.list(limit=limit, offset=offset, **filters)
        
        # Convert dict results to Repository models
        return [_dict_to_repository(repo_dict) for repo_dict in repositories]
    except Exception as e:
        import traceback
        error_detail = f"Failed to list repositories: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/{repo_id}", response_model=Repository)
def get_repository(
    repo_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific repository by ID."""
    try:
        session = _get_session()
        repos_repo = RepositoriesRepoDB(session)
        
        repo_dict = repos_repo.get(repo_id)
        if not repo_dict:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check ownership
        if repo_dict.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return _dict_to_repository(repo_dict)
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
        session = _get_session()
        repos_repo = RepositoriesRepoDB(session)
        
        # Check if repository exists and user has access
        existing_repo = repos_repo.get(repo_id)
        if not existing_repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check ownership - existing_repo is a dictionary
        if existing_repo.get("owner") != user.get("id", "public"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update fields
        update_fields = {}
        if repo_data.name is not None:
            update_fields["name"] = repo_data.name
        if repo_data.url is not None:
            update_fields["url"] = str(repo_data.url)
        if repo_data.api_url is not None:
            update_fields["api_url"] = repo_data.api_url
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
            return _dict_to_repository(existing_repo)
        
        updated_repo_dict = repos_repo.update(repo_id, update_fields)
        if not updated_repo_dict:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        return _dict_to_repository(updated_repo_dict)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Failed to update repository: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)

@router.delete("/{repo_id}", status_code=204)
def delete_repository(
    repo_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a repository."""
    try:
        session = _get_session()
        repos_repo = RepositoriesRepoDB(session)
        
        # Check if repository exists and user has access
        existing_repo = repos_repo.get(repo_id)
        if not existing_repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # Check ownership - existing_repo is a dictionary
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