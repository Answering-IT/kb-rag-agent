#!/usr/bin/env python3
"""
Invoke Agent Core Runtime via HTTP POST
Direct invocation to /invocations endpoint
"""

import boto3
import json
import requests
from requests_aws4auth import AWS4Auth
import sys

# Configuration
RUNTIME_ID = 'processapp_agent_runtime_v2_dev-9b2dszEtqw'
REGION = 'us-east-1'
PROFILE = 'ans-super'

def get_runtime_endpoint():
    """
    Get the runtime endpoint URL from AWS
    """
    # Note: There might not be a direct API to get this
    # The runtime endpoint is typically:
    # https://{runtime-id}.bedrock-agentcore.{region}.amazonaws.com
    # But this is not officially documented

    # For now, we'll construct it based on the pattern
    endpoint = f"https://{RUNTIME_ID}.bedrock-agentcore.{REGION}.amazonaws.com"
    return endpoint

def invoke_runtime(question: str, session_id: str = None):
    """
    Invoke the runtime via HTTP POST
    """
    import uuid
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Get AWS credentials
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    credentials = session.get_credentials()

    # Create AWS4Auth for signing requests
    auth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'bedrock-agentcore',
        session_token=credentials.token
    )

    # Runtime endpoint
    endpoint = get_runtime_endpoint()
    url = f"{endpoint}/invocations"

    print(f"🚀 Invoking Agent Core Runtime")
    print(f"   Endpoint: {url}")
    print(f"   Session: {session_id}")
    print(f"   Question: {question}")
    print("=" * 80)

    # Request payload
    payload = {
        "inputText": question,
        "sessionId": session_id
    }

    try:
        # Make HTTP POST request
        response = requests.post(
            url,
            json=payload,
            auth=auth,
            headers={'Content-Type': 'application/json'},
            stream=True  # Enable streaming
        )

        print(f"\n📡 Response Status: {response.status_code}")

        if response.status_code == 200:
            print("\n💬 Agent Response (streaming):")
            print("-" * 80)

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if data.get('type') == 'chunk':
                            print(data.get('data', ''), end='', flush=True)
                        elif data.get('type') == 'complete':
                            print("\n" + "-" * 80)
                            print("✅ Response complete")
                    except json.JSONDecodeError:
                        # Might be plain text
                        print(line.decode('utf-8'), end='', flush=True)

            print()
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)

    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\nℹ️  The runtime endpoint might not be publicly accessible.")
        print("   Agent Core Runtimes are typically accessed via:")
        print("   1. AWS Console")
        print("   2. AWS SDK (bedrock-agent-runtime client)")
        print("   3. VPC-private endpoints")
        print("\n   Try using the AWS SDK instead of direct HTTP:")
        print(f"   aws bedrock-agent-runtime invoke-agent-runtime --runtime-id {RUNTIME_ID} ...")

    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == '__main__':
    question = sys.argv[1] if len(sys.argv) > 1 else "Hello, how can you help me?"

    try:
        invoke_runtime(question)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
