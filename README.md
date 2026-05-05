# ProcessApp RAG - Knowledge Base Agent

Multi-tenant RAG (Retrieval-Augmented Generation) infrastructure using AWS Bedrock, S3 Vector storage, and serverless document processing.

## ⚡ Quick Deploy

```bash
# Set AWS profile
export AWS_PROFILE=ans-super

# Compile and deploy Agent V2
cd infrastructure
npm install && npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

**Agent V2** - Simplified normative consultant (~259 lines) specialized in Colombian pension regulations using Strand SDK.

---

## 📌 Common Commands

| Task | Command |
|------|---------|
| **Compile** | `cd infrastructure && npm run build` |
| **Deploy Agent V2** | `cd infrastructure && npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never` |
| **Check compilation** | `cd infrastructure && npm run build` (no errors = success) |
| **View logs** | `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_dev --follow --profile ans-super` |
| **Get outputs** | `aws cloudformation describe-stacks --stack-name dev-us-east-1-agent-v2 --query 'Stacks[0].Outputs' --profile ans-super` |
| **Verify AWS profile** | `aws sts get-caller-identity --profile ans-super` |

---

## 🚀 Quick Start

### Agent V2 - Normative Consultant (Recommended)

**Agent V2** is a custom agent specialized in Colombian pension regulations using Strand SDK.

#### Deploy Agent V2

```bash
# 1. Set AWS profile
export AWS_PROFILE=ans-super

# 2. Compile and deploy
cd infrastructure
npm install && npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

#### What Agent V2 Does

- 📚 **Consults Colpensiones regulations** - Laws, decrees, circulars, jurisprudence
- 🌐 **Fetches official sources** - funcionpublica.gov.co, presidencia.gov.co, etc.
- 💬 **Conversation memory** - Maintains context across questions (simple session dict)
- 🔍 **Smart search** - Uses normative framework index to find relevant documents
- ⚡ **Low latency** - Streams responses in 3-word chunks
- 🛡️ **User-friendly errors** - Technical details only in logs
- 🧹 **Clean output** - Filters `<thinking>` tags automatically

**Example Questions:**
```
- "¿Qué es la Ley 2381 de 2024?"
- "¿Dónde puedo consultar el Decreto 1225 de 2024?"
- "¿Cuál es el marco normativo de la reforma pensional?"
```

**Test via WebSocket:**
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c wss://6aqhp0u2zk.execute-api.us-east-1.amazonaws.com/dev

# Send message
{"action":"sendMessage","data":{"inputText":"¿Cómo me puedes ayudar?","sessionId":"test-123"}}
```

**Stack Outputs:**
```bash
# Get runtime endpoint
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent-v2 \
  --query 'Stacks[0].Outputs' \
  --profile ans-super
```

---

### For Infrastructure Developers

#### Prerequisites

- AWS CLI configured with credentials (`ans-super` profile)
- AWS CDK installed (`npm install -g aws-cdk`)
- Node.js 18+
- Python 3.11+

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      DOCUMENT INGESTION                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │  Upload to S3 docs bucket                │
        │  (documents/ prefix)                     │
        └─────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
    ┌───────────────────┐       ┌──────────────────┐
    │ Text Files        │       │ Images/PDFs      │
    │ (TXT, DOCX, MD)   │       │ (PNG, JPG, PDF)  │
    └───────────────────┘       └──────────────────┘
                │                           │
                │                           ▼
                │               ┌──────────────────────┐
                │               │ OCR Lambda           │
                │               │ (Textract)           │
                │               └──────────────────────┘
                │                           │
                │                           ▼
                │               ┌──────────────────────┐
                │               │ Processed Text       │
                │               │ (documents/          │
                │               │  processed-*.txt)    │
                │               └──────────────────────┘
                │                           │
                └───────────┬───────────────┘
                            ▼
                ┌───────────────────────────┐
                │ Bedrock KB Sync           │
                │ (Manual or Scheduled)     │
                └───────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │ Bedrock Processing                    │
        │ - Chunking (512 tokens, 20% overlap)  │
        │ - Embedding (Titan v2)                │
        │ - Indexing (S3 Vector Storage)        │
        └───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      QUERY INTERFACE                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                │                        │
                ▼                        ▼
    ┌────────────────────┐   ┌────────────────────────┐
    │ REST API           │   │ Direct AWS SDK         │
    │ (API Gateway)      │   │ (bedrock-agent-runtime)│
    │                    │   │                        │
    │ POST /query        │   │ invoke_agent()         │
    │ + API Key Auth     │   │ + AWS Credentials      │
    │ + CORS             │   │                        │
    │ + Rate Limiting    │   │                        │
    └────────┬───────────┘   └────────┬───────────────┘
             │                        │
             │  ┌─────────────────────┘
             │  │
             ▼  ▼
    ┌──────────────────────────────────┐
    │  API Handler Lambda              │
    │  (invoke bedrock agent)          │
    └──────────────┬───────────────────┘
                   │
                   ▼
        ┌───────────────────────────────────────┐
        │ Bedrock Agent Core                    │
        │                                       │
        │ - Model: Amazon Nova Pro              │
        │ - Guardrails: PII + Content Filters   │
        │ - Knowledge Base: Vector Search       │
        │ - Session Management                  │
        └───────────────────────────────────────┘
```

