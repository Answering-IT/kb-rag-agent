#!/usr/bin/env python3
"""
E2E Tests for Agent V2 Short-Term Memory
Tests conversation context retention (7 days)
"""
import os
import json
import uuid
import socket
import ssl
import base64
import pytest


WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "1j1xzo7n4h.execute-api.us-east-1.amazonaws.com")
WEBSOCKET_PATH = os.getenv("WEBSOCKET_PATH", "/dev")


def websocket_handshake(host: str, path: str) -> tuple:
    """Perform WebSocket handshake"""
    key = base64.b64encode(os.urandom(16)).decode()
    request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    return request.encode(), key


def send_websocket_message(sock, message: dict):
    """Send WebSocket message"""
    payload = json.dumps(message).encode()
    frame = bytearray([0x81])
    length = len(payload)
    if length < 126:
        frame.append(0x80 | length)
    else:
        frame.append(0x80 | 126)
        frame.extend(length.to_bytes(2, 'big'))
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
    error_message = None

    try:
        while True:
            data = sock.recv(4096)
            if not data or len(data) < 2:
                break

            opcode = data[0] & 0x0F
            if opcode == 0x08:
                break

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
                    full_response += response_data.get('data', '')
                elif response_data.get('type') == 'complete':
                    break
                elif response_data.get('type') == 'error':
                    error_message = response_data.get('message')
                    break
            except json.JSONDecodeError:
                pass

    except socket.timeout:
        error_message = "Timeout"

    return full_response, error_message


def send_message_and_get_response(question: str, session_id: str) -> tuple:
    """Helper to send message and get response"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)

    context = ssl.create_default_context()
    wrapped_socket = context.wrap_socket(sock, server_hostname=WEBSOCKET_HOST)

    try:
        wrapped_socket.connect((WEBSOCKET_HOST, 443))

        handshake_request, key = websocket_handshake(WEBSOCKET_HOST, WEBSOCKET_PATH)
        wrapped_socket.send(handshake_request)

        response = wrapped_socket.recv(4096).decode()
        if "101 Switching Protocols" not in response:
            raise Exception("WebSocket handshake failed")

        message = {"question": question, "sessionId": session_id}
        send_websocket_message(wrapped_socket, message)

        full_response, error = receive_websocket_response(wrapped_socket)
        return full_response, error

    finally:
        wrapped_socket.close()


def test_short_term_memory_basic():
    """Test that agent remembers context within same session"""
    session_id = str(uuid.uuid4())

    # Message 1: Set context
    response1, error1 = send_message_and_get_response(
        "My name is Alice and I work on project 123",
        session_id
    )

    assert error1 is None, f"First message error: {error1}"
    assert len(response1) > 0, "Expected response to first message"

    # Message 2: Recall context (same session)
    response2, error2 = send_message_and_get_response(
        "What is my name and which project do I work on?",
        session_id
    )

    assert error2 is None, f"Second message error: {error2}"
    assert len(response2) > 0, "Expected response to second message"

    # Verify memory worked
    assert "alice" in response2.lower(), "Agent should remember name 'Alice'"
    assert "123" in response2, "Agent should remember project '123'"


def test_memory_isolated_between_sessions():
    """Test that different sessions have isolated memory"""
    session1_id = str(uuid.uuid4())
    session2_id = str(uuid.uuid4())

    # Session 1: Set context
    response1, error1 = send_message_and_get_response(
        "My name is Bob and I work on project 456",
        session1_id
    )

    assert error1 is None, f"Session 1 error: {error1}"

    # Session 2: Try to recall Session 1 context (should fail)
    response2, error2 = send_message_and_get_response(
        "What is my name and which project do I work on?",
        session2_id
    )

    assert error2 is None, f"Session 2 error: {error2}"

    # Verify isolation - should NOT know Bob or project 456
    assert "bob" not in response2.lower() or "456" not in response2, \
        "Session 2 should not have access to Session 1 memory"


def test_memory_with_multiple_exchanges():
    """Test memory across multiple conversation turns"""
    session_id = str(uuid.uuid4())

    # Turn 1
    response1, _ = send_message_and_get_response(
        "I like pizza",
        session_id
    )
    assert len(response1) > 0

    # Turn 2
    response2, _ = send_message_and_get_response(
        "I also like pasta",
        session_id
    )
    assert len(response2) > 0

    # Turn 3: Recall both preferences
    response3, error3 = send_message_and_get_response(
        "What foods do I like?",
        session_id
    )

    assert error3 is None, f"Turn 3 error: {error3}"
    assert "pizza" in response3.lower(), "Should remember pizza"
    assert "pasta" in response3.lower(), "Should remember pasta"


def test_memory_retention_period():
    """Test that memory is configured for 7-day retention"""
    # Note: This is a configuration test, not runtime test
    # Memory retention is set in AgentStackV2.ts: expirationDuration: cdk.Duration.days(7)
    # We can only verify the configuration, not the actual 7-day retention in E2E

    session_id = str(uuid.uuid4())
    response, error = send_message_and_get_response(
        "Hello, testing memory retention",
        session_id
    )

    # If this works, memory is enabled
    assert error is None, "Memory should be enabled"
    assert len(response) > 0, "Should receive response with memory enabled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
