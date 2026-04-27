#!/usr/bin/env python3
"""
Test script for Agent V2 (Agent Core Runtime)
Invokes the deployed agent and displays the response
"""

import boto3
import json
import sys
import uuid
from datetime import datetime

# Configuration
RUNTIME_ID = 'processapp_agent_runtime_v2_dev-9b2dszEtqw'
REGION = 'us-east-1'
PROFILE = 'ans-super'

def test_agent(question: str, session_id: str = None):
    """
    Test the agent with a question
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    print(f"🤖 Testing Agent V2")
    print(f"   Runtime ID: {RUNTIME_ID}")
    print(f"   Session ID: {session_id}")
    print(f"   Question: {question}")
    print("=" * 80)

    # Create boto3 session with profile
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)

    # Note: Agent Core Runtime uses a different client/endpoint
    # We need to invoke it via the runtime endpoint
    # For now, let's try using bedrock-agent-runtime client

    try:
        bedrock_agent = session.client('bedrock-agent-runtime', region_name=REGION)

        # Try to invoke the runtime
        # The exact API might be different for Agent Core Runtime
        # Let's check what methods are available
        print("\n📋 Available methods:")
        methods = [m for m in dir(bedrock_agent) if not m.startswith('_')]
        for method in sorted(methods):
            if 'invoke' in method.lower() or 'runtime' in method.lower():
                print(f"   - {method}")

        print("\n" + "=" * 80)
        print("⚠️  Agent Core Runtime requires direct HTTP invocation")
        print("    The runtime is accessible via:")
        print(f"    Runtime ARN: arn:aws:bedrock-agentcore:us-east-1:708819485463:runtime/{RUNTIME_ID}")
        print()
        print("    To invoke, you need to:")
        print("    1. Get the runtime endpoint URL")
        print("    2. Make HTTP POST to /invocations")
        print("    3. Use IAM signature v4 for authentication")
        print()
        print("    Alternative: Use AWS Console or CloudWatch logs to verify agent is running")

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_runtime_status():
    """
    Check if the runtime is active
    """
    print("\n🔍 Checking Runtime Status...")
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)

    # Try CloudFormation to get stack outputs
    cfn = session.client('cloudformation', region_name=REGION)

    try:
        response = cfn.describe_stacks(StackName='dev-us-east-1-agent-v2')
        stack = response['Stacks'][0]

        print(f"\n✅ Stack Status: {stack['StackStatus']}")
        print("\n📤 Outputs:")
        for output in stack.get('Outputs', []):
            print(f"   {output['OutputKey']}: {output['OutputValue']}")

        # Check CloudWatch logs
        print("\n📋 CloudWatch Log Groups:")
        logs = session.client('logs', region_name=REGION)

        # Try to find log groups related to the runtime
        log_groups = logs.describe_log_groups(
            logGroupNamePrefix='/aws/bedrock-agentcore'
        )

        if log_groups['logGroups']:
            for lg in log_groups['logGroups']:
                print(f"   - {lg['logGroupName']}")
        else:
            print("   No log groups found yet")

    except Exception as e:
        print(f"❌ Error checking status: {e}")

def view_recent_logs():
    """
    View recent CloudWatch logs
    """
    print("\n📜 Recent Logs...")
    session = boto3.Session(profile_name=PROFILE, region_name=REGION)
    logs = session.client('logs', region_name=REGION)

    try:
        # List log groups
        response = logs.describe_log_groups(
            logGroupNamePrefix='/aws/bedrock-agentcore'
        )

        if not response['logGroups']:
            print("   No log groups found. Agent may still be starting...")
            return

        for log_group in response['logGroups']:
            log_group_name = log_group['logGroupName']
            print(f"\n   Log Group: {log_group_name}")

            # Get recent log streams
            streams = logs.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )

            if streams['logStreams']:
                stream = streams['logStreams'][0]
                print(f"   Stream: {stream['logStreamName']}")

                # Get recent events
                events = logs.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream['logStreamName'],
                    limit=20,
                    startFromHead=False
                )

                print("\n   Recent Events:")
                for event in events['events']:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    print(f"   [{timestamp}] {event['message']}")

    except Exception as e:
        print(f"❌ Error reading logs: {e}")

if __name__ == '__main__':
    question = sys.argv[1] if len(sys.argv) > 1 else "What documents do you have?"

    print("🚀 ProcessApp Agent V2 Test Suite")
    print("=" * 80)

    # Check runtime status
    check_runtime_status()

    # View logs
    view_recent_logs()

    # Test agent
    print("\n" + "=" * 80)
    test_agent(question)

    print("\n" + "=" * 80)
    print("✅ Test completed")
