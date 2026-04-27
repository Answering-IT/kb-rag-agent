# WebSocket Testing Guide

Quick reference for testing the ProcessApp Agent V2 via WebSocket.

---

## Quick Test

### Using Test Scripts

**Comprehensive test** (recommended):
```bash
python3 scripts/test-tools.py
```

Tests:
- ✅ Knowledge Base search tool
- ✅ Project Info tool (ECS integration)
- ✅ Short-term memory (conversation context)

**Simple connection test**:
```bash
python3 scripts/quick-ws-test.py
```

Tests:
- ✅ WebSocket connection
- ✅ Single KB query
- ✅ Streaming response

---

## WebSocket Details

**URL:** `wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev`  
**API ID:** `1j1xzo7n4h`  
**Stage:** `dev`

---

## Message Format

### Request
```json
{
  "question": "What documents do you have in the knowledge base?",
  "sessionId": "test-session-123456789012345678901234567890"
}
```

**Important:** Session ID must be at least 33 characters (AWS requirement).

### Response (Streamed)
```json
{"type": "status", "message": "Processing your request...", "sessionId": "..."}
{"type": "chunk", "data": "Here are "}
{"type": "chunk", "data": "the documents "}
{"type": "chunk", "data": "available: "}
{"type": "complete", "sessionId": "..."}
```

### Error Response
```json
{"type": "error", "message": "Error description"}
```

---

## Testing with wscat

Install wscat (Node.js):
```bash
npm install -g wscat
```

Connect and send message:
```bash
wscat -c wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev

# After connection, send:
{"question":"What documents do you have?","sessionId":"test-12345678901234567890123456789012"}
```

Expected output:
```json
< {"type": "status", "message": "Processing your request...", "sessionId": "test-12345678901234567890123456789012"}
< {"type": "chunk", "data": "Here are "}
< {"type": "chunk", "data": "the documents..."}
< {"type": "complete", "sessionId": "test-12345678901234567890123456789012"}
```

---

## Test Scenarios

### 1. Simple KB Query
```json
{"question":"What documents are in the knowledge base?","sessionId":"query1-1234567890123456789012345678901"}
```

### 2. Project Info Tool
```json
{"question":"Get information for organization 1 project 123","sessionId":"tool1-12345678901234567890123456789012"}
```

### 3. Memory Test (2 messages, same session)
```json
// Message 1
{"question":"My name is Alice and I work on project 123","sessionId":"memory1-123456789012345678901234567890"}

// Message 2 (new connection, same sessionId)
{"question":"What is my name and which project do I work on?","sessionId":"memory1-123456789012345678901234567890"}
```

Expected: Agent recalls "Alice" and "project 123"

---

## Troubleshooting

### Connection Fails
```bash
# Check WebSocket deployment
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super

# Check Lambda logs
aws logs tail /aws/lambda/processapp-ws-message-v2-dev --follow --profile ans-super
```

### Session ID Too Short Error
```json
{"type": "error", "message": "Invalid length for parameter runtimeSessionId..."}
```
**Fix:** Use session ID with 33+ characters.

### No Response
```bash
# Check Agent Runtime logs
aws logs tail /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super
```

### KB Returns No Results
```bash
# Check documents exist
aws s3 ls s3://processapp-docs-v2-dev-708819485463/documents/ --profile ans-super

# Run ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id <DS_ID> \
  --profile ans-super
```

---

## Expected Results

### KB Search Tool
- **Query:** "What documents do you have?"
- **Expected:** List of 2+ documents from Knowledge Base
- **Response time:** 5-15 seconds
- **Chunks:** 15-20 chunks

### Project Info Tool
- **Query:** "Get info for organization 1 project 123"
- **Expected:** Project details from ECS service (or error if service unavailable)
- **Response time:** 5-20 seconds
- **Chunks:** 5-10 chunks

### Memory
- **Setup:** Send name in message 1
- **Test:** Ask for name in message 2 (same session)
- **Expected:** Agent recalls name from previous message
- **Retention:** 7 days

---

## Integration Tests

### E2E Test Suite
```bash
# Run all WebSocket tests
python3 -m pytest e2e/agent-v2/ -v

# Run specific tests
python3 -m pytest e2e/agent-v2/test_websocket_tools.py::test_knowledge_base_search_tool -v
python3 -m pytest e2e/agent-v2/test_memory.py::test_short_term_memory_basic -v
```

---

## Logs

### Real-time monitoring
```bash
# Lambda handler
aws logs tail /aws/lambda/processapp-ws-message-v2-dev --follow --profile ans-super

# Agent runtime
aws logs tail /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super
```

### Search logs
```bash
# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/processapp-ws-message-v2-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile ans-super

# Search by session ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/processapp-ws-message-v2-dev \
  --filter-pattern "test-session-12345" \
  --profile ans-super
```

---

**Last Updated:** 2026-04-26  
**WebSocket URL:** `wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev`  
**Agent:** V2 (Agent Core Runtime with Strand SDK)
