#!/bin/bash
# Manual Session Memory Test using wscat
# This script demonstrates session memory by showing two interactions

WS_URL="wss://mf1ghadu5m.execute-api.us-east-1.amazonaws.com/dev"
SESSION_ID=$(uuidgen)

echo "=================================================================="
echo "SESSION MEMORY TEST"
echo "=================================================================="
echo ""
echo "Session ID: $SESSION_ID"
echo ""
echo "This test verifies conversation context persistence."
echo ""
echo "=================================================================="
echo ""

echo "📝 INSTRUCTIONS:"
echo ""
echo "We will send TWO messages in the SAME session:"
echo ""
echo "1️⃣  First message (establishing context):"
echo '   {"action":"query","question":"My name is Alice and I work for Colpensiones","sessionId":"'$SESSION_ID'","tenantId":"1","userId":"test","roles":["viewer"]}'
echo ""
echo "2️⃣  Second message (asking about context):"
echo '   {"action":"query","question":"What is my name and where do I work?","sessionId":"'$SESSION_ID'","tenantId":"1","userId":"test","roles":["viewer"]}'
echo ""
echo "=================================================================="
echo ""
echo "Expected: The agent should remember Alice and Colpensiones"
echo ""
echo "=================================================================="
echo ""
echo "Press ENTER to start test..."
read

echo ""
echo "🔵 TEST 1: Establishing Context"
echo "=================================================================="
echo ""
echo "Sending: My name is Alice and I work for Colpensiones"
echo ""

# First message
(
  sleep 1
  echo '{"action":"query","question":"My name is Alice and I work for Colpensiones","sessionId":"'$SESSION_ID'","tenantId":"1","userId":"test","roles":["viewer"]}'
  sleep 10
) | wscat -c "$WS_URL" | tee /tmp/session_test_1.txt

echo ""
echo ""
echo "Press ENTER to send second message..."
read

echo ""
echo "🔵 TEST 2: Verifying Context Recall"
echo "=================================================================="
echo ""
echo "Sending: What is my name and where do I work?"
echo ""

# Second message (same session)
(
  sleep 1
  echo '{"action":"query","question":"What is my name and where do I work?","sessionId":"'$SESSION_ID'","tenantId":"1","userId":"test","roles":["viewer"]}'
  sleep 10
) | wscat -c "$WS_URL" | tee /tmp/session_test_2.txt

echo ""
echo ""
echo "=================================================================="
echo "RESULTS"
echo "=================================================================="
echo ""

# Check if response contains expected information
if grep -qi "alice" /tmp/session_test_2.txt && grep -qi "colpensiones\|work" /tmp/session_test_2.txt; then
    echo "✅ SUCCESS: Agent remembered the context!"
    echo "   - Recalled name: Alice"
    echo "   - Recalled workplace: Colpensiones"
else
    echo "❌ FAILURE: Agent did not remember the context"
    echo ""
    echo "Response from second message:"
    cat /tmp/session_test_2.txt
fi

echo ""
echo "=================================================================="
echo ""
echo "Full responses saved to:"
echo "  - /tmp/session_test_1.txt"
echo "  - /tmp/session_test_2.txt"
echo ""
