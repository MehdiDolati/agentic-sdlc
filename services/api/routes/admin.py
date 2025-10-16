# services/api/routes/admin.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from uuid import uuid4

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import ProjectsRepoDB, PlansRepoDB, RunsRepoDB, InteractionHistoryRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

class SystemStats(BaseModel):
    total_projects: int
    total_plans: int
    total_runs: int
    total_users: int
    projects_by_status: Dict[str, int]
    plans_by_status: Dict[str, int]
    runs_by_status: Dict[str, int]

class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    role: str
    created_at: str
    last_login: str

class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.get("/stats", response_model=SystemStats)
def get_system_stats(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get system statistics (admin only)."""
    try:
        # Check if user has admin privileges
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        plans_repo = PlansRepoDB(engine)
        runs_repo = RunsRepoDB(engine)
        
        # Get basic counts
        projects, total_projects = projects_repo.list(limit=1, offset=0)
        plans, total_plans = plans_repo.list(limit=1, offset=0)
        
        # Get status distributions (simplified - in real implementation, you'd query with GROUP BY)
        projects_by_status = {"active": 0, "completed": 0, "planning": 0}
        plans_by_status = {"new": 0, "running": 0, "completed": 0, "failed": 0}
        runs_by_status = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        
        # Sample implementation - you'd want to implement proper aggregation in repos
        all_projects, _ = projects_repo.list(limit=1000, offset=0)
        for project in all_projects:
            status = project.get("status", "planning")
            projects_by_status[status] = projects_by_status.get(status, 0) + 1
        
        all_plans, _ = plans_repo.list(limit=1000, offset=0)
        for plan in all_plans:
            status = plan.get("status", "new")
            plans_by_status[status] = plans_by_status.get(status, 0) + 1
        
        # For runs, we need a different approach since we don't have a list_all method
        # This is a simplified implementation
        runs_by_status = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        
        return SystemStats(
            total_projects=total_projects,
            total_plans=total_plans,
            total_runs=0,  # You'd implement proper counting
            total_users=1,  # You'd implement user counting
            projects_by_status=projects_by_status,
            plans_by_status=plans_by_status,
            runs_by_status=runs_by_status
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system stats: {str(e)}")

@router.get("/users", response_model=List[UserInfo])
def list_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List all users (admin only)."""
    try:
        # Check if user has admin privileges
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # This is a simplified implementation
        # In a real system, you'd have a proper users table and repo
        users = []
        
        # Sample user data - replace with actual user repository
        sample_user = UserInfo(
            id=user.get("id", "1"),
            username=user.get("username", "admin"),
            email=user.get("email", "admin@example.com"),
            role=user.get("role", "admin"),
            created_at=datetime.now().isoformat(),
            last_login=datetime.now().isoformat()
        )
        users.append(sample_user)
        
        return users[:limit]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {str(e)}")

@router.get("/activity")
def get_recent_activity(
    limit: int = Query(default=50, ge=1, le=200),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get recent system activity (admin only)."""
    try:
        # Check if user has admin privileges
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        engine = _get_engine()
        history_repo = InteractionHistoryRepoDB(engine)
        
        # Get recent activity from interaction history
        recent_history = history_repo.list_all()
        recent_history = sorted(recent_history, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "recent_activity": recent_history[:limit],
            "total_activities": len(recent_history)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent activity: {str(e)}")