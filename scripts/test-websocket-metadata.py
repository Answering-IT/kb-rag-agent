#!/usr/bin/env python3
"""
Test WebSocket with metadata filtering (snake_case format)
"""

import asyncio
import websockets
import json
import sys

# WebSocket URL - get from stack outputs
WS_URL = "wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"


async def test_with_metadata():
    """Test query with metadata filtering"""
    print("🔌 Connecting to WebSocket...")

    async with websockets.connect(WS_URL) as ws:
        # Test query with metadata (snake_case for AWS Bedrock)
        query = {
            "action": "query",
            "question": "¿Qué es la Ley 2381 de 2024?",
            "sessionId": "test-metadata-123",
            "tenant_id": "company-123",
            "user_id": "user456",
            "user_roles": ["admin", "analyst"],
            "project_id": "project-789"
        }

        print(f"\n📤 Sending query with metadata:")
        print(f"   tenant_id: {query['tenant_id']}")
        print(f"   user_id: {query['user_id']}")
        print(f"   user_roles: {query['user_roles']}")
        print(f"   project_id: {query['project_id']}")
        print(f"\n❓ Question: {query['question']}\n")

        await ws.send(json.dumps(query))

        # Receive streaming response
        full_response = ""
        chunk_count = 0

        async for message in ws:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'status':
                print(f"⏳ {data.get('message')}")

            elif msg_type == 'chunk':
                chunk = data.get('data', '')
                print(chunk, end='', flush=True)
                full_response += chunk
                chunk_count += 1

            elif msg_type == 'complete':
                print(f"\n\n✅ Complete!")
                print(f"   Total chunks: {chunk_count}")

                # Show stats if available
                stats = data.get('stats', {})
                if stats:
                    print(f"\n📊 Session Stats:")
                    print(f"   Message count: {stats.get('message_count', 'N/A')}")
                    print(f"   Window size: {stats.get('window_size', 'N/A')}")
                    print(f"   Truncations: {stats.get('truncation_count', 0)}")
                    print(f"   Age (min): {stats.get('age_minutes', 'N/A')}")

                # Check if metadata filtering was applied
                metadata_filtered = data.get('metadata_filtered', False)
                print(f"\n🔒 Metadata filtered: {metadata_filtered}")

                break

            elif msg_type == 'error':
                print(f"\n❌ Error: {data.get('message')}")
                break

        return full_response


async def test_without_metadata():
    """Test query without metadata (no filtering)"""
    print("\n" + "="*70)
    print("🔌 Testing WITHOUT metadata (no filtering)...")

    async with websockets.connect(WS_URL) as ws:
        query = {
            "action": "query",
            "question": "¿Cuál es el marco normativo de pensiones?",
            "sessionId": "test-no-metadata-456"
        }

        print(f"\n📤 Sending query WITHOUT metadata")
        print(f"❓ Question: {query['question']}\n")

        await ws.send(json.dumps(query))

        # Receive response
        async for message in ws:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'status':
                print(f"⏳ {data.get('message')}")

            elif msg_type == 'chunk':
                chunk = data.get('data', '')
                print(chunk, end='', flush=True)

            elif msg_type == 'complete':
                metadata_filtered = data.get('metadata_filtered', False)
                print(f"\n\n✅ Complete!")
                print(f"🔒 Metadata filtered: {metadata_filtered}")
                break

            elif msg_type == 'error':
                print(f"\n❌ Error: {data.get('message')}")
                break


async def test_conversation():
    """Test multi-turn conversation with context"""
    print("\n" + "="*70)
    print("🔌 Testing CONVERSATION CONTEXT...")

    session_id = "test-conversation-789"

    async with websockets.connect(WS_URL) as ws:
        # Turn 1: Introduce name
        print(f"\n🗣️  Turn 1: Setting context...")
        query1 = {
            "action": "query",
            "question": "Mi nombre es Carlos y trabajo en Colpensiones",
            "sessionId": session_id,
            "tenant_id": "colpensiones",
            "user_id": "carlos",
            "user_roles": ["employee"]
        }

        await ws.send(json.dumps(query1))

        async for message in ws:
            data = json.loads(message)
            if data.get('type') == 'chunk':
                print(data.get('data', ''), end='', flush=True)
            elif data.get('type') == 'complete':
                print("\n✅ Turn 1 complete\n")
                break

    # Turn 2: Ask about name (should remember)
    async with websockets.connect(WS_URL) as ws:
        print(f"\n🗣️  Turn 2: Testing memory...")
        query2 = {
            "action": "query",
            "question": "¿Cuál es mi nombre y dónde trabajo?",
            "sessionId": session_id,
            "tenant_id": "colpensiones",
            "user_id": "carlos",
            "user_roles": ["employee"]
        }

        await ws.send(json.dumps(query2))

        response = ""
        async for message in ws:
            data = json.loads(message)
            if data.get('type') == 'chunk':
                chunk = data.get('data', '')
                print(chunk, end='', flush=True)
                response += chunk
            elif data.get('type') == 'complete':
                print("\n✅ Turn 2 complete")

                # Check if it remembered
                if "carlos" in response.lower() and "colpensiones" in response.lower():
                    print("\n✅ Context REMEMBERED correctly!")
                else:
                    print("\n⚠️  Context may not have been remembered")
                break


async def main():
    """Run all tests"""
    print("="*70)
    print("  WebSocket Metadata Filtering Tests (snake_case)")
    print("="*70)

    try:
        # Test 1: With metadata
        await test_with_metadata()

        # Test 2: Without metadata
        await test_without_metadata()

        # Test 3: Conversation context
        await test_conversation()

        print("\n" + "="*70)
        print("✅ All tests completed!")
        print("="*70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
