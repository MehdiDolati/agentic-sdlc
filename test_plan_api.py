import sys
import os
from pathlib import Path

# Add the services/api directory to the path
_BASE_DIR = Path(__file__).resolve().parent / 'services' / 'api'
if str(_BASE_DIR) not in sys.path:
    sys.path.insert(0, str(_BASE_DIR))

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(Path(__file__).resolve().parent)

from fastapi.testclient import TestClient
from app import app

def test_project_endpoint():
    client = TestClient(app)

    # Test the project endpoint
    response = client.get("/api/projects/c35c3d53")

    print(f"Project Status Code: {response.status_code}")
    print(f"Project Response: {response.text}")

    if response.status_code == 200:
        data = response.json()
        print("Success! Project found:")
        print(f"ID: {data.get('id', 'N/A')}")
        print(f"Title: {data.get('title', 'N/A')}")
    else:
        print("Project not found or error")

def test_plan_generation():
    client = TestClient(app)

    # Test the plan generation endpoint with JSON format
    response = client.post("/ui/requests?format=json", data={
        "project_vision": "Build a simple web application with user authentication and database storage",
        "agent_mode": "single",
        "llm_provider": "none"
    })

    print(f"Plan Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Plan generation successful!")
    else:
        print(f"Plan generation failed: {response.text}")

if __name__ == "__main__":
    test_project_endpoint()
    print("\n" + "="*50 + "\n")
    test_plan_generation()