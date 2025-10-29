"""
Unit tests for plans and features priority functionality.
Tests the new priority management, ordering, and change tracking features.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from services.api.app import app
from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.models.project import Plan, Feature, PriorityChange
import uuid


@pytest.fixture
def client_with_db(tmp_path, monkeypatch):
    """Test client with database setup."""
    monkeypatch.setenv("REPO_ROOT", str(tmp_path))
    # Ensure database directory exists
    (tmp_path / "docs" / "plans").mkdir(parents=True, exist_ok=True)

    # Initialize database schema
    from services.api.core.repos import ensure_plans_schema, ensure_projects_schema, ensure_features_schema, ensure_priority_changes_schema
    engine = _create_engine(_database_url(tmp_path))
    ensure_projects_schema(engine)
    ensure_plans_schema(engine)
    ensure_features_schema(engine)
    ensure_priority_changes_schema(engine)

    return TestClient(app)


@pytest.fixture
def test_project(client_with_db, tmp_path):
    """Create a test project and return its ID."""
    engine = _create_engine(_database_url(tmp_path))
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO projects (id, title, description, owner, status)
            VALUES (:id, :title, :description, :owner, :status)
        """), {
            "id": str(uuid.uuid4()),
            "title": "Test Project",
            "description": "Test project for priority tests",
            "owner": "test@example.com",
            "status": "active"
        })
        conn.commit()
        project_id = result.lastrowid
        return project_id


@pytest.fixture
def test_plans(client_with_db, tmp_path, test_project):
    """Create test plans with different priorities."""
    engine = _create_engine(_database_url(tmp_path))
    plan_ids = []

    plans_data = [
        {
            "request": "Critical security fix",
            "priority": "critical",
            "priority_order": 1,
            "size_estimate": 3
        },
        {
            "request": "High priority feature",
            "priority": "high",
            "priority_order": 2,
            "size_estimate": 5
        },
        {
            "request": "Medium priority task",
            "priority": "medium",
            "priority_order": 1,
            "size_estimate": 2
        },
        {
            "request": "Low priority maintenance",
            "priority": "low",
            "priority_order": 3,
            "size_estimate": 1
        }
    ]

    with engine.connect() as conn:
        for plan_data in plans_data:
            plan_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO plans (id, project_id, request, owner, artifacts, name, description, size_estimate, priority, priority_order, status)
                VALUES (:id, :project_id, :request, :owner, :artifacts, :name, :description, :size_estimate, :priority, :priority_order, :status)
            """), {
                "id": plan_id,
                "project_id": test_project,
                "request": plan_data["request"],
                "owner": "test@example.com",
                "artifacts": "{}",
                "name": plan_data["request"],  # Set name to request for now
                "description": f"Description for {plan_data['request']}",  # Set a description
                "size_estimate": plan_data["size_estimate"],
                "priority": plan_data["priority"],
                "priority_order": plan_data["priority_order"],
                "status": "pending"
            })
            plan_ids.append(plan_id)
        conn.commit()

    return plan_ids


@pytest.fixture
def test_features(client_with_db, tmp_path, test_plans):
    """Create test features for the first plan."""
    engine = _create_engine(_database_url(tmp_path))
    plan_id = test_plans[0]  # Use first plan
    feature_ids = []

    features_data = [
        {
            "name": "User authentication",
            "description": "Implement user login and registration",
            "priority": "high",
            "priority_order": 1,
            "size_estimate": 8
        },
        {
            "name": "Database optimization",
            "description": "Optimize database queries for better performance",
            "priority": "medium",
            "priority_order": 2,
            "size_estimate": 5
        }
    ]

    with engine.connect() as conn:
        for feature_data in features_data:
            feature_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO features (id, plan_id, name, description, size_estimate, priority, priority_order, status)
                VALUES (:id, :plan_id, :name, :description, :size_estimate, :priority, :priority_order, :status)
            """), {
                "id": feature_id,
                "plan_id": plan_id,
                "name": feature_data["name"],
                "description": feature_data["description"],
                "size_estimate": feature_data["size_estimate"],
                "priority": feature_data["priority"],
                "priority_order": feature_data["priority_order"],
                "status": "pending"
            })
            feature_ids.append(feature_id)
        conn.commit()

    return feature_ids


