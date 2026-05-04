# Quick Start Guide

Get started with ProcessApp RAG Agent in 5 minutes.

---

## Prerequisites

- **AWS Account:** 708819485463
- **AWS Profile:** `ans-super` (or `default`)
- **Region:** `us-east-1`
- **Node.js:** v18+ (for CDK)
- **Python:** 3.11+

---

## 1. Test the Agent (No Deployment Needed)

The agent is already deployed! Just test it:

```bash
# Quick test
python3 scripts/quick-ws-test.py

# Comprehensive test (KB + Tools + Memory)
python3 scripts/test-tools.py
```

Expected output:
```
✅ WebSocket connection established
✅ Knowledge Base search returned 2 documents
✅ Memory working (conversation context)
```

---

## 2. Query via WebSocket

### Using Python
```python
import websockets
import json
import asyncio

async def test():
    uri = "wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "question": "What documents do you have?",
            "sessionId": "test-12345678901234567890123456789012"
        }))
        
        async for message in ws:
            data = json.loads(message)
            if data['type'] == 'chunk':
                print(data['data'], end='', flush=True)
            elif data['type'] == 'complete':
                break

asyncio.run(test())
```

### Using wscat (Node.js)
```bash
npm install -g wscat
wscat -c wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev

# Send:
{"question":"Hello!","sessionId":"test-12345678901234567890123456789012"}
```

---

## 3. Upload Documents

```bash
# Upload document
aws s3 cp document.pdf \
  s3://processapp-docs-v2-dev-708819485463/documents/ \
  --sse aws:kms \
  --sse-kms-key-id e6a714f6-70a7-47bf-a9ee-55d871d33cc6 \
  --profile ans-super

# Sync Knowledge Base
KB_ID=R80HXGRLHO
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id $KB_ID \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text \
  --profile ans-super)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --profile ans-super
```

---

## 4. Deploy Changes

### Update Agent Code
```bash
cd agents
# Edit main.py
# Add/modify @tool functions

# Deploy
cd ../infrastructure
npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
```

### Update WebSocket Handler
```bash
cd infrastructure
# Edit lambdas/websocket-handler-v2/message_handler.py

# Deploy
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super
```

### Deploy All Stacks
```bash
cd infrastructure
npm run build
npx cdk deploy --all --profile ans-super --require-approval never
```

---

## 5. View Logs

### Agent Runtime
```bash
aws logs tail \
  /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super
```

### WebSocket Handler
```bash
aws logs tail /aws/lambda/processapp-ws-message-v2-dev \
  --follow --profile ans-super
```

---

## Architecture Overview

```
Client (WebSocket)
  ↓
API Gateway WebSocket (wss://...execute-api.../dev)
  ↓
Lambda Handler (message_handler.py)
  ↓
Agent Core Runtime (FastAPI + Strand SDK)
  ├─ Tool: search_knowledge_base()
  ├─ Tool: get_project_info()
  └─ Memory: 7-day retention
  ↓
Response streamed back to client
```

---

## Resources

**WebSocket URL:** `wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev`  
**Knowledge Base ID:** `R80HXGRLHO`  
**Agent ID (V1):** `QWTVV3BY3G`  
**Runtime ID (V2):** `processapp_agent_runtime_v2_dev-9b2dszEtqw`

---

## Next Steps

1. **Read full docs:** [README.md](README.md)
2. **Test WebSocket:** [TEST_WEBSOCKET.md](TEST_WEBSOCKET.md)
3. **Check deployment:** [DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)
4. **Run E2E tests:** [e2e/README.md](e2e/README.md)

---

**Last Updated:** 2026-04-26
