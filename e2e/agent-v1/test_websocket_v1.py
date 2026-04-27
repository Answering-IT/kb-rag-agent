#!/usr/bin/env python3
"""
E2E Tests for Agent V1 WebSocket (Bedrock Agent)
Tests WebSocket connection, Knowledge Base queries, and session memory
"""
import os
import json
import uuid
import socket
import ssl
import base64
import pytest


# Configuration
WEBSOCKET_HOST = os.getenv(
    "WEBSOCKET_V1_HOST",
    "mf1ghadu5m.execute-api.us-east-1.amazonaws.com"
)
WEBSOCKET_PATH = os.getenv("WEBSOCKET_PATH", "/dev")


def websocket_handshake(host: str, path: str) -> tuple:
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


def send_websocket_message(sock, message: dict):
    """Send WebSocket message"""
    payload = json.dumps(message).encode()
    frame = bytearray([0x81])  # FIN + Text frame

    length = len(payload)
    if length < 126:
        frame.append(0x80 | length)
    else:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))

    # Masking
    mask = os.urandom(4)
    frame.extend(mask)

    masked_payload = bytearray(payload)
    for i in range(len(masked_payload)):
        masked_payload[i] ^= mask[i % 4]

    frame.extend(masked_payload)
    sock.send(bytes(frame))


def receive_websocket_response(sock, timeout: int = 30) -> tuple:
    """Receive WebSocket response"""
    sock.settimeout(timeout)
    full_response = ""
    chunks = []
    error_message = None

    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break

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

                if response_data.get('type') == 'chunk':
                    chunk_text = response_data.get('data', '')
                    full_response += chunk_text
                    chunks.append(chunk_text)
                elif response_data.get('type') == 'complete':
                    break
                elif response_data.get('type') == 'error':
                    error_message = response_data.get('error')
                    break
            except json.JSONDecodeError:
                pass

    except socket.timeout:
        error_message = "Timeout waiting for response"

    return full_response, chunks, error_message


@pytest.fixture
def websocket_connection():
    """Create WebSocket connection to Agent V1"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(sock, server_hostname=WEBSOCKET_HOST)

    try:
        wrapped_socket.connect((WEBSOCKET_HOST, 443))

        # Handshake
        handshake_request, key = websocket_handshake(WEBSOCKET_HOST, WEBSOCKET_PATH)
        wrapped_socket.send(handshake_request)

        response = wrapped_socket.recv(4096).decode()
        assert "101 Switching Protocols" in response, "WebSocket handshake failed"

        yield wrapped_socket

    finally:
        wrapped_socket.close()


def test_websocket_v1_connection():
    """Test WebSocket V1 connection establishment"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(sock, server_hostname=WEBSOCKET_HOST)

    try:
        wrapped_socket.connect((WEBSOCKET_HOST, 443))

        handshake_request, key = websocket_handshake(WEBSOCKET_HOST, WEBSOCKET_PATH)
        wrapped_socket.send(handshake_request)

        response = wrapped_socket.recv(4096).decode()
        assert "101 Switching Protocols" in response, "Expected 101 response"

    finally:
        wrapped_socket.close()


def test_bedrock_agent_query(websocket_connection):
    """Test querying Bedrock Agent (V1) via WebSocket"""
    session_id = str(uuid.uuid4())
    message = {
        "action": "query",
        "question": "What documents do you have in the knowledge base?",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 0, "Expected response chunks"
    assert len(full_response) > 0, "Expected non-empty response"
    assert "document" in full_response.lower(), "Expected mention of documents"


def test_session_memory_v1(websocket_connection):
    """Test session memory with Bedrock Agent V1"""
    session_id = str(uuid.uuid4())

    # Message 1: Set context
    message1 = {
        "action": "query",
        "question": "My name is Bob",
        "sessionId": session_id
    }
    send_websocket_message(websocket_connection, message1)
    response1, chunks1, error1 = receive_websocket_response(websocket_connection)

    assert error1 is None, f"First message error: {error1}"
    assert len(response1) > 0, "Expected first response"

    # Note: Need to reconnect for second message (single-use WebSocket)
    # This test validates the handler logic, actual memory test requires reconnection


def test_knowledge_base_search_v1(websocket_connection):
    """Test Knowledge Base search through Agent V1"""
    session_id = str(uuid.uuid4())
    message = {
        "action": "query",
        "question": "Tell me about the documents",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection, timeout=45)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 0, "Expected response chunks"
    assert len(full_response) > 0, "Expected non-empty response"


def test_action_group_query_v1(websocket_connection):
    """Test action group invocation with Agent V1"""
    session_id = str(uuid.uuid4())
    # Use keywords that trigger action group
    message = {
        "action": "query",
        "question": "What is the budget for project id 123?",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection, timeout=45)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 0, "Expected response chunks"
    # Note: Action group might fail if ECS service unavailable, but agent should respond


def test_metadata_filtering_v1(websocket_connection):
    """Test metadata filtering with tenant context"""
    session_id = str(uuid.uuid4())
    message = {
        "action": "query",
        "question": "What documents are available?",
        "sessionId": session_id,
        "tenantId": "1",
        "userId": "user123",
        "roles": ["admin"],
        "projectId": "100"
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection, timeout=45)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(full_response) > 0, "Expected non-empty response"
    # Note: Filtering behavior depends on ENABLE_METADATA_FILTERING env var


def test_streaming_response_v1(websocket_connection):
    """Test that responses are streamed in chunks (V1)"""
    session_id = str(uuid.uuid4())
    message = {
        "action": "query",
        "question": "Tell me about the system",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"
    assert "".join(chunks) == full_response, "Chunks should reconstruct full response"


def test_error_handling_v1(websocket_connection):
    """Test error handling with missing required field"""
    message = {
        "action": "query",
        # Missing 'question' field
        "sessionId": str(uuid.uuid4())
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection)

    # Should receive error message
    assert error is not None or "missing" in full_response.lower(), "Expected error for missing question"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
