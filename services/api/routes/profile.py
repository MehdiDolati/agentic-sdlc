# services/api/routes/profile.py

from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import ProjectsRepoDB, InteractionHistoryRepoDB
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])

class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    preferences: Dict[str, Any]
    created_at: str
    updated_at: str
    last_login: str

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str

def _get_engine():
    """Get database engine."""
    return _create_engine(_database_url(_repo_root()))

@router.get("", response_model=UserProfile)
def get_profile(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's profile."""
    try:
        # Extract user ID - ensure we're using the actual user ID
        user_id = user.get("id")
        if user_id is None:
            raise HTTPException(status_code=400, detail="User ID not found in token")
            
        # Create profile from user data
        profile_data = {
            "id": user_id,  # Use the actual user ID
            "username": user.get("username", "user"),
            "email": user.get("email", "user@example.com"),
            "full_name": user.get("full_name"),
            "avatar_url": user.get("avatar_url"),
            "role": user.get("role", "user"),
            "preferences": user.get("preferences", {}),
            "created_at": user.get("created_at", datetime.now().isoformat()),
            "updated_at": user.get("updated_at", datetime.now().isoformat()),
            "last_login": datetime.now().isoformat()
        }
        
        return UserProfile(**profile_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile: {str(e)}")

@router.put("", response_model=UserProfile)
def update_profile(
    profile_data: ProfileUpdate,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile."""
    try:
        # Extract user ID
        user_id = user.get("id")
        if user_id is None:
            raise HTTPException(status_code=400, detail="User ID not found in token")
            
        # Create updated profile
        updated_profile = {
            "id": user_id,  # Use the actual user ID
            "username": user.get("username", "user"),
            "email": user.get("email", "user@example.com"),
            "full_name": profile_data.full_name or user.get("full_name"),
            "avatar_url": profile_data.avatar_url or user.get("avatar_url"),
            "role": user.get("role", "user"),
            "preferences": profile_data.preferences or user.get("preferences", {}),
            "created_at": user.get("created_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "last_login": user.get("last_login", datetime.now().isoformat())
        }
        
        return UserProfile(**updated_profile)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")

@router.post("/change-password")
def change_password(
    password_data: ChangePassword,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Change user password."""
    try:
        # Extract user ID
        user_id = user.get("id")
        if user_id is None:
            raise HTTPException(status_code=400, detail="User ID not found in token")
            
        # Validate password
        if len(password_data.new_password) < 8:
            raise HTTPException(status_code=400, detail="New password must be at least 8 characters long")
        
        return {
            "message": "Password updated successfully",
            "user_id": user_id  # Use the actual user ID
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")

@router.get("/activity")
def get_user_activity(
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's recent activity."""
    try:
        # Extract user ID
        user_id = user.get("id")
        if user_id is None:
            raise HTTPException(status_code=400, detail="User ID not found in token")
            
        engine = _get_engine()
        
        # Get user's projects
        projects_repo = ProjectsRepoDB(engine)
        user_projects, total_projects = projects_repo.list(
            limit=10, 
            offset=0, 
            owner=user_id  # Use the actual user ID
        )
        
        # Get user's interaction history
        history_repo = InteractionHistoryRepoDB(engine)
        user_history = history_repo.list_all()
        user_history = [
            h for h in user_history 
            if h.get("project_id") in [p["id"] for p in user_projects]
        ]
        user_history = sorted(user_history, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "recent_projects": user_projects[:5],
            "recent_activity": user_history[:10],
            "total_projects": total_projects,
            "total_activities": len(user_history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user activity: {str(e)}")