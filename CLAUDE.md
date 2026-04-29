# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

Multi-tenant RAG (Retrieval-Augmented Generation) infrastructure using AWS Bedrock Agent Core Runtime, S3 Vector storage, and serverless document processing. Built with AWS CDK (TypeScript) and Python.

**Primary Stack:** Agent V2 (Agent Core Runtime with Strand SDK)  
**Legacy Stack:** Agent V1 (Bedrock Agent service - still deployed but not primary)

---

## AWS Configuration

**AWS Profile:** `ans-super` (configured in `infrastructure/config/environments.ts:20`)  
**Account:** 708819485463  
**Region:** us-east-1 (single region deployment)  
**Stage:** dev

```bash
export AWS_PROFILE=ans-super
aws sts get-caller-identity  # Should show account 708819485463
```

---

## Build and Deployment

### Compile Infrastructure

```bash
cd infrastructure
npm install
npm run build  # MUST pass with 0 errors before deploying
```

### Deploy Agent V2 (Current)

```bash
# Deploy only Agent V2 stack (fastest)
cd infrastructure
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never

# Deploy all stacks (full infrastructure rebuild)
npx cdk deploy --all --profile ans-super --require-approval never
```

### Verify Deployment

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent-v2 \
  --query 'Stacks[0].Outputs' \
  --profile ans-super

# Check runtime logs
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super
```

---

## Architecture Overview

### Stack Deployment Order

CDK deploys 9 stacks with strict dependencies (defined in `infrastructure/bin/app.ts:41-198`):

1. **PrereqsStack** (line 45) - S3 buckets, KMS keys, IAM roles
2. **SecurityStack** (line 57) - Bucket policies, IAM policies → depends on Prereqs
3. **BedrockStack** (line 71) - Knowledge Base, Data Source, Vector index → depends on Security
4. **DocumentProcessingStack** (line 85) - OCR Lambda with Textract → depends on Security
5. **GuardrailsStack** (line 98) - PII filters, content filters (independent)
6. **AgentStackV2** (line 112) - Agent Core Runtime (Strand SDK) → depends on Bedrock
7. **WebSocketStackV2** (line 125) - WebSocket API for streaming → depends on AgentV2
8. **BedrockStreamApiStack** (line 139) - REST streaming API → depends on AgentV2
9. **MonitoringStack** (line 172) - CloudWatch dashboards, alarms → depends on Bedrock, DocProcessing

**Important:** Stacks are deployed ONLY in GlobalResourceRegion (us-east-1). Multi-region code exists but is not active.

### Agent V2 vs Agent V1

**Agent V2 (ACTIVE - infrastructure/lib/AgentStackV2.ts):**
- Uses `@aws-cdk/aws-bedrock-agentcore-alpha` (Agent Core Runtime)
- Custom Python agent in `agents/main.py` using Strand SDK
- Specialized for Colombian pension regulations (Colpensiones)
- Tools: `consult_normative_document`, `http_request` (fetches government URLs)
- FastAPI server in Docker container
- Stack name: `dev-us-east-1-agent-v2`

**Agent V1 (LEGACY - infrastructure/lib/AgentStack.ts):**
- Uses Bedrock Agent service (managed)
- Model: Amazon Nova Pro (`amazon.nova-pro-v1:0`)
- REST API via API Gateway
- Agent IDs: `QWTVV3BY3G` / `QZITGFMONE`
- Test: `python3 scripts/test-agent.py`

**When modifying the agent, you're working with Agent V2 (`agents/main.py`), NOT Agent V1.**

### Document Processing Flow

```
S3 Upload → OCR Lambda (if image/PDF) → Bedrock KB Sync → Chunking/Embedding → S3 Vectors
```

**Key Components:**
- **OCR Lambda** (`infrastructure/lambdas/ocr-processor/index.py`) - Textract integration for images/PDFs
- **Bedrock KB** - Automatic chunking (512 tokens, 20% overlap), embedding (Titan v2), indexing
- **S3 Vectors** - Storage type (~90% cheaper than OpenSearch)
- **Sync Schedule** - Every 6 hours (`config/environments.ts:138`)

**NOT USED:** The `embedder` Lambda exists but is inactive (Bedrock KB handles embeddings natively). May be removed in future cleanup.

---

## Configuration

### Main Config: `infrastructure/config/environments.ts`

**Critical Lines:**
- **Line 20:** AWS profile `ans-super`
- **Lines 40-50:** Bedrock models (Titan v2 embedding, Claude Sonnet 4.5 LLM)
- **Lines 90-95:** Chunking strategy (512 tokens, 20% overlap)
- **Line 138:** KB sync schedule (`rate(6 hours)`)
- **Lines 156-166:** Guardrails PII entities (EMAIL, PHONE, SSN, etc.)
- **Lines 209-231:** Agent V1 system instructions
- **Lines 382-393:** Multi-tenancy config (metadata filtering enabled)

**Key Insight:** Multi-tenancy is implemented via S3 object metadata (`x-amz-meta-*` headers), not separate buckets.

### CDK Entry Point: `infrastructure/bin/app.ts`

Pattern to understand:
```typescript
// Lines 33-199: Deploy to all accounts and regions
SDLCAccounts.forEach((account) => {
  TargetRegions.forEach((region) => {
    // But stacks only created if isGlobalResourceRegion(region)
    if (isGlobalResourceRegion(region)) {
      // Create all stacks with dependency chain
    }
  });
});
```

**Why this matters:** Adding new stacks requires understanding the dependency chain and where to insert them.

---

## Modifying Agent V2

### Agent V2 Structure

```
agents/
├── main.py                           # Agent implementation (Strand SDK)
├── marco_normativo_colpensiones.md   # Normative framework index (loaded at runtime)
├── requirements.txt                  # Python dependencies
└── Dockerfile                        # Container definition (auto-built by CDK)
```

### Development Workflow

1. Edit agent code: `vim agents/main.py`
2. Verify TypeScript compiles: `cd infrastructure && npm run build`
3. Deploy: `npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never`
4. Check logs: `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super`

**Agent V2 Active Tools:**
- ✅ `consult_normative_document` - Searches normative framework index
- ✅ `http_request` (Strands) - Fetches URLs from official government sites (funcionpublica.gov.co, presidencia.gov.co)

**Disabled Tools (can be re-enabled):**
- ❌ `search_knowledge_base`
- ❌ `get_project_info`

---

## Document Management

### Upload Documents

```bash
BUCKET="processapp-docs-v2-dev-708819485463"
KMS_KEY="e6a714f6-70a7-47bf-a9ee-55d871d33cc6"

