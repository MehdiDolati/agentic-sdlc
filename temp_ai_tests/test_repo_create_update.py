"""Test repository create and update operations."""
import requests
import json

BASE_URL = "http://localhost:8000"
TOKEN = "test-token"
headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

print("=" * 60)
print("Testing Repository CREATE operation")
print("=" * 60)

create_data = {
    "name": "Test Repo",
    "url": "https://github.com/test/repo",
    "description": "Test repository",
    "type": "git",
    "branch": "main"
}

try:
    response = requests.post(f"{BASE_URL}/api/repositories", headers=headers, json=create_data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✓ CREATE Success!")
        repo_data = response.json()
        print(f"Created repository: {json.dumps(repo_data, indent=2)}")
        repo_id = repo_data["id"]
        
        print("\n" + "=" * 60)
        print("Testing Repository UPDATE operation")
        print("=" * 60)
        
        update_data = {
            "description": "Updated description",
            "branch": "develop"
        }
        
        response = requests.put(f"{BASE_URL}/api/repositories/{repo_id}", headers=headers, json=update_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✓ UPDATE Success!")
            updated_data = response.json()
            print(f"Updated repository: {json.dumps(updated_data, indent=2)}")
        else:
            print(f"✗ UPDATE Failed: {response.text}")
    else:
        print(f"✗ CREATE Failed: {response.text}")
except Exception as e:
    print(f"✗ Exception: {e}")
