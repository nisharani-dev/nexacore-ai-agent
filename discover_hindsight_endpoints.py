#!/usr/bin/env python3
"""
Discover Hindsight API endpoints by trying common patterns.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").rstrip("/")
API_KEY = os.getenv("HINDSIGHT_API_KEY", "")
PROJECT = os.getenv("HINDSIGHT_PROJECT", "ramp-onboarding-demo")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Try different endpoint patterns
patterns = [
    # With project prefix
    f"/projects/{PROJECT}/search",
    f"/projects/{PROJECT}/records",
    f"/projects/{PROJECT}/namespaces",
    f"/v1/projects/{PROJECT}/search",
    f"/v1/projects/{PROJECT}/records",
    
    # Without project
    "/v1/search",
    "/v1/records",
    "/v1/namespaces",
    "/api/search",
    "/api/records",
    
    # Different naming
    "/memories",
    "/memories/search",
    "/query",
    "/store",
]

print(f"Discovering endpoints for: {BASE_URL}")
print("=" * 60)

working_endpoints = []

for path in patterns:
    url = BASE_URL + path
    try:
        # Try GET first
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 404:
            print(f"✅ GET  {path} → {response.status_code}")
            working_endpoints.append(("GET", path, response.status_code))
            continue
            
        # Try POST with minimal payload
        response = requests.post(url, headers=headers, json={}, timeout=5)
        if response.status_code != 404:
            print(f"✅ POST {path} → {response.status_code}")
            working_endpoints.append(("POST", path, response.status_code))
        else:
            print(f"   {path} → 404")
    except Exception as e:
        print(f"❌ {path} → Error: {e}")

print("\n" + "=" * 60)
if working_endpoints:
    print("Working endpoints found:")
    for method, path, status in working_endpoints:
        print(f"  {method} {path} (Status: {status})")
else:
    print("No working endpoints found beyond /health")
    print("\nThis suggests you may need to:")
    print("1. Register your project first")
    print("2. Check Hindsight API documentation")
    print("3. Contact Hindsight support for the correct endpoints")
print("=" * 60)
