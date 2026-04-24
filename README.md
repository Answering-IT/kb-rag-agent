# ProcessApp RAG - Knowledge Base Agent

Multi-tenant RAG (Retrieval-Augmented Generation) infrastructure using AWS Bedrock, S3 Vector storage, and serverless document processing.

## 🚀 Quick Start

### For Backend Developers - Use the REST API

The fastest way to query the RAG system is via our REST API endpoint:

**API Endpoint:** `https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query`

```bash
# 1. Get your API key (ask admin)
aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text

# 2. Make a query
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"question": "What documents do you have?"}'

# Response
{
  "answer": "I have documents about...",
  "sessionId": "abc-123-def",
  "status": "success"
}
```

📖 **Documentation:**
- **Quick Reference:** [docs/API_QUICKREF.md](docs/API_QUICKREF.md) - One-page cheat sheet
- **Complete API Guide:** [docs/API_USAGE.md](docs/API_USAGE.md) - Full reference with error handling, rate limits, and advanced usage

---

### For Infrastructure Developers

#### Prerequisites

- AWS CLI configured with credentials
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

## 💬 Querying the Agent

### Option 1: Via REST API (Recommended for Backends)

The agent is exposed via API Gateway for easy integration from any backend.

**Endpoint:** `https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query`

**Get API Key:**
```bash
# Ask admin to retrieve API key
aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text

# Set as environment variable
export API_KEY="<your-api-key>"
```

**Quick Example (curl):**
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{"question": "What documents do you have?"}'
```

**Python Example:**
```python
import requests

API_ENDPOINT = "https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query"
API_KEY = "your-api-key"

response = requests.post(
    API_ENDPOINT,
    headers={"Content-Type": "application/json", "x-api-key": API_KEY},
    json={"question": "What was the incident date?"}
)

result = response.json()
print(result['answer'])
```

**Test Script:**
```bash
# Set API key first
export API_KEY="your-api-key"

# Run tests
python3 scripts/test-api.py
```

📖 **Full API Documentation:** [docs/API_USAGE.md](docs/API_USAGE.md)

### Option 2: Using Python SDK (Direct AWS Access)

Create a script `query-agent.py`:

```python
#!/usr/bin/env python3
import boto3
import json
import uuid

# Initialize client
session = boto3.Session(profile_name='default')
bedrock_agent_runtime = session.client('bedrock-agent-runtime', region_name='us-east-1')

# Agent configuration
AGENT_ID = 'QWTVV3BY3G'
AGENT_ALIAS_ID = 'QZITGFMONE'

def ask_agent(question):
    """Ask a question to the Bedrock Agent"""
    session_id = str(uuid.uuid4())

    response = bedrock_agent_runtime.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=question
    )

    # Process response stream
    answer = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                answer += chunk['bytes'].decode('utf-8')

    return answer

# Example usage
if __name__ == "__main__":
    question = "What information do you have about the security incident?"
    answer = ask_agent(question)
    print(f"Q: {question}\nA: {answer}")
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
1. **PrereqsStack** - S3 buckets, KMS keys, IAM roles
2. **SecurityStack** - Bucket policies, guardrails permissions
3. **BedrockStack** - Knowledge Base, Data Source, Vector Index
4. **DocumentProcessingStack** - OCR Lambda, Textract, SNS
5. **GuardrailsStack** - Content filters and PII protection
6. **AgentStack** - Bedrock Agent with Nova Pro model
7. **APIStack** - API Gateway REST endpoint with Lambda handler
8. **MonitoringStack** - CloudWatch dashboards and alarms

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

### Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build

# Deploy all stacks
npx cdk deploy --all --profile default --require-approval never

# Deploy specific stack
npx cdk deploy dev-us-east-1-bedrock --profile default
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
├── infrastructure/
│   ├── bin/
│   │   └── app.ts                    # CDK app entry point
│   ├── lib/
│   │   ├── PrereqsStack.ts           # S3, KMS, IAM
│   │   ├── SecurityStack.ts          # Policies, guardrails
│   │   ├── BedrockStack.ts           # Knowledge Base
│   │   ├── DocumentProcessingStack.ts # OCR Lambda
│   │   ├── GuardrailsStack.ts        # Content filters
│   │   ├── AgentStack.ts             # Bedrock Agent
│   │   ├── APIStack.ts               # API Gateway
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
│   ├── test-agent.py                 # Direct agent test
│   ├── test-ocr-agent.py             # OCR flow test
│   ├── test-dos-flujos.py            # Dual flow test
│   └── create-ocr-image.py           # Generate test images
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

### Issue: OCR not processing images

**Check:**
1. File extension is supported (`.png`, `.jpg`, `.pdf`, `.tiff`)
2. OCR Lambda logs: `aws logs tail /aws/lambda/processapp-ocr-processor-dev`
3. Textract limits not exceeded

**Solution:**
Re-upload file or check Textract service quotas.

### Issue: Agent not finding documents

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

### Issue: Access denied on S3 upload

**Check:**
1. KMS encryption specified: `--sse aws:kms --sse-kms-key-id ${KMS_KEY_ID}`
2. IAM user has permissions (check SecurityStack.ts line 81-100)

**Solution:**
Ensure bucket policy allows your IAM principal and KMS key access.

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
