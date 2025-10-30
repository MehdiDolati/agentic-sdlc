#!/usr/bin/env python3
"""Simple test server script to run the backend for PRD testing."""

import sys
import os
from pathlib import Path

# Set up the path properly
current_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(current_dir))

# Set environment variables
os.environ["PYTHONPATH"] = str(current_dir)

try:
    import uvicorn
    from services.api.app import app
    
    print("Starting test backend server...")
    print(f"Working directory: {current_dir}")
    print("Server will run on http://localhost:8000")
    print("Press Ctrl+C to stop")
    
    # Start the server
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        log_level="info",
        reload=False
    )
    
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're in the correct directory and dependencies are installed")
except Exception as e:
    print(f"Error starting server: {e}")