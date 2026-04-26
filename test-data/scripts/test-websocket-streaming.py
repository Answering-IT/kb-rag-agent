#!/usr/bin/env python3
"""
WebSocket Streaming Test Client
Tests real-time streaming from Bedrock Agent via WebSocket
"""

import asyncio
import websockets
import json
import sys

# WebSocket URL from deployment output
WS_URL = "wss://mf1ghadu5m.execute-api.us-east-1.amazonaws.com/dev"


async def test_streaming(tenant_id: str, question: str):
    """
    Test WebSocket streaming with tenant filtering
    """
    print(f"Connecting to WebSocket: {WS_URL}")

    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ Connected to WebSocket")

            # Send query message
            message = {
                "action": "query",
                "question": question,
                "tenantId": tenant_id,
                "userId": f"user_{tenant_id}",
                "roles": ["viewer"],
                "projectId": "100",
                "users": ["*"]
            }

            print(f"\nSending message: {json.dumps(message, indent=2)}")
            await websocket.send(json.dumps(message))

            print("\n--- Streaming Response ---")

            full_response = ""
            chunk_count = 0

            # Receive streaming chunks
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)

                    msg_type = data.get('type')

                    if msg_type == 'status':
                        print(f"📊 Status: {data.get('message')}")

                    elif msg_type == 'chunk':
                        chunk = data.get('data', '')
                        full_response += chunk
                        chunk_count += 1
                        # Print chunk with visual indicator
                        print(chunk, end='', flush=True)

                    elif msg_type == 'complete':
                        print(f"\n\n✅ Stream complete!")
                        print(f"Total chunks: {data.get('totalChunks')}")
                        print(f"Session ID: {data.get('sessionId')}")
                        break

                    elif msg_type == 'error':
                        print(f"\n❌ Error: {data.get('error')}")
                        break

                except asyncio.TimeoutError:
                    print("\n⚠️  Timeout waiting for response")
                    break

            print(f"\n--- End of Stream ---")
            print(f"\nFull response ({len(full_response)} characters):")
            print(f"{full_response}")

            return full_response

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def run_tests():
    """
    Run comprehensive WebSocket streaming tests
    """
    print("=" * 80)
    print("WEBSOCKET STREAMING TEST")
    print("=" * 80)

    tests = [
        {
            'name': 'Test 1: Tenant 1 - Colpensiones Info',
            'tenant_id': '1',
            'question': 'What is the mission of Colpensiones?'
        },
        {
            'name': 'Test 2: Tenant 2 - Organization AC Info',
            'tenant_id': '2',
            'question': 'How many active users does Organization AC have?'
        },
        {
            'name': 'Test 3: Tenant 1 - Try to access Tenant 2 data',
            'tenant_id': '1',
            'question': 'How many users does Organization AC have?'
        },
        {
            'name': 'Test 4: Long streaming response',
            'tenant_id': '1',
            'question': 'Tell me everything you know about Colpensiones services and mission'
        }
    ]

    results = []

    for i, test in enumerate(tests, 1):
        print(f"\n{'='*80}")
        print(f"{test['name']}")
        print(f"{'='*80}")

        response = await test_streaming(test['tenant_id'], test['question'])

        results.append({
            'test': test['name'],
            'success': response is not None,
            'response_length': len(response) if response else 0
        })

        if i < len(tests):
            print("\nWaiting 2 seconds before next test...")
            await asyncio.sleep(2)

    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {result['test']} ({result['response_length']} chars)")

    success_count = sum(1 for r in results if r['success'])
    print(f"\nTotal: {success_count}/{len(tests)} tests passed")


def main():
    """
    Main entry point
    """
    if WS_URL == "wss://YOUR_WEBSOCKET_URL":
        print("❌ Error: Please update WS_URL with your actual WebSocket URL")
        print("\nTo get your WebSocket URL, run:")
        print("  aws cloudformation describe-stacks \\")
        print("    --stack-name dev-us-east-1-websocket \\")
        print("    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURL`].OutputValue' \\")
        print("    --output text --profile ans-super")
        sys.exit(1)

    # Run async tests
    asyncio.run(run_tests())


if __name__ == '__main__':
    main()
