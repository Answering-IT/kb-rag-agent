#!/usr/bin/env python3
"""
Test metadata isolation to verify filtering behavior.

Tests:
1. tenant_id only → Should return all docs from tenant 1001
2. tenant_id + project_id → Should return ONLY docs from that project
3. tenant_id + project_id + task_id → Should return project docs + task docs
4. Different project → Should return NO docs from other projects
"""

import json
import websocket
import time

WS_URL = "wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

def send_message(ws, input_text, session_id, metadata):
    """Send message via WebSocket with metadata"""
    payload = {
        "action": "sendMessage",
        "data": {
            "inputText": input_text,
            "sessionId": session_id,
            **metadata
        }
    }
    print(f"\n📤 Sending: {input_text}")
    print(f"   Metadata: {metadata}")
    ws.send(json.dumps(payload))

    # Collect response
    response = ""
    while True:
        try:
            result = ws.recv()
            data = json.loads(result)

            if data.get("type") == "chunk":
                response += data.get("data", "")
            elif data.get("type") == "complete":
                break
            elif data.get("type") == "error":
                print(f"❌ Error: {data.get('message')}")
                break
        except Exception as e:
            print(f"❌ Error receiving: {e}")
            break

    print(f"📥 Response: {response.strip()}")
    return response.strip()

def test_scenario(title, metadata, question, expected_behavior):
    """Run a test scenario"""
    print(f"\n{'='*80}")
    print(f"🧪 {title}")
    print(f"{'='*80}")

    ws = websocket.create_connection(WS_URL)
    response = send_message(ws, question, "test-isolation", metadata)
    ws.close()

    print(f"\n✅ Expected: {expected_behavior}")

    # Check if response matches expectation
    if "no tengo información" in response.lower():
        result = "❌ NO INFO"
    elif "luis" in response.lower() or "fernández" in response.lower() or "fernandez" in response.lower():
        result = "✅ INFO FOUND"
    elif "juan" in response.lower() or "daniel" in response.lower() or "pérez" in response.lower():
        result = "✅ INFO FOUND"
    else:
        result = "❓ UNCLEAR"

    print(f"   Result: {result}")
    time.sleep(2)
    return result

def main():
    print("="*80)
    print("METADATA ISOLATION TEST")
    print("="*80)

    # Test 1: Only tenant_id (should access all tenant docs)
    test_scenario(
        "Test 1: Only tenant_id (all tenant docs)",
        {"tenant_id": "1001"},
        "¿Quién es Luis Fernández?",
        "Should find Luis (from any project in tenant 1001)"
    )

    test_scenario(
        "Test 1b: Only tenant_id (all tenant docs)",
        {"tenant_id": "1001"},
        "¿Quién es Juan Daniel Pérez?",
        "Should find Juan Daniel (from any project in tenant 1001)"
    )

    # Test 2: tenant_id + project_id (should access ONLY that project)
    test_scenario(
        "Test 2a: Project 165 (Luis's project)",
        {"tenant_id": "1001", "project_id": "165"},
        "¿Quién es Luis Fernández?",
        "✅ Should find Luis (he's in project 165)"
    )

    test_scenario(
        "Test 2b: Project 165 (Luis's project)",
        {"tenant_id": "1001", "project_id": "165"},
        "¿Quién es Juan Daniel Pérez?",
        "❌ Should NOT find Juan Daniel (he's in project 6636, not 165)"
    )

    test_scenario(
        "Test 2c: Project 6636 (Juan's project)",
        {"tenant_id": "1001", "project_id": "6636"},
        "¿Quién es Juan Daniel Pérez?",
        "✅ Should find Juan Daniel (he's in project 6636)"
    )

    test_scenario(
        "Test 2d: Project 6636 (Juan's project)",
        {"tenant_id": "1001", "project_id": "6636"},
        "¿Quién es Luis Fernández?",
        "❌ Should NOT find Luis (he's in project 165, not 6636)"
    )

    # Test 3: tenant_id + project_id + task_id
    test_scenario(
        "Test 3a: Project 165 + Task 174 (Luis's task)",
        {"tenant_id": "1001", "project_id": "165", "task_id": "174"},
        "¿Qué hazañas ha realizado Luis?",
        "✅ Should find Luis's achievements (task-level doc)"
    )

    test_scenario(
        "Test 3b: Project 165 + Task 174",
        {"tenant_id": "1001", "project_id": "165", "task_id": "174"},
        "¿Dónde nació Luis?",
        "✅ Should find Luis's birthplace (project-level doc, accessible from task)"
    )

    test_scenario(
        "Test 3c: Project 165 + Wrong Task 999",
        {"tenant_id": "1001", "project_id": "165", "task_id": "999"},
        "¿Qué hazañas ha realizado Luis?",
        "❌ Should NOT find achievements (task 174 doc not accessible from task 999)"
    )

    test_scenario(
        "Test 3d: Project 165 + Wrong Task 999",
        {"tenant_id": "1001", "project_id": "165", "task_id": "999"},
        "¿Dónde nació Luis?",
        "✅ Should find birthplace (project-level doc, accessible from any task)"
    )

    # Test 4: Different tenant (should be isolated)
    test_scenario(
        "Test 4: Different tenant",
        {"tenant_id": "9999", "project_id": "165"},
        "¿Quién es Luis Fernández?",
        "❌ Should NOT find Luis (different tenant)"
    )

    print("\n" + "="*80)
    print("✅ TEST SUITE COMPLETE")
    print("="*80)
    print("\nReview results above to verify isolation is working correctly.")
    print("Expected behavior:")
    print("  - Tenant-only filter: Access all tenant docs")
    print("  - Tenant + Project: Access ONLY that project (exclude other projects)")
    print("  - Tenant + Project + Task: Access project docs + specific task docs")

if __name__ == "__main__":
    main()
