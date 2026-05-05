#!/bin/bash
# Run Agent Locally - Start FastAPI server with local configuration
# Requires: ./scripts/local_setup.sh to be run first

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Get script directory and navigate to agents root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="$(dirname "$SCRIPT_DIR")"
cd "$AGENTS_DIR"

echo -e "${GREEN}🚀 ProcessApp Agent v2.0 - Local Runner${NC}"
echo "=========================================="

# Check if we're in the agents directory
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ Error: main.py not found${NC}"
    echo "Run this script from the agents/ directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found${NC}"
    echo "   Run ./scripts/local_setup.sh first"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Get Knowledge Base ID from AWS (requires ans-super profile)
echo "🔍 Getting Knowledge Base ID from AWS..."
export AWS_PROFILE="${AWS_PROFILE:-ans-super}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

KB_ID=$(aws bedrock-agent list-knowledge-bases \
    --query 'knowledgeBaseSummaries[?contains(name, `processapp`)].knowledgeBaseId' \
    --output text \
    --profile $AWS_PROFILE \
    --region $AWS_REGION 2>/dev/null | head -1)

if [ -z "$KB_ID" ]; then
    echo -e "${YELLOW}⚠️  Warning: Could not fetch Knowledge Base ID from AWS${NC}"
    echo "   Using hardcoded ID from CLAUDE.md"
    KB_ID="R80HXGRLHO"
fi

echo -e "${GREEN}✅ Knowledge Base ID: $KB_ID${NC}"

# Set environment variables
export KNOWLEDGE_BASE_ID="$KB_ID"
export KB_ID="$KB_ID"
export MODEL_ID="${MODEL_ID:-amazon.nova-pro-v1:0}"
export PORT="${PORT:-8080}"
export DEBUG="${DEBUG:-false}"

echo ""
echo "📋 Configuration:"
echo "   AWS Profile: $AWS_PROFILE"
echo "   AWS Region: $AWS_REGION"
echo "   Knowledge Base: $KB_ID"
echo "   Model: $MODEL_ID"
echo "   Port: $PORT"
echo "   Debug: $DEBUG"
echo ""

echo -e "${GREEN}🚀 Starting FastAPI server...${NC}"
echo "   Health check: http://localhost:$PORT/health"
echo "   Invocations: http://localhost:$PORT/invocations (POST)"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

# Run the agent
python3 main.py
