#!/usr/bin/env python3
"""
Comprehensive metadata filtering test
"""

import requests
import json

API_URL = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query'
API_KEY = 'x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV'

print("=" * 80)
print("COMPREHENSIVE METADATA FILTERING TEST")
print("=" * 80)

tests = [
    {
        'name': 'Test 1: Tenant 1 accesses own data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'user1',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is Colpensiones?',
        'expect': 'PASS - Should find Colpensiones info',
        'check': lambda answer: 'colpensiones' in answer.lower() or 'pensiones' in answer.lower()
    },
    {
        'name': 'Test 2: Tenant 2 accesses own data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '2',
            'x-user-id': 'user2',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'How many active users does Organization AC have?',
        'expect': 'PASS - Should find 150 users',
        'check': lambda answer: '150' in answer or 'ciento cincuenta' in answer.lower()
    },
    {
        'name': 'Test 3: Tenant 1 tries to access Tenant 2 data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'user1',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'How many users does Organization AC have?',
        'expect': 'PASS - Should NOT find Tenant 2 data',
        'check': lambda answer: '150' not in answer and 'unable to assist' in answer.lower()
    },
    {
        'name': 'Test 4: Tenant 2 tries to access Tenant 1 data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '2',
            'x-user-id': 'user2',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is the mission of Colpensiones?',
        'expect': 'PASS - Should NOT find Tenant 1 data',
        'check': lambda answer: 'prima media' not in answer.lower() and 'unable to assist' in answer.lower()
    }
]

passed = 0
failed = 0

for i, test in enumerate(tests, 1):
    print(f"\n{'='*80}")
    print(f"{test['name']}")
    print(f"{'='*80}")
    print(f"Question: {test['question']}")
    print(f"Expected: {test['expect']}")
    
    try:
        response = requests.post(
            API_URL,
            headers=test['headers'],
            json={'question': test['question']},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            print(f"\nAnswer: {answer[:200]}...")
            
            if test['check'](answer):
                print(f"\n✅ PASS")
                passed += 1
            else:
                print(f"\n❌ FAIL - Answer doesn't match expected criteria")
                failed += 1
        else:
            print(f"\n❌ FAIL - HTTP {response.status_code}: {response.text}")
            failed += 1
            
    except Exception as e:
        print(f"\n❌ FAIL - Exception: {e}")
        failed += 1

print(f"\n{'='*80}")
print(f"FINAL RESULTS")
print(f"{'='*80}")
print(f"Total: {len(tests)} tests")
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print(f"\nResult: {'🎉 ALL TESTS PASSED!' if failed == 0 else '⚠️ SOME TESTS FAILED'}")
print(f"{'='*80}")