**Key Components:**
- **8 CDK Stacks** deployed and operational
- **REST API Endpoint** for backend integration (recommended)
- **Direct SDK Access** for advanced use cases
- **Automatic OCR** for images and scanned PDFs
- **Bedrock Native Processing** for optimal performance

---

## 📥 Ingesting Documents

### Step 1: Upload Documents to S3

```bash
# Set your AWS profile
export AWS_PROFILE=default

# Get bucket name and KMS key from deployment outputs
BUCKET_NAME="processapp-docs-v2-dev-708819485463"
KMS_KEY_ID="e6a714f6-70a7-47bf-a9ee-55d871d33cc6"

# Upload text files (processed directly by Bedrock)
aws s3 cp your-document.txt s3://${BUCKET_NAME}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY_ID}

# Upload images/PDFs (will be processed by OCR Lambda)
aws s3 cp your-scanned-document.png s3://${BUCKET_NAME}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY_ID}
```

**Supported File Types:**
- **Text files** (no OCR needed): `.txt`, `.docx`, `.md`
- **Images/Scans** (OCR processed): `.png`, `.jpg`, `.jpeg`, `.pdf`, `.tiff`

### Step 2: Wait for OCR Processing (if applicable)

For images/PDFs, the OCR Lambda will:
1. Extract text using AWS Textract (~5-10 seconds)
2. Save extracted text to `documents/processed-{filename}.txt`

Check OCR logs:
```bash
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow
```

### Step 3: Trigger Knowledge Base Sync

```bash
# Get KB and Data Source IDs
KB_ID=$(aws bedrock-agent list-knowledge-bases \
  --query 'knowledgeBaseSummaries[?contains(name, `processapp`)].knowledgeBaseId' \
  --output text)

DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID}

# Check status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id <JOB_ID>
```

**Note:** KB sync also runs automatically every 6 hours (configurable in `config/environments.ts`).

---

## 💬 Testing the Agent

### WebSocket V2 - Real-Time Streaming (Recommended)

Agent V2 uses WebSocket for real-time streaming responses with metadata filtering support.

#### Quick Test with wscat

```bash
# Install wscat (if not already installed)
npm install -g wscat

# Get WebSocket URL from stack outputs
WS_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-websocket-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`WebSocketURLV2`].OutputValue' \
  --output text \
  --profile ans-super)

# Connect to WebSocket
wscat -c $WS_URL

# Send query (paste after connecting)
{
  "action": "query",
  "question": "¿Qué es la Ley 2381 de 2024?",
  "tenant_id": "1",
  "user_id": "user1",
  "user_roles": ["viewer"],
  "project_id": "100"
}
```

**With Metadata Filtering:**
```json
{
  "action": "query",
  "question": "Search for Colpensiones documents",
  "sessionId": "my-session-123",
  "tenant_id": "company-123",
  "user_id": "user456",
  "user_roles": ["admin", "analyst"],
  "project_id": "project-789",
  "metadata": {
    "custom_filter": "value"
  }
}
```

#### Expected Response Format

```json
// Status message
{"type": "status", "message": "Processing your request...", "sessionId": "..."}

// Streaming chunks
{"type": "chunk", "data": "## Decreto 1558 de 2024...", "sessionId": "..."}
{"type": "chunk", "data": " - Ahorro Individual\n\n**Tema:**...", "sessionId": "..."}

// Completion
{
  "type": "complete",
  "sessionId": "...",
  "stats": {
    "message_count": 5,
    "window_size": 5,
    "truncation_count": 0,
    "age_minutes": 2.3
  },
  "metadata_filtered": true
}
```

