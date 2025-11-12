import json
import requests

# Test the fixed feature-planning endpoint
url = "http://localhost:8000/plans/project/proj-20251029141049-plan-05cd1d/feature-planning"

try:
    response = requests.post(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ SUCCESS! Feature planning endpoint is working")
        print(f"Generated {data.get('user_stories_count', 0)} user stories")
        print(f"Selected plan: {data.get('selected_plan', {}).get('name', 'Unknown')}")
        print(f"Stories file: {data.get('stories_file', 'None')}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"❌ Connection Error: {e}")