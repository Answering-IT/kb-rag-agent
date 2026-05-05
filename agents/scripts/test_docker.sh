#!/bin/bash
# Test Docker container with different filter scenarios

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PORT=8080
BASE_URL="http://localhost:$PORT"

echo -e "${BLUE}🧪 ProcessApp Agent - Docker Testing Suite${NC}"
echo "=============================================="
echo ""

# Test 1: Health check
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test 1: Health Check${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
curl -s "${BASE_URL}/health" | python3 -m json.tool
echo ""

# Test 2: No filters
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test 2: No Filters (Unrestricted)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Request:"
cat <<'EOF' | tee /tmp/test_req.json
{
  "inputText": "Hola, ¿cómo puedes ayudarme?",
  "sessionId": "docker-test-1"
}
EOF

echo ""
echo -e "${GREEN}Response:${NC}"
curl -s -X POST "${BASE_URL}/invocations" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_req.json \
  | while IFS= read -r line; do
      echo "$line" | python3 -c "import sys, json; data = json.loads(sys.stdin.read()); print(data.get('data', ''), end='')" 2>/dev/null
    done
echo ""

# Test 3: Tenant only
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test 3: Tenant Filter (tenant_id=1001)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Request:"
cat <<'EOF' | tee /tmp/test_req.json
{
  "inputText": "¿Qué información tienes disponible?",
  "sessionId": "docker-test-2",
  "metadata": {
    "tenant_id": "1001"
  }
}
EOF

echo ""
echo -e "${GREEN}Response:${NC}"
curl -s -X POST "${BASE_URL}/invocations" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_req.json \
  | while IFS= read -r line; do
      echo "$line" | python3 -c "import sys, json; data = json.loads(sys.stdin.read()); print(data.get('data', ''), end='')" 2>/dev/null
    done
echo ""

# Test 4: Tenant + Project
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test 4: Tenant + Project Filter${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Expected partition_key: t1001_p165"
echo ""
echo "Request:"
cat <<'EOF' | tee /tmp/test_req.json
{
  "inputText": "¿Qué hay en el proyecto 165?",
  "sessionId": "docker-test-3",
  "metadata": {
    "tenant_id": "1001",
    "project_id": "165"
  }
}
EOF

echo ""
echo -e "${GREEN}Response:${NC}"
curl -s -X POST "${BASE_URL}/invocations" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_req.json \
  | while IFS= read -r line; do
      echo "$line" | python3 -c "import sys, json; data = json.loads(sys.stdin.read()); print(data.get('data', ''), end='')" 2>/dev/null
    done
echo ""

# Test 5: Tenant + Project + Task
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test 5: Tenant + Project + Task Filter${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Expected partition_key: t1001_p165_t174"
echo ""
echo "Request:"
cat <<'EOF' | tee /tmp/test_req.json
{
  "inputText": "¿Qué documentos hay en la tarea 174?",
  "sessionId": "docker-test-4",
  "metadata": {
    "tenant_id": "1001",
    "project_id": "165",
    "task_id": "174"
  }
}
EOF

echo ""
echo -e "${GREEN}Response:${NC}"
curl -s -X POST "${BASE_URL}/invocations" \
  -H "Content-Type: application/json" \
  -d @/tmp/test_req.json \
  | while IFS= read -r line; do
      echo "$line" | python3 -c "import sys, json; data = json.loads(sys.stdin.read()); print(data.get('data', ''), end='')" 2>/dev/null
    done
echo ""

# Show filter logs
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Filter Logs (from container)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Last filter built:"
docker logs processapp-agent-local 2>&1 | grep -A 20 "Filter.*Built.*{" | tail -25

echo ""
echo -e "${GREEN}✅ All tests completed!${NC}"
echo ""
echo "To view full logs: docker logs -f processapp-agent-local"
echo "To stop container: ./scripts/docker_stop.sh"
echo ""

# Cleanup
rm -f /tmp/test_req.json