#### Python Client Example

```python
import asyncio
import websockets
import json

WS_URL = "wss://<your-websocket-url>/dev"  # Get from stack outputs

async def query_agent(question, tenant_id="1"):
    async with websockets.connect(WS_URL) as ws:
        # Send query with metadata (snake_case for AWS Bedrock)
        await ws.send(json.dumps({
            'action': 'query',
            'question': question,
            'tenant_id': tenant_id,
            'user_id': f'user_{tenant_id}',
            'user_roles': ['viewer']
        }))
        
        # Receive streaming response
        full_response = ""
        async for message in ws:
            data = json.loads(message)
            
            if data['type'] == 'chunk':
                chunk = data['data']
                print(chunk, end='', flush=True)
                full_response += chunk
                
            elif data['type'] == 'complete':
                print(f"\n✅ Complete")
                print(f"Stats: {data.get('stats', {})}")
                print(f"Filtered: {data.get('metadata_filtered', False)}")
                break
                
        return full_response

# Run
asyncio.run(query_agent("¿Qué es la Ley 2381 de 2024?"))
```

#### Test Multi-Turn Conversation

```bash
# Use same sessionId for conversation continuity
SESSION="test-$(date +%s)"

# Turn 1
wscat -c $WS_URL
> {"action": "query", "question": "Mi nombre es Carlos", "sessionId": "$SESSION", "tenant_id": "1", "user_id": "user1", "user_roles": ["viewer"]}

# Turn 2 - should remember name
> {"action": "query", "question": "¿Cuál es mi nombre?", "sessionId": "$SESSION", "tenant_id": "1", "user_id": "user1", "user_roles": ["viewer"]}

# Expected: Agent responds with "Carlos"
```

#### Automated Test Script

```bash
# Install websockets library (if not installed)
pip3 install websockets

# Run comprehensive tests
python3 scripts/test-websocket-metadata.py

# Tests include:
# 1. Query WITH metadata (tenant isolation)
# 2. Query WITHOUT metadata (unrestricted)
# 3. Multi-turn conversation (context memory)
```

📖 **Full WebSocket Documentation:** [docs/WEBSOCKET_STREAMING_GUIDE.md](docs/WEBSOCKET_STREAMING_GUIDE.md)

**Important:** All metadata fields use **snake_case** format for AWS Bedrock compatibility:
- ✅ `tenant_id`, `user_id`, `user_roles`, `project_id`
- ❌ ~~`tenantId`, `userId`, `roles`, `projectId`~~ (deprecated)
```

Run:
```bash
python3 query-agent.py
```

### Using AWS CLI (Advanced)

```bash
# Create a session
SESSION_ID=$(uuidgen)

# Invoke agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id QWTVV3BY3G \
  --agent-alias-id QZITGFMONE \
  --session-id ${SESSION_ID} \
  --input-text "What documents do you have?" \
  --region us-east-1 \
  output.txt

# View response
cat output.txt
```

---

## 🖥️ Frontend - Chat Interface

A modern bilingual Next.js 14 chat interface with dual-mode connectivity (WebSocket/REST).

### Quick Start

```bash
cd fe
npm install
npm run dev
# Open http://localhost:3000
```

### Key Features

- ✅ **Bilingual** - Spanish (default) and English support
- ✅ **Dual connectivity** - WebSocket (default) and REST streaming
- ✅ **Connection mode** - Selector hidden in production, visible on `/test` page
- ✅ **Embeddable widget** - iframe support with postMessage API
- ✅ **Version tracking** - Built-in version display (v0.0.1)
- ✅ **Real-time streaming** - Server-sent streaming responses
- ✅ **Session management** - Maintains conversation context
- ✅ **Dark mode** - Tokyo Night theme

### Environment Configuration

```env
# WebSocket API (default)
NEXT_PUBLIC_WS_URL=wss://your-id.execute-api.us-east-1.amazonaws.com/dev

# REST Streaming API (alternative)
NEXT_PUBLIC_STREAMING_API_URL=https://your-id.lambda-url.us-east-1.on.aws/

