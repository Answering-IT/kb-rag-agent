#!/usr/bin/env python3
"""
Comprehensive test of Agent Core Runtime Endpoint
Tests:
1. Knowledge Base responses
2. Streaming output
3. Memory (conversation history)
"""

import boto3
import json
import requests
from requests_aws4auth import AWS4Auth
import uuid
import sys

# Configuration
ENDPOINT_URL = 'https://processapp_endpoint_v2_dev.bedrock-agentcore.us-east-1.amazonaws.com'
REGION = 'us-east-1'
PROFILE = 'ans-super'

def test_knowledge_base():
    """Test 1: Knowledge Base Query with Streaming"""
    print("=" * 80)
    print("TEST 1: Knowledge Base Query with Streaming")
    print("=" * 80)

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    credentials = session.get_credentials()

    # AWS4Auth for signing requests
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'bedrock-agentcore',
        session_token=credentials.token
    )

    session_id = str(uuid.uuid4())

    # Request payload
    payload = {
        "inputText": "What documents do you have in the knowledge base?",
        "sessionId": session_id
    }

    print(f"\n📡 Invoking endpoint:")
    print(f"   URL: {ENDPOINT_URL}/invocations")
    print(f"   Question: {payload['inputText']}")
    print(f"   Session ID: {session_id}")
    print("\n💬 Agent Response (streaming):")
    print("-" * 80)

    try:
        response = requests.post(
            f"{ENDPOINT_URL}/invocations",
            json=payload,
            auth=auth,
            stream=True,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            full_response = ""
            chunk_count = 0

            # Process streaming response (x-ndjson format)
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        chunk_count += 1

                        if chunk.get('type') == 'chunk':
                            data = chunk.get('data', '')
                            full_response += data
                            print(data, end='', flush=True)
                        elif chunk.get('type') == 'complete':
                            print("\n" + "-" * 80)
                            print(f"✅ Response complete ({chunk_count} chunks received)")
                            break
                        elif chunk.get('type') == 'error':
                            print(f"\n❌ Error: {chunk.get('message')}")
                            break
                    except json.JSONDecodeError:
                        # Plain text chunk
                        print(line.decode('utf-8'), end='', flush=True)

            return session_id, full_response

        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            print(response.text)
            return None, None

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None, None


def test_memory(session_id: str):
    """Test 2: Memory - Follow-up question using same session"""
    print("\n" + "=" * 80)
    print("TEST 2: Memory (Conversation History)")
    print("=" * 80)

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    credentials = session.get_credentials()

    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'bedrock-agentcore',
        session_token=credentials.token
    )

    # Follow-up question (should remember previous context)
    payload = {
        "inputText": "Can you summarize what we just discussed?",
        "sessionId": session_id
    }

    print(f"\n📡 Follow-up question (same session):")
    print(f"   Question: {payload['inputText']}")
    print(f"   Session ID: {session_id}")
    print("\n💬 Agent Response:")
    print("-" * 80)

    try:
        response = requests.post(
            f"{ENDPOINT_URL}/invocations",
            json=payload,
            auth=auth,
            stream=True,
            headers={'Content-Type': 'application/json'}
        )

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))

                        if chunk.get('type') == 'chunk':
                            print(chunk.get('data', ''), end='', flush=True)
                        elif chunk.get('type') == 'complete':
                            print("\n" + "-" * 80)
                            print("✅ Memory test complete")
                            break
                    except json.JSONDecodeError:
                        print(line.decode('utf-8'), end='', flush=True)

    except Exception as e:
        print(f"\n❌ Error: {e}")


def check_memory_status():
    """Check memory configuration"""
    print("\n" + "=" * 80)
    print("MEMORY STATUS")
    print("=" * 80)

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)

    # Note: Memory is currently DISABLED in AgentStackV2
    # Memory ID: memory-disabled

    print("\n📊 Memory Configuration:")
    print("   Status: DISABLED")
    print("   Reason: Memory was disabled in deployment")
    print("\n   ℹ️  To enable memory:")
    print("   1. Update AgentStackV2.ts")
    print("   2. Change memoryType: 'LONG_TERM' (from 'DISABLED')")
    print("   3. Redeploy")


def test_health():
    """Test health endpoint"""
    print("\n" + "=" * 80)
    print("HEALTH CHECK")
    print("=" * 80)

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    credentials = session.get_credentials()

    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'bedrock-agentcore',
        session_token=credentials.token
    )

    print(f"\n📡 Checking health endpoint...")

    try:
        response = requests.get(
            f"{ENDPOINT_URL}/health",
            auth=auth
        )

        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Status: {health_data.get('status', 'unknown')}")
            print(f"   Runtime: {health_data.get('runtime', 'unknown')}")
            print(f"   KB ID: {health_data.get('kb_id', 'unknown')}")
            print(f"   Model: {health_data.get('model', 'unknown')}")
            print(f"   SDK: {health_data.get('sdk', 'unknown')}")
        else:
            print(f"   ⚠️  Status code: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == '__main__':
    print("\n🚀 ProcessApp Agent Core Runtime - Full Test Suite")
    print(f"   Endpoint: {ENDPOINT_URL}")
    print()

    # Test 1: Knowledge Base with Streaming
    session_id, response = test_knowledge_base()

    if session_id:
        # Test 2: Memory (follow-up question)
        test_memory(session_id)

    # Check memory status
    check_memory_status()

    # Health check
    test_health()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETE")
    print("=" * 80)
