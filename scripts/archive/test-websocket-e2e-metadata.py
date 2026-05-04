#!/usr/bin/env python3
"""
End-to-End WebSocket Test with Metadata Filtering

Tests the complete flow:
1. Connect to WebSocket
2. Send query with metadata (tenant_id, knowledge_type, project_id)
3. Receive streaming response
4. Verify metadata filtering works correctly
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime

# WebSocket endpoint
WS_URL = "wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

async def test_query(session_id, query, metadata, test_name):
    """
    Test a single query with metadata through WebSocket
    """
    print("\n" + "="*70)
    print(f"Test: {test_name}")
    print("="*70)
    print(f"Session ID: {session_id}")
    print(f"Query: {query}")
    print(f"Metadata:")
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print()

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to WebSocket")

            # Build message with metadata
            message = {
                "action": "sendMessage",
                "data": {
                    "inputText": query,
                    "sessionId": session_id,
                    **metadata  # Spread metadata into message
                }
            }

            print(f"\n📤 Sending message...")
            await websocket.send(json.dumps(message))

            print(f"\n📥 Receiving response:\n")
            response_text = ""
            chunk_count = 0

            # Receive streaming response
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)

                    msg_type = data.get('type')

                    if msg_type == 'status':
                        print(f"   [Status] {data.get('message')}")

                    elif msg_type == 'chunk':
                        chunk_data = data.get('data', '')
                        response_text += chunk_data
                        chunk_count += 1
                        # Print chunks in real-time
                        print(chunk_data, end='', flush=True)

                    elif msg_type == 'complete':
                        print(f"\n\n✅ Response complete ({chunk_count} chunks)")
                        break

                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('message')}")
                        return None

                except asyncio.TimeoutError:
                    print(f"\n⚠️  Timeout waiting for response")
                    break

            return response_text

    except Exception as e:
        print(f"\n❌ Connection error: {e}")
        return None


async def main():
    """Run all E2E tests"""
    print("="*70)
    print("WebSocket E2E Tests with Metadata Filtering")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"WebSocket URL: {WS_URL}")
    print()

    # Test cases
    tests = [
        {
            "name": "Test 1: Tenant 1001 - Champions League (specific knowledge)",
            "session_id": "test-1001-champions-001",
            "query": "¿Cuál es el récord de Real Madrid en semifinales de Champions League?",
            "metadata": {
                "tenant_id": "1001",
                "project_id": "5001",
                "knowledge_type": "specific",
                "user_roles": ["admin", "viewer"]
            },
            "expected_keywords": ["Real Madrid", "Champions", "semifinal"]
        },
        {
            "name": "Test 2: Tenant 1003 - Philosophy (specific knowledge)",
            "session_id": "test-1003-philosophy-001",
            "query": "¿Qué es La República de Platón?",
            "metadata": {
                "tenant_id": "1003",
                "project_id": "6001",
                "knowledge_type": "specific",
                "user_roles": ["admin", "viewer"]
            },
            "expected_keywords": ["Platón", "República", "justicia"]
        },
        {
            "name": "Test 3: Tenant 1001 - Generic Knowledge (normative framework)",
            "session_id": "test-1001-normative-001",
            "query": "¿Qué leyes regulan las pensiones en Colombia?",
            "metadata": {
                "tenant_id": "1001",
                "knowledge_type": "generic",
                "user_roles": ["admin"]
            },
            "expected_keywords": ["ley", "pensión", "Colombia"]
        },
        {
            "name": "Test 4: Tenant 1003 - Generic Knowledge (normative framework)",
            "session_id": "test-1003-normative-001",
            "query": "¿Cuáles son las normativas sobre reforma pensional?",
            "metadata": {
                "tenant_id": "1003",
                "knowledge_type": "generic",
                "user_roles": ["viewer"]
            },
            "expected_keywords": ["reforma", "pensional", "normativ"]
        },
        {
            "name": "Test 5: Cross-tenant isolation - Tenant 1001 cannot access Tenant 1003 docs",
            "session_id": "test-1001-isolation-001",
            "query": "¿Qué dice Platón sobre la justicia?",
            "metadata": {
                "tenant_id": "1001",
                "project_id": "5001",
                "knowledge_type": "specific",
                "user_roles": ["admin"]
            },
            "expected_keywords": [],  # Should NOT find philosophy docs
            "should_not_contain": ["Platón", "República", "Filosofía"]
        }
    ]

    passed = 0
    failed = 0
    results = []

    # Run each test
    for test in tests:
        response = await test_query(
            session_id=test["session_id"],
            query=test["query"],
            metadata=test["metadata"],
            test_name=test["name"]
        )

        # Validate response
        test_passed = True
        failure_reasons = []

        if response is None:
            test_passed = False
            failure_reasons.append("No response received")

        elif response:
            response_lower = response.lower()

            # Check expected keywords
            if test.get("expected_keywords"):
                for keyword in test["expected_keywords"]:
                    if keyword.lower() not in response_lower:
                        test_passed = False
                        failure_reasons.append(f"Expected keyword '{keyword}' not found")

            # Check should_not_contain
            if test.get("should_not_contain"):
                for keyword in test["should_not_contain"]:
                    if keyword.lower() in response_lower:
                        test_passed = False
                        failure_reasons.append(f"Found forbidden keyword '{keyword}' (isolation broken)")

        # Record result
        if test_passed:
            print(f"\n✅ TEST PASSED")
            passed += 1
        else:
            print(f"\n❌ TEST FAILED")
            for reason in failure_reasons:
                print(f"   - {reason}")
            failed += 1

        results.append({
            "test": test["name"],
            "passed": test_passed,
            "reasons": failure_reasons
        })

        # Wait between tests
        await asyncio.sleep(2)

    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()

    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} - {result['test']}")
        if result["reasons"]:
            for reason in result["reasons"]:
                print(f"         {reason}")

    print("="*70)

    if failed > 0:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
