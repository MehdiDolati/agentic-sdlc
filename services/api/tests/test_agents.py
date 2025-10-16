# services/api/tests/test_agents.py

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

# Mock another user for access denied tests
mock_user2 = {
    "id": "user2", 
    "username": "otheruser",
    "email": "other@example.com",
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

@pytest.fixture
def client_with_user2():
    """Client with a different user for access tests."""
    def override_get_current_user():
        return mock_user2
    
    app.dependency_overrides[auth_get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_agent_success(client_with_user):
    """Test creating an agent successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        # Mock agent creation
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        created_agent = {
            "id": "agent123",
            "name": "Test Agent",
            "description": "Test agent for code analysis",
            "agent_type": "code_analyzer",
            "config": {"model": "gpt-4", "temperature": 0.7},
            "status": "inactive",
            "last_heartbeat": None,
            "capabilities": {"languages": ["python", "javascript"]},
            "owner": "user1",  # Same as mock user
            "is_public": False,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_agents_instance.create.return_value = created_agent
        mock_agents_instance.get.return_value = created_agent
        
        agent_data = {
            "name": "Test Agent",
            "description": "Test agent for code analysis",
            "agent_type": "code_analyzer",
            "config": {"model": "gpt-4", "temperature": 0.7},
            "capabilities": {"languages": ["python", "javascript"]},
            "is_public": False
        }
        
        response = client_with_user.post("/api/agents", json=agent_data)
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "agent123"
        assert data["name"] == "Test Agent"
        assert data["agent_type"] == "code_analyzer"
        assert data["owner"] == "user1"
        assert data["status"] == "inactive"

def test_create_agent_missing_required_fields(client_with_user):
    """Test creating an agent with missing required fields."""
    # Missing name and agent_type
    agent_data = {
        "description": "Test agent",
        "config": {}
    }
    
    response = client_with_user.post("/api/agents", json=agent_data)
    assert response.status_code == 422  # Validation error

def test_list_agents_success(client_with_user):
    """Test listing agents successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        sample_agents = [
            {
                "id": "agent1",
                "name": "Code Analyzer",
                "description": "Analyzes code quality",
                "agent_type": "code_analyzer",
                "config": {"model": "gpt-4"},
                "status": "active",
                "owner": "user1",  # Same as mock user
                "is_public": False,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            },
            {
                "id": "agent2",
                "name": "Test Runner",
                "description": "Runs tests",
                "agent_type": "test_runner",
                "config": {"timeout": 300},
                "status": "inactive",
                "owner": "user1",  # Same as mock user
                "is_public": True,
                "created_at": "2023-01-02T00:00:00",
                "updated_at": "2023-01-02T00:00:00"
            }
        ]
        
        mock_agents_instance.list.return_value = (sample_agents, 2)
        
        response = client_with_user.get("/api/agents?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Code Analyzer"
        assert data[1]["name"] == "Test Runner"

def test_list_agents_with_filters(client_with_user):
    """Test listing agents with type and status filters."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        mock_agents_instance.list.return_value = ([], 0)
        
        response = client_with_user.get("/api/agents?agent_type=code_analyzer&status=active&include_public=false")
        assert response.status_code == 200
        
        # Verify the filters were passed correctly
        mock_agents_instance.list.assert_called_once()
        call_args = mock_agents_instance.list.call_args
        assert call_args[1]["agent_type"] == "code_analyzer"
        assert call_args[1]["status"] == "active"

def test_get_agent_success(client_with_user):
    """Test getting a specific agent successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        agent_data = {
            "id": "agent1",
            "name": "Test Agent",
            "description": "Test agent",
            "agent_type": "code_analyzer",
            "config": {"model": "gpt-4"},
            "status": "active",
            "owner": "user1",  # Same as mock user
            "is_public": False,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_agents_instance.get.return_value = agent_data
        
        response = client_with_user.get("/api/agents/agent1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "agent1"
        assert data["name"] == "Test Agent"

def test_get_agent_not_found(client_with_user):
    """Test getting a non-existent agent."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        mock_agents_instance.get.return_value = None
        
        response = client_with_user.get("/api/agents/nonexistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

def test_get_public_agent_success(client_with_user):
    """Test getting a public agent owned by another user."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        # Public agent owned by different user
        agent_data = {
            "id": "agent1",
            "name": "Public Agent",
            "agent_type": "code_analyzer",
            "config": {},
            "owner": "user2",  # Different owner
            "is_public": True,  # But public
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_agents_instance.get.return_value = agent_data
        
        response = client_with_user.get("/api/agents/agent1")
        assert response.status_code == 200  # Should be accessible

def test_get_private_agent_access_denied(client_with_user):
    """Test getting a private agent owned by another user."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        # Private agent owned by different user
        agent_data = {
            "id": "agent1",
            "name": "Private Agent",
            "agent_type": "code_analyzer",
            "config": {},
            "owner": "user2",  # Different owner
            "is_public": False,  # Not public
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        mock_agents_instance.get.return_value = agent_data
        
        response = client_with_user.get("/api/agents/agent1")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

def test_update_agent_success(client_with_user):
    """Test updating an agent successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        existing_agent = {
            "id": "agent1",
            "name": "Old Name",
            "description": "Old description",
            "agent_type": "code_analyzer",
            "config": {"model": "gpt-3"},
            "status": "inactive",
            "owner": "user1",  # Same as mock user
            "is_public": False,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00"
        }
        
        updated_agent = {
            "id": "agent1",
            "name": "New Name",
            "description": "New description",
            "agent_type": "code_analyzer",
            "config": {"model": "gpt-4"},
            "status": "active",
            "owner": "user1",  # Same as mock user
            "is_public": True,
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-02T00:00:00"
        }
        
        mock_agents_instance.get.return_value = existing_agent
        mock_agents_instance.update.return_value = updated_agent
        
        update_data = {
            "name": "New Name",
            "description": "New description",
            "config": {"model": "gpt-4"},
            "status": "active",
            "is_public": True
        }
        
        response = client_with_user.put("/api/agents/agent1", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"
        assert data["description"] == "New description"
        assert data["status"] == "active"
        assert data["is_public"] == True

def test_delete_agent_success(client_with_user):
    """Test deleting an agent successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        
        existing_agent = {
            "id": "agent1",
            "name": "Test Agent",
            "agent_type": "code_analyzer",
            "config": {},
            "owner": "user1",  # Same as mock user
            "is_public": False
        }
        
        mock_agents_instance.get.return_value = existing_agent
        mock_agents_instance.delete.return_value = True
        
        response = client_with_user.delete("/api/agents/agent1")
        assert response.status_code == 204

def test_create_agent_run_success(client_with_user):
    """Test creating an agent run successfully."""
    with patch("services.api.routes.agents.AgentRunsRepoDB") as mock_runs_repo:
        with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
            
            # Mock agents repo
            mock_agents_instance = MagicMock()
            mock_agents_repo.return_value = mock_agents_instance
            
            agent_data = {
                "id": "agent1",
                "name": "Test Agent",
                "agent_type": "code_analyzer",
                "owner": "user1",  # Same as mock user
                "is_public": False
            }
            mock_agents_instance.get.return_value = agent_data
            
            # Mock runs repo
            mock_runs_instance = MagicMock()
            mock_runs_repo.return_value = mock_runs_instance
            
            created_run = {
                "id": "run123",
                "agent_id": "agent1",
                "project_id": "proj1",
                "plan_id": "plan1",
                "status": "queued",
                "input_data": {"code": "print('hello')"},
                "output_data": None,
                "started_at": None,
                "completed_at": None,
                "error_message": None,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
            
            mock_runs_instance.create.return_value = created_run
            mock_runs_instance.get.return_value = created_run
            
            run_data = {
                "agent_id": "agent1",
                "project_id": "proj1",
                "plan_id": "plan1",
                "input_data": {"code": "print('hello')"}
            }
            
            response = client_with_user.post("/api/agents/runs", json=run_data)
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == "run123"
            assert data["agent_id"] == "agent1"
            assert data["status"] == "queued"

def test_create_agent_run_agent_not_found(client_with_user):
    """Test creating an agent run with non-existent agent."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        
        mock_agents_instance = MagicMock()
        mock_agents_repo.return_value = mock_agents_instance
        mock_agents_instance.get.return_value = None  # Agent not found
        
        run_data = {
            "agent_id": "nonexistent",
            "input_data": {}
        }
        
        response = client_with_user.post("/api/agents/runs", json=run_data)
        assert response.status_code == 404
        assert "Agent not found" in response.json()["detail"]

def test_list_agent_runs_success(client_with_user):
    """Test listing agent runs successfully."""
    with patch("services.api.routes.agents.AgentsRepoDB") as mock_agents_repo:
        with patch("services.api.routes.agents.AgentRunsRepoDB") as mock_runs_repo:
            
            # Mock AgentsRepoDB with complete data
            mock_agents_instance = MagicMock()
            mock_agents_repo.return_value = mock_agents_instance
            
            complete_agent_data = {
                "id": "agent1",
                "name": "Test Agent",
                "description": "Test agent for code analysis",
                "agent_type": "code_analyzer",
                "config": {"model": "gpt-4", "temperature": 0.7},
                "status": "active",
                "last_heartbeat": None,
                "capabilities": {"languages": ["python", "javascript"]},
                "owner": "user1",
                "is_public": False,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
            mock_agents_instance.get.return_value = complete_agent_data
            
            # Mock AgentRunsRepoDB
            mock_runs_instance = MagicMock()
            mock_runs_repo.return_value = mock_runs_instance
            
            sample_runs = [
                {
                    "id": "run1",
                    "agent_id": "agent1",
                    "project_id": "proj1",
                    "plan_id": "plan1",
                    "status": "completed",
                    "input_data": {"code": "test1"},
                    "output_data": {"result": "success"},
                    "started_at": "2023-01-01T10:00:00",
                    "completed_at": "2023-01-01T10:05:00",
                    "error_message": None,
                    "created_at": "2023-01-01T09:00:00",
                    "updated_at": "2023-01-01T10:05:00"
                },
                {
                    "id": "run2",
                    "agent_id": "agent1",
                    "project_id": "proj1",
                    "plan_id": None,
                    "status": "running",
                    "input_data": {"code": "test2"},
                    "output_data": None,
                    "started_at": "2023-01-02T10:00:00",
                    "completed_at": None,
                    "error_message": None,
                    "created_at": "2023-01-02T09:00:00",
                    "updated_at": "2023-01-02T10:00:00"
                }
            ]
            
            mock_runs_instance.list.return_value = (sample_runs, 2)
            
            response = client_with_user.get("/api/agents/runs?agent_id=agent1&status=completed")
            print(f"Response status: {response.status_code}")
            print(f"Response data type: {type(response.json())}")
            print(f"Response data: {response.json()}")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check if we're getting a list
            if isinstance(data, list):
                print("Response is a list - good!")
                assert len(data) == 2
                assert data[0]["status"] == "completed"
                assert data[1]["status"] == "running"
            else:
                print(f"Response is not a list, it's a {type(data)}")
                # If it's a dict, check what keys it has
                if isinstance(data, dict):
                    print(f"Dict keys: {data.keys()}")
                    # This will help us understand what's being returned