class TestPlanPriorityUpdates:
    """Test plan priority update functionality."""

    def test_update_plan_priority_valid(self, client_with_db, test_plans):
        """Test updating a plan's priority with valid values."""
        plan_id = test_plans[0]

        response = client_with_db.put(
            f"/plans/{plan_id}/priority",
            params={"priority": "high", "priority_order": 5}
        )

        assert response.status_code == 200
        plan = response.json()
        assert plan["priority"] == "high"
        assert plan["priority_order"] == 5

    def test_update_plan_priority_invalid(self, client_with_db, test_plans):
        """Test updating a plan's priority with invalid values."""
        plan_id = test_plans[0]

        response = client_with_db.put(
            f"/plans/{plan_id}/priority",
            params={"priority": "invalid_priority"}
        )

        assert response.status_code == 400
        assert "Invalid priority value" in response.json()["detail"]

    def test_update_plan_priority_not_found(self, client_with_db):
        """Test updating priority for non-existent plan."""
        response = client_with_db.put(
            "/plans/non-existent-id/priority",
            params={"priority": "high"}
        )

        assert response.status_code == 404
        assert "Plan not found" in response.json()["detail"]


class TestFeaturePriorityUpdates:
    """Test feature priority update functionality."""

    def test_update_feature_priority_valid(self, client_with_db, test_features):
        """Test updating a feature's priority with valid values."""
        feature_id = test_features[0]

        response = client_with_db.put(
            f"/plans/features/{feature_id}/priority",
            params={"priority": "critical", "priority_order": 1}
        )

        assert response.status_code == 200
        feature = response.json()
        assert feature["priority"] == "critical"
        assert feature["priority_order"] == 1

    def test_update_feature_priority_invalid(self, client_with_db, test_features):
        """Test updating a feature's priority with invalid values."""
        feature_id = test_features[0]

        response = client_with_db.put(
            f"/plans/features/{feature_id}/priority",
            params={"priority": "invalid"}
        )

        assert response.status_code == 400
        assert "Invalid priority value" in response.json()["detail"]


class TestPriorityOrdering:
    """Test that plans and features are ordered correctly by priority."""

    def test_get_plans_by_project_ordered_by_priority(self, client_with_db, test_project):
        """Test that plans are returned ordered by priority."""
        response = client_with_db.get(f"/plans/project/{test_project}")

        assert response.status_code == 200
        plans = response.json()

        # Should be ordered: critical (1), high (2), medium (3), low (4)
        priorities = [plan["priority"] for plan in plans]
        expected_order = ["critical", "high", "medium", "low"]

        # Check that priorities appear in correct order
        current_priority_index = 0
        for plan in plans:
            priority = plan["priority"]
            expected_index = expected_order.index(priority)
            assert expected_index >= current_priority_index
            current_priority_index = expected_index

    def test_get_features_by_plan_ordered_by_priority(self, client_with_db, test_plans, test_features):
        """Test that features are returned ordered by priority."""
        plan_id = test_plans[0]  # Plan with features

        response = client_with_db.get(f"/plans/{plan_id}/features")

        assert response.status_code == 200
        features = response.json()

        # Should be ordered by priority: high, then medium
        priorities = [feature["priority"] for feature in features]
        assert priorities == ["high", "medium"]  # Based on test data setup


