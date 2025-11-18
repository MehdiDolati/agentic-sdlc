from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import json
from datetime import datetime
import httpx

from services.api.core.shared import _repo_root, _auth_enabled, _create_engine, _database_url
from services.api.auth.routes import get_current_user
from services.api.llm import get_llm_from_env

router = APIRouter(prefix="/api/plans", tags=["feature-stories"])

def get_db():
    """Get database session."""
    engine = _create_engine(_database_url(_repo_root()))
    with Session(engine) as session:
        yield session

@router.post("/{plan_id}/features/{feature_id}/generate-stories")
def generate_feature_stories(
    plan_id: str,
    feature_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Generate user stories and tasks for a specific feature using LLM.
    """
    
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    try:
        # Get plan details
        plan_result = db.execute(text("""
            SELECT * FROM plans WHERE id = :plan_id LIMIT 1
        """), {"plan_id": plan_id}).fetchone()
        
        if not plan_result:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        plan = dict(plan_result._mapping)
        
        # Get feature details
        feature_result = db.execute(text("""
            SELECT * FROM features WHERE id = :feature_id AND plan_id = :plan_id LIMIT 1
        """), {"feature_id": feature_id, "plan_id": plan_id}).fetchone()
        
        if not feature_result:
            raise HTTPException(status_code=404, detail="Feature not found")
        
        feature = dict(feature_result._mapping)
        
        # Get project details for more context
        project_result = db.execute(text("""
            SELECT * FROM projects WHERE id = :project_id LIMIT 1
        """), {"project_id": plan['project_id']}).fetchone()
        
        project = dict(project_result._mapping) if project_result else {}
        
        # Generate user stories using LLM (uses get_llm_from_env internally)
        user_stories = _generate_stories_with_llm(
            feature, 
            plan, 
            project,
            feature_id
        )
        
        # Save user stories to file
        repo_root = _repo_root()
        stories_dir = Path(repo_root) / "docs" / "stories"
        stories_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        stories_file = stories_dir / f"{timestamp}-{plan['project_id']}-feature-{feature_id}-user-stories.json"
        
        stories_data = {
            "project_id": plan['project_id'],
            "plan_id": plan_id,
            "plan_name": plan['name'],
            "feature_id": feature_id,
            "feature_name": feature['name'],
            "generated_at": datetime.now().isoformat(),
            "user_stories": user_stories
        }
        
        with open(stories_file, 'w', encoding='utf-8') as f:
            json.dump(stories_data, f, indent=2, ensure_ascii=False)
        
        return {
            "success": True,
            "message": f"Generated {len(user_stories)} user stories for feature '{feature['name']}'",
            "stories": user_stories,
            "stories_file": str(stories_file)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Failed to generate user stories: {str(e)}\n{traceback.format_exc()}"
        print(f"[ERROR in generate_feature_stories] {error_detail}")
        raise HTTPException(status_code=500, detail=f"Failed to generate user stories: {str(e)}")


def _generate_stories_with_llm(
    feature: Dict[str, Any],
    plan: Dict[str, Any],
    project: Dict[str, Any],
    feature_id: str
) -> list:
    """Generate user stories using LLM - same pattern as core.py."""
    
    # Get LLM client using the standard infrastructure (same as planner/core.py)
    llm_client = get_llm_from_env()
    
    if not llm_client:
        raise HTTPException(
            status_code=503,
            detail="LLM service is not configured. Please set LLM_PROVIDER environment variable to 'anthropic', 'openai', or 'supabase' and provide the corresponding API key."
        )
    
    # Build a comprehensive prompt that the LLM can understand
    request_text = f"""Generate user stories for this software feature:

PROJECT: {project.get('title', 'Unknown Project')}
PROJECT DESCRIPTION: {project.get('description', 'No description')}

PLAN: {plan.get('name', 'Unknown Plan')}
PLAN DESCRIPTION: {plan.get('description', 'No description')}

FEATURE: {feature['name']}
FEATURE DESCRIPTION: {feature.get('description', 'No description')}
PRIORITY: {feature.get('priority', 'medium')}
SIZE ESTIMATE: {feature.get('size_estimate', 5)} days

Generate 2-4 user stories in this JSON format:
{{
  "user_stories": [
    {{
      "title": "As a [role], I want to [action] so that [benefit]",
      "description": "Detailed description",
      "priority": "critical|high|medium|low",
      "acceptance_criteria": ["criterion 1", "criterion 2"],
      "story_points": <1-13>,
      "tasks": [
        {{"title": "Task description", "description": "Details"}},
        {{"title": "Another task", "description": "Details"}}
      ]
    }}
  ]
}}

Include both user-facing and technical stories (testing, deployment, documentation).
Each story should have 3-5 specific, actionable tasks."""

    try:
        # Use the LLM client's generate_plan method (same as core.py does)
        print(f"[DEBUG] Generating stories with LLM client: {type(llm_client).__name__}")
        artifacts = llm_client.generate_plan(request_text)
        
        # The generate_plan returns PlanArtifacts with prd_markdown
        # We need to extract JSON from it
        content = artifacts.prd_markdown if hasattr(artifacts, 'prd_markdown') else str(artifacts)
        
        # Extract JSON from markdown code blocks if present
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        
        # Try to parse as JSON
        try:
            response_data = json.loads(content)
        except json.JSONDecodeError as json_err:
            # If the content is not JSON, try to find JSON-like structure
            print(f"[WARN] LLM returned non-JSON content: {content[:200]}...")
            # Look for { "user_stories": pattern
            json_start = content.find('{"user_stories"')
            if json_start == -1:
                json_start = content.find("{'user_stories'")
            if json_start >= 0:
                # Find matching closing brace
                brace_count = 0
                json_end = json_start
                for i in range(json_start, len(content)):
                    if content[i] == '{':
                        brace_count += 1
                    elif content[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                content = content[json_start:json_end]
                try:
                    response_data = json.loads(content)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=500,
                        detail=f"LLM returned invalid JSON format. Please try again or check LLM configuration."
                    )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"LLM did not return valid JSON structure. Please try again or check LLM configuration."
                )
        
        if not response_data or "user_stories" not in response_data:
            raise HTTPException(
                status_code=500,
                detail="LLM failed to generate valid user stories. Please try again."
            )
        
        # Process and enrich the LLM response
        user_stories = []
        for idx, story in enumerate(response_data["user_stories"], 1):
            story_id = f"story-{feature_id}-{idx}"
            
            # Add tasks with proper IDs
            tasks = []
            for task_idx, task in enumerate(story.get("tasks", []), 1):
                tasks.append({
                    "id": f"task-{feature_id}-{idx}-{task_idx}",
                    "title": task.get("title", "Implement requirement"),
                    "description": task.get("description", ""),
                    "status": "pending"
                })
            
            user_stories.append({
                "id": story_id,
                "title": story.get("title", f"User story {idx}"),
                "description": story.get("description", ""),
                "feature_id": feature_id,
                "feature_name": feature['name'],
                "priority": story.get("priority", "medium"),
                "acceptance_criteria": story.get("acceptance_criteria", []),
                "story_points": story.get("story_points", 3),
                "status": "ready",
                "tasks": tasks
            })
        
        return user_stories
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] LLM story generation failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate user stories with LLM: {str(e)}"
        )
