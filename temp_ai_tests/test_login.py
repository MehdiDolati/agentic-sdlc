import requests
import json
import os

# Disable proxy
os.environ['NO_PROXY'] = '*'

url = "http://127.0.0.1:8000/auth/login"
payload = {
    "email": "persianmd@yahoo.com",
    "password": "dolati60"
}

print(f"Testing login to {url}")
print(f"Payload: {payload}")

try:
    resp = requests.post(url, json=payload, proxies={'http': None, 'https': None})
    print(f"\nStatus Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Body: {resp.text}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nLogin successful!")
        print(f"Access token: {data.get('access_token', 'N/A')[:50]}...")
    else:
        print(f"\nLogin failed!")
        try:
            error_data = resp.json()
            print(f"Error detail: {error_data}")
        except:
            pass
            
except Exception as e:
    print(f"\nError: {e}")
