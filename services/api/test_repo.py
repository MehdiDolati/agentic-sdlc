import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test database connection
try:
    from services.api.core.shared import _database_url, _create_engine, _repo_root
    print("1. Imported shared functions successfully")
    
    repo_root = _repo_root()
    print(f"2. Repo root: {repo_root}")
    
    db_url = _database_url(repo_root)
    print(f"3. Database URL: {db_url}")
    
    engine = _create_engine(db_url)
    print(f"4. Engine created: {engine}")
    
    # Test ProjectsRepoDB
    from services.api.core.repos import ProjectsRepoDB
    print("5. Imported ProjectsRepoDB successfully")
    
    projects_repo = ProjectsRepoDB(engine)
    print("6. ProjectsRepoDB instance created successfully")
    
    # Test basic list operation
    try:
        projects, total = projects_repo.list(limit=1, offset=0)
        print(f"7. Projects list successful: found {total} total projects, got {len(projects)} in result")
        if projects:
            print(f"8. Sample project: {projects[0].get('id')} - {projects[0].get('title')}")
    except Exception as e:
        print(f"7. ERROR in projects list: {e}")
        import traceback
        traceback.print_exc()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()