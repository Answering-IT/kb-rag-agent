# E2E Testing Guide

Complete guide for running End-to-End tests for ProcessApp RAG Agent.

---

## Quick Start

```bash
# Run all E2E tests
./scripts/run-e2e-tests.sh

# Run specific component
./scripts/run-e2e-tests.sh --agent-v2
./scripts/run-e2e-tests.sh --agent-v1
./scripts/run-e2e-tests.sh --ingestion
```

---

## Test Components

### 1. Document Ingestion (`e2e/ingestion/`)
Tests the complete document processing pipeline:
- ✅ S3 upload with KMS encryption
- ✅ Knowledge Base ingestion jobs
- ✅ Document synchronization
- ✅ OCR processing (Textract)

**Run:**
```bash
./scripts/run-e2e-tests.sh --ingestion
# or
python3 -m pytest e2e/ingestion/ -v
```

### 2. Agent V1 (`e2e/agent-v1/`) - Bedrock Agent
Tests the Bedrock Agent with WebSocket:
- ✅ WebSocket connection
- ✅ Knowledge Base queries
- ✅ Action group invocation (GetProjectInfo)
- ✅ Session memory (DynamoDB-backed)
- ✅ Metadata filtering (tenant isolation)
- ✅ Streaming responses

**WebSocket URL:** `wss://mf1ghadu5m.execute-api.us-east-1.amazonaws.com/dev`

**Run:**
```bash
./scripts/run-e2e-tests.sh --agent-v1
# or
python3 -m pytest e2e/agent-v1/ -v
```

**Message format:**
```json
{
  "action": "query",
  "question": "What documents do you have?",
  "sessionId": "test-session-123",
  "tenantId": "1",
  "userId": "user123",
  "roles": ["admin"]
}
```

### 3. Agent V2 (`e2e/agent-v2/`) - Agent Core Runtime ⭐
Tests the Agent Core Runtime with Strand SDK:
- ✅ WebSocket connection
- ✅ Knowledge Base search tool
- ✅ Project Info tool (ECS integration)
- ✅ Short-term memory (7-day retention)
- ✅ Multi-tool support
- ✅ Streaming responses

**WebSocket URL:** `wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev`

**Run:**
```bash
./scripts/run-e2e-tests.sh --agent-v2
# or
python3 -m pytest e2e/agent-v2/ -v
```

**Message format:**
```json
{
  "question": "What documents do you have?",
  "sessionId": "test-12345678901234567890123456789012"
}
```

---

## Prerequisites

### Install Dependencies
```bash
pip install pytest pytest-asyncio boto3 websockets
```

### Environment Variables
```bash
export AWS_PROFILE=ans-super
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=708819485463

# Agent V2 (recommended)
export WEBSOCKET_HOST=1j1xzo7n4h.execute-api.us-east-1.amazonaws.com

# Agent V1
export WEBSOCKET_V1_HOST=mf1ghadu5m.execute-api.us-east-1.amazonaws.com
export AGENT_ID=QWTVV3BY3G
export AGENT_ALIAS_ID=QZITGFMONE

# Knowledge Base
export KB_ID=R80HXGRLHO
```

---

## Script Options

```bash
./scripts/run-e2e-tests.sh [OPTIONS]

Options:
  --ingestion      Run only document ingestion tests
  --agent-v1       Run only Agent V1 tests (Bedrock Agent)
  --agent-v2       Run only Agent V2 tests (Agent Core Runtime)
  --kb             Run only Knowledge Base tests
  --all            Run all tests (default: ingestion + agents)
  -v, --verbose    Verbose output
  -x, --stop-on-fail  Stop on first failure
  -h, --help       Show help message
```

**Examples:**
```bash
# Default: ingestion + agents
./scripts/run-e2e-tests.sh

# All tests with verbose output
./scripts/run-e2e-tests.sh --all -v

# Only Agent V2 tests
./scripts/run-e2e-tests.sh --agent-v2

# Stop on first failure
./scripts/run-e2e-tests.sh -x
```

---

## Test Scenarios

### Agent V1 Test Scenarios

1. **Basic Query**
```python
{
  "action": "query",
  "question": "What documents do you have?",
  "sessionId": "test-123"
}
```

2. **With Metadata Filtering**
```python
{
  "action": "query",
  "question": "What documents are available?",
  "sessionId": "test-456",
  "tenantId": "1",
  "userId": "user123",
  "roles": ["admin"],
  "projectId": "100"
}
```

3. **Action Group Trigger**
```python
{
  "action": "query",
  "question": "What is the budget for project id 123?",
  "sessionId": "test-789"
}
```

### Agent V2 Test Scenarios

1. **Knowledge Base Search**
```python
{
  "question": "What documents do you have in the knowledge base?",
  "sessionId": "test-12345678901234567890123456789012"
}
```

2. **Project Info Tool**
```python
{
  "question": "Get information for organization 1 project 123",
  "sessionId": "test-12345678901234567890123456789012"
}
```

3. **Memory Test (2 messages, same session)**
```python
# Message 1
{
  "question": "My name is Alice and I work on project 123",
  "sessionId": "memory-12345678901234567890123456789012"
}

# Message 2 (new connection, same sessionId)
{
  "question": "What is my name and which project do I work on?",
  "sessionId": "memory-12345678901234567890123456789012"
}
```

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
        with:
          python-version: '3.11'
      - run: pip install -r requirements-test.txt
      - run: ./scripts/run-e2e-tests.sh --all
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

### AWS CodeBuild
```yaml
version: 0.2
phases:
  install:
    commands:
      - pip install -r requirements-test.txt
  test:
    commands:
      - ./scripts/run-e2e-tests.sh --all -v
reports:
  e2e-tests:
    files:
      - 'test-results.xml'
    file-format: 'JUNITXML'
```

---

## Troubleshooting

### Connection Failures

**Agent V1:**
```bash
# Check WebSocket deployment
aws apigatewayv2 get-api --api-id mf1ghadu5m --profile ans-super

# Check Lambda logs
aws logs tail /aws/lambda/processapp-ws-message-dev --follow --profile ans-super
```

**Agent V2:**
```bash
# Check WebSocket deployment
aws apigatewayv2 get-api --api-id 1j1xzo7n4h --profile ans-super

# Check Lambda logs
aws logs tail /aws/lambda/processapp-ws-message-v2-dev --follow --profile ans-super

# Check Agent Runtime
aws logs tail /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super
```

### Test Failures

**Check test output:**
```bash
./scripts/run-e2e-tests.sh --agent-v2 -v
```

**Run single test:**
```bash
python3 -m pytest e2e/agent-v2/test_websocket_tools.py::test_knowledge_base_search_tool -v -s
```

**Debug with Python:**
```python
import pytest
pytest.main([
    'e2e/agent-v2/test_memory.py::test_short_term_memory_basic',
    '-v', '-s', '--pdb'
])
```

---

## Additional Resources

- **Full E2E Documentation:** [e2e/README.md](e2e/README.md)
- **WebSocket Testing:** [TEST_WEBSOCKET.md](TEST_WEBSOCKET.md)
- **Deployment Guide:** [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
- **Quick Start:** [QUICK_START.md](QUICK_START.md)

---

**Last Updated:** 2026-04-26  
**Test Coverage:** Ingestion, Agent V1, Agent V2, Knowledge Base  
**Status:** ✅ All tests passing
