#!/usr/bin/env python3
"""
E2E Test: Metadata Filtering with Retrieve Tool
Tests that metadata filters correctly restrict Knowledge Base results
"""

import json
import time
import websocket
from typing import Dict, Any

WS_URL = "wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

def send_message_and_get_response(ws_url: str, message: Dict[str, Any]) -> str:
    """Send WebSocket message and collect full response"""
    ws = websocket.create_connection(ws_url)
    ws.send(json.dumps(message))

    response = ""
    while True:
        result = ws.recv()
        data = json.loads(result)
        if data.get("type") == "chunk":
            response += data.get("data", "")
        elif data.get("type") == "complete":
            break

    ws.close()
    return response.strip()

def test_case(name: str, message: Dict[str, Any], expected_content: str, should_not_contain: str = None):
    """Run a single test case"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Request: {json.dumps(message, indent=2)}")

    response = send_message_and_get_response(WS_URL, message)

    print(f"\nResponse:\n{response}\n")

    # Check expectations
    success = expected_content.lower() in response.lower()
    if should_not_contain:
        success = success and (should_not_contain.lower() not in response.lower())

    status = "✅ PASS" if success else "❌ FAIL"
    print(f"Status: {status}")

    if expected_content:
        found = "FOUND" if expected_content.lower() in response.lower() else "NOT FOUND"
        print(f"  - Expected '{expected_content}': {found}")

    if should_not_contain:
        found = "FOUND" if should_not_contain.lower() in response.lower() else "NOT FOUND"
        print(f"  - Should NOT contain '{should_not_contain}': {found}")

    return success

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║   E2E Test: Metadata Filtering in Knowledge Base          ║
║   Testing retrieve tool with tenant/project filters       ║
╚════════════════════════════════════════════════════════════╝
    """)

    results = []

    # Test 1: Tenant 1001 (Fútbol) - Con filtro correcto
    results.append(test_case(
        name="Tenant 1001 - Buscar PSG (CON filtro tenant_id=1001)",
        message={
            "action": "sendMessage",
            "data": {
                "inputText": "Háblame sobre PSG vs Arsenal",
                "sessionId": "e2e-test-1",
                "tenant_id": "1001",
                "project_id": "5001"
            }
        },
        expected_content="PSG",
        should_not_contain="Platón"
    ))

    time.sleep(2)

    # Test 2: Tenant 1003 (Filosofía) - Con filtro correcto
    results.append(test_case(
        name="Tenant 1003 - Buscar Platón (CON filtro tenant_id=1003)",
        message={
            "action": "sendMessage",
            "data": {
                "inputText": "¿Qué dice Platón en La República?",
                "sessionId": "e2e-test-2",
                "tenant_id": "1003",
                "project_id": "6001"
            }
        },
        expected_content="Platón",
        should_not_contain="PSG"
    ))

    time.sleep(2)

    # Test 3: Sin filtro - Debería acceder a todo (o según configuración)
    results.append(test_case(
        name="Sin filtro de tenant - Acceso general",
        message={
            "action": "sendMessage",
            "data": {
                "inputText": "¿Qué información tienes disponible?",
                "sessionId": "e2e-test-3"
            }
        },
        expected_content=""  # Solo verificamos que responda
    ))

    time.sleep(2)

    # Test 4: Tenant incorrecto - NO debería encontrar contenido de otro tenant
    results.append(test_case(
        name="Tenant 1001 buscando contenido de Tenant 1003 (DEBE FALLAR)",
        message={
            "action": "sendMessage",
            "data": {
                "inputText": "Háblame sobre Platón y La República",
                "sessionId": "e2e-test-4",
                "tenant_id": "1001",  # Tenant incorrecto
                "project_id": "5001"
            }
        },
        expected_content="no encuentro",
        should_not_contain="Platón"
    ))

    time.sleep(2)

    # Test 5: Verificar project_id específico
    results.append(test_case(
        name="Project 5001 - Real Madrid vs Bayern",
        message={
            "action": "sendMessage",
            "data": {
                "inputText": "Información sobre Real Madrid vs Bayern",
                "sessionId": "e2e-test-5",
                "tenant_id": "1001",
                "project_id": "5001"
            }
        },
        expected_content="Real Madrid"
    ))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    print(f"Success rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\n✅ All tests PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
