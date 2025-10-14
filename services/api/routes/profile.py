# services/api/routes/profile.py

from __future__ import annotations
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str

@router.get("/", response_model=ProfileResponse)
async def get_profile_data(user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's profile data."""
    try:
        if user.get("id") == "public":
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # In a real implementation, you would fetch from your database
        # For now, return basic user info
        return ProfileResponse(
            id=user["id"],
            email=user["email"],
            full_name=user.get("full_name"),
            avatar_url=user.get("avatar_url"),
            role=user.get("role", "user")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get profile data: {str(e)}")

@router.put("/")
async def update_profile(
    update_data: ProfileUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update user profile."""
    try:
        if user.get("id") == "public":
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # In a real implementation, you would update the database
        # For now, just return success
        return {
            "status": "success",
            "message": "Profile updated successfully",
            "data": {
                "full_name": update_data.full_name,
                "avatar_url": update_data.avatar_url
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {str(e)}")