#!/usr/bin/env python
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set REPO_ROOT environment variable to ensure correct database path
os.environ["REPO_ROOT"] = str(project_root)

if __name__ == "__main__":
    import uvicorn
    # Import app after path is set
    from services.api.app import app
    
    # Run with reload disabled to prevent shutdown issues
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
