from typing import List, Optional
import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.api.core.shared import _create_engine, _database_url, _repo_root, _auth_enabled
from services.api.auth.routes import get_current_user
from services.api.models.project import (
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

@router.get("/project/{project_id}", response_model=List[dict])
def get_plans_by_project(project_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get all plans for a project."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    plans = db.execute(text("""
        SELECT * FROM plans 
        WHERE project_id = :project_id 
        ORDER BY priority_order ASC
    """), {"project_id": project_id}).fetchall()
    
    # Convert to dict and return
    result = []
    for plan in plans:
        plan_dict = dict(plan._mapping)
        plan_dict['features'] = []
        result.append(plan_dict)
    
    return result

@router.delete("/{plan_id}")
def delete_plan(plan_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a plan and all its features."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    # Delete features first (due to foreign key constraints)
    db.execute(text("DELETE FROM features WHERE plan_id = :plan_id"), {"plan_id": plan_id})
    
    # Delete the plan
    result = db.execute(text("DELETE FROM plans WHERE id = :plan_id"), {"plan_id": plan_id})
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return {"message": "Plan deleted successfully"}

@router.delete("/{plan_id}/features/{feature_id}")
def delete_feature(plan_id: str, feature_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Delete a specific feature."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    # Delete the feature
    result = db.execute(text("DELETE FROM features WHERE id = :feature_id AND plan_id = :plan_id"), {
        "feature_id": feature_id,
        "plan_id": plan_id
    })
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return {"message": "Feature deleted successfully"}

@router.get("/{plan_id}", response_model=Plan)
def get_plan(plan_id: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Get a specific plan."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    plan = db.execute(text("SELECT * FROM plans WHERE id = :id"), {"id": plan_id}).fetchone()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_dict = dict(plan._mapping)
    plan_dict['name'] = plan_dict.get('request', '')
    plan_dict['description'] = plan_dict.get('request', '')
    plan_dict['features'] = []  # Add empty features list
    return Plan(**plan_dict)

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
    return Plan(**plan._mapping)

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

    current_plan_dict = current_plan._mapping

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
    return Plan(**plan._mapping)

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
        ORDER BY priority_order ASC,
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            created_at ASC
    """), {"plan_id": plan_id}).fetchall()

    return [Feature(**feature._mapping) for feature in features]

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

    current_feature_dict = current_feature._mapping

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
    return Feature(**feature._mapping)

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

    return [PriorityChange(**change._mapping) for change in changes]

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
        ORDER BY f.priority_order ASC,
            CASE f.priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            f.created_at ASC
        LIMIT 1
    """), {"project_id": project_id}).fetchone()

    if feature:
        feature_dict = feature._mapping
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
        ORDER BY priority_order ASC,
            CASE priority
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END,
            created_at ASC
        LIMIT 1
    """), {"project_id": project_id}).fetchone()

    if plan:
        plan_dict = plan._mapping
        return {
            "type": "plan",
            "id": plan_dict['id'],
            "request": plan_dict['request'],
            "artifacts": plan_dict['artifacts'],
            "priority": plan_dict['priority'],
            "size_estimate": plan_dict['size_estimate']
        }

    return {"message": "No pending tasks found"}

