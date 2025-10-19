"""Test repositories API endpoint."""
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "test-token"

headers = {"Authorization": f"Bearer {TOKEN}"}

print("Testing /api/repositories endpoint...")
try:
    response = requests.get(f"{BASE_URL}/api/repositories", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✓ Success!")
    else:
        print(f"✗ Error: {response.status_code}")
except Exception as e:
    print(f"✗ Exception: {e}")
