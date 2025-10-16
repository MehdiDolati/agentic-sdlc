# services/api/tests/test_api_profile.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from services.api.app import app
from services.api.auth.routes import get_current_user as auth_get_current_user

# Mock user data
mock_user = {
    "id": "user1",
    "username": "testuser", 
    "email": "test@example.com",
    "role": "user"
}

mock_user_no_id = {
    "username": "testuser",
    "email": "test@example.com", 
    "role": "user"
}

def override_get_current_user():
    return mock_user

def override_get_current_user_no_id():
    return mock_user_no_id

def test_get_profile():
    """Test getting user profile."""
    # Override the dependency
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    
    client = TestClient(app)
    
    try:
        response = client.get("/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user1"
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    finally:
        # Clear the override
        app.dependency_overrides.clear()

def test_get_profile_missing_user_id():
    """Test getting profile when user ID is missing from token."""
    # Override with user that has no ID
    app.dependency_overrides[auth_get_current_user] = override_get_current_user_no_id
    
    client = TestClient(app)
    
    try:
        response = client.get("/api/profile")
        assert response.status_code == 400
        assert "User ID not found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

def test_update_profile():
    """Test updating user profile."""
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    
    client = TestClient(app)
    
    try:
        update_data = {
            "full_name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg", 
            "preferences": {"theme": "dark", "language": "en"}
        }
        
        response = client.put("/api/profile", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user1"
        assert data["full_name"] == "Test User"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"
        assert data["preferences"]["theme"] == "dark"
    finally:
        app.dependency_overrides.clear()

def test_change_password_success():
    """Test changing password successfully."""
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    
    client = TestClient(app)
    
    try:
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/profile/change-password", json=password_data)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["user_id"] == "user1"
    finally:
        app.dependency_overrides.clear()

def test_change_password_short_password():
    """Test changing password with too short new password."""
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    
    client = TestClient(app)
    
    try:
        password_data = {
            "current_password": "oldpassword123",
            "new_password": "short"
        }
        
        response = client.post("/api/profile/change-password", json=password_data)
        assert response.status_code == 400
        assert "at least 8 characters" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

def test_get_user_activity():
    """Test getting user activity."""
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    
    client = TestClient(app)
    
    try:
        with patch("services.api.routes.profile.ProjectsRepoDB") as mock_projects_repo:
            with patch("services.api.routes.profile.InteractionHistoryRepoDB") as mock_history_repo:
                
                # Mock projects repo
                mock_projects_instance = MagicMock()
                mock_projects_repo.return_value = mock_projects_instance
                mock_projects_instance.list.return_value = ([
                    {"id": "proj1", "title": "Test Project"}
                ], 1)
                
                # Mock history repo
                mock_history_instance = MagicMock()
                mock_history_repo.return_value = mock_history_instance
                mock_history_instance.list_all.return_value = [
                    {"id": "1", "project_id": "proj1", "prompt": "test", "response": "test"}
                ]
                
                response = client.get("/api/profile/activity")
                assert response.status_code == 200
                data = response.json()
                assert "recent_projects" in data
                assert "recent_activity" in data
                assert "total_projects" in data
    finally:
        app.dependency_overrides.clear()