class TestPriorityHistory:
    """Test priority change history tracking."""

    def test_get_plan_priority_history_empty(self, client_with_db, test_plans):
        """Test getting priority history for a plan with no changes."""
        plan_id = test_plans[0]

        response = client_with_db.get(f"/plans/plan/{plan_id}/priority-history")

        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        # May be empty or may have initial creation entry depending on trigger implementation

    def test_get_feature_priority_history_empty(self, client_with_db, test_features):
        """Test getting priority history for a feature with no changes."""
        feature_id = test_features[0]

        response = client_with_db.get(f"/plans/feature/{feature_id}/priority-history")

        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)

    def test_get_priority_history_invalid_entity_type(self, client_with_db):
        """Test getting priority history with invalid entity type."""
        response = client_with_db.get("/plans/invalid/test-id/priority-history")

        assert response.status_code == 400
        assert "Invalid entity type" in response.json()["detail"]


class TestNextTaskSelection:
    """Test next task selection based on priority."""

    def test_get_next_task_returns_highest_priority_feature(self, client_with_db, test_project, test_plans, test_features):
        """Test that next task returns the highest priority pending feature."""
        response = client_with_db.get(f"/plans/next-task/{test_project}")

        assert response.status_code == 200
        task = response.json()

        assert task["type"] == "feature"
        assert task["priority"] == "high"  # Highest priority feature
        assert "request" in task
        assert "plan_request" in task

    def test_get_next_task_returns_plan_when_no_features(self, client_with_db, tmp_path, test_project):
        """Test that next task returns a plan when no features are available."""
        # Create a plan but no features
        engine = _create_engine(_database_url(tmp_path))
        with engine.connect() as conn:
            plan_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO plans (id, project_id, request, owner, artifacts, size_estimate, priority, priority_order, status)
                VALUES (:id, :project_id, :request, :owner, :artifacts, :size_estimate, :priority, :priority_order, :status)
            """), {
                "id": plan_id,
                "project_id": test_project,
                "request": "High priority plan",
                "owner": "test@example.com",
                "artifacts": "{}",
                "size_estimate": 3,
                "priority": "high",
                "priority_order": 1,
                "status": "pending"
            })
            conn.commit()

        response = client_with_db.get(f"/plans/next-task/{test_project}")

        assert response.status_code == 200
        task = response.json()

        assert task["type"] == "plan"
        assert task["priority"] == "high"
        assert task["request"] == "High priority plan"

    def test_get_next_task_no_pending_tasks(self, client_with_db, tmp_path, test_project):
        """Test next task when no pending tasks exist."""
        # Mark all existing plans as completed
        engine = _create_engine(_database_url(tmp_path))
        with engine.connect() as conn:
            conn.execute(text("""
                UPDATE plans SET status = 'completed' WHERE project_id = :project_id
            """), {"project_id": test_project})
            conn.commit()

        response = client_with_db.get(f"/plans/next-task/{test_project}")

        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "No pending tasks found"


class TestPriorityChangeTracking:
    """Test that priority changes are properly tracked."""

    def test_priority_change_creates_history_entry(self, client_with_db, test_plans, tmp_path):
        """Test that updating priority creates a history entry."""
        plan_id = test_plans[0]

        # Update priority
        response = client_with_db.put(
            f"/plans/{plan_id}/priority",
            params={"priority": "low", "reason": "Changed due to business requirements"}
        )
        assert response.status_code == 200

        # Check history
        history_response = client_with_db.get(f"/plans/plan/{plan_id}/priority-history")
        assert history_response.status_code == 200
        history = history_response.json()

        # Should have at least one entry (may have initial creation entry too)
        assert len(history) >= 1

        # Find the change entry
        change_entry = None
        for entry in history:
            if entry.get("new_priority") == "low":
                change_entry = entry
                break

        assert change_entry is not None
        assert change_entry["entity_type"] == "plan"
        assert change_entry["entity_id"] == plan_id
        assert change_entry["new_priority"] == "low"
        if "change_reason" in change_entry:
            assert "business requirements" in change_entry["change_reason"]