# Connection mode: 'websocket' (default) or 'streaming'
NEXT_PUBLIC_CHAT_MODE=websocket

# Show connection mode selector: false (default), always visible on /test
NEXT_PUBLIC_SHOW_MODE_SELECTOR=false

# Language: 'es' (default) or 'en'
NEXT_PUBLIC_LANGUAGE=es
```

### Available Routes

| Route | Purpose | Selector Visible? |
|-------|---------|-------------------|
| `/` | Main chat interface | ❌ No (production) |
| `/widget` | Embeddable widget | ❌ No (production) |
| `/test` | Developer test page | ✅ Yes (for testing) |

### Language Support

All UI text is fully translated:

| Spanish (Default) | English | Location |
|-------------------|---------|----------|
| ¿Cómo puedo ayudarte? | How can I help you? | Widget placeholder |
| Inicia una conversación | Start a conversation | Empty state |
| Conectado y listo | Connected and ready | Connection status |
| Versión v0.0.1 | Version v0.0.1 | Version label |

**Switch language:**
```env
NEXT_PUBLIC_LANGUAGE=en  # English
NEXT_PUBLIC_LANGUAGE=es  # Spanish (default)
```

### Deployment

```bash
# Vercel (recommended)
cd fe
vercel

# Or build for self-hosting
npm run build
npm run start
```

See `fe/README.md` for detailed documentation.

---

## 🛡️ Security Features

### Guardrails Active
The agent has the following content filters:
- **PII Detection**: Blocks person names, SSN, credit cards, addresses
- **Content Filtering**: Blocks hate speech, violence, sexual content
- **Prompt Attack Protection**: Detects jailbreak attempts

Example blocked content:
```python
ask_agent("Who is the CEO?")
# Response: "The generated text has been blocked by our content filters."
```

---

## 🔌 API Gateway Configuration

### Endpoint Details

| Property | Value |
|----------|-------|
| **Endpoint URL** | `https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query` |
| **Method** | POST |
| **Authentication** | API Key (x-api-key header) |
| **API Key ID** | `6a0h023lec` |
| **Region** | us-east-1 |
| **Stage** | dev |

### Rate Limits and Quotas

| Limit Type | Value |
|------------|-------|
| **Rate Limit** | 100 requests/second |
| **Burst Limit** | 200 concurrent requests |
| **Monthly Quota** | 10,000 requests |
| **Timeout** | 30 seconds |

### Request Format

**Headers:**
```
Content-Type: application/json
x-api-key: <your-api-key>
```

**Body:**
```json
{
  "question": "Your question here",
  "sessionId": "optional-session-id-for-conversation-continuity"
}
```

**Response (Success):**
```json
{
  "answer": "Agent's response",
  "sessionId": "abc-123-def-456",
  "status": "success"
}
```

**Response (Error):**
```json
{
  "error": "Error message",
  "status": "error"
}
```

### CORS Support

The API supports CORS for web applications:
- **Allowed Origins:** `*` (all origins)
- **Allowed Methods:** `GET, POST, OPTIONS`
- **Allowed Headers:** `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`

### Getting Your API Key

**Option 1: AWS CLI (requires API Gateway permissions)**
```bash
aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text
```

**Option 2: Ask Administrator**
If you don't have API Gateway permissions, ask an administrator to retrieve the key for you.

### Language Examples

**Python:**
```python
import requests

response = requests.post(
    "https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query",
    headers={"Content-Type": "application/json", "x-api-key": "YOUR_KEY"},
    json={"question": "What documents do you have?"}
)
print(response.json()['answer'])
```

**JavaScript (Node.js):**
```javascript
const axios = require('axios');

const response = await axios.post(
  'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query',
  { question: 'What documents do you have?' },
  { headers: { 'Content-Type': 'application/json', 'x-api-key': 'YOUR_KEY' } }
);
console.log(response.data.answer);
```

**TypeScript (fetch):**
```typescript
const response = await fetch(
  'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query',
  {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': 'YOUR_KEY'
    },
    body: JSON.stringify({ question: 'What documents do you have?' })
  }
);
const data = await response.json();
console.log(data.answer);
```

**curl:**
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV" \
  -d '{"question": "What documents do you have?"}'
```

### Monitoring and Logs

**API Gateway Logs:**
```bash
# View API Gateway logs
aws logs tail /aws/apigateway/processapp-dev --follow
```

