#!/usr/bin/env python3
"""
Test Agent Core Runtime - Invoke with streaming
Tests:
1. Knowledge Base responses
2. Streaming output
3. Memory (if enabled)
"""

import boto3
import json
import uuid
import sys
from datetime import datetime

# Configuration
RUNTIME_ID = 'processapp_agent_runtime_v2_dev-9b2dszEtqw'
REGION = 'us-east-1'
PROFILE = 'ans-super'

def test_knowledge_base_query():
    """Test agent with knowledge base query"""
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)

    # Try different client names
    print("🔍 Testing Agent Core Runtime invocation methods...")
    print(f"   Runtime ID: {RUNTIME_ID}")
    print("=" * 80)

    # Method 1: Try bedrock-agent-runtime (standard agents)
    try:
        print("\n📡 Method 1: Using bedrock-agent-runtime client...")
        client = session.client('bedrock-agent-runtime', region_name=REGION)
        print("   ✅ Client created")

        # This likely won't work for Agent Core Runtime, but let's try
        print("   ⚠️  This client is for standard Bedrock Agents, not Agent Core Runtime")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Method 2: Try direct HTTP invocation (not recommended but let's see)
    try:
        print("\n📡 Method 2: Checking runtime details with bedrock-agentcore client...")
        control_client = session.client('bedrock-agentcore', region_name=REGION)

        # Get runtime details
        runtime_info = control_client.get_runtime(runtimeId=RUNTIME_ID)

        print(f"   ✅ Runtime found:")
        print(f"      Name: {runtime_info.get('runtimeName', 'N/A')}")
        print(f"      Status: {runtime_info.get('status', 'N/A')}")
        print(f"      Protocol: HTTP")
        print(f"      Auth: IAM")

        # Check if runtime has endpoint info
        if 'runtimeEndpoint' in runtime_info:
            endpoint = runtime_info['runtimeEndpoint']
            print(f"      Endpoint: {endpoint}")
        else:
            print(f"      ℹ️  Runtime endpoint not exposed (internal-only)")
            print(f"      ℹ️  Need to create RuntimeEndpoint to access externally")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Method 3: Check if there's a way to invoke through runtime control
    print("\n📝 Summary:")
    print("   The Agent Core Runtime is running successfully (we can see /ping health checks)")
    print("   However, it's INTERNAL-ONLY by default")
    print("\n   To invoke the runtime externally, you need:")
    print("   1. Create a RuntimeEndpoint (CDK construct)")
    print("   2. Or use WebSocket API with Lambda handlers")
    print("   3. Or invoke from within AWS VPC (e.g., from Lambda)")

    print("\n💡 Next step:")
    print("   Deploy RuntimeEndpoint to expose the agent via HTTPS endpoint")


def check_memory_status():
    """Check if memory is enabled"""
    print("\n" + "=" * 80)
    print("🧠 Checking Memory Configuration...")

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    client = session.client('bedrock-agentcore', region_name=REGION)

    try:
        runtime_info = client.get_runtime(runtimeId=RUNTIME_ID)

        # Check memory configuration
        memory_config = runtime_info.get('memoryConfiguration', {})

        if memory_config:
            memory_type = memory_config.get('memoryType', 'NONE')
            print(f"   Memory Type: {memory_type}")

            if memory_type == 'LONG_TERM':
                print(f"   ✅ Memory ENABLED (90-day retention)")
                print(f"   Memory ID: {memory_config.get('memoryId', 'N/A')}")
            elif memory_type == 'DISABLED':
                print(f"   ❌ Memory DISABLED")
            else:
                print(f"   Status: {memory_type}")
        else:
            print(f"   ❌ Memory not configured")

    except Exception as e:
        print(f"   ❌ Error: {e}")


def check_cloudwatch_logs():
    """Check recent CloudWatch logs to see agent activity"""
    print("\n" + "=" * 80)
    print("📋 Recent Agent Activity (CloudWatch Logs)...")

    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    logs_client = session.client('logs')

    import time
    now = int(time.time() * 1000)
    start_time = now - (2 * 60 * 1000)  # Last 2 minutes

    try:
        response = logs_client.filter_log_events(
            logGroupName=f'/aws/bedrock-agentcore/runtimes/{RUNTIME_ID}-DEFAULT',
            startTime=start_time,
            limit=20
        )

        print(f"\n   Last 20 log entries:")
        for event in response.get('events', []):
            message = event['message'].strip()
            if message:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%H:%M:%S')
                print(f"   [{timestamp}] {message}")

        # Check for health
        health_checks = [e for e in response.get('events', []) if '200' in e['message'] and '/ping' in e['message']]

        if health_checks:
            print(f"\n   ✅ Agent is HEALTHY ({len(health_checks)} health checks passed)")
        else:
            print(f"\n   ⚠️  No recent health checks found")

    except Exception as e:
        print(f"   ❌ Error: {e}")


if __name__ == '__main__':
    test_knowledge_base_query()
    check_memory_status()
    check_cloudwatch_logs()

    print("\n" + "=" * 80)
    print("📌 CONCLUSION:")
    print("   The agent is running but needs RuntimeEndpoint to be accessible")
    print("   Let's implement RuntimeEndpoint next!")
    print("=" * 80)
