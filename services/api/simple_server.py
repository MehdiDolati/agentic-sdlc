import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Import our working components
from services.api.core.shared import _database_url, _create_engine, _repo_root
from services.api.core.repos import ProjectsRepoDB

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
def list_projects(limit: int = 20, offset: int = 0):
    """List ALL projects without authentication."""
    try:
        engine = _get_engine()
        projects_repo = ProjectsRepoDB(engine)
        
        print(f"[DEBUG] Listing projects without filters")
        
        # Get ALL projects without any filtering
        projects, total = projects_repo.list(limit=limit, offset=offset)
        
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
    print("Starting simple server without auth...")
    uvicorn.run(app, host="0.0.0.0", port=8000)