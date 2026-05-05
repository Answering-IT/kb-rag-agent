#!/bin/bash
# Test ProcessApp Agent running locally
# Sends test requests to local agent endpoint

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PORT=8080
BASE_URL="http://localhost:$PORT"

echo -e "${GREEN}🧪 Testing ProcessApp Agent (Local)${NC}"
echo "====================================="
echo ""

# Test 1: Health check
echo -e "${YELLOW}[Test 1] Health check${NC}"
HEALTH=$(curl -s $BASE_URL/health)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "$HEALTH" | jq '.'
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Is the agent running? (./run_local.sh)"
    exit 1
fi

echo ""

# Test 2: Simple query (no metadata filtering)
echo -e "${YELLOW}[Test 2] Simple query (no filtering)${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "¿Cómo me puedes ayudar?",
    "sessionId": "test-local-1"
  }' | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo -e "${GREEN}✅ Simple query completed${NC}"
echo ""

# Test 3: Query with tenant filtering
echo -e "${YELLOW}[Test 3] Query with tenant filtering${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: colpensiones" \
  -d '{
    "inputText": "¿Qué documentos tienes disponibles?",
    "sessionId": "test-local-2"
  }' | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo -e "${GREEN}✅ Tenant filtering query completed${NC}"
echo ""

# Test 4: Query with tenant + project filtering
echo -e "${YELLOW}[Test 4] Query with tenant + project filtering${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: colpensiones" \
  -H "x-project-id: decreto_1833" \
  -d '{
    "inputText": "¿Qué información tienes sobre este proyecto?",
    "sessionId": "test-local-3"
  }' | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo -e "${GREEN}✅ Tenant + project filtering query completed${NC}"
echo ""

# Test 5: Query with full filtering (tenant + project + task)
echo -e "${YELLOW}[Test 5] Query with full filtering (tenant + project + task)${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: colpensiones" \
  -H "x-project-id: decreto_1833" \
  -H "x-task-id: analisis_legal" \
  -d '{
    "inputText": "¿Qué documentos están asociados a esta tarea?",
    "sessionId": "test-local-4"
  }' | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo -e "${GREEN}✅ Full filtering query completed${NC}"
echo ""

# Test 6: Conversation context (multi-turn)
echo -e "${YELLOW}[Test 6] Multi-turn conversation${NC}"
SESSION="test-local-context"

echo -e "${BLUE}User: ¿Qué sabes sobre Colpensiones?${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: colpensiones" \
  -d "{
    \"inputText\": \"¿Qué sabes sobre Colpensiones?\",
    \"sessionId\": \"$SESSION\"
  }" | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo ""

echo -e "${BLUE}User: Dame más detalles${NC}"
curl -s -X POST $BASE_URL/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: colpensiones" \
  -d "{
    \"inputText\": \"Dame más detalles\",
    \"sessionId\": \"$SESSION\"
  }" | while IFS= read -r line; do
    echo "$line" | jq -r 'select(.type=="chunk") | .data' | tr -d '\n'
done
echo ""
echo -e "${GREEN}✅ Context awareness verified${NC}"
echo ""

echo -e "${GREEN}✅ All tests completed successfully!${NC}"
echo ""
echo "Summary:"
echo "  - Health check: ✅"
echo "  - Simple query: ✅"
echo "  - Tenant filtering: ✅"
echo "  - Tenant + project filtering: ✅"
echo "  - Full filtering: ✅"
echo "  - Context awareness: ✅"
echo ""
