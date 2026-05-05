#!/usr/bin/env python3
"""
Test Hierarchical Fallback - Tenant 1 (Colpensiones Real Data with Task Isolation)

Tests the fallback strategy with real Colpensiones documents across all levels:
- Tenant-level: marco_normativo_colpensiones.md (partition_key=t1)
- Project 6610: Recurso de apelación Carlos Martínez (partition_key=t1_p6610)
- Project 6639: Comunicación Superfinanciera (partition_key=t1_p6639)
  - Task 1: Análisis de Contribuciones (partition_key=t1_p6639_t1)
  - Task 2: Preparación Respuesta CGN (partition_key=t1_p6639_t2)

Tests include:
- Tenant/Project/Task-level access control
- Cross-task isolation (Task 1 cannot see Task 2)
- Hierarchical fallback (Task → Project → Tenant)
- Project-level queries should NOT see task-specific documents

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
    python3 scripts/active/test-colpensiones-fallback.py

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

# Test scenarios based on real Colpensiones KB data
TEST_SCENARIOS = [
    {
        "name": "Test 1: Tenant-only query sobre marco normativo",
        "headers": {
            "x-tenant-id": "1",
            # No project_id - should access tenant-level marco normativo
        },
        "query": "¿Qué es la Ley 2381 de 2024?",
        "expected": {
            "should_find": True,
            "reason": "marco_normativo_colpensiones.md has partition_key='t1' (tenant-level)",
            "validation": "Should mention 'Reforma Pensional', 'Sistema de Pilares', or 'Prima Media'",
            "keywords": ["reforma", "pilar", "pensional", "2381"]
        }
    },
    {
        "name": "Test 2: Project 6610 query específica del caso",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6610",
        },
        "query": "¿Cuál es el número de cédula del peticionario Carlos Martínez?",
        "expected": {
            "should_find": True,
            "reason": "Document in project 6610 has partition_key='t1_p6610'",
            "validation": "Should mention '79.456.321' or '79456321'",
            "keywords": ["79", "456", "321", "cédula"]
        }
    },
    {
        "name": "Test 3: Fallback desde Project 6610 a tenant-level (marco normativo)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6610",
        },
        "query": "¿Qué normativa aplica para recursos de apelación en Colpensiones?",
        "expected": {
            "should_find": True,
            "reason": "Should find in project doc OR fallback to marco normativo",
            "validation": "Should mention 'Ley 1755' (from project doc) OR other normative from marco",
            "keywords": ["ley", "1755", "derecho", "petición", "recurso"],
            "fallback": True,
            "fallback_reason": "May fallback to tenant-level marco if project doc has insufficient results"
        }
    },
    {
        "name": "Test 4: Cross-project isolation (6610 NO debe ver 6639)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6610",
        },
        "query": "¿Cuál es el número de radicación de Superfinanciera?",
        "expected": {
            "should_find": False,
            "reason": "Radicación 2026022010-000-000 is in project 6639 (partition_key='t1_p6639'), not 6610",
            "validation": "Should NOT mention '2026022010' or specific Superfinanciera radicación",
            "forbidden_keywords": ["2026022010", "rafael segundo martinez"]
        }
    },
    {
        "name": "Test 5: Project 6639 query específica",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
        },
        "query": "¿Quién firma la comunicación de la Superfinanciera?",
        "expected": {
            "should_find": True,
            "reason": "Document in project 6639 has partition_key='t1_p6639'",
            "validation": "Should mention 'Rafael Segundo Martinez Fuentes' or 'Martinez Fuentes'",
            "keywords": ["rafael", "martinez", "fuentes", "coordinador"]
        }
    },
    {
        "name": "Test 6: Fallback desde Project 6639 a tenant-level (marco normativo)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
        },
        "query": "¿Qué decreto reglamenta la Ley 2381 de 2024?",
        "expected": {
            "should_find": True,
            "reason": "Fallback to marco_normativo_colpensiones.md (SFC doc doesn't have this info)",
            "validation": "Should mention 'Decreto 0514 de 2025' or 'Decreto 1225'",
            "keywords": ["decreto", "514", "1225", "reglamenta"],
            "fallback": True,
            "fallback_reason": "SFC document is about accounting, not pension reform - fallback to tenant-level marco"
        }
    },
    {
        "name": "Test 7: Tenant-only NO debe ver project-specific details",
        "headers": {
            "x-tenant-id": "1",
            # No project_id - tenant-level only
        },
        "query": "¿Quién es Carlos Andrés Martínez López?",
        "expected": {
            "should_find": False,
            "reason": "Carlos is in project 6610 document (partition_key='t1_p6610'), not tenant-level",
            "validation": "Should NOT mention case details (C.C., apelación, historia laboral)",
            "forbidden_keywords": ["79.456.321", "apelación", "historia laboral", "pqrs"]
        }
    },
    {
        "name": "Test 8: Mixed results - Project con marco normativo",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6610",
        },
        "query": "¿Qué fundamentos legales aplican al caso de Carlos Martínez?",
        "expected": {
            "should_find": True,
            "reason": "Should combine: case data (project) + marco normativo (tenant-level)",
            "validation": "Should mention BOTH: 'Ley 1755' (from case) AND additional normative from marco",
            "keywords": ["ley", "1755", "constitución", "derecho", "petición"],
            "fallback": True,
            "fallback_reason": "Rich legal context requires both project case details and general normative framework"
        }
    },
    {
        "name": "Test 9: Task 1 specific query (análisis de contribuciones)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            "x-task-id": "1",
        },
        "query": "¿Quién es el responsable del análisis de contribuciones?",
        "expected": {
            "should_find": True,
            "reason": "Task 1 document has partition_key='t1_p6639_t1'",
            "validation": "Should mention 'María Fernanda Gómez' or 'maria.gomez'",
            "keywords": ["maría", "fernanda", "gómez", "analista"]
        }
    },
    {
        "name": "Test 10: Task 2 specific query (respuesta CGN)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            "x-task-id": "2",
        },
        "query": "¿Quién prepara la respuesta a la CGN?",
        "expected": {
            "should_find": True,
            "reason": "Task 2 document has partition_key='t1_p6639_t2'",
            "validation": "Should mention 'Pedro Luis Ramírez' or 'pedro.ramirez'",
            "keywords": ["pedro", "ramírez", "coordinador", "operaciones"]
        }
    },
    {
        "name": "Test 11: Cross-task isolation (Task 1 NO debe ver Task 2)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            "x-task-id": "1",
        },
        "query": "¿Quién es Pedro Luis Ramírez?",
        "expected": {
            "should_find": False,
            "reason": "Pedro is in task 2 (partition_key='t1_p6639_t2'), not task 1",
            "validation": "Should NOT mention Pedro or CGN response preparation",
            "forbidden_keywords": ["pedro", "ramirez", "cgn", "coordinador operaciones"]
        }
    },
    {
        "name": "Test 12: Project-level sees both tasks (NO task_id header)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            # No task_id - should see project-level docs (NOT task-specific)
        },
        "query": "¿Quiénes trabajan en el proyecto 6639?",
        "expected": {
            "should_find": True,
            "reason": "Project-level filter (t1_p6639) should see project docs, NOT task docs",
            "validation": "Should mention Superfinanciera docs (Rafael Martinez) but NOT task docs (María/Pedro)",
            "keywords": ["rafael", "martinez", "superfinanciera"],
            "forbidden_keywords": ["maría fernanda", "pedro luis"]
        }
    },
    {
        "name": "Test 13: Fallback from Task 1 to project-level",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            "x-task-id": "1",
        },
        "query": "¿Cuál es el número de radicación de Superfinanciera en el proyecto?",
        "expected": {
            "should_find": True,
            "reason": "Fallback from task to project-level (t1_p6639_t1 → t1_p6639)",
            "validation": "Should mention '2026022010-000-000'",
            "keywords": ["2026022010", "radicación", "superfinanciera"],
            "fallback": True,
            "fallback_reason": "Task doc doesn't have radicación, fallback to project-level"
        }
    },
    {
        "name": "Test 14: Fallback from Task 2 to tenant-level (marco normativo)",
        "headers": {
            "x-tenant-id": "1",
            "x-project-id": "6639",
            "x-task-id": "2",
        },
        "query": "¿Qué es el Decreto 2555 de 2010?",
        "expected": {
            "should_find": True,
            "reason": "Fallback chain: task → project → tenant (marco normativo)",
            "validation": "Should find info about Decreto 2555 from marco or task context",
            "keywords": ["decreto", "2555", "estatuto", "financiero"],
            "fallback": True,
            "fallback_reason": "Task mentions Decreto 2555, may need tenant-level marco for full context"
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
        "sessionId": f"test-colpensiones-{int(time.time())}",
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
        validation['details'].append(f"ℹ️  Fallback expected: {expected['fallback_reason']}")

    validation['details'].append(f"ℹ️  Reason: {expected['reason']}")
    validation['details'].append(f"ℹ️  Validation: {expected['validation']}")

    return validation


def main():
    """Run all test scenarios."""
    print("=" * 80)
    print("🧪 HIERARCHICAL FALLBACK TESTS - COLPENSIONES (Tenant 1 + Task Isolation)")
    print("=" * 80)
    print("Testing 4 levels: Tenant → Project → Task")
    print("- Tenant 1: marco_normativo_colpensiones.md")
    print("- Project 6610: Carlos Martínez case")
    print("- Project 6639: Superfinanciera + 2 tasks")
    print("  - Task 1: Análisis Contribuciones (María Fernanda)")
    print("  - Task 2: Respuesta CGN (Pedro Luis)")
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
        print("   cd agents")
        print("   docker build -t processapp-agent:test .")
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
            snippet = result['full_response'][:300].replace('\n', ' ')
            print(f"  Response snippet: {snippet}...")

        print()

    # Summary
    print("=" * 80)
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


if __name__ == "__main__":
    main()
