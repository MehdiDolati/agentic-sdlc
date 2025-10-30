import requests
import time
import json

def test_api():
    base_url = 'http://localhost:8001'

    # Wait for server to start
    time.sleep(3)

    print("Testing priority system API...")

    # Test next-task endpoint
    try:
        response = requests.get(f'{base_url}/plans/next-task')
        print(f"Next-task status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Next task: {json.dumps(data, indent=2)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Next-task error: {e}")

    # Test plans endpoint
    try:
        response = requests.get(f'{base_url}/plans')
        print(f"Plans status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Number of plans: {len(data)}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Plans error: {e}")

if __name__ == "__main__":
    test_api()