#!/usr/bin/env python3
"""
Simple test for metadata filtering - Query API with tenant headers
"""

import requests
import json

API_URL = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query'
API_KEY = 'x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV'

print("=" * 80)
print("TESTING METADATA FILTERING")
print("=" * 80)

# Test 1: Tenant 1 with viewer role - should find document
print("\n[Test 1] Tenant 1 - Viewer role")
print("Question: What is the mission of Colpensiones?")

response = requests.post(
    API_URL,
    headers={
        'X-Api-Key': API_KEY,
        'x-tenant-id': '1',
        'x-user-id': 'testuser1',
        'x-user-roles': '["viewer"]',
        'Content-Type': 'application/json'
    },
    json={'question': 'What is the mission of Colpensiones?'},
    timeout=30
)

result = response.json()
print(f"Status: {response.status_code}")
if response.status_code == 200:
    answer = result.get('answer', '')
    print(f"Answer: {answer[:300]}...")
    
    if 'prima media' in answer.lower() or 'pensiones' in answer.lower():
        print("✅ PASS: Found tenant 1 document")
    else:
        print("❌ FAIL: Did not find expected content")
else:
    print(f"❌ ERROR: {result}")

# Test 2: Tenant 2 - should NOT find tenant 1 document
print("\n[Test 2] Tenant 2 - Trying to access Tenant 1 data")
print("Question: What is the mission of Colpensiones?")

response = requests.post(
    API_URL,
    headers={
        'X-Api-Key': API_KEY,
        'x-tenant-id': '2',
        'x-user-id': 'testuser2',
        'x-user-roles': '["viewer"]',
        'Content-Type': 'application/json'
    },
    json={'question': 'What is the mission of Colpensiones?'},
    timeout=30
)

result = response.json()
print(f"Status: {response.status_code}")
if response.status_code == 200:
    answer = result.get('answer', '')
    print(f"Answer: {answer[:300]}...")
    
    if 'prima media' in answer.lower() or 'pensiones' in answer.lower():
        print("❌ FAIL: Tenant 2 should NOT see tenant 1 documents!")
    else:
        print("✅ PASS: Tenant isolation working correctly")
else:
    print(f"❌ ERROR: {result}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
