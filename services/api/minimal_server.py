import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import uvicorn

# Import our working components
from services.api.core.shared import _database_url, _create_engine, _repo_root, _auth_enabled
from services.api.core.repos import ProjectsRepoDB
from services.api.auth.routes import get_current_user

app = FastAPI()

def _get_engine():
    """Get database engine."""
    repo_root = _repo_root()
    db_url = _database_url(repo_root)
    return _create_engine(db_url)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/projects")
def list_projects(
    limit: int = 20,
    offset: int = 0,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List projects with authentication filtering."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        # Build filters - filter by authenticated user's projects
        filters = {}
        
        # If auth is enabled and user is not public, filter by user's projects
        if _auth_enabled() and user.get("id") != "public":
            filters["owner"] = user.get("id")
            print(f"[DEBUG] Auth enabled, filtering by user: {user.get('id')}")
        else:
            # For public/unauthenticated access, show ALL projects (temporarily for debugging)
            print(f"[DEBUG] Auth disabled or public user, showing all projects")
            pass
        
        projects, total = projects_repo.list(limit=limit, offset=offset, **filters)
        
        print(f"[DEBUG] Found {total} total projects, returning {len(projects)} projects")
        
        # Convert to simple response format
        result = []
        for p in projects:
            result.append({
                "id": p["id"],
                "title": p["title"],
                "description": p.get("description", ""),
                "owner": p.get("owner", "public"),
                "status": p.get("status", "planning"),
                "createdAt": p.get("created_at", ""),
                "updatedAt": p.get("updated_at", ""),
            })
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Failed to list projects: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": f"Failed to list projects: {str(e)}"})

if __name__ == "__main__":
    print("Starting minimal test server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)