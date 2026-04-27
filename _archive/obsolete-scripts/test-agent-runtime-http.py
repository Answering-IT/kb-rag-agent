#!/usr/bin/env python3
"""
Test Agent Core Runtime via internal HTTP endpoint
This script tests the /invocations endpoint directly
"""

import boto3
import json
import sys

# Configuration
RUNTIME_ID = 'processapp_agent_runtime_v2_dev-9b2dszEtqw'
REGION = 'us-east-1'
PROFILE = 'ans-super'

def test_agent_runtime(question: str = "What documents do you have?"):
    """
    Test the agent runtime by invoking through SDK
    Note: Direct HTTP invocation is not supported - use SDK
    """
    print(f"🚀 Testing Agent Core Runtime")
    print(f"   Runtime ID: {RUNTIME_ID}")
    print(f"   Question: {question}")
    print("=" * 80)

    # Use AWS SDK to invoke the runtime
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    bedrock_runtime = session.client('bedrock-agentcore-runtime')

    try:
        # Invoke runtime
        response = bedrock_runtime.invoke_agent_runtime(
            runtimeId=RUNTIME_ID,
            inputText=question
        )

        print("\n💬 Agent Response:")
        print("-" * 80)

        # Process streaming response
        full_response = ""
        for event in response.get('body', []):
            if 'chunk' in event:
                chunk_data = event['chunk']
                if 'bytes' in chunk_data:
                    text = chunk_data['bytes'].decode('utf-8')
                    full_response += text
                    print(text, end='', flush=True)

        print("\n" + "-" * 80)
        print("✅ Test complete")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nNote: Direct HTTP invocation of Agent Core Runtime is not supported.")
        print(f"The runtime is accessible only through AWS SDK or WebSocket API.")

if __name__ == '__main__':
    question = sys.argv[1] if len(sys.argv) > 1 else "What documents do you have in the knowledge base?"
    test_agent_runtime(question)
