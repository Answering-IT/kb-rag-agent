#!/bin/bash
###############################################################################
# ProcessApp RAG Agent - E2E Test Runner
#
# Runs all E2E tests for the ProcessApp RAG Agent system:
# - Document ingestion pipeline
# - Agent V1 (Bedrock Agent with WebSocket)
# - Agent V2 (Agent Core Runtime with Strand SDK)
# - Knowledge Base queries
###############################################################################

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
E2E_DIR="${PROJECT_ROOT}/e2e"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        ProcessApp RAG Agent - E2E Test Suite Runner           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 not found. Please install Python 3.11+${NC}"
    exit 1
fi

if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${RED}❌ pytest not installed${NC}"
    echo -e "${YELLOW}   Please install: python3 -m pip install pytest pytest-asyncio${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites OK${NC}"
echo ""

# Display configuration
echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "   Project root: ${PROJECT_ROOT}"
echo "   E2E tests:    ${E2E_DIR}"
echo "   AWS Profile:  ${AWS_PROFILE:-default}"
echo "   AWS Region:   ${AWS_REGION:-us-east-1}"
echo ""

# Parse command line arguments
RUN_INGESTION=true
RUN_AGENT_V1=true
RUN_AGENT_V2=true
RUN_KB=false
VERBOSE=false
STOP_ON_FAIL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --ingestion)
      RUN_INGESTION=true
      RUN_AGENT_V1=false
      RUN_AGENT_V2=false
      RUN_KB=false
      shift
      ;;
    --agent-v1)
      RUN_INGESTION=false
      RUN_AGENT_V1=true
      RUN_AGENT_V2=false
      RUN_KB=false
      shift
      ;;
    --agent-v2)
      RUN_INGESTION=false
      RUN_AGENT_V1=false
      RUN_AGENT_V2=true
      RUN_KB=false
      shift
      ;;
    --kb)
      RUN_INGESTION=false
      RUN_AGENT_V1=false
      RUN_AGENT_V2=false
      RUN_KB=true
      shift
      ;;
    --all)
      RUN_INGESTION=true
      RUN_AGENT_V1=true
      RUN_AGENT_V2=true
      RUN_KB=true
      shift
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -x|--stop-on-fail)
      STOP_ON_FAIL=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --ingestion      Run only document ingestion tests"
      echo "  --agent-v1       Run only Agent V1 tests"
      echo "  --agent-v2       Run only Agent V2 tests"
      echo "  --kb             Run only Knowledge Base tests"
      echo "  --all            Run all tests (default: ingestion + agents)"
      echo "  -v, --verbose    Verbose output"
      echo "  -x, --stop-on-fail  Stop on first failure"
      echo "  -h, --help       Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                    # Run ingestion + agent tests"
      echo "  $0 --agent-v2         # Run only Agent V2 tests"
      echo "  $0 --all -v           # Run all tests with verbose output"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Build pytest command
PYTEST_ARGS="-v"
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -s"
fi
if [ "$STOP_ON_FAIL" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -x"
fi

# Track results
FAILED_SUITES=()
PASSED_SUITES=()

# Function to run test suite
run_test_suite() {
    local suite_name=$1
    local test_path=$2

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🧪 Running: ${suite_name}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if python3 -m pytest "${test_path}" ${PYTEST_ARGS}; then
        echo -e "${GREEN}✅ ${suite_name} - PASSED${NC}"
        PASSED_SUITES+=("$suite_name")
        return 0
    else
        echo -e "${RED}❌ ${suite_name} - FAILED${NC}"
        FAILED_SUITES+=("$suite_name")
        return 1
    fi
}

# Run selected test suites
START_TIME=$(date +%s)

if [ "$RUN_INGESTION" = true ]; then
    run_test_suite "Document Ingestion" "${E2E_DIR}/ingestion/" || true
fi

if [ "$RUN_AGENT_V1" = true ]; then
    run_test_suite "Agent V1 (Bedrock Agent)" "${E2E_DIR}/agent-v1/" || true
fi

if [ "$RUN_AGENT_V2" = true ]; then
    run_test_suite "Agent V2 (Agent Core Runtime)" "${E2E_DIR}/agent-v2/" || true
fi

if [ "$RUN_KB" = true ]; then
    if [ -d "${E2E_DIR}/knowledge-base" ] && [ -n "$(ls -A ${E2E_DIR}/knowledge-base 2>/dev/null)" ]; then
        run_test_suite "Knowledge Base" "${E2E_DIR}/knowledge-base/" || true
    else
        echo -e "${YELLOW}⚠️  Knowledge Base tests not implemented yet${NC}"
    fi
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Print summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Test Summary                              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ${#PASSED_SUITES[@]} -gt 0 ]; then
    echo -e "${GREEN}✅ Passed (${#PASSED_SUITES[@]}):${NC}"
    for suite in "${PASSED_SUITES[@]}"; do
        echo -e "   ${GREEN}✓${NC} $suite"
    done
    echo ""
fi

if [ ${#FAILED_SUITES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Failed (${#FAILED_SUITES[@]}):${NC}"
    for suite in "${FAILED_SUITES[@]}"; do
        echo -e "   ${RED}✗${NC} $suite"
    done
    echo ""
fi

echo -e "${BLUE}Duration:${NC} ${DURATION}s"
echo ""

# Exit with appropriate code
if [ ${#FAILED_SUITES[@]} -gt 0 ]; then
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
fi
