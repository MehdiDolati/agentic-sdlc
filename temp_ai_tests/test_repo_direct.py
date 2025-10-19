"""Direct test of repositories endpoint."""
import sys
sys.path.insert(0, r"C:\Users\Mehdi\Projects\agentic\agentic-sdlc")

from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import RepositoriesRepoDB
from sqlalchemy.orm import Session

print("Testing repository access...")
try:
    engine = _create_engine(_database_url(_repo_root()))
    session = Session(engine)
    repos_repo = RepositoriesRepoDB(session)
    
    print("Listing repositories...")
    filters = {"$or": [{"owner": "public"}, {"is_public": True}]}
    repositories, total = repos_repo.list(limit=20, offset=0, **filters)
    
    print(f"Found {total} repositories:")
    for repo in repositories:
        print(f"  - {repo}")
        
except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
