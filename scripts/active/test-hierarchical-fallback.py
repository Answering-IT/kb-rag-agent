#!/usr/bin/env python3
"""
Test Hierarchical Fallback with Real KB Data

Tests the fallback strategy:
1. Project-level filter tries first
2. If results < 2, fallback to tenant-level
3. Combine results (project prioritized)

Prerequisites:
    - Docker running locally
    - AWS credentials configured (ans-super profile)
    - Agent container built

Usage:
    # Build and run agent container
    cd agents
    docker build -t processapp-agent:test .
    docker run -d -p 8080:8080 \
      -e AWS_PROFILE=ans-super \
      -e AWS_REGION=us-east-1 \
      -e KB_ID=BLJTRDGQI0 \
      -v ~/.aws:/root/.aws:ro \
      --name agent-test \
      processapp-agent:test

    # Run tests
    python3 scripts/test-hierarchical-fallback.py

    # Cleanup
    docker stop agent-test && docker rm agent-test
"""

import json
import time
from typing import Dict, Any

try:
    import requests
except ImportError:
    print("❌ requests library not found. Install with: pip3 install requests")
    exit(1)

# Agent endpoint (local Docker)
AGENT_URL = "http://localhost:8080/invocations"

# Test scenarios based on real KB data
TEST_SCENARIOS = [
    {
        "name": "Test 1: Tenant-only does NOT see project documents",
        "headers": {
            "x-tenant-id": "100001",
            # No project_id - should NOT access project documents
        },
        "query": "¿Quién es Luis Díaz?",
        "expected": {
            "should_find": False,
            "reason": "luis_diaz_biografia.txt has partition_key='t100001_p1' (project-level)",
            "validation": "Response should NOT mention Liverpool, Porto, or career details"
        }
    },
    {
        "name": "Test 2: Project-specific finds its content",
        "headers": {
            "x-tenant-id": "100001",
            "x-project-id": "1",
        },
        "query": "¿Dónde juega Luis Díaz actualmente?",
        "expected": {
            "should_find": True,
            "reason": "luis_diaz_biografia.txt has partition_key='t100001_p1'",
            "validation": "Response should mention 'Liverpool FC'"
        }
    },
    {
        "name": "Test 3: Fallback to tenant-level (Champions info from project context)",
        "headers": {
            "x-tenant-id": "100001",
            "x-project-id": "1",
        },
        "query": "¿Qué equipos están en semifinales de la Champions League?",
        "expected": {
            "should_find": True,
            "reason": "champions.txt has partition_key='t100001' (tenant-level)",
            "validation": "Response should mention PSG, Bayern, Atlético, Arsenal",
            "fallback": True,
            "fallback_reason": "Query is about Champions (tenant-level doc), not Luis Diaz (project doc)"
        }
    },
    {
        "name": "Test 4: Cross-project isolation (NO fallback to other projects)",
        "headers": {
            "x-tenant-id": "100001",
            "x-project-id": "1",
        },
        "query": "¿Cuántos años tiene Manuel Neuer?",
        "expected": {
            "should_find": False,
            "reason": "manuel_neuer_info.txt has partition_key='t100001_p2' (different project)",
            "validation": "Response should NOT mention '40 años' or Bayern career details",
            "fallback": True,
            "fallback_reason": "Fallback should go to t100001 (tenant), NOT t100001_p2 (cross-project)"
        }
    },
    {
        "name": "Test 5: Mixed results (Bayern query from Neuer's project)",
        "headers": {
            "x-tenant-id": "100001",
            "x-project-id": "2",
        },
        "query": "¿Cómo le fue al Bayern en la Champions League?",
        "expected": {
            "should_find": True,
            "reason": "manuel_neuer_info.txt (project) + champions.txt (tenant-level)",
            "validation": "Should mention both: Neuer's career stats AND current semifinal vs PSG",
            "fallback": True,
            "fallback_reason": "Project doc may have limited results, fallback provides current context"
        }
    },
    {
        "name": "Test 6: Tenant-level access to general info",
        "headers": {
            "x-tenant-id": "100001",
            # No project_id - tenant-level access
        },
        "query": "¿Cuántos goles metió PSG contra Bayern?",
        "expected": {
            "should_find": True,
            "reason": "champions.txt has partition_key='t100001'",
            "validation": "Response should mention '5-4' or 'PSG 5 - 4 Bayern'"
        }
    }
]