**Lambda Handler Logs:**
```bash
# View Lambda handler logs
aws logs tail /aws/lambda/processapp-api-handler-dev --follow
```

### Test Script

A comprehensive test script is provided at the root of the repository:

```bash
# Set your API key
export API_KEY="your-api-key-here"

# Run the test script
python3 scripts/test-api.py
```

The test script includes:
- ✅ Simple query
- ✅ Follow-up question (session continuity)
- ✅ OCR document query
- ✅ Company data query
- ✅ PII filter test (guardrails)

📖 **API Documentation:**
- **Quick Reference:** [docs/API_QUICKREF.md](docs/API_QUICKREF.md) - One-page cheat sheet with all essentials
- **Complete Guide:** [docs/API_USAGE.md](docs/API_USAGE.md) - Full reference with advanced topics

---

## 🏗️ Infrastructure

### Deployed Stacks

#### Core Infrastructure (Shared)
1. **PrereqsStack** - S3 buckets, KMS keys, IAM roles
2. **SecurityStack** - Bucket policies, guardrails permissions
3. **BedrockStack** - Knowledge Base, Data Source, Vector Index
4. **DocumentProcessingStack** - OCR Lambda, Textract, SNS
5. **GuardrailsStack** - Content filters and PII protection
6. **SessionMemoryStack** - DynamoDB for conversation history
7. **MonitoringStack** - CloudWatch dashboards and alarms

#### Agent V1 (Legacy)
8. **AgentStack** - Bedrock Agent with Nova Pro model
9. **APIStack** - API Gateway REST endpoint with Lambda handler
10. **WebSocketStack** - WebSocket API for streaming

#### Agent V2 (Active) 🆕
11. **AgentStackV2** - Agent Core Runtime with Strand SDK (simplified, ~259 lines)
12. **WebSocketStackV2** - WebSocket API for Agent V2 streaming

**Deploy Commands:**
```bash
# Deploy Agent V2 only (recommended for updates)
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never

# Deploy all stacks (full infrastructure)
npx cdk deploy --all --profile ans-super --require-approval never
```

**Agent V2 Features:**
- ✅ Simplified codebase (849 → 259 lines, ~70% reduction)
- ✅ Fast streaming (3-word chunks for low latency)
- ✅ Clean output (filters `<thinking>` tags automatically)
- ✅ User-friendly errors (technical details in CloudWatch only)
- ✅ Token overflow prevention (truncation at load time)
- ✅ Multi-tenant support (metadata filtering)

### Key Configuration

**Knowledge Base:**
- **Chunking**: 512 tokens per chunk, 20% overlap
- **Embedding Model**: Amazon Titan Embed Text v2 (1024 dimensions)
- **Vector Storage**: S3 Vectors (AWS::S3Vectors resource)

**OCR Processing:**
- **Service**: AWS Textract
- **Features**: Text detection, tables, forms
- **Output**: Saved to `documents/processed-{filename}.txt`

**Agent:**
- **Model**: Amazon Nova Pro (amazon.nova-pro-v1:0)
- **Temperature**: 0.7
- **Max Tokens**: 4096

---

## 📊 Monitoring

### CloudWatch Logs

**OCR Lambda:**
```bash
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow
```

**Agent Invocations:**
```bash
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agents/QWTVV3BY3G \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### Ingestion Jobs

```bash
# List recent jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --max-results 10
```

---

## 🧪 Testing

### Quick Test Script

Use the provided test scripts:

```bash
# Test OCR flow
python3 scripts/test-ocr-agent.py

# Test normal flow (text documents)
python3 scripts/test-dos-flujos.py
```

### Example Questions

**About company data (doc-empresa.txt):**
- "What were TechFlow Solutions' Q1 2026 revenues?"
- "How many employees does TechFlow have?"
- "What are the active projects?"

**About security incident (OCR document):**
- "When was the DataFlow security incident?"
- "How long was the system offline?"
- "What improvements were implemented?"

---

## 🔧 Development

### Agent V2 - Normative Consultant (Strand SDK)

**Agent V2** uses Strand SDK and Agent Core Runtime for custom agent logic with web search capabilities.

#### Quick Deploy

```bash
# 1. Set AWS profile (IMPORTANT: use ans-super for this project)
export AWS_PROFILE=ans-super

