#!/bin/bash

# Test Agent V2 tool usage via WebSocket

WS_URL="wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev"

echo "Testing Agent V2 with metadata filtering..."
echo "================================================"
echo ""

# Test 1: Basic query with tenant 1001 (Champions League)
echo "Test 1: Basic query with tenant 1001"
echo "Expected: Should search KB and find Champions League info"
echo ""

cat << 'EOF' | wscat -c "$WS_URL" -w 5
{"action":"sendMessage","data":{"inputText":"Hola, ¿qué información tienes disponible?","sessionId":"test-tools-001","tenant_id":"1001","project_id":"5001","knowledge_type":"specific","user_roles":["admin"]}}
EOF

echo ""
echo "================================================"
echo ""

# Test 2: Specific query about Real Madrid
echo "Test 2: Specific query about Real Madrid"
echo "Expected: Should use search_knowledge_base tool"
echo ""

cat << 'EOF' | wscat -c "$WS_URL" -w 5
{"action":"sendMessage","data":{"inputText":"¿Cuál es el récord de Real Madrid en semifinales?","sessionId":"test-tools-002","tenant_id":"1001","project_id":"5001","knowledge_type":"specific","user_roles":["admin"]}}
EOF

echo ""
echo "================================================"
echo ""

# Test 3: Query about normative framework
echo "Test 3: Normative framework query"
echo "Expected: Should use search_normative_framework tool"
echo ""

cat << 'EOF' | wscat -c "$WS_URL" -w 5
{"action":"sendMessage","data":{"inputText":"¿Qué leyes regulan las pensiones en Colombia?","sessionId":"test-tools-003","tenant_id":"1001","knowledge_type":"generic","user_roles":["admin"]}}
EOF

echo ""
echo "================================================"
echo "Tests complete. Check if agent used tools in CloudWatch:"
echo "aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super"
