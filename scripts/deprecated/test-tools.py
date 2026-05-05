#!/usr/bin/env python3
"""Test WebSocket with both tools: Knowledge Base and Project Info"""
import socket
import ssl
import json
import base64
import os
import uuid
import sys


def websocket_handshake(host, path):
    """Perform WebSocket handshake"""
    key = base64.b64encode(os.urandom(16)).decode()

    request = f"GET {path} HTTP/1.1\r\n"
    request += f"Host: {host}\r\n"
    request += "Upgrade: websocket\r\n"
    request += "Connection: Upgrade\r\n"
    request += f"Sec-WebSocket-Key: {key}\r\n"
    request += "Sec-WebSocket-Version: 13\r\n"
    request += "\r\n"

    return request.encode(), key


def send_websocket_message(wrapped_socket, connection_id, message):
    """Send a message through WebSocket"""
    payload = json.dumps(message).encode()
    frame = bytearray([0x81])  # FIN + Text frame

    length = len(payload)
    if length < 126:
        frame.append(0x80 | length)  # Mask bit + length
    else:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))

    # Add masking key
    mask = os.urandom(4)
    frame.extend(mask)

    # Mask payload
    masked_payload = bytearray(payload)
    for i in range(len(masked_payload)):
        masked_payload[i] ^= mask[i % 4]

    frame.extend(masked_payload)
    wrapped_socket.send(bytes(frame))


def receive_websocket_response(wrapped_socket):
    """Receive and parse WebSocket responses"""
    full_response = ""
    chunk_count = 0

    while True:
        try:
            data = wrapped_socket.recv(4096)
            if not data:
                break

            # Parse WebSocket frame
            if len(data) < 2:
                continue

            opcode = data[0] & 0x0F
            if opcode == 0x08:  # Close frame
                break

            # Extract payload
            payload_length = data[1] & 0x7F
            offset = 2

            if payload_length == 126:
                payload_length = int.from_bytes(data[2:4], 'big')
                offset = 4
            elif payload_length == 127:
                payload_length = int.from_bytes(data[2:10], 'big')
                offset = 10

            payload = data[offset:offset+payload_length].decode('utf-8')

            try:
                response_data = json.loads(payload)

                if response_data.get('type') == 'status':
                    print(f"[STATUS] {response_data.get('message')}")
                elif response_data.get('type') == 'chunk':
                    chunk_text = response_data.get('data', '')
                    print(chunk_text, end='', flush=True)
                    full_response += chunk_text
                    chunk_count += 1
                elif response_data.get('type') == 'complete':
                    print("\n" + "-" * 60)
                    print(f"✅ Complete! ({chunk_count} chunks)")
                    break
                elif response_data.get('type') == 'error':
                    print(f"\n❌ Error: {response_data.get('message')}")
                    break

            except json.JSONDecodeError:
                print(f"Raw: {payload}")

        except socket.timeout:
            print("\n⏱️  Timeout")
            break

    return full_response, chunk_count


def test_tool(host, path, question, session_id, description):
    """Test a specific tool via WebSocket"""
    print(f"\n{'=' * 60}")
    print(f"🧪 Test: {description}")
    print(f"{'=' * 60}")

    # Create socket and wrap with SSL
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(sock, server_hostname=host)

    try:
        wrapped_socket.connect((host, 443))
        print("✅ Connected!")

        # Perform handshake
        handshake_request, key = websocket_handshake(host, path)
        wrapped_socket.send(handshake_request)

        # Read handshake response
        response = wrapped_socket.recv(4096).decode()
        if "101 Switching Protocols" in response:
            print("✅ WebSocket handshake successful!")
        else:
            print(f"❌ Handshake failed: {response}")
            return False

        # Send message
        message = {
            "question": question,
            "sessionId": session_id
        }

        print(f"\n📤 Question: {question}")
        print(f"   Session: {session_id}\n")

        send_websocket_message(wrapped_socket, None, message)

        print("💬 Response:")
        print("-" * 60)

        # Read responses
        full_response, chunk_count = receive_websocket_response(wrapped_socket)

        print(f"\n📊 Summary:")
        print(f"   Chunks: {chunk_count}")
        print(f"   Length: {len(full_response)} chars")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        wrapped_socket.close()
        print("🔌 Connection closed")


def main():
    """Test both Knowledge Base and Project Info tools"""
    host = "1j1xzo7n4h.execute-api.us-east-1.amazonaws.com"
    path = "/dev"

    print("\n" + "=" * 60)
    print("🚀 ProcessApp Agent - Tool Testing")
    print("=" * 60)
    print(f"WebSocket: wss://{host}{path}")
    print()

    # Test 1: Knowledge Base Search
    test_tool(
        host, path,
        question="What documents do you have in the knowledge base?",
        session_id=str(uuid.uuid4()),
        description="Knowledge Base Search Tool"
    )

    # Test 2: Project Info Tool
    test_tool(
        host, path,
        question="What is the information for organization 1 project 123?",
        session_id=str(uuid.uuid4()),
        description="Project Info Tool (ECS Service)"
    )

    # Test 3: Memory Test (same session)
    session_id = str(uuid.uuid4())

    print(f"\n{'=' * 60}")
    print("🧠 Test: Memory (2 messages, same session)")
    print(f"{'=' * 60}")

    test_tool(
        host, path,
        question="My name is Alice and I work on project 123",
        session_id=session_id,
        description="Memory Test - Set Context"
    )

    test_tool(
        host, path,
        question="What is my name and which project do I work on?",
        session_id=session_id,
        description="Memory Test - Recall Context"
    )

    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
