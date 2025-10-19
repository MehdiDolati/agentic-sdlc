"""Direct test to see the actual error."""
import sys
sys.path.insert(0, r"C:\Users\Mehdi\Projects\agentic\agentic-sdlc")

import traceback
from sqlalchemy.orm import Session
from services.api.core.shared import _create_engine, _database_url, _repo_root
from services.api.core.repos import RepositoriesRepoDB

print("Testing repository list...")
try:
    engine = _create_engine(_database_url(_repo_root()))
    session = Session(engine)
    repos_repo = RepositoriesRepoDB(session)
    
    print("Calling list()...")
    repositories, total = repos_repo.list(limit=20, offset=0)
    
    print(f"\nFound {total} repositories:")
    for repo in repositories:
        print(f"  Type: {type(repo)}")
        print(f"  Data: {repo}")
        print()
        
except Exception as e:
    print(f"\nError: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
