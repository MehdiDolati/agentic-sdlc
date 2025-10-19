import requests
import json
import time

# Wait for server to start
time.sleep(2)

try:
    response = requests.get("http://localhost:8000/api/repositories", headers={"Authorization": "Bearer test-token"}, timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response:\n{json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
