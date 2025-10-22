# services/api/routes/dashboard.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, text

from services.api.core.shared import _create_engine, _database_url, _repo_root, _auth_enabled
from services.api.core.repos import ProjectsRepoDB, PlansRepoDB, RunsRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

class ProjectSummary(BaseModel):
    id: str
    name: str
    description: str
    status: str
    progress: int
    stage: str
    createdAt: str
    documents: Dict[str, bool]
    currentPlan: Optional[Dict[str, Any]] = None

class DashboardStats(BaseModel):
    totalProjects: int
    inDevelopment: int
    completed: int
    teamMembers: int

class DashboardResponse(BaseModel):
    stats: DashboardStats
    recentProjects: List[ProjectSummary]

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

def _calculate_project_progress(project_id: str, plans_repo: PlansRepoDB, runs_repo: RunsRepoDB) -> int:
    """Calculate project progress based on plans and runs."""
    try:
        # Get all plans for this project
        plans, _ = plans_repo.list(limit=1000, offset=0, project_id=project_id)
        if not plans:
            return 0
        
        total_plans = len(plans)
        completed_plans = 0
        
        for plan in plans:
            # Get runs for this plan
            runs = runs_repo.list_for_plan(plan['id'])
            if runs:
                # Check if any run is completed
                for run in runs:
                    if run['status'] in ['completed', 'success']:
                        completed_plans += 1
                        break
        
        return int((completed_plans / total_plans) * 100) if total_plans > 0 else 0
    except Exception:
        return 0

def _get_project_stage(status: str, artifacts: Dict[str, Any]) -> str:
    """Determine project stage based on status and artifacts."""
    if status == "new":
        return "requirements"
    elif status == "planning":
        return "requirements"
    elif status == "development":
        if artifacts.get("prd") and artifacts.get("architecture"):
            return "features"
        elif artifacts.get("prd"):
            return "architecture"
        else:
            return "requirements"
    elif status == "testing":
        return "development"
    elif status == "completed":
        return "development"
    else:
        return "requirements"

def _to_iso_str(value: Any) -> str:
    """Return ISO-8601 string for datetime or passthrough for string; now() if missing."""
    try:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str) and value:
            return value
    except Exception:
        pass
    return datetime.now().isoformat()

def _to_date_str(value: Any) -> str:
    iso = _to_iso_str(value)
    # Expect "YYYY-MM-DD..."; split at 'T' if present
    return iso.split('T', 1)[0]

def _get_document_status(artifacts: Dict[str, Any]) -> Dict[str, bool]:
    """Extract document completion status from artifacts."""
    return {
        "prd": bool(artifacts.get("prd")),
        "architecture": bool(artifacts.get("architecture")),
        "userStories": bool(artifacts.get("stories")),
        "apis": bool(artifacts.get("openapi")),
        "plans": bool(artifacts.get("tasks")),
        "adr": bool(artifacts.get("adr"))
    }

def _get_current_plan_info(project_id: str, plans_repo: PlansRepoDB, runs_repo: RunsRepoDB) -> Optional[Dict[str, Any]]:
    """Get current plan information for a project."""
    try:
        plans, _ = plans_repo.list(limit=1, offset=0, project_id=project_id, sort="created_at", order="desc")
        if not plans:
            return None
        
        plan = plans[0]
        runs = runs_repo.list_for_plan(plan['id'])
        
        if not runs:
            return None
        
        latest_run = runs[0]  # Already sorted by created_at desc
        
        # Calculate progress based on run status
        progress = 0
        if latest_run['status'] == 'completed':
            progress = 100
        elif latest_run['status'] == 'running':
            progress = 50
        elif latest_run['status'] == 'failed':
            progress = 0
        
        return {
            "id": plan['id'],
            "name": plan['request'][:50] + "..." if len(plan['request']) > 50 else plan['request'],
            "status": latest_run['status'],
            "progress": progress,
            "completedTasks": progress // 5,  # Rough estimate
            "totalTasks": 20,  # Default estimate
            "createdAt": _to_iso_str(plan.get('created_at'))
        }
    except Exception:
        return None

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(user: Dict[str, Any] = Depends(get_current_user)):
    """Get dashboard statistics."""
    try:
        if _auth_enabled() and user.get("id") == "public":
            raise HTTPException(status_code=401, detail="authentication required")
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Get all projects for the user
        projects, total = projects_repo.list(limit=1000, offset=0, owner=user.get("id", "public"))
        
        # Calculate stats
        total_projects = len(projects)
        in_development = len([p for p in projects if p.get("status") == "development"])
        completed = len([p for p in projects if p.get("status") == "completed"])
        
        # For now, return a default team size - this could be enhanced with actual user management
        team_members = 5
        
        return DashboardStats(
            totalProjects=total_projects,
            inDevelopment=in_development,
            completed=completed,
            teamMembers=team_members
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")

@router.get("/recent-projects", response_model=List[ProjectSummary])
def get_recent_projects(
    limit: int = Query(default=10, ge=1, le=50),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get recent projects for the dashboard."""
    try:
        if _auth_enabled() and user.get("id") == "public":
            raise HTTPException(status_code=401, detail="authentication required")
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        plans_repo = PlansRepoDB(engine)
        runs_repo = RunsRepoDB(engine)
        
        # Get recent projects
        projects, _ = projects_repo.list(limit=limit, offset=0, sort="created_at", order="desc", owner=user.get("id", "public"))
        
        project_summaries = []
        for project in projects:
            # Calculate progress
            progress = _calculate_project_progress(project['id'], plans_repo, runs_repo)
            
            # Determine stage
            stage = _get_project_stage(project['status'], project.get('artifacts', {}))
            
            # Get document status
            documents = _get_document_status(project.get('artifacts', {}))
            
            # Get current plan info
            current_plan = _get_current_plan_info(project['id'], plans_repo, runs_repo)
            
            project_summary = ProjectSummary(
                id=project['id'],
                name=project['title'],
                description=project.get('description', ''),
                status=project['status'],
                progress=progress,
                stage=stage,
                createdAt=_to_date_str(project.get('created_at')),
                documents=documents,
                currentPlan=current_plan
            )
            project_summaries.append(project_summary)
        
        return project_summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent projects: {str(e)}")

@router.get("/", response_model=DashboardResponse)
def get_dashboard_data(
    limit: int = Query(default=10, ge=1, le=50),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get complete dashboard data (stats + recent projects)."""
    try:
        if _auth_enabled() and user.get("id") == "public":
            raise HTTPException(status_code=401, detail="authentication required")
        # Get stats
        stats = get_dashboard_stats(user)
        
        # Get recent projects
        recent_projects = get_recent_projects(limit, user)
        
        return DashboardResponse(
            stats=stats,
            recentProjects=recent_projects
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")


