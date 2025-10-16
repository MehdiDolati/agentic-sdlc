# services/api/tests/test_repositories.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from services.api.app import app  # Changed from main to app
from services.api.auth.routes import get_current_user as auth_get_current_user

# Mock user data
mock_user = {
    "id": "user1", 
    "username": "testuser",
    "email": "test@example.com",
    "role": "user"
}

@pytest.fixture
def client_with_user():
    """Client with authenticated user."""
    def override_get_current_user():
        return mock_user
    
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_repository_success(client_with_user):
    """Test creating a repository successfully."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        # Mock repository creation
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        created_repo = {
            "id": "repo123",
            "name": "Test Repo",
            "url": "https://github.com/test/repo.git",
            "description": "Test repository",
            "type": "git",
            "branch": "main",
            "auth_type": None,
            "auth_config": None,
            "owner": "user1",  # Same as mock user
            "is_active": True,
            "last_sync_status": None,
            "last_sync_at": None,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_repo_instance.create.return_value = created_repo
        mock_repo_instance.get.return_value = created_repo
        
        repo_data = {
            "name": "Test Repo",
            "url": "https://github.com/test/repo.git",
            "description": "Test repository",
            "type": "git",
            "branch": "main"
        }
        
        response = client_with_user.post("/api/repositories", json=repo_data)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "repo123"
        assert data["name"] == "Test Repo"
        assert data["url"] == "https://github.com/test/repo.git"
        assert data["owner"] == "user1"

def test_create_repository_missing_required_fields(client_with_user):
    """Test creating a repository with missing required fields."""
    # Missing name and url
    repo_data = {
        "description": "Test repository"
    }
    
    response = client_with_user.post("/api/repositories", json=repo_data)
    assert response.status_code == 422  # Validation error

def test_list_repositories_success(client_with_user):
    """Test listing repositories successfully."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        sample_repos = [
            {
                "id": "repo1",
                "name": "Repo 1",
                "url": "https://github.com/test/repo1.git",
                "description": "First repo",
                "type": "git",
                "branch": "main",
                "owner": "user1",  # Same as mock user
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            },
            {
                "id": "repo2", 
                "name": "Repo 2",
                "url": "https://github.com/test/repo2.git",
                "description": "Second repo",
                "type": "git",
                "branch": "develop",
                "owner": "user1",  # Same as mock user
                "is_active": True,
                "created_at": "2023-01-02T00:00:00",
                "updated_at": "2023-01-02T00:00:00"
            }
        ]
        
        mock_repo_instance.list.return_value = (sample_repos, 2)
        
        response = client_with_user.get("/api/repositories?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Repo 1"
        assert data[1]["name"] == "Repo 2"

def test_list_repositories_with_filters(client_with_user):
    """Test listing repositories with type and active filters."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.list.return_value = ([], 0)
        
        response = client_with_user.get("/api/repositories?type=git&is_active=true")
        assert response.status_code == 200
        
        # Verify the filters were passed correctly
        mock_repo_instance.list.assert_called_once()
        call_args = mock_repo_instance.list.call_args
        assert call_args[1]["type"] == "git"
        assert call_args[1]["is_active"] == True

def test_get_repository_success(client_with_user):
    """Test getting a specific repository successfully."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        repo_data = {
            "id": "repo1",
            "name": "Test Repo",
            "url": "https://github.com/test/repo.git",
            "description": "Test repository",
            "type": "git",
            "branch": "main",
            "owner": "user1",  # Same as mock user
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_repo_instance.get.return_value = repo_data
        
        response = client_with_user.get("/api/repositories/repo1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "repo1"
        assert data["name"] == "Test Repo"

def test_get_repository_not_found(client_with_user):
    """Test getting a non-existent repository."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.get.return_value = None
        
        response = client_with_user.get("/api/repositories/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

def test_get_repository_access_denied(client_with_user):
    """Test getting a repository owned by another user."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        # Repository owned by different user
        repo_data = {
            "id": "repo1",
            "name": "Test Repo",
            "url": "https://github.com/test/repo.git",
            "owner": "user2",  # Different owner
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_repo_instance.get.return_value = repo_data
        
        response = client_with_user.get("/api/repositories/repo1")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

def test_update_repository_success(client_with_user):
    """Test updating a repository successfully."""
    with patch("services.api.routes.repositories.RepositoriesRepoDB") as mock_repo:
        
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        
        existing_repo = {
            "id": "repo1",
            "name": "Old Name",
            "url": "https://github.com/test/repo.git",
            "description": "Old description",
            "type": "git",
            "branch": "main",
            "owner": "user1",  # Same as mock user
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        updated_repo = {
            "id": "repo1",
            "name": "New Name",
            "url": "https://github.com/test/repo.git",
            "description": "New description",
            "type": "git",
            "branch": "develop",
            "owner": "user1",  # Same as mock user
            "is_active": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00"
        }
        
        mock_repo_instance.get.return_value = existing_repo
        mock_repo_instance.update.return_value = updated_repo
        
        update_data = {
            "name": "New Name",
            "description": "New description",
            "branch": "develop"
        }
        
       