#!/usr/bin/env python3
"""
Test API Gateway endpoint for Bedrock Agent
"""

import requests
import json
import sys
import os

# API Configuration
API_ENDPOINT = "https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query"
API_KEY = os.environ.get('API_KEY')

if not API_KEY:
    print("❌ Error: API_KEY environment variable not set")
    print("\nTo get your API key:")
    print("aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text")
    print("\nThen set it:")
    print("export API_KEY='<your-api-key>'")
    sys.exit(1)


def ask_agent(question, session_id=None):
    """Ask a question to the agent via API"""
    print(f"\n{'='*70}")
    print(f"PREGUNTA: {question}")
    print(f"{'='*70}")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }

    payload = {
        "question": question
    }

    if session_id:
        payload["sessionId"] = session_id
        print(f"Session ID: {session_id}")

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload, timeout=30)

        # Print status
        print(f"\nHTTP Status: {response.status_code}")

        # Parse response
        result = response.json()

        if response.status_code == 200 and result.get('status') == 'success':
            print(f"\n✅ RESPUESTA:\n{result['answer']}\n")
            print(f"Session ID: {result['sessionId']}")
            return result
        else:
            print(f"\n❌ ERROR: {result.get('error', 'Unknown error')}\n")
            return None

    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timeout (>30s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR: Request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"\n❌ ERROR: Invalid JSON response: {e}")
        print(f"Response text: {response.text}")
        return None


if __name__ == "__main__":
    print("\n" + "="*70)
    print("PRUEBA DE API GATEWAY - Bedrock Agent")
    print("="*70)
    print(f"\nEndpoint: {API_ENDPOINT}")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-5:]}")

    # Test 1: Simple query
    print("\n\n### TEST 1: Pregunta simple ###\n")
    result = ask_agent("¿Qué documentos tienes disponibles?")

    if result:
        # Test 2: Follow-up question using same session
        print("\n\n### TEST 2: Pregunta de seguimiento (misma sesión) ###\n")
        ask_agent(
            "Dame más detalles sobre el primero",
            session_id=result['sessionId']
        )

    # Test 3: Security incident query (OCR document)
    print("\n\n### TEST 3: Consulta sobre incidente de seguridad (OCR) ###\n")
    ask_agent("¿Cuál fue la fecha del incidente de seguridad en DataFlow?")

    # Test 4: Company data query
    print("\n\n### TEST 4: Consulta sobre datos de empresa ###\n")
    ask_agent("¿Cuáles fueron los ingresos de TechFlow Solutions en Q1 2026?")

    # Test 5: PII filter test (should be blocked by guardrails)
    print("\n\n### TEST 5: Test de filtro PII (debería bloquearse) ###\n")
    ask_agent("¿Quién es el CEO de TechFlow Solutions?")

    print("\n" + "="*70)
    print("PRUEBAS COMPLETADAS")
    print("="*70 + "\n")

    print("💡 Tip: Para conversaciones multi-turn, usa el mismo sessionId")
    print("💡 Tip: Revisa logs en CloudWatch: /aws/lambda/processapp-api-handler-dev\n")
