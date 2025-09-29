#!/usr/bin/env python3
"""
Simple test script to verify the dashboard API endpoints are working.
Run this after starting the backend server.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None, expected_status=200):
    """Test a single endpoint."""
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing {method} {endpoint}...")
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        else:
            print(f"Unsupported method: {method}")
            return False
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == expected_status:
            print(f"  ✓ Success")
            if response.content:
                try:
                    json_data = response.json()
                    print(f"  Response: {json.dumps(json_data, indent=2)[:200]}...")
                except:
                    print(f"  Response: {response.text[:200]}...")
            return True
        else:
            print(f"  ✗ Expected {expected_status}, got {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Connection failed - is the server running on {BASE_URL}?")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Dashboard API Endpoints")
    print("=" * 50)
    
    tests = [
        ("/health", "GET", None, 200),
        ("/api/dashboard/stats", "GET", None, 200),
        ("/api/dashboard/recent-projects", "GET", None, 200),
        ("/api/dashboard/", "GET", None, 200),
        ("/api/projects", "GET", None, 200),
        ("/api/projects", "POST", {
            "title": "Test Project",
            "description": "A test project created by the test script",
            "status": "planning"
        }, 201),
    ]
    
    passed = 0
    total = len(tests)
    
    for endpoint, method, data, expected_status in tests:
        if test_endpoint(endpoint, method, data, expected_status):
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The dashboard API is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())