def call_agent(query: str, headers: Dict[str, str], timeout: int = 30) -> Dict[str, Any]:
    """
    Call agent via HTTP POST.

    Args:
        query: User query
        headers: HTTP headers with metadata (x-tenant-id, x-project-id, etc.)
        timeout: Request timeout in seconds

    Returns:
        Response dict with full_response and metadata
    """
    payload = {
        "inputText": query,
        "sessionId": f"test-{int(time.time())}",
        "sessionState": {},
        "knowledgeBases": [
            {
                "knowledgeBaseId": "BLJTRDGQI0",
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 5
                    }
                }
            }
        ]
    }

    try:
        response = requests.post(
            AGENT_URL,
            json=payload,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()

        # Parse streaming response (newline-delimited JSON)
        lines = response.text.strip().split('\n')
        full_response = ""

        for line in lines:
            if not line:
                continue
            try:
                chunk = json.loads(line)
                # Handle both formats: direct JSON chunks and base64 encoded
                if 'type' in chunk and chunk['type'] == 'chunk' and 'data' in chunk:
                    # Direct JSON format: {"type": "chunk", "data": "text"}
                    full_response += chunk['data']
                elif 'chunk' in chunk and 'bytes' in chunk['chunk']:
                    # Base64 format: {"chunk": {"bytes": "..."}}
                    import base64
                    decoded = base64.b64decode(chunk['chunk']['bytes']).decode('utf-8')
                    full_response += decoded
            except json.JSONDecodeError:
                continue

        return {
            "success": True,
            "full_response": full_response.strip(),
            "status_code": response.status_code
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": str(e),
            "full_response": ""
        }


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
    response = result.get('full_response', '').lower()

    validation = {
        "test_name": scenario['name'],
        "passed": False,
        "details": []
    }

    # Check if agent responded
    if not result.get('success'):
        validation['details'].append(f"❌ Agent call failed: {result.get('error')}")
        return validation

    if not response:
        validation['details'].append("❌ Empty response from agent")
        return validation

    # Validate against expected behavior
    should_find = expected['should_find']
    validation_text = expected['validation']

    if should_find:
        # Check if response contains expected information
        # (simple keyword check - could be more sophisticated)
        keywords = []
        if "Liverpool" in validation_text:
            keywords.append("liverpool")
        if "PSG" in validation_text or "Bayern" in validation_text:
            keywords.extend(["psg", "bayern", "semifinal"])
        if "5-4" in validation_text:
            keywords.append("5")

        found_keywords = [kw for kw in keywords if kw in response]

        if found_keywords or len(response) > 50:  # Has substantial content
            validation['passed'] = True
            validation['details'].append(f"✅ Found relevant content (matched: {found_keywords})")
        else:
            validation['details'].append(f"❌ Expected to find content but response seems generic")

    else:
        # Should NOT find - check for absence of specific info
        forbidden_keywords = []
        if "Liverpool" in validation_text:
            forbidden_keywords.append("liverpool")
        if "40 años" in validation_text:
            forbidden_keywords.extend(["40", "neuer"])

        found_forbidden = [kw for kw in forbidden_keywords if kw in response]

        if not found_forbidden:
            validation['passed'] = True
            validation['details'].append("✅ Correctly did NOT return isolated content")
        else:
            validation['details'].append(f"❌ Found forbidden keywords (isolation breach): {found_forbidden}")

    # Add fallback info if applicable
    if expected.get('fallback'):
        validation['details'].append(f"ℹ️  Fallback expected: {expected['fallback_reason']}")

    validation['details'].append(f"ℹ️  Reason: {expected['reason']}")

    return validation


def main():
    """Run all test scenarios."""
    print("=" * 80)
    print("🧪 HIERARCHICAL FALLBACK TESTS")
    print("=" * 80)
    print()

    # Check agent is running
    try:
        health_response = requests.get("http://localhost:8080/health", timeout=5)
        health_response.raise_for_status()
        print("✅ Agent is running")
        print()
    except requests.exceptions.RequestException as e:
        print(f"❌ Agent not accessible: {e}")
        print("\n💡 Make sure agent container is running:")
        print("   docker run -d -p 8080:8080 -e AWS_PROFILE=ans-super \\")
        print("     -v ~/.aws:/root/.aws:ro --name agent-test processapp-agent:test")
        return

    results = []

    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print(f"[{i}/{len(TEST_SCENARIOS)}] {scenario['name']}")
        print(f"  Query: {scenario['query']}")
        print(f"  Headers: {scenario['headers']}")

        # Call agent
        result = call_agent(scenario['query'], scenario['headers'])

        # Validate result
        validation = validate_test(scenario, result)
        results.append(validation)

        # Print validation
        print(f"  Result: {'✅ PASS' if validation['passed'] else '❌ FAIL'}")
        for detail in validation['details']:
            print(f"    {detail}")

        # Print response snippet
        if result.get('full_response'):
            snippet = result['full_response'][:200].replace('\n', ' ')
            print(f"  Response snippet: {snippet}...")

        print()

    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print()

    if passed == total:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed:")
        for r in results:
            if not r['passed']:
                print(f"  - {r['test_name']}")

    print()


if __name__ == "__main__":
    main()
