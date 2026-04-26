#!/usr/bin/env python3
"""
Comprehensive metadata filtering test - Fixed criteria
"""

import requests

API_URL = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query'
API_KEY = 'x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV'

print("=" * 80)
print("✅ MULTI-TENANT METADATA FILTERING - FINAL VALIDATION")
print("=" * 80)

tests = [
    {
        'name': 'Test 1: Tenant 1 ✓ own data',
        'tenant': '1',
        'question': 'What is Colpensiones?',
        'expect_find': True,
        'keywords': ['colpensiones', 'pensiones', 'pension']
    },
    {
        'name': 'Test 2: Tenant 2 ✓ own data',
        'tenant': '2',
        'question': 'How many active users does Organization AC have?',
        'expect_find': True,
        'keywords': ['150', 'organizacion ac', 'organization ac']
    },
    {
        'name': 'Test 3: Tenant 1 ✗ Tenant 2 data (isolation)',
        'tenant': '1',
        'question': 'How many users does Organization AC have?',
        'expect_find': False,
        'blocked_keywords': ['150']
    },
    {
        'name': 'Test 4: Tenant 2 ✗ Tenant 1 data (isolation)',
        'tenant': '2',
        'question': 'What is the mission of Colpensiones?',
        'expect_find': False,
        'blocked_keywords': ['prima media', 'régimen de prima']
    }
]

passed = 0
failed = 0

for i, test in enumerate(tests, 1):
    print(f"\n{test['name']}")
    
    response = requests.post(
        API_URL,
        headers={
            'X-Api-Key': API_KEY,
            'x-tenant-id': test['tenant'],
            'x-user-id': f"user{test['tenant']}",
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        json={'question': test['question']},
        timeout=30
    )
    
    answer = response.json().get('answer', '').lower()
    
    if test['expect_find']:
        # Should find data - check for keywords
        found = any(keyword.lower() in answer for keyword in test['keywords'])
        if found:
            print(f"  ✅ PASS - Found expected content")
            passed += 1
        else:
            print(f"  ❌ FAIL - Did not find expected content")
            print(f"     Answer: {answer[:150]}...")
            failed += 1
    else:
        # Should NOT find data - check that blocked keywords are absent
        blocked_found = any(keyword.lower() in answer for keyword in test['blocked_keywords'])
        cannot_find = 'cannot find' in answer or 'unable to assist' in answer
        
        if not blocked_found and cannot_find:
            print(f"  ✅ PASS - Correctly blocked cross-tenant access")
            passed += 1
        else:
            print(f"  ❌ FAIL - Tenant isolation breach detected!")
            print(f"     Answer: {answer[:150]}...")
            failed += 1

print(f"\n{'='*80}")
print(f"RESULTS: {passed}/{len(tests)} tests passed")
if failed == 0:
    print(f"🎉 SUCCESS - Multi-tenant metadata filtering is working correctly!")
else:
    print(f"⚠️  {failed} test(s) failed")
print(f"{'='*80}")
