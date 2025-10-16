# services/api/tests/test_api_admin.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from services.api.app import app  # Changed from main to app
from services.api.auth.routes import get_current_user as auth_get_current_user

# Mock regular user (non-admin)
mock_user = {
    "id": "user1",
    "username": "testuser", 
    "email": "test@example.com",
    "role": "user"
}

# Mock admin user
mock_admin_user = {
    "id": "admin1",
    "username": "adminuser",
    "email": "admin@example.com", 
    "role": "admin"
}

@pytest.fixture
def client_with_user():
    """Client with regular user."""
    def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture
def client_with_admin():
    """Client with admin user."""
    def override_get_current_user():
        return mock_admin_user
    
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_get_system_stats_without_admin_role(client_with_user):
    """Test that non-admin users cannot access system stats."""
    response = client_with_user.get("/api/admin/stats")
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

def test_get_system_stats_with_admin_role(client_with_admin):
    """Test that admin users can access system stats."""
    with patch("services.api.routes.admin.ProjectsRepoDB") as mock_projects_repo:
        with patch("services.api.routes.admin.PlansRepoDB") as mock_plans_repo:
            
            # Mock projects repo
            mock_projects_instance = MagicMock()
            mock_projects_repo.return_value = mock_projects_instance
            mock_projects_instance.list.return_value = ([{"id": "1", "status": "active"}], 1)
            
            # Mock plans repo
            mock_plans_instance = MagicMock()
            mock_plans_repo.return_value = mock_plans_instance
            mock_plans_instance.list.return_value = ([{"id": "1", "status": "new"}], 1)
            
            response = client_with_admin.get("/api/admin/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_projects" in data
            assert "total_plans" in data

def test_list_users_without_admin_role(client_with_user):
    """Test that non-admin users cannot list users."""
    response = client_with_user.get("/api/admin/users")
    assert response.status_code == 403

def test_list_users_with_admin_role(client_with_admin):
    """Test that admin users can list users."""
    response = client_with_admin.get("/api/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_get_recent_activity_without_admin_role(client_with_user):
    """Test that non-admin users cannot access recent activity."""
    response = client_with_user.get("/api/admin/activity")
    assert response.status_code == 403

def test_get_recent_activity_with_admin_role(client_with_admin):
    """Test that admin users can access recent activity."""
    with patch("services.api.routes.admin.InteractionHistoryRepoDB") as mock_history_repo:
        
        # Mock history repo
        mock_history_instance = MagicMock()
        mock_history_repo.return_value = mock_history_instance
        mock_history_instance.list_all.return_value = [
            {"id": "1", "prompt": "test", "response": "test", "created_at": "2023-01-01T00:00:00"}
        ]
        
        response = client_with_admin.get("/api/admin/activity?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "recent_activity" in data
        assert "total_activities" in data