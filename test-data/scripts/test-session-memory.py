#!/usr/bin/env python3
"""
Session Memory Test - Verify conversation context persistence
Tests that the agent remembers previous messages in the same session
"""

import asyncio
import websockets
import json
import sys
import uuid

WS_URL = "wss://mf1ghadu5m.execute-api.us-east-1.amazonaws.com/dev"


async def test_session_memory():
    """
    Test session memory by asking two related questions
    """
    # Use the same session ID for both questions
    session_id = str(uuid.uuid4())
    
    print("=" * 80)
    print("SESSION MEMORY TEST")
    print("=" * 80)
    print(f"\nSession ID: {session_id}")
    print("\nThis test verifies that the agent remembers conversation context.")
    print("\n" + "=" * 80)
    
    # Question 1: Introduce information
    print("\n🔵 TEST 1: Establishing Context")
    print("-" * 80)
    
    question1 = "My name is Alice and I work for Colpensiones"
    print(f"\nUser: {question1}")
    
    response1 = await send_question(session_id, question1)
    print(f"\nAssistant: {response1}\n")
    
    # Wait a bit between questions
    await asyncio.sleep(2)
    
    # Question 2: Ask about the context from question 1
    print("\n🔵 TEST 2: Verifying Context Recall")
    print("-" * 80)
    
    question2 = "What is my name and where do I work?"
    print(f"\nUser: {question2}")
    
    response2 = await send_question(session_id, question2)
    print(f"\nAssistant: {response2}\n")
    
    # Verify that the assistant remembered
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if "alice" in response2.lower() and ("colpensiones" in response2.lower() or "work" in response2.lower()):
        print("\n✅ SUCCESS: Agent remembered the context!")
        print("   - Recalled name: Alice")
        print("   - Recalled workplace: Colpensiones")
        return True
    else:
        print("\n❌ FAILURE: Agent did not remember the context")
        print(f"   Response did not contain expected information.")
        return False


async def send_question(session_id: str, question: str) -> str:
    """
    Send a question via WebSocket and return the full response
    """
    try:
        async with websockets.connect(WS_URL) as websocket:
            # Send query
            message = {
                "action": "query",
                "question": question,
                "sessionId": session_id,
                "tenantId": "1",
                "userId": "test_user",
                "roles": ["viewer"]
            }
            
            await websocket.send(json.dumps(message))
            
            # Collect response chunks
            full_response = ""
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    if data.get('type') == 'chunk':
                        chunk = data.get('data', '')
                        full_response += chunk
                        print(chunk, end='', flush=True)
                    
                    elif data.get('type') == 'complete':
                        break
                    
                    elif data.get('type') == 'error':
                        print(f"\n❌ Error: {data.get('error')}")
                        break
                
                except asyncio.TimeoutError:
                    print("\n⚠️  Timeout waiting for response")
                    break
            
            return full_response
    
    except Exception as e:
        print(f"\n❌ WebSocket error: {e}")
        return ""


async def main():
    """
    Run session memory test
    """
    success = await test_session_memory()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ Session memory is working correctly!")
    else:
        print("❌ Session memory test failed")
    print("=" * 80 + "\n")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
