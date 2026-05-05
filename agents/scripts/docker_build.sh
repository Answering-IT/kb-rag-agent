#!/bin/bash
# Build Docker image for ProcessApp Agent v2.0

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory and navigate to agents root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(dirname "$SCRIPT_DIR")"
cd "$AGENTS_DIR"

echo -e "${BLUE}🐳 Building ProcessApp Agent Docker Image${NC}"
echo "==========================================="
echo ""

# Image details
IMAGE_NAME="processapp-agent"
IMAGE_TAG="2.0.0"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo -e "${YELLOW}Building image: ${FULL_IMAGE}${NC}"
echo ""

# Build the image
docker build \
  --tag "${FULL_IMAGE}" \
  --tag "${IMAGE_NAME}:latest" \
  --file Dockerfile \
  --progress=plain \
  .

echo ""
echo -e "${GREEN}✅ Docker image built successfully!${NC}"
echo ""
echo "Image details:"
docker images | grep "${IMAGE_NAME}" | head -2
echo ""
echo "To run the container:"
echo "  ./scripts/docker_run.sh"
echo ""
echo "To inspect the image:"
echo "  docker run --rm -it ${FULL_IMAGE} /bin/bash"
