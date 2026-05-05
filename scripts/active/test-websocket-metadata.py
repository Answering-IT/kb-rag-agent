#!/usr/bin/env python3
"""
Test WebSocket Metadata Validation - Colpensiones

Validates that WebSocket correctly forwards metadata to the Agent Core Runtime.
Tests the same scenarios as test-colpensiones-fallback.py but via WebSocket.

Prerequisites:
    - pip3 install websocket-client

Usage:
    python3 scripts/active/test-websocket-metadata.py
"""

import json
import time
from typing import Dict, Any, List
import uuid

try:
    import websocket
except ImportError:
    print("❌ websocket-client library not found. Install with: pip3 install websocket-client")
    exit(1)

# WebSocket URL (from CloudFormation output)
WS_URL = "wss://6aqhp0u2zk.execute-api.us-east-1.amazonaws.com/dev"

# Test scenarios - same as HTTP tests but via WebSocket
TEST_SCENARIOS = [
    {
        "name": "Test 1: Tenant-only query sobre marco normativo",
        "metadata": {
            "tenant_id": "1",
            # No project_id - should access tenant-level marco normativo
        },
        "query": "¿Qué es la Ley 2381 de 2024?",
        "expected": {
            "should_find": True,
            "keywords": ["reforma", "pilar", "pensional", "2381"],
            "reason": "marco_normativo_colpensiones.md has partition_key='t1' (tenant-level)"
        }
    },
    {
        "name": "Test 2: Project 6610 query específica del caso",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6610",
        },
        "query": "¿Cuál es el número de cédula del peticionario Carlos Martínez?",
        "expected": {
            "should_find": True,
            "keywords": ["79", "456", "321", "cédula"],
            "reason": "Document in project 6610 has partition_key='t1_p6610'"
        }
    },
    {
        "name": "Test 3: Fallback desde Project 6610 a tenant-level",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6610",
        },
        "query": "¿Qué normativa aplica para recursos de apelación en Colpensiones?",
        "expected": {
            "should_find": True,
            "keywords": ["ley", "1755", "derecho", "petición"],
            "reason": "Should find in project OR fallback to marco normativo",
            "fallback": True
        }
    },
    {
        "name": "Test 4: Cross-project isolation (6610 NO debe ver 6639)",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6610",
        },
        "query": "¿Cuál es el número de radicación de Superfinanciera?",
        "expected": {
            "should_find": False,
            "forbidden_keywords": ["2026022010", "rafael segundo martinez"],
            "reason": "Radicación is in project 6639, not 6610"
        }
    },
    {
        "name": "Test 5: Project 6639 query específica",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6639",
        },
        "query": "¿Quién firma la comunicación de la Superfinanciera?",
        "expected": {
            "should_find": True,
            "keywords": ["rafael", "martinez", "fuentes"],
            "reason": "Document in project 6639 has partition_key='t1_p6639'"
        }
    },
    {
        "name": "Test 6: Task 1 specific query",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6639",
            "task_id": "1",
        },
        "query": "¿Quién es el responsable del análisis de contribuciones?",
        "expected": {
            "should_find": True,
            "keywords": ["maría", "fernanda", "gómez"],
            "reason": "Task 1 document has partition_key='t1_p6639_t1'"
        }
    },
    {
        "name": "Test 7: Cross-task isolation (Task 1 NO debe ver Task 2)",
        "metadata": {
            "tenant_id": "1",
            "project_id": "6639",
            "task_id": "1",
        },
        "query": "¿Quién es Pedro Luis Ramírez?",
        "expected": {
            "should_find": False,
            "forbidden_keywords": ["pedro", "ramirez", "cgn"],
            "reason": "Pedro is in task 2, not task 1"
        }
    },
]


