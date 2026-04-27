# ProcessApp RAG Agent - Test Scripts

Essential scripts for testing the RAG agent infrastructure.

---

## Testing Scripts

### Agent V2 (Agent Core Runtime with Strand SDK)

**`test-tools.py`** - Comprehensive E2E test for Agent V2
- ✅ Tests Knowledge Base search tool
- ✅ Tests Project Info tool (ECS service integration)
- ✅ Tests Memory (conversation context across sessions)
- **Usage:** `python3 test-tools.py`
- **WebSocket:** Connects to `wss://.../dev` endpoint

**`quick-ws-test.py`** - Quick WebSocket connection test
- ✅ Simple test to verify WebSocket connectivity
- ✅ Tests single Knowledge Base query
- **Usage:** `python3 quick-ws-test.py`

### Agent V1 (Bedrock Agent)

**`test-agent.py`** - Test Agent V1 via AWS SDK
- ✅ Tests Bedrock Agent directly (no API Gateway)
- ✅ Uses AWS credentials from profile
- **Usage:** `python3 test-agent.py`
- **Requirements:** AWS profile `default` configured

**`test-api.py`** - Test Agent V1 via REST API
- ✅ Tests API Gateway endpoint
- ✅ Requires API key
- **Usage:** `python3 test-api.py`

### Document Processing

**`test-ocr-agent.py`** - Test OCR Lambda function
- ✅ Tests document processing pipeline
- ✅ Verifies Textract integration
- **Usage:** `python3 test-ocr-agent.py`

**`create-ocr-image.py`** - Generate test images for OCR
- ✅ Creates synthetic documents for testing
- **Usage:** `python3 create-ocr-image.py`

---

## Running Tests

### E2E Test Suite (Recommended)

**Run all E2E tests:**
```bash
# Run all tests (ingestion + agents)
./run-e2e-tests.sh

# Run all tests including KB
./run-e2e-tests.sh --all

# Run specific component
./run-e2e-tests.sh --agent-v2
./run-e2e-tests.sh --agent-v1
./run-e2e-tests.sh --ingestion

# Options
./run-e2e-tests.sh --all -v      # Verbose output
./run-e2e-tests.sh -x            # Stop on first failure
./run-e2e-tests.sh --help        # Show help
```

### Quick Tests (Individual Scripts)

**Quick Test (V2 Agent with all features):**
```bash
python3 test-tools.py
```

**Individual Component Tests:**
```bash
# Knowledge Base only (V2)
python3 quick-ws-test.py

# Agent V1 (Bedrock Agent)
python3 test-agent.py

# REST API (V1)
python3 test-api.py

# Document processing
python3 test-ocr-agent.py
```

---

## Configuration

All scripts use environment variables or AWS profiles for configuration:
- **AWS Profile:** `default` (or set `AWS_PROFILE`)
- **Region:** `us-east-1`
- **Account:** `708819485463`

WebSocket URL is hardcoded in test scripts (update if needed):
```python
# In test-tools.py and quick-ws-test.py
host = "1j1xzo7n4h.execute-api.us-east-1.amazonaws.com"
path = "/dev"
```

---

## Troubleshooting

### WebSocket connection fails
- Check deployment status: `npx cdk deploy dev-us-east-1-websocket-v2`
- Check Lambda logs: `aws logs tail /aws/lambda/processapp-ws-message-v2-dev --follow`

### Agent doesn't respond
- Check runtime health: `aws logs tail /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-*`
- Verify Knowledge Base ID in agent environment variables

### Knowledge Base returns no results
- Run ingestion job: `aws bedrock-agent start-ingestion-job --knowledge-base-id <KB_ID> --data-source-id <DS_ID>`
- Check documents in S3: `aws s3 ls s3://processapp-docs-v2-dev-708819485463/documents/`

---

**Last Updated:** 2026-04-26
