# End-to-End Testing Suite

Comprehensive E2E tests for ProcessApp RAG Agent infrastructure.

---

## Test Structure

```
e2e/
├── ingestion/          # Document upload and processing tests
├── agent-v1/           # Bedrock Agent (V1) tests
├── agent-v2/           # Agent Core Runtime (V2) tests
├── knowledge-base/     # Knowledge Base query tests
└── README.md           # This file
```

---

## Running Tests

### Quick Start (Recommended)

**Run all tests with the automated script:**
```bash
# Run ingestion + agents (default)
./scripts/run-e2e-tests.sh

# Run all tests (including KB)
./scripts/run-e2e-tests.sh --all

# Run specific component
./scripts/run-e2e-tests.sh --agent-v2
./scripts/run-e2e-tests.sh --agent-v1
./scripts/run-e2e-tests.sh --ingestion

# Verbose output
./scripts/run-e2e-tests.sh --all -v

# Stop on first failure
./scripts/run-e2e-tests.sh -x
```

### Manual Execution

**All Tests (Full E2E):**
```bash
# Run complete test suite
python3 -m pytest e2e/ -v

# Run with coverage
python3 -m pytest e2e/ --cov=. --cov-report=html
```

**By Component:**
```bash
# Document ingestion tests
python3 -m pytest e2e/ingestion/ -v

# Agent V1 tests (Bedrock Agent)
python3 -m pytest e2e/agent-v1/ -v

# Agent V2 tests (Agent Core Runtime)
python3 -m pytest e2e/agent-v2/ -v

# Knowledge Base tests
python3 -m pytest e2e/knowledge-base/ -v
```

**Individual Tests:**
```bash
# Specific test file
python3 e2e/agent-v2/test_websocket_tools.py
python3 e2e/agent-v1/test_websocket_v1.py

# Specific test function
python3 -m pytest e2e/agent-v2/test_memory.py::test_short_term_memory -v
```

---

## Test Categories

### 1. Ingestion Tests (`ingestion/`)
- ✅ **`test_document_upload.py`** - Upload documents to S3
- ✅ **`test_ocr_processing.py`** - Test Textract OCR pipeline
- ✅ **`test_kb_sync.py`** - Test Knowledge Base ingestion

### 2. Agent V1 Tests (`agent-v1/`) - Bedrock Agent
- ✅ **`test_websocket_v1.py`** - WebSocket connection and queries
  - Connection establishment
  - Knowledge Base queries
  - Session memory (DynamoDB-backed)
  - Action group invocation
  - Metadata filtering (tenant isolation)
  - Streaming responses

### 3. Agent V2 Tests (`agent-v2/`) - **Recommended**
- ✅ **`test_websocket_connection.py`** - WebSocket connectivity
- ✅ **`test_kb_search_tool.py`** - Knowledge Base search tool
- ✅ **`test_project_info_tool.py`** - ECS service integration
- ✅ **`test_memory.py`** - Short-term memory (7 days)
- ✅ **`test_streaming.py`** - Response streaming

### 4. Knowledge Base Tests (`knowledge-base/`)
- ✅ **`test_vector_search.py`** - Vector similarity search
- ✅ **`test_hybrid_search.py`** - Hybrid (vector + keyword) search
- ✅ **`test_metadata_filtering.py`** - Tenant-based metadata filtering

---

## Configuration

Tests use environment variables from `.env` or environment:

```bash
# Required
export AWS_PROFILE=ans-super
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=708819485463

# Agent V2 (Agent Core Runtime - WebSocket)
export WEBSOCKET_HOST=1j1xzo7n4h.execute-api.us-east-1.amazonaws.com
export WEBSOCKET_PATH=/dev

# Agent V1 (Bedrock Agent - WebSocket)
export WEBSOCKET_V1_HOST=mf1ghadu5m.execute-api.us-east-1.amazonaws.com
export AGENT_ID=QWTVV3BY3G
export AGENT_ALIAS_ID=QZITGFMONE

# Knowledge Base
export KB_ID=R80HXGRLHO

# S3
export DOCS_BUCKET=processapp-docs-v2-dev-708819485463
export KMS_KEY_ID=e6a714f6-70a7-47bf-a9ee-55d871d33cc6
```

---

## Prerequisites

Install dependencies:
```bash
pip install -r requirements-test.txt
```

Required packages:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `boto3` - AWS SDK
- `websockets` - WebSocket client
- `requests` - HTTP client

---

## Test Data

Sample documents for testing are in `/test-data/documents/`:
- `doc-empresa.txt` - Company information
- `doc-flujo-normal.txt` - Process flow
- `test_auto_metadata.txt` - Metadata testing

---

## CI/CD Integration

### GitHub Actions
```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements-test.txt
      - run: pytest e2e/ -v
```

### AWS CodePipeline
```yaml
version: 0.2
phases:
  install:
    commands:
      - pip install -r requirements-test.txt
  test:
    commands:
      - pytest e2e/ --junitxml=test-results.xml
reports:
  e2e-tests:
    files:
      - test-results.xml
```

---

## Best Practices

1. **Isolation** - Each test should be independent
2. **Cleanup** - Always clean up resources after tests
3. **Timeouts** - Set reasonable timeouts for async operations
4. **Retries** - Implement retries for flaky external services
5. **Mocking** - Mock external services when appropriate
6. **Assertions** - Use descriptive assertion messages

---

## Troubleshooting

### Tests timeout
- Increase timeout values in test fixtures
- Check AWS service health
- Verify network connectivity

### WebSocket tests fail
- Ensure Lambda is deployed: `npx cdk deploy dev-us-east-1-websocket-v2`
- Check WebSocket URL in configuration
- Verify IAM permissions

### Knowledge Base tests return no results
- Run ingestion job first
- Check documents exist in S3
- Verify KB sync status

---

**Last Updated:** 2026-04-26
