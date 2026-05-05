#!/bin/bash
# Stop ProcessApp Agent Docker container

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CONTAINER_NAME="processapp-agent-local"

echo -e "${YELLOW}🛑 Stopping ProcessApp Agent container...${NC}"

if docker ps | grep -q "${CONTAINER_NAME}"; then
    docker stop "${CONTAINER_NAME}"
    echo -e "${GREEN}✅ Container stopped${NC}"
else
    echo "No running container found"
fi
