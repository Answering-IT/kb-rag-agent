#!/bin/bash
# Manual WebSocket test using wscat
# Install: npm install -g wscat

WS_URL="wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

echo "=========================================="
echo "WebSocket Manual Test with wscat"
echo "=========================================="
echo ""
echo "WebSocket URL: $WS_URL"
echo ""
echo "Instructions:"
echo "  1. Connect with: wscat -c $WS_URL"
echo "  2. Copy-paste one of the test messages below"
echo ""
echo "=========================================="
echo "Test Messages:"
echo "=========================================="
echo ""

echo "--- Test 1: Tenant 1001 - Champions League (specific) ---"
cat << 'EOF'
{"action":"sendMessage","data":{"inputText":"¿Cuál es el récord de Real Madrid en semifinales de Champions League?","sessionId":"test-1001-champions","tenant_id":"1001","project_id":"5001","knowledge_type":"specific","user_roles":["admin","viewer"]}}
EOF
echo ""
echo ""

echo "--- Test 2: Tenant 1003 - Philosophy (specific) ---"
cat << 'EOF'
{"action":"sendMessage","data":{"inputText":"¿Qué es La República de Platón?","sessionId":"test-1003-philosophy","tenant_id":"1003","project_id":"6001","knowledge_type":"specific","user_roles":["admin","viewer"]}}
EOF
echo ""
echo ""

echo "--- Test 3: Tenant 1001 - Generic Knowledge (normative) ---"
cat << 'EOF'
{"action":"sendMessage","data":{"inputText":"¿Qué leyes regulan las pensiones en Colombia?","sessionId":"test-1001-normative","tenant_id":"1001","knowledge_type":"generic","user_roles":["admin"]}}
EOF
echo ""
echo ""

echo "--- Test 4: Tenant 1003 - Generic Knowledge (normative) ---"
cat << 'EOF'
{"action":"sendMessage","data":{"inputText":"¿Cuáles son las normativas sobre reforma pensional?","sessionId":"test-1003-normative","tenant_id":"1003","knowledge_type":"generic","user_roles":["viewer"]}}
EOF
echo ""
echo ""

echo "--- Test 5: Cross-tenant Isolation (should NOT find philosophy docs) ---"
cat << 'EOF'
{"action":"sendMessage","data":{"inputText":"¿Qué dice Platón sobre la justicia?","sessionId":"test-1001-isolation","tenant_id":"1001","project_id":"5001","knowledge_type":"specific","user_roles":["admin"]}}
EOF
echo ""
echo ""

echo "=========================================="
echo "To start testing:"
echo "=========================================="
echo "  wscat -c $WS_URL"
echo ""
echo "Then paste any message above and press Enter"
echo ""
echo "Press Ctrl+C to exit wscat"
echo "=========================================="
