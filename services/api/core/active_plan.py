# services/api/core/active_plan.py
"""
Active Plan Management

This module provides utilities for determining and managing the active plan for a project.
"""

from typing import Optional, Dict, Any
from sqlalchemy import text
from services.api.core.shared import _create_engine

def get_active_plan_for_project(project_id: str) -> Optional[Dict[str, Any]]:
    """
    Determine the active plan for a project using business logic.
    
    Priority order:
    1. Explicitly set active_plan_id in projects table
    2. Plan with status 'in_progress' 
    3. Plan with status 'planning'
    4. Highest priority plan (by priority_order, then priority level)
    
    Returns:
        Dict with plan details and metadata, or None if no plans found
    """
    try:
        engine = _create_engine()
        with engine.begin() as db:
            # Try to get explicitly set active plan first
            explicit_result = db.execute(text("""
                SELECT p.*, pr.active_plan_id
                FROM projects pr 
                LEFT JOIN plans p ON pr.active_plan_id = p.id
                WHERE pr.id = :project_id AND pr.active_plan_id IS NOT NULL
            """), {"project_id": project_id}).fetchone()
            
            if explicit_result:
                plan_data = dict(explicit_result._mapping)
                plan_data["determination_method"] = "explicit"
                plan_data["is_explicit"] = True
                return plan_data
            
            # Find plan by status priority: in_progress > planning > others
            status_result = db.execute(text("""
                SELECT * FROM plans 
                WHERE project_id = :project_id 
                AND status IN ('in_progress', 'planning')
                ORDER BY 
                    CASE 
                        WHEN status = 'in_progress' THEN 1 
                        WHEN status = 'planning' THEN 2 
                        ELSE 3 
                    END,
                    priority_order ASC, 
                    CASE priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        WHEN 'low' THEN 4 
                    END
                LIMIT 1
            """), {"project_id": project_id}).fetchone()
            
            if status_result:
                plan_data = dict(status_result._mapping)
                plan_data["determination_method"] = "status_priority"
                plan_data["is_explicit"] = False
                return plan_data
            
            # Fall back to highest priority plan
            priority_result = db.execute(text("""
                SELECT * FROM plans 
                WHERE project_id = :project_id 
                ORDER BY 
                    priority_order ASC,
                    CASE priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        WHEN 'low' THEN 4 
                    END
                LIMIT 1
            """), {"project_id": project_id}).fetchone()
            
            if priority_result:
                plan_data = dict(priority_result._mapping)
                plan_data["determination_method"] = "highest_priority"
                plan_data["is_explicit"] = False
                return plan_data
            
            return None
            
    except Exception as e:
        print(f"[ERROR in get_active_plan_for_project] {str(e)}")
        return None

def set_active_plan_for_project(project_id: str, plan_id: str) -> bool:
    """
    Explicitly set the active plan for a project.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        engine = _create_engine()
        with engine.begin() as db:
            # Verify the plan exists and belongs to the project
            plan_check = db.execute(text("""
                SELECT id FROM plans 
                WHERE id = :plan_id AND project_id = :project_id
            """), {"plan_id": plan_id, "project_id": project_id}).fetchone()
            
            if not plan_check:
                return False
            
            # Update the project's active plan
            db.execute(text("""
                UPDATE projects 
                SET active_plan_id = :plan_id 
                WHERE id = :project_id
            """), {"plan_id": plan_id, "project_id": project_id})
            
            return True
            
    except Exception as e:
        print(f"[ERROR in set_active_plan_for_project] {str(e)}")
        return False

def get_plan_navigation_context(project_id: str) -> Dict[str, Any]:
    """
    Get navigation context for a project's plans.
    
    Returns information about:
    - Active plan
    - All plans for the project 
    - Navigation suggestions
    """
    try:
        engine = _create_engine()
        with engine.begin() as db:
            # Get active plan
            active_plan = get_active_plan_for_project(project_id)
            
            # Get all plans for context
            all_plans = db.execute(text("""
                SELECT id, name, description, status, priority, priority_order
                FROM plans 
                WHERE project_id = :project_id
                ORDER BY 
                    priority_order ASC,
                    CASE priority 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        WHEN 'low' THEN 4 
                    END
            """), {"project_id": project_id}).fetchall()
            
            plans_list = [dict(row._mapping) for row in all_plans]
            
            return {
                "active_plan": active_plan,
                "all_plans": plans_list,
                "has_multiple_plans": len(plans_list) > 1,
                "navigation_suggestion": "plan_specific" if active_plan else "project_wide"
            }
            
    except Exception as e:
        print(f"[ERROR in get_plan_navigation_context] {str(e)}")
        return {
            "active_plan": None,
            "all_plans": [],
            "has_multiple_plans": False,
            "navigation_suggestion": "project_wide"
        }