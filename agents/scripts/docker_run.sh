#!/bin/bash
# Run ProcessApp Agent in Docker container

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🐳 Running ProcessApp Agent in Docker${NC}"
echo "========================================"
echo ""

# Image details
IMAGE_NAME="processapp-agent"
IMAGE_TAG="2.0.0"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"
CONTAINER_NAME="processapp-agent-local"

# Check if image exists
if ! docker images | grep -q "${IMAGE_NAME}"; then
    echo -e "${RED}❌ Error: Docker image not found${NC}"
    echo "Build it first with: ./scripts/docker_build.sh"
    exit 1
fi

# Get AWS credentials from profile
export AWS_PROFILE="${AWS_PROFILE:-ans-super}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

echo -e "${YELLOW}Fetching AWS credentials...${NC}"

# Get temporary credentials
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile $AWS_PROFILE)
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile $AWS_PROFILE)
AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile $AWS_PROFILE 2>/dev/null || echo "")

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo -e "${RED}❌ Error: Could not get AWS credentials from profile $AWS_PROFILE${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS credentials loaded${NC}"

# Get Knowledge Base ID
echo -e "${YELLOW}Fetching Knowledge Base ID...${NC}"
KB_ID=$(aws bedrock-agent list-knowledge-bases \
    --query 'knowledgeBaseSummaries[?contains(name, `processapp`)].knowledgeBaseId' \
    --output text \
    --profile $AWS_PROFILE \
    --region $AWS_REGION 2>/dev/null | head -1)

if [ -z "$KB_ID" ]; then
    echo -e "${YELLOW}⚠️  Warning: Could not fetch KB ID, using default${NC}"
    KB_ID="R80HXGRLHO"
fi

echo -e "${GREEN}✅ Knowledge Base ID: $KB_ID${NC}"

# Stop existing container if running
if docker ps -a | grep -q "${CONTAINER_NAME}"; then
    echo -e "${YELLOW}Stopping existing container...${NC}"
    docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1
fi

echo ""
echo -e "${GREEN}🚀 Starting container...${NC}"
echo ""
echo "Configuration:"
echo "  - Image: ${FULL_IMAGE}"
echo "  - Container: ${CONTAINER_NAME}"
echo "  - Port: 8080 → 8080"
echo "  - KB ID: ${KB_ID}"
echo "  - Region: ${AWS_REGION}"
echo ""

# Run the container
docker run -d \
  --name "${CONTAINER_NAME}" \
  --rm \
  -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
  -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
  -e AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN}" \
  -e AWS_REGION="${AWS_REGION}" \
  -e KB_ID="${KB_ID}" \
  -e MODEL_ID="amazon.nova-pro-v1:0" \
  -e PORT="8080" \
  -e DEBUG="true" \
  "${FULL_IMAGE}"

echo -e "${GREEN}✅ Container started!${NC}"
echo ""
echo "Available at:"
echo "  - Health check: http://localhost:8080/health"
echo "  - Invocations: http://localhost:8080/invocations"
echo ""
echo "Commands:"
echo "  - View logs: docker logs -f ${CONTAINER_NAME}"
echo "  - Stop: docker stop ${CONTAINER_NAME}"
echo "  - Test: ./scripts/test_local.sh"
echo ""

# Wait a moment for container to start
sleep 3

# Show initial logs
echo -e "${BLUE}Container logs (last 20 lines):${NC}"
docker logs --tail 20 "${CONTAINER_NAME}"
echo ""

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
sleep 2

if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Agent is healthy!${NC}"
    echo ""
    curl -s http://localhost:8080/health | python3 -m json.tool
else
    echo -e "${RED}⚠️  Health check failed, container may still be starting...${NC}"
    echo "Check logs with: docker logs -f ${CONTAINER_NAME}"
fi

echo ""
echo -e "${GREEN}Ready to test!${NC}"
echo "Run: ./scripts/test_local.sh"
