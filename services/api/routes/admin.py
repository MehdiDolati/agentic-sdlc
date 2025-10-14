# services/api/routes/admin.py

from __future__ import annotations
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    created_at: Optional[str] = None

class AdminStats(BaseModel):
    total_users: int
    total_projects: int
    active_projects: int
    completed_projects: int

def require_admin(user: Dict[str, Any] = Depends(get_current_user)):
    """Dependency to require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/stats", response_model=AdminStats)
async def get_admin_stats(admin: Dict[str, Any] = Depends(require_admin)):
    """Get admin dashboard statistics."""
    try:
        # Mock data - replace with actual database queries
        return AdminStats(
            total_users=150,
            total_projects=45,
            active_projects=28,
            completed_projects=17
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get admin stats: {str(e)}")

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    admin: Dict[str, Any] = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """Get all users (admin only)."""
    try:
        # Mock data - replace with actual database queries
        users = [
            UserResponse(
                id="u_1",
                email="admin@example.com",
                role="admin",
                created_at="2024-01-01"
            ),
            UserResponse(
                id="u_2", 
                email="user1@example.com",
                role="user",
                created_at="2024-01-02"
            ),
            UserResponse(
                id="u_3",
                email="user2@example.com", 
                role="user",
                created_at="2024-01-03"
            )
        ]
        return users[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")

@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Promote a user to admin role."""
    try:
        # In real implementation, update user role in database
        return {
            "status": "success", 
            "message": f"User {user_id} promoted to admin"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to promote user: {str(e)}")

@router.post("/users/{user_id}/demote") 
async def demote_user(
    user_id: str,
    admin: Dict[str, Any] = Depends(require_admin)
):
    """Demote an admin to user role."""
    try:
        # In real implementation, update user role in database
        return {
            "status": "success",
            "message": f"User {user_id} demoted to user role"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to demote user: {str(e)}")