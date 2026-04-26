#!/bin/bash
# Simple WebSocket test using wscat
# Install wscat first: npm install -g wscat

WS_URL="wss://mf1ghadu5m.execute-api.us-east-1.amazonaws.com/dev"

echo "================================"
echo "WEBSOCKET STREAMING TEST"
echo "================================"
echo ""
echo "WebSocket URL: $WS_URL"
echo ""
echo "To test manually:"
echo "  1. Install wscat: npm install -g wscat"
echo "  2. Connect: wscat -c $WS_URL"
echo "  3. Send message:"
echo ""
echo "     {\"action\":\"query\",\"question\":\"What is Colpensiones?\",\"tenantId\":\"1\",\"userId\":\"user1\",\"roles\":[\"viewer\"]}"
echo ""
echo "  4. Watch for streaming chunks in real-time"
echo ""

# Check if wscat is installed
if command -v wscat &> /dev/null; then
    echo "✅ wscat is installed"
    echo ""
    echo "Starting interactive WebSocket connection..."
    echo "Paste the message above after connecting."
    echo ""
    wscat -c $WS_URL
else
    echo "⚠️  wscat is not installed"
    echo ""
    echo "Install with: npm install -g wscat"
fi