# Text files (direct to KB)
aws s3 cp document.txt s3://${BUCKET}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY} \
  --profile ans-super

# Images/PDFs (OCR processing)
aws s3 cp scanned.pdf s3://${BUCKET}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY} \
  --profile ans-super
```

**Supported Formats:**
- **Text** (no OCR): `.txt`, `.docx`, `.md`
- **OCR**: `.png`, `.jpg`, `.jpeg`, `.pdf`, `.tiff`

### Trigger Knowledge Base Sync

```bash
KB_ID=$(aws bedrock-agent list-knowledge-bases \
  --query 'knowledgeBaseSummaries[?contains(name, `processapp`)].knowledgeBaseId' \
  --output text --profile ans-super)

DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text --profile ans-super)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --profile ans-super
```

---

## Testing

### Test Agent V1 (Legacy)

```bash
python3 scripts/test-agent.py
```

### Test OCR Flow

```bash
python3 scripts/test-ocr-agent.py
```

### Monitor Agent V2

```bash
# Runtime logs
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super

# OCR Lambda logs
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile ans-super
```

---

## Troubleshooting

### CDK Build Fails

```bash
cd infrastructure
npm run build
# Fix TypeScript errors in lib/*.ts files
```

### Deployment Fails

```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-agent-v2 \
  --max-items 20 \
  --profile ans-super

# Detailed CDK logs
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --verbose
```

### OCR Not Processing

1. Verify file extension (`.png`, `.jpg`, `.pdf`, `.tiff`)
2. Check OCR logs: `aws logs tail /aws/lambda/processapp-ocr-processor-dev --profile ans-super`
3. Confirm S3 event triggers active

### Agent Not Finding Documents

1. Check ingestion job status: `aws bedrock-agent list-ingestion-jobs --knowledge-base-id ${KB_ID} --data-source-id ${DS_ID} --profile ans-super`
2. Verify documents in `documents/` prefix (not root)
3. Trigger manual sync (see "Trigger Knowledge Base Sync" above)

---

## Key Files Reference

| File | Purpose | Important Lines |
|------|---------|-----------------|
| `infrastructure/bin/app.ts` | CDK entry point, stack orchestration | 112-123 (Agent V2) |
| `infrastructure/config/environments.ts` | All configuration | 20 (profile), 40-50 (models), 90-95 (chunking) |
| `infrastructure/lib/AgentStackV2.ts` | Agent V2 CDK stack | Entire file |
| `agents/main.py` | Agent V2 implementation | Entire file |
| `infrastructure/lambdas/ocr-processor/index.py` | OCR Lambda | Entire file |
| `README.md` | User documentation | Reference for commands |

---

## Additional Documentation

Full technical documentation available in:
- **README.md** - Complete operational guide
- **docs/DEPLOYMENT_GUIDE.md** - Deployment procedures
- **docs/WEBSOCKET_STREAMING_GUIDE.md** - WebSocket API usage
- **docs/SESSION_MEMORY_GUIDE.md** - Conversation memory
- **docs/METADATA_FILTERING_SUCCESS.md** - Multi-tenancy implementation

---

**Last Updated:** 2026-04-29  
**Primary Stack:** Agent V2 (Agent Core Runtime with Strand SDK)  
**AWS Account:** 708819485463 (dev)  
**AWS Profile:** ans-super
