#!/bin/bash
#
# Automated Test Runner for ProcessApp Agent
# Builds Docker container, runs tests, and displays results
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="agent-test"
IMAGE_NAME="processapp-agent:test"
AGENT_PORT=8080
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🧪 PROCESSAPP AGENT - AUTOMATED TEST RUNNER${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Cleanup existing container
echo -e "${YELLOW}[1/5] Cleaning up existing containers...${NC}"
if docker ps -a | grep -q $CONTAINER_NAME; then
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    echo -e "  ${GREEN}✅ Removed old container${NC}"
else
    echo -e "  ${GREEN}✅ No existing container to clean${NC}"
fi
echo ""

# Step 2: Build Docker image
echo -e "${YELLOW}[2/5] Building Docker image...${NC}"
cd "$PROJECT_ROOT/agents"
if docker build -t $IMAGE_NAME . -q > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "  ${RED}❌ Docker build failed${NC}"
    exit 1
fi
cd "$PROJECT_ROOT"
echo ""

# Step 3: Start container
echo -e "${YELLOW}[3/5] Starting agent container...${NC}"
CONTAINER_ID=$(docker run -d \
    -p $AGENT_PORT:$AGENT_PORT \
    -e AWS_PROFILE=ans-super \
    -e AWS_REGION=us-east-1 \
    -e KB_ID=BLJTRDGQI0 \
    -e MODEL_ID=amazon.nova-pro-v1:0 \
    -v ~/.aws:/root/.aws:ro \
    --name $CONTAINER_NAME \
    $IMAGE_NAME 2>&1)

if [ $? -ne 0 ]; then
    echo -e "  ${RED}❌ Failed to start container${NC}"
    exit 1
fi

echo -e "  ${GREEN}✅ Container started (ID: ${CONTAINER_ID:0:12})${NC}"
echo -e "  ⏳ Waiting for agent to be ready..."
sleep 8
echo ""

# Step 4: Verify agent health
echo -e "${YELLOW}[4/5] Verifying agent health...${NC}"
HEALTH_CHECK=$(curl -s http://localhost:$AGENT_PORT/health | jq -r '.status' 2>/dev/null || echo "unhealthy")
if [ "$HEALTH_CHECK" = "healthy" ]; then
    echo -e "  ${GREEN}✅ Agent is healthy and ready${NC}"
else
    echo -e "  ${RED}❌ Agent health check failed${NC}"
    echo -e "  ${YELLOW}Showing container logs:${NC}"
    docker logs $CONTAINER_NAME | tail -20
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi
echo ""

# Step 5: Run tests
echo -e "${YELLOW}[5/5] Running hierarchical fallback tests...${NC}"
echo ""
python3 "$SCRIPT_DIR/test-hierarchical-fallback.py" 2>&1 | tee /tmp/test-results-$(date +%Y%m%d-%H%M%S).txt

# Capture test exit code
TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

# Step 6: Cleanup (optional)
read -p "$(echo -e ${YELLOW}Clean up test container? [Y/n]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    docker stop $CONTAINER_NAME > /dev/null 2>&1
    docker rm $CONTAINER_NAME > /dev/null 2>&1
    echo -e "${GREEN}✅ Container cleaned up${NC}"
else
    echo -e "${BLUE}ℹ️  Container '$CONTAINER_NAME' still running on port $AGENT_PORT${NC}"
    echo -e "${BLUE}   To view logs: docker logs $CONTAINER_NAME${NC}"
    echo -e "${BLUE}   To stop: docker stop $CONTAINER_NAME && docker rm $CONTAINER_NAME${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════════════════════${NC}"

# Exit with test result code
exit $TEST_EXIT_CODE
