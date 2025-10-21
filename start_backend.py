import sys
import os
from pathlib import Path

# Add the project root to Python path  
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

if __name__ == "__main__":
    try:
        print("Starting backend server...")
        from services.api.app import app
        import uvicorn
        
        # Start the server with proper configuration
        port = int(os.getenv("PORT", "8000"))
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=port,
            log_level="debug",
            access_log=True,
            reload=False,
            lifespan="on"
        )
        server = uvicorn.Server(config)
        print("Server configured, starting...")
        try:
            server.run()
        except Exception as e:
            print(f"Server run error: {e}")
            import traceback
            traceback.print_exc()
        print("Server run completed")
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()