# 2. Compile Infrastructure
cd infrastructure
npm install
npm run build

# 3. Deploy Agent V2 Stack
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

#### Development Workflow

```bash
# 1. Edit agent code
cd agents
vim main.py

# 2. Test agent locally (optional)
python3 main.py
# Access: http://localhost:8080/health

# 3. Compile and verify TypeScript
cd ../infrastructure
npm run build

# 4. Check for compilation errors
# If no errors, proceed to deploy

# 5. Deploy updated agent
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

#### Agent V2 Features

**Active Tools:**
- ✅ `consult_normative_document` - Consulta marco normativo de Colpensiones
- ✅ `http_request` (Strands) - Fetch de URLs oficiales del gobierno

**Disabled Tools:**
- ❌ `search_knowledge_base` - Disabled (can be re-enabled)
- ❌ `get_project_info` - Disabled (can be re-enabled)

**Stack Resources:**
- **Agent Runtime** - FastAPI server with Strand SDK
- **Agent Memory** - 7-day conversation history
- **Runtime Endpoint** - HTTPS endpoint for invocation
- **Normative Framework** - Loaded from `agents/marco_normativo_colpensiones.md`

#### Agent Configuration Files

```
agents/
├── main.py                           # Agent code (Strand SDK)
├── marco_normativo_colpensiones.md   # Normative framework index
├── requirements.txt                  # Python dependencies
└── Dockerfile                        # Container definition (auto-built by CDK)
```

#### Quick Verification Commands

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent-v2 \
  --query 'Stacks[0].StackStatus' \
  --profile ans-super

# Get runtime endpoint
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent-v2 \
  --query 'Stacks[0].Outputs[?OutputKey==`RuntimeEndpointUrlV2`].OutputValue' \
  --output text \
  --profile ans-super

# Check agent runtime logs
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super
```

#### Deployment Outputs

After successful deployment, you'll see:

```
✅  dev-us-east-1-agent-v2

Outputs:
dev-us-east-1-agent-v2.RuntimeIdV2 = processapp_agent_runtime_v2_dev-XXXXX
dev-us-east-1-agent-v2.RuntimeEndpointUrlV2 = https://processapp_endpoint_v2_dev...
dev-us-east-1-agent-v2.MemoryIdV2 = processapp_agent_memory_v2_dev-XXXXX
```

#### Troubleshooting Deployment

**Issue: Compilation errors**
```bash
# Check TypeScript errors
cd infrastructure
npm run build
# Fix errors in lib/AgentStackV2.ts or bin/app.ts
```

**Issue: Docker build fails**
```bash
# Check agent dependencies
cd agents
pip install -r requirements.txt
# Ensure all imports work
python3 -c "import strands; import strands_tools; print('OK')"
```

**Issue: Deployment fails**
```bash
# Check CDK logs
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --verbose

# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-agent-v2 \
  --max-items 20 \
  --profile ans-super
```

---

### Agent V1 (Legacy) - Bedrock Agent

The original agent using Bedrock Agent service.

#### Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build

# Deploy all stacks
npx cdk deploy --all --profile ans-super --require-approval never

