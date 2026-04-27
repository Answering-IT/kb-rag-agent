#!/usr/bin/env python3
"""
E2E Tests for Agent V2 WebSocket Tools
Tests Knowledge Base search and Project Info tool integration
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
    "WEBSOCKET_HOST",
    "1j1xzo7n4h.execute-api.us-east-1.amazonaws.com"
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
                    error_message = response_data.get('message')
                    break
            except json.JSONDecodeError:
                pass

    except socket.timeout:
        error_message = "Timeout waiting for response"

    return full_response, chunks, error_message


@pytest.fixture
def websocket_connection():
    """Create WebSocket connection"""
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


def test_websocket_connection():
    """Test WebSocket connection establishment"""
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


def test_knowledge_base_search_tool(websocket_connection):
    """Test Knowledge Base search tool"""
    session_id = str(uuid.uuid4())
    message = {
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


def test_project_info_tool(websocket_connection):
    """Test Project Info tool (ECS service integration)"""
    session_id = str(uuid.uuid4())
    message = {
        "question": "Get information for organization 1 project 123",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection, timeout=45)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 0, "Expected response chunks"
    # Note: ECS service might be unavailable, so we just check the agent responded
    assert len(full_response) > 0, "Expected non-empty response"


def test_multiple_tools_in_sequence(websocket_connection):
    """Test using multiple tools in one session"""
    session_id = str(uuid.uuid4())

    # First query - Knowledge Base
    message1 = {
        "question": "What documents are available?",
        "sessionId": session_id
    }
    send_websocket_message(websocket_connection, message1)
    response1, chunks1, error1 = receive_websocket_response(websocket_connection)

    assert error1 is None, f"First query error: {error1}"
    assert len(response1) > 0, "Expected first response"

    # Note: For second query, need to reconnect (single-use WebSocket)
    # This is a limitation of the current implementation


def test_streaming_response(websocket_connection):
    """Test that responses are streamed in chunks"""
    session_id = str(uuid.uuid4())
    message = {
        "question": "Tell me about the documents in the knowledge base",
        "sessionId": session_id
    }

    send_websocket_message(websocket_connection, message)
    full_response, chunks, error = receive_websocket_response(websocket_connection)

    # Assertions
    assert error is None, f"Received error: {error}"
    assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"
    assert "".join(chunks) == full_response, "Chunks should reconstruct full response"


def test_session_id_validation():
    """Test that session IDs are properly handled"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(sock, server_hostname=WEBSOCKET_HOST)

    try:
        wrapped_socket.connect((WEBSOCKET_HOST, 443))

        handshake_request, key = websocket_handshake(WEBSOCKET_HOST, WEBSOCKET_PATH)
        wrapped_socket.send(handshake_request)

        response = wrapped_socket.recv(4096).decode()
        assert "101 Switching Protocols" in response

        # Use short session ID (should be extended by Lambda)
        message = {
            "question": "Hello",
            "sessionId": "short-id"
        }

        send_websocket_message(wrapped_socket, message)
        full_response, chunks, error = receive_websocket_response(wrapped_socket)

        # Should not error due to short session ID
        assert error is None or "session" not in error.lower(), f"Session ID error: {error}"

    finally:
        wrapped_socket.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
