#!/usr/bin/env python
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Now import and run the app
from services.api.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.app:app", host="0.0.0.0", port=8000, log_level="info", reload=False)