# Deploy specific stack
npx cdk deploy dev-us-east-1-agent --profile ans-super
```

### Configuration

Edit `infrastructure/config/environments.ts` to configure:
- Stage name (`dev`, `prod`)
- Region
- Sync schedule
- Chunking parameters
- PII entities to detect
- Content filter strengths

---

## 📂 Project Structure

```
kb-rag-agent/
├── agents/                           # 🆕 Agent V2 Code (Strand SDK, simplified)
│   ├── main.py                       # Agent implementation (~259 lines)
│   ├── marco_normativo_colpensiones.md # Normative framework (truncated to 2000 chars)
│   ├── metadata_handler.py           # Multi-tenant KB filtering
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Container definition
├── infrastructure/
│   ├── bin/
│   │   └── app.ts                    # CDK app entry point
│   ├── lib/
│   │   ├── PrereqsStack.ts           # S3, KMS, IAM
│   │   ├── SecurityStack.ts          # Policies, guardrails
│   │   ├── BedrockStack.ts           # Knowledge Base
│   │   ├── DocumentProcessingStack.ts # OCR Lambda
│   │   ├── GuardrailsStack.ts        # Content filters
│   │   ├── AgentStack.ts             # Bedrock Agent (V1 - Legacy)
│   │   ├── AgentStackV2.ts           # 🆕 Agent Core Runtime (V2)
│   │   ├── APIStack.ts               # API Gateway
│   │   ├── WebSocketStack.ts         # WebSocket API (V1)
│   │   ├── WebSocketStackV2.ts       # 🆕 WebSocket API (V2)
│   │   └── MonitoringStack.ts        # CloudWatch
│   ├── lambdas/
│   │   ├── ocr-processor/            # Textract integration
│   │   ├── api-handler/              # API Gateway handler
│   │   └── embedder/                 # ⚠️ NOT USED (Bedrock handles this)
│   └── config/
│       ├── environments.ts           # Environment config
│       └── security.config.ts        # Security policies
├── docs/
│   ├── INDEX.md                      # Documentation index
│   ├── API_QUICKREF.md               # API quick reference
│   ├── API_USAGE.md                  # Complete API guide
│   ├── ARCHITECTURE_DIAGRAM.md       # System architecture
│   ├── TESTING_GUIDE.md              # Testing procedures
│   ├── SYSTEM_OVERVIEW.md            # Detailed documentation
│   └── LAMBDA_INVENTORY.md           # Lambda status inventory
├── scripts/
│   ├── test-api.py                   # API endpoint test
│   ├── test-agent.py                 # Direct agent test (V1)
│   ├── test-agent-v2-http.py         # 🆕 Agent V2 HTTP test
│   ├── test-ocr-agent.py             # OCR flow test
│   ├── test-dos-flujos.py            # Dual flow test
│   └── create-ocr-image.py           # Generate test images
├── CLAUDE.md                         # 🆕 Claude Code project instructions
└── README.md                         # This file
```

---

## ⚠️ Important Notes

### What's NOT Used

The following components exist in the infrastructure but are **NOT actively used**:

1. **Embedder Lambda** (`lambdas/embedder/`) - Bedrock KB generates embeddings automatically
2. **SQS Chunks Queue** - Not needed; Bedrock handles chunking internally
3. **vectorsBucket (regular S3)** - Only VectorBucket (AWS::S3Vectors) is used

These may be removed in a future cleanup. For now, they're deployed but inactive.

### Cost Optimization

**S3 Vector Storage** is ~90% cheaper than OpenSearch Serverless:
- **S3 Vectors**: ~$0.024/GB/month
- **OpenSearch**: ~$0.24/GB/month

Current setup with 1GB of vectors: **~$0.02/month** vs $2.40/month.

---

## 🐛 Troubleshooting

### Agent V2 Issues

#### Issue: "max_tokens limit" error

**Solution:** ✅ Fixed in current version
- Framework truncated to 2000 chars at load time
- Responses max 4000 chars
- System prompt reduced to 28 lines
- If issue persists, reduce `NORMATIVE_FRAMEWORK[:2000]` to lower value in `agents/main.py:38`

#### Issue: Agent returns technical errors to user

**Solution:** ✅ Fixed in current version
- User sees: "Disculpa, tuve un problema procesando tu pregunta. ¿Puedes intentarlo de nuevo?"
- Technical details logged to CloudWatch
- Check logs: `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --profile ans-super`

#### Issue: Responses contain `<thinking>` tags

**Solution:** ✅ Fixed in current version
- `remove_thinking_tags()` filters them before sending to user
- Original tags still visible in CloudWatch logs for debugging

#### Issue: Slow response time

**Solution:** ✅ Fixed in current version
- Streaming chunks reduced to 3 words (was 10)
- To adjust: modify `agents/main.py:207` chunk size

#### Issue: Compilation errors

**Check:**
```bash
cd infrastructure
npm run build
```

**Solution:**
Fix TypeScript errors in:
- `lib/AgentStackV2.ts`
- `bin/app.ts`
- `config/environments.ts`

#### Issue: Docker build fails during deployment

**Check:**
```bash
cd agents
python3 -c "import strands; import strands_tools; print('OK')"
```

**Solution:**
Update `agents/requirements.txt` and ensure all dependencies are compatible:
```bash
pip install -r requirements.txt
```

#### Issue: Agent not responding

**Check logs:**
```bash
# Runtime logs
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super

# Deployment logs
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-agent-v2 \
  --max-items 20 \
  --profile ans-super