# Bulk save plans and features to files
@router.post("/save-all")
def save_all_plans(payload: dict, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    """Save all plans and features to both database and markdown files."""
    from pathlib import Path
    import json
    from datetime import datetime
    
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    project_id = payload.get("project_id")
    project_name = payload.get("project_name", project_id)
    plans = payload.get("plans", [])
    
    if not project_id or not plans:
        raise HTTPException(status_code=400, detail="project_id and plans are required")
    
    # Get the docs root directory
    docs_root = _repo_root() / "docs"
    plans_dir = docs_root / "plans"
    features_dir = docs_root / "features"
    plans_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    saved_plan_count = 0
    saved_feature_count = 0
    db_plan_ids = []
    
    try:
        for plan_idx, plan_data in enumerate(plans, 1):
            # Extract plan data
            plan_id = plan_data.get("id") or str(uuid.uuid4())
            plan_name = plan_data.get("name", f"Plan {plan_idx}")
            plan_desc = plan_data.get("description", "")
            plan_priority = plan_data.get("priority", "medium")
            plan_order = plan_data.get("priority_order", plan_idx)
            plan_size = plan_data.get("size_estimate", 0)
            plan_features = plan_data.get("features", [])
            
            print(f"[SAVE PLANS] Saving plan: id={plan_id}, name={plan_name}, priority={plan_priority}, priority_order={plan_order}")
            
            # Save plan to database
            db.execute(text("""
                INSERT OR REPLACE INTO plans 
                (id, project_id, request, owner, artifacts, name, description, priority, priority_order, 
                 size_estimate, status, created_at, updated_at)
                VALUES (:id, :project_id, :request, :owner, :artifacts, :name, :description, :priority, 
                        :priority_order, :size_estimate, :status,
                        COALESCE((SELECT created_at FROM plans WHERE id = :id), datetime('now')),
                        datetime('now'))
            """), {
                "id": plan_id,
                "project_id": project_id,
                "request": plan_name,  # Using plan name as the request
                "owner": user.get("id", "system"),
                "artifacts": "{}",  # Empty JSON object
                "name": plan_name,
                "description": plan_desc,
                "priority": plan_priority,
                "priority_order": plan_order,
                "size_estimate": plan_size,
                "status": "pending"
            })
            db.commit()
            db_plan_ids.append(plan_id)
            
            # Sanitize filename
            safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in plan_name)
            safe_name = safe_name.replace(' ', '-').lower()
            plan_filename = f"{plan_order:02d}-{safe_name}.md"
            plan_file = plans_dir / plan_filename
            
            # Create plan markdown content
            plan_content = f"""# {plan_name}

**Priority:** {plan_priority.upper()}  
**Order:** {plan_order}  
**Estimated Size:** {plan_size} days  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Description

{plan_desc}

## Features

"""
            
            # Save features as separate files and reference them in plan
            feature_files = []
            for feat_idx, feature in enumerate(plan_features, 1):
                feat_id = feature.get("id") or str(uuid.uuid4())
                feat_name = feature.get("name", f"Feature {feat_idx}")
                feat_desc = feature.get("description", "")
                feat_priority = feature.get("priority", "medium")
                feat_order = feature.get("priority_order", feat_idx)
                feat_size = feature.get("size_estimate", 0)
                feat_criteria = feature.get("acceptance_criteria", [])
                
                print(f"[SAVE PLANS] Saving feature: id={feat_id}, name={feat_name}, priority={feat_priority}, priority_order={feat_order}")
                
                # Save feature to database
                db.execute(text("""
                    INSERT OR REPLACE INTO features 
                    (id, plan_id, name, description, priority, priority_order, size_estimate, status,
                     created_at, updated_at)
                    VALUES (:id, :plan_id, :name, :description, :priority, :priority_order, :size_estimate,
                            :status,
                            COALESCE((SELECT created_at FROM features WHERE id = :id), datetime('now')),
                            datetime('now'))
                """), {
                    "id": feat_id,
                    "plan_id": plan_id,
                    "name": feat_name,
                    "description": feat_desc,
                    "priority": feat_priority,
                    "priority_order": feat_order,
                    "size_estimate": feat_size,
                    "status": "pending"
                })
                db.commit()
                saved_feature_count += 1
                
                # Create separate feature file
                safe_feat_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in feat_name)
                safe_feat_name = safe_feat_name.replace(' ', '-').lower()
                feature_filename = f"{plan_order:02d}-{feat_order:02d}-{safe_feat_name}.md"
                feature_file = features_dir / feature_filename
                
                # Create feature markdown content
                feature_content = f"""# {feat_name}

**Plan:** {plan_name}  
**Priority:** {feat_priority.upper()}  
**Order:** {feat_order}  
**Estimated Size:** {feat_size} hours  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Description

{feat_desc}

"""
                if feat_criteria:
                    feature_content += "**Acceptance Criteria:**\n\n"
                    for criterion in feat_criteria:
                        feature_content += f"- {criterion}\n"
                    feature_content += "\n"
                
                # Write feature file
                feature_file.write_text(feature_content, encoding='utf-8')
                feature_files.append(str(feature_file.relative_to(_repo_root())))
                
                # Add reference to plan file
                plan_content += f"""### {feat_order}. {feat_name}

**Priority:** {feat_priority.upper()}  
**Estimated Size:** {feat_size} hours  
**File:** [{feature_filename}](../features/{feature_filename})

"""
            
            # Write plan file
            plan_file.write_text(plan_content, encoding='utf-8')
            saved_files.append(str(plan_file.relative_to(_repo_root())))
            saved_files.extend(feature_files)  # Include feature files in saved files list
            saved_plan_count += 1
        
        return {
            "success": True,
            "saved_plans": saved_plan_count,
            "saved_features": saved_feature_count,
            "file_paths": saved_files,
            "plan_ids": db_plan_ids,
            "message": f"Successfully saved {saved_plan_count} plans and {saved_feature_count} features to database and separate files"
        }
        
    except Exception as e:
        import traceback
        error_detail = f"Failed to save plans: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR in save_all_plans] {error_detail}")
        raise HTTPException(status_code=500, detail=f"Failed to save plans: {str(e)}")