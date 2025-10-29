from typing import List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.api.core.shared import _create_engine, _database_url, _repo_root, _auth_enabled
from services.api.auth.routes import get_current_user
from ..models.project import (
    Plan, PlanCreate, PlanBase,
    Feature, FeatureCreate, FeatureBase,
    PriorityChange, PriorityChangeCreate
)

router = APIRouter(prefix="/plans", tags=["plans"])

def get_db():
    """Get database session."""
    engine = _create_engine(_database_url(_repo_root()))
    with Session(engine) as session:
        yield session

# Plan CRUD endpoints
@router.post("/", response_model=Plan)
def create_plan(plan: PlanCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Create a new plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    # Create plan in database
    result = db.execute(text("""
        INSERT INTO plans (id, project_id, name, description, size_estimate, priority, priority_order, status)
        VALUES (:id, :project_id, :name, :description, :size_estimate, :priority, :priority_order, :status)
    """), {
        "id": str(uuid.uuid4()),
        "project_id": plan.project_id,
        "name": plan.name,
        "description": plan.description,
        "size_estimate": plan.size_estimate,
        "priority": plan.priority,
        "priority_order": plan.priority_order,
        "status": plan.status
    })
    db.commit()

    # Return created plan
    plan_data = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": result.lastrowid}).fetchone()
    return Plan(**plan_data)

@router.get("/project/{project_id}", response_model=List[Plan])
def get_plans_by_project(project_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get all plans for a project."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    plans = db.execute(text("""
        SELECT * FROM plans
        WHERE project_id = :project_id
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            priority_order ASC,
            created_at ASC
    """), {"project_id": project_id}).fetchall()

    return [Plan(**plan) for plan in plans]

@router.get("/{plan_id}", response_model=Plan)
def get_plan(plan_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get a specific plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    plan = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": plan_id}).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return Plan(**plan._asdict())

@router.put("/{plan_id}", response_model=Plan)
def update_plan(plan_id: str, plan_update: PlanBase, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Update a plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    # Update plan
    db.execute(text("""
        UPDATE plans
        SET name = :name, description = :description, size_estimate = :size_estimate,
            priority = :priority, priority_order = :priority_order, status = :status
        WHERE id = :id
    """), {
        "id": plan_id,
        "name": plan_update.name,
        "description": plan_update.description,
        "size_estimate": plan_update.size_estimate,
        "priority": plan_update.priority,
        "priority_order": plan_update.priority_order,
        "status": plan_update.status
    })
    db.commit()

    # Return updated plan
    plan = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": plan_id}).fetchone()
    return Plan(**plan._asdict())

@router.put("/{plan_id}/priority", response_model=Plan)
def update_plan_priority(
    plan_id: str,
    priority: str,
    priority_order: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update a plan's priority."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    if priority not in ['low', 'medium', 'high', 'critical']:
        raise HTTPException(status_code=400, detail="Invalid priority value")

    from sqlalchemy import text
    # Get current plan data
    current_plan = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": plan_id}).fetchone()
    if not current_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    current_plan_dict = current_plan._asdict()

    # Check if priority actually changed
    priority_changed = (current_plan_dict['priority'] != priority or 
                       current_plan_dict.get('priority_order') != priority_order)

    # Update priority
    db.execute(text("""
        UPDATE plans
        SET priority = :priority, priority_order = :priority_order
        WHERE id = :id
    """), {
        "id": plan_id,
        "priority": priority,
        "priority_order": priority_order
    })

    # Record priority change if it actually changed
    if priority_changed:
        db.execute(text("""
            INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order, change_reason, changed_by)
            VALUES (:entity_type, :entity_id, :old_priority, :new_priority, :old_priority_order, :new_priority_order, :change_reason, :changed_by)
        """), {
            "entity_type": "plan",
            "entity_id": plan_id,
            "old_priority": current_plan_dict['priority'],
            "new_priority": priority,
            "old_priority_order": current_plan_dict.get('priority_order'),
            "new_priority_order": priority_order,
            "change_reason": reason,
            "changed_by": user.get("id")
        })

    db.commit()

    # Return updated plan
    plan = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": plan_id}).fetchone()
    return Plan(**plan._asdict())

# Feature CRUD endpoints
@router.post("/{plan_id}/features", response_model=Feature)
def create_feature(plan_id: str, feature: FeatureCreate, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Create a new feature for a plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    from sqlalchemy import text
    import uuid
    result = db.execute(text("""
        INSERT INTO features (id, plan_id, name, description, size_estimate, priority, priority_order, status)
        VALUES (:id, :plan_id, :name, :description, :size_estimate, :priority, :priority_order, :status)
    """), {
        "id": str(uuid.uuid4()),
        "plan_id": plan_id,
        "name": feature.name,
        "description": feature.description,
        "size_estimate": feature.size_estimate,
        "priority": feature.priority,
        "priority_order": feature.priority_order,
        "status": feature.status
    })
    db.commit()

    # Return created feature
    feature_data = db.execute(text("SELECT * FROM features WHERE id = :id"), {"id": result.lastrowid}).fetchone()
    return Feature(**feature_data)

@router.get("/{plan_id}/features", response_model=List[Feature])
def get_features_by_plan(plan_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get all features for a plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    from sqlalchemy import text
    features = db.execute(text("""
        SELECT * FROM features
        WHERE plan_id = :plan_id
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            priority_order ASC,
            created_at ASC
    """), {"plan_id": plan_id}).fetchall()

    return [Feature(**feature._asdict()) for feature in features]

@router.put("/features/{feature_id}/priority", response_model=Feature)
def update_feature_priority(
    feature_id: str,
    priority: str,
    priority_order: Optional[int] = None,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Update a feature's priority."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    if priority not in ['low', 'medium', 'high', 'critical']:
        raise HTTPException(status_code=400, detail="Invalid priority value")

    from sqlalchemy import text
    # Get current feature data
    current_feature = db.execute(text("SELECT * FROM features WHERE id = :id"), {"id": feature_id}).fetchone()
    if not current_feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    current_feature_dict = current_feature._asdict()

    # Check if priority actually changed
    priority_changed = (current_feature_dict['priority'] != priority or 
                       current_feature_dict.get('priority_order') != priority_order)

    # Update priority
    db.execute(text("""
        UPDATE features
        SET priority = :priority, priority_order = :priority_order
        WHERE id = :id
    """), {
        "id": feature_id,
        "priority": priority,
        "priority_order": priority_order
    })

    # Record priority change if it actually changed
    if priority_changed:
        db.execute(text("""
            INSERT INTO priority_changes (entity_type, entity_id, old_priority, new_priority, old_priority_order, new_priority_order, change_reason, changed_by)
            VALUES (:entity_type, :entity_id, :old_priority, :new_priority, :old_priority_order, :new_priority_order, :change_reason, :changed_by)
        """), {
            "entity_type": "feature",
            "entity_id": feature_id,
            "old_priority": current_feature_dict['priority'],
            "new_priority": priority,
            "old_priority_order": current_feature_dict.get('priority_order'),
            "new_priority_order": priority_order,
            "change_reason": reason,
            "changed_by": user.get("id")
        })

    db.commit()

    # Return updated feature
    feature = db.execute(text("SELECT * FROM features WHERE id = :id"), {"id": feature_id}).fetchone()
    return Feature(**feature._asdict())

# Priority change history endpoints
@router.get("/{entity_type}/{entity_id}/priority-history", response_model=List[PriorityChange])
def get_priority_history(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get priority change history for a plan or feature."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    if entity_type not in ['plan', 'feature']:
        raise HTTPException(status_code=400, detail="Invalid entity type")

    from sqlalchemy import text
    changes = db.execute(text("""
        SELECT * FROM priority_changes
        WHERE entity_type = :entity_type AND entity_id = :entity_id
        ORDER BY created_at DESC
    """), {"entity_type": entity_type, "entity_id": entity_id}).fetchall()

    return [PriorityChange(**change._asdict()) for change in changes]

# Priority-based selection endpoint
@router.get("/next-task/{project_id}")
def get_next_task(project_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get the next highest priority task (plan or feature) to work on."""
    # if _auth_enabled() and user.get("id") == "public":
    #     raise HTTPException(status_code=401, detail="authentication required")

    from sqlalchemy import text
    # Find the highest priority pending feature
    feature = db.execute(text("""
        SELECT f.*, p.request as plan_request
        FROM features f
        JOIN plans p ON f.plan_id = p.id
        WHERE p.project_id = :project_id AND f.status = 'pending'
        ORDER BY
            CASE f.priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            f.priority_order ASC,
            f.created_at ASC
        LIMIT 1
    """), {"project_id": project_id}).fetchone()

    if feature:
        feature_dict = feature._asdict()
        return {
            "type": "feature",
            "id": feature_dict['id'],
            "request": feature_dict['name'],  # features table uses 'name'
            "artifacts": feature_dict['description'],  # features table uses 'description'
            "plan_request": feature_dict['plan_request'],  # Use request from joined plans table
            "priority": feature_dict['priority'],
            "size_estimate": feature_dict['size_estimate']
        }

    # If no features, find the highest priority pending plan
    plan = db.execute(text("""
        SELECT * FROM plans
        WHERE project_id = :project_id AND status = 'pending'
        ORDER BY
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            priority_order ASC,
            created_at ASC
        LIMIT 1
    """), {"project_id": project_id}).fetchone()

    if plan:
        plan_dict = plan._asdict()
        return {
            "type": "plan",
            "id": plan_dict['id'],
            "request": plan_dict['request'],
            "artifacts": plan_dict['artifacts'],
            "priority": plan_dict['priority'],
            "size_estimate": plan_dict['size_estimate']
        }

    return {"message": "No pending tasks found"}