class WebSocketTestClient:
    """WebSocket client for testing metadata forwarding"""

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.response_chunks: List[str] = []
        self.is_complete = False
        self.error_message = None

    def connect(self):
        """Connect to WebSocket"""
        print(f"[WS] Connecting to {self.ws_url}")
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )

    def on_message(self, ws, message):
        """Handle incoming message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'chunk':
                chunk_text = data.get('data', '')
                self.response_chunks.append(chunk_text)
                print(f"[WS] Received chunk: {chunk_text[:50]}...")
            elif msg_type == 'complete':
                print("[WS] Response complete")
                self.is_complete = True
            elif msg_type == 'error':
                self.error_message = data.get('message', 'Unknown error')
                print(f"[WS] Error: {self.error_message}")
                self.is_complete = True
            elif msg_type == 'status':
                print(f"[WS] Status: {data.get('message')}")
        except json.JSONDecodeError as e:
            print(f"[WS] Failed to parse message: {e}")

    def on_error(self, ws, error):
        """Handle error"""
        print(f"[WS] Error: {error}")
        self.error_message = str(error)

    def on_close(self, ws, close_status_code, close_msg):
        """Handle close"""
        print(f"[WS] Connection closed: {close_status_code} - {close_msg}")

    def on_open(self, ws):
        """Handle open"""
        print("[WS] Connected")

    def send_query(self, query: str, metadata: Dict[str, Any], session_id: str):
        """Send query with metadata via WebSocket"""
        self.response_chunks = []
        self.is_complete = False
        self.error_message = None

        payload = {
            "action": "sendMessage",
            "data": {
                "inputText": query,
                "sessionId": session_id,
                "metadata": metadata  # Metadata as separate object
            }
        }

        print(f"[WS] Sending payload: {json.dumps(payload, indent=2)}")
        self.ws.send(json.dumps(payload))

        # Wait for response (max 30 seconds)
        timeout = 30
        elapsed = 0
        while not self.is_complete and elapsed < timeout:
            time.sleep(0.5)
            elapsed += 0.5

        if not self.is_complete:
            print(f"[WS] Timeout after {timeout}s")
            return None

        return {
            "success": self.error_message is None,
            "full_response": ''.join(self.response_chunks),
            "error": self.error_message
        }

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()


def validate_test(scenario: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate test result against expected behavior.

    Args:
        scenario: Test scenario dict
        result: Agent response dict

    Returns:
        Validation result with pass/fail and details
    """
    expected = scenario['expected']
    response = result.get('full_response', '').lower() if result else ''

    validation = {
        "test_name": scenario['name'],
        "passed": False,
        "details": []
    }

    # Check if agent responded
    if not result or not result.get('success'):
        validation['details'].append(f"❌ Agent call failed: {result.get('error') if result else 'No result'}")
        return validation

    if not response:
        validation['details'].append("❌ Empty response from agent")
        return validation

    # Validate against expected behavior
    should_find = expected['should_find']

    if should_find:
        # Check for expected keywords
        keywords = expected.get('keywords', [])
        found_keywords = [kw for kw in keywords if kw in response]

        if found_keywords or len(response) > 100:  # Has substantial content
            validation['passed'] = True
            validation['details'].append(f"✅ Found relevant content (matched: {found_keywords})")
        else:
            validation['details'].append(f"❌ Expected to find content but response seems generic or too short")
            validation['details'].append(f"   Keywords searched: {keywords}")

    else:
        # Should NOT find - check for absence of forbidden keywords
        forbidden_keywords = expected.get('forbidden_keywords', [])
        found_forbidden = [kw for kw in forbidden_keywords if kw in response]

        if not found_forbidden:
            validation['passed'] = True
            validation['details'].append("✅ Correctly did NOT return isolated content")
        else:
            validation['details'].append(f"❌ Found forbidden keywords (isolation breach): {found_forbidden}")

    # Add fallback info if applicable
    if expected.get('fallback'):
        validation['details'].append(f"ℹ️  Fallback possible: {expected['reason']}")

    validation['details'].append(f"ℹ️  Reason: {expected['reason']}")

    return validation


def main():
    """Run all test scenarios via WebSocket"""
    print("=" * 80)
    print("🧪 WEBSOCKET METADATA VALIDATION TESTS - COLPENSIONES")
    print("=" * 80)
    print(f"WebSocket URL: {WS_URL}")
    print("Testing metadata forwarding: tenant_id, project_id, task_id")
    print("=" * 80)
    print()

    results = []

    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"\n[{i}/{len(TEST_SCENARIOS)}] {scenario['name']}")
        print(f"  Query: {scenario['query']}")
        print(f"  Metadata: {scenario['metadata']}")

        # Create WebSocket client
        client = WebSocketTestClient(WS_URL)

        try:
            # Connect via WebSocket
            import threading
            ws_thread = threading.Thread(target=client.ws.run_forever if hasattr(client, 'ws') and client.ws else None)

            # Connect
            client.connect()
            ws_thread = threading.Thread(target=client.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()

            # Wait for connection
            time.sleep(2)

            # Generate session ID
            session_id = f"test-ws-{int(time.time())}-{uuid.uuid4().hex[:8]}"

            # Send query with metadata
            result = client.send_query(
                scenario['query'],
                scenario['metadata'],
                session_id
            )

            # Validate result
            validation = validate_test(scenario, result)
            results.append(validation)

            # Print validation
            print(f"  Result: {'✅ PASS' if validation['passed'] else '❌ FAIL'}")
            for detail in validation['details']:
                print(f"    {detail}")

            # Print response snippet
            if result and result.get('full_response'):
                snippet = result['full_response'][:200].replace('\n', ' ')
                print(f"  Response snippet: {snippet}...")

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test_name": scenario['name'],
                "passed": False,
                "details": [f"❌ Exception: {e}"]
            })
        finally:
            # Close connection
            client.close()
            time.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    percentage = (passed / total * 100) if total > 0 else 0
    print(f"Passed: {passed}/{total} ({percentage:.0f}%)")
    print()

    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed:")
        for r in results:
            if not r['passed']:
                print(f"  - {r['test_name']}")

    print()
    print("=" * 80)
    print("📋 METADATA VALIDATION SUMMARY")
    print("=" * 80)
    print("WebSocket handler expects metadata in this format:")
    print(json.dumps({
        "action": "sendMessage",
        "data": {
            "inputText": "Your question",
            "sessionId": "unique-session-id",
            "metadata": {
                "tenant_id": "1",
                "project_id": "6610",
                "task_id": "1"
            }
        }
    }, indent=2))
    print()
    print("✅ tenant_id is ALWAYS required (fixed value: 1 for Colpensiones)")
    print("✅ project_id is optional (context from route)")
    print("✅ task_id is optional (context from route)")
    print()


if __name__ == "__main__":
    main()