```

**Solution:**
Check for runtime errors in logs and redeploy if needed.

### Agent V1 Issues

#### Issue: OCR not processing images

**Check:**
1. File extension is supported (`.png`, `.jpg`, `.pdf`, `.tiff`)
2. OCR Lambda logs: `aws logs tail /aws/lambda/processapp-ocr-processor-dev`
3. Textract limits not exceeded

**Solution:**
Re-upload file or check Textract service quotas.

#### Issue: Agent not finding documents

**Check:**
1. Ingestion job completed: `aws bedrock-agent get-ingestion-job`
2. Documents uploaded to correct prefix: `documents/`
3. KB sync ran after upload

**Solution:**
```bash
# Trigger manual sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID}
```

#### Issue: Access denied on S3 upload

**Check:**
1. KMS encryption specified: `--sse aws:kms --sse-kms-key-id ${KMS_KEY_ID}`
2. IAM user has permissions (check SecurityStack.ts line 81-100)

**Solution:**
Ensure bucket policy allows your IAM principal and KMS key access.

---

## ✅ Pre-Deployment Checklist

Before deploying Agent V2, verify:

```bash
# 1. AWS Profile configured
aws sts get-caller-identity --profile ans-super

# 2. Dependencies installed
cd infrastructure
npm install

# 3. TypeScript compiles without errors
npm run build
# Should complete with no errors

# 4. Python dependencies valid
cd ../agents
pip install -r requirements.txt
python3 -c "import strands; import strands_tools; print('✅ Dependencies OK')"

# 5. Agent code has no syntax errors
python3 -m py_compile main.py
# Should complete with no output

# 6. Ready to deploy
cd ../infrastructure
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

---

## 🆕 Recent Changes (2026-04-29)

### Agent V2 Simplification & Optimization

**Major update:** Simplified agent codebase by ~70% while improving performance and reliability.

**Code reduction:**
- Before: 849 lines
- After: 259 lines
- Reduction: ~70%

**Key improvements:**
1. ✅ **Removed `<thinking>` tags** - Clean output for users, full context in logs
2. ✅ **Reduced latency** - Streaming chunks: 10 words → 3 words (~70% faster initial response)
3. ✅ **User-friendly errors** - Generic messages for users, detailed traces in CloudWatch
4. ✅ **Token overflow prevention** - Aggressive truncation at load time (2000 chars framework, 4000 chars max response)
5. ✅ **Simplified session management** - Removed complex classes, using simple dict
6. ✅ **Clean system prompt** - Reduced from 590 lines to 28 lines

**Removed complexity:**
- ❌ `ConversationMessage`, `SessionConversation`, `ConversationStore` classes
- ❌ Background cleanup threads
- ❌ Multiple truncation strategies
- ❌ Session statistics endpoints
- ❌ `get_project_info` tool (unused)

**Files modified:**
- `agents/main.py` - Core agent implementation (now 259 lines)
- `scripts/test-websocket.sh` - New WebSocket test utility
- `CLAUDE.md` - Updated with optimization details
- `README.md` - Updated troubleshooting section

**Test the improvements:**
```bash
wscat -c wss://0wyp9wnba7.execute-api.us-east-1.amazonaws.com/dev
{"action":"sendMessage","data":{"inputText":"¿Cómo me puedes ayudar?","sessionId":"test"}}
```

---

## 📝 License

Internal use only - ProcessApp infrastructure.

---

## 📚 Complete Documentation

**Full documentation index:** [docs/INDEX.md](docs/INDEX.md)

### Quick Links
- **[API Quick Reference](docs/API_QUICKREF.md)** - One-page API cheat sheet
- **[API Complete Guide](docs/API_USAGE.md)** - REST API full documentation
- **[System Overview](docs/SYSTEM_OVERVIEW.md)** - Detailed architecture
- **[Testing Guide](docs/TESTING_GUIDE.md)** - End-to-end testing
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Infrastructure deployment
- **[Architecture Diagrams](docs/ARCHITECTURE_DIAGRAM.md)** - Visual architecture

## 👥 Support

For issues or questions:
- Check CloudWatch logs first
- Review [docs/INDEX.md](docs/INDEX.md) for complete documentation index
- Review [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) for testing procedures
- Review [docs/SYSTEM_OVERVIEW.md](docs/SYSTEM_OVERVIEW.md) for architecture details
