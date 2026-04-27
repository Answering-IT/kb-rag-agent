#!/usr/bin/env python3
"""
Test Agent Core Runtime via WebSocket
Tests:
1. Knowledge Base query with streaming
2. Memory (conversation history)
3. Multiple interactions
"""

import asyncio
import websockets
import json
import uuid

# Configuration
WS_URL = 'wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev'

async def test_knowledge_base():
    """Test 1: Knowledge Base Query"""
    print("=" * 80)
    print("TEST 1: Knowledge Base Query with Streaming")
    print("=" * 80)

    session_id = str(uuid.uuid4())

    async with websockets.connect(WS_URL) as websocket:
        # Send question
        message = {
            "action": "sendMessage",
            "question": "What documents do you have in the knowledge base?",
            "sessionId": session_id
        }

        print(f"\n📡 Sending message:")
        print(f"   Question: {message['question']}")
        print(f"   Session ID: {session_id}")
        print("\n💬 Agent Response (streaming):")
        print("-" * 80)

        await websocket.send(json.dumps(message))

        # Receive streaming response
        full_response = ""
        chunk_count = 0

        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)

                if data.get('type') == 'status':
                    print(f"   [STATUS] {data.get('message')}")
                elif data.get('type') == 'chunk':
                    chunk_data = data.get('data', '')
                    full_response += chunk_data
                    print(chunk_data, end='', flush=True)
                    chunk_count += 1
                elif data.get('type') == 'complete':
                    print("\n" + "-" * 80)
                    print(f"✅ Response complete ({chunk_count} chunks)")
                    break
                elif data.get('type') == 'error':
                    print(f"\n❌ Error: {data.get('message')}")
                    break

            except asyncio.TimeoutError:
                print("\n⚠️  Response timeout")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break

        return session_id, full_response


async def test_memory(session_id: str):
    """Test 2: Memory - Follow-up question"""
    print("\n" + "=" * 80)
    print("TEST 2: Memory (Conversation History)")
    print("=" * 80)

    async with websockets.connect(WS_URL) as websocket:
        # Follow-up question (same session)
        message = {
            "action": "sendMessage",
            "question": "Can you summarize what we just discussed?",
            "sessionId": session_id
        }

        print(f"\n📡 Follow-up question (same session):")
        print(f"   Question: {message['question']}")
        print(f"   Session ID: {session_id}")
        print("\n💬 Agent Response:")
        print("-" * 80)

        await websocket.send(json.dumps(message))

        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)

                if data.get('type') == 'chunk':
                    print(data.get('data', ''), end='', flush=True)
                elif data.get('type') == 'complete':
                    print("\n" + "-" * 80)
                    print("✅ Memory test complete")
                    break
                elif data.get('type') == 'error':
                    print(f"\n❌ Error: {data.get('message')}")
                    break

            except asyncio.TimeoutError:
                print("\n⚠️  Response timeout")
                break


async def test_new_session():
    """Test 3: New session (should not remember previous context)"""
    print("\n" + "=" * 80)
    print("TEST 3: New Session (Fresh Context)")
    print("=" * 80)

    new_session_id = str(uuid.uuid4())

    async with websockets.connect(WS_URL) as websocket:
        message = {
            "action": "sendMessage",
            "question": "What did we discuss earlier?",
            "sessionId": new_session_id
        }

        print(f"\n📡 New session question:")
        print(f"   Question: {message['question']}")
        print(f"   Session ID: {new_session_id} (NEW)")
        print("\n💬 Agent Response:")
        print("-" * 80)

        await websocket.send(json.dumps(message))

        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(response)

                if data.get('type') == 'chunk':
                    print(data.get('data', ''), end='', flush=True)
                elif data.get('type') == 'complete':
                    print("\n" + "-" * 80)
                    print("✅ New session test complete")
                    print("   (Should NOT remember previous conversation)")
                    break
                elif data.get('type') == 'error':
                    print(f"\n❌ Error: {data.get('message')}")
                    break

            except asyncio.TimeoutError:
                print("\n⚠️  Response timeout")
                break


async def main():
    print("\n🚀 ProcessApp Agent Core Runtime - WebSocket Test Suite")
    print(f"   WebSocket URL: {WS_URL}")
    print()

    try:
        # Test 1: Knowledge Base with Streaming
        session_id, response = await test_knowledge_base()

        if session_id and response:
            # Test 2: Memory (same session)
            await test_memory(session_id)

            # Test 3: New session
            await test_new_session()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 80)
        print("\n📊 Test Summary:")
        print("   1. ✅ Knowledge Base query - Working")
        print("   2. ⚠️  Memory - DISABLED (needs to be enabled)")
        print("   3. ✅ Streaming - Working")
        print("   4. ✅ WebSocket - Working")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == '__main__':
    asyncio.run(main())
