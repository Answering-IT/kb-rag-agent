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
- Model: Amazon Nova Pro (`amazon.nova-pro-v1:0`) - set via `MODEL_ID` environment variable
- Custom Python agent in `agents/main.py` using Strand SDK (256 lines, optimized for simplicity)
- Specialized for Colombian pension regulations (Colpensiones)
- Tools: `search_knowledge_base`, `consult_normative_document`, `http_request`
- FastAPI server in Docker container
- Stack name: `dev-us-east-1-agent-v2`
- **Optimizations:**
  - Filters `<thinking>` tags from responses (user sees clean output)
  - Streaming chunks: 3 words (low latency)
  - Token limits: 2000 chars framework, 4000 chars max response
  - User-friendly error messages (technical details only in logs)

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

**Model Assignment Flow:**
- `environments.ts:234` defines `AgentConfig.foundationModel = 'amazon.nova-pro-v1:0'`
- `AgentStackV2.ts:162` passes this to Agent V2 runtime as `MODEL_ID` environment variable
- `agents/main.py:18` has fallback to Claude 3.5 Sonnet (unused in deployment, only for local dev without env vars)

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
├── main.py                           # Agent implementation (~259 lines, simplified)
├── marco_normativo_colpensiones.md   # Normative framework index (truncated to 2000 chars)
├── metadata_handler.py               # Multi-tenant KB filtering
├── requirements.txt                  # Python dependencies
└── Dockerfile                        # Container definition (auto-built by CDK)
```

### Development Workflow

1. Edit agent code: `vim agents/main.py`
2. Verify TypeScript compiles: `cd infrastructure && npm run build`
3. Deploy: `npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never`
4. Check logs: `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super`

**Agent V2 Active Tools:**
- ✅ `search_knowledge_base` - Searches ProcessApp KB with metadata filtering (multi-tenant)
- ✅ `consult_normative_document` - Searches normative framework index
- ✅ `http_request` (Strands) - Fetches URLs from official government sites

**Design Principles (agents/main.py):**
- ✅ **Simple:** No complex session management, minimal abstractions
- ✅ **Functional:** All tools work correctly with proper error handling
- ✅ **User-friendly:** Clean output (no `<thinking>` tags, no technical errors)
- ✅ **Observable:** Detailed logs in CloudWatch for debugging
- ✅ **Fast:** 3-word streaming chunks for low latency responses

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

### Test Agent V2 (WebSocket)

```bash
# Install wscat if not available
npm install -g wscat

# Connect to WebSocket
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# Send message (copy-paste after connecting)
{"action":"sendMessage","data":{"inputText":"¿Cómo me puedes ayudar?","sessionId":"test-123"}}

# Or use the test script
./scripts/test-websocket.sh
```

**Expected behavior:**
- ✅ Response streams in chunks of 3 words (low latency)
- ✅ Clean Markdown output (no `<thinking>` tags)
- ✅ If error occurs: user sees friendly message, logs have details
- ✅ If token limit hit: response truncates at 4000 chars

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
# Runtime logs (watch for detailed errors, thinking tags, performance metrics)
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super

# OCR Lambda logs
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile ans-super
```

---

## Troubleshooting

### Agent Errors

**"max_tokens limit" error:**
- ✅ **Fixed:** Framework truncated to 2000 chars, responses max 4000 chars, system prompt reduced to 28 lines
- If still occurs: reduce `NORMATIVE_FRAMEWORK[:2000]` to lower value in `agents/main.py:38`

**Agent returns technical errors to user:**
- ✅ **Fixed:** User sees "Disculpa, tuve un problema..." message
- Technical details logged to CloudWatch: `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --profile ans-super`

**Responses contain `<thinking>` tags:**
- ✅ **Fixed:** `remove_thinking_tags()` filters them before sending to user
- Original tags still visible in CloudWatch logs for debugging

**Slow response time:**
- ✅ **Fixed:** Streaming chunks reduced to 3 words (was 10)
- To adjust: modify `agents/main.py:207` chunk size

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

## Frontend - Chat Interface

### Overview

Modern Next.js 14 bilingual chat interface with dual-mode connectivity (WebSocket/REST).

**Location:** `/fe` directory  
**Version:** v0.0.1 (defined in `fe/lib/translations.ts`)  
**Default Language:** Spanish (configurable to English)  
**Default Connection:** WebSocket (configurable to REST)

### Quick Commands

```bash
cd fe
npm install          # Install dependencies
npm run dev          # Start dev server (http://localhost:3000)
npm run build        # Build for production
npm run start        # Start production server
```

### Environment Configuration

**File:** `fe/.env.local`

```env
# WebSocket endpoint (default)
NEXT_PUBLIC_WS_URL=wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# REST streaming endpoint (alternative)
NEXT_PUBLIC_STREAMING_API_URL=https://elgoe2eluevfh2kpte4dyuttji0romxw.lambda-url.us-east-1.on.aws/

# Connection mode: 'websocket' (default) or 'streaming'
NEXT_PUBLIC_CHAT_MODE=websocket

# Show mode selector: false (default), always visible on /test
NEXT_PUBLIC_SHOW_MODE_SELECTOR=false

# Language: 'es' (default) or 'en'
NEXT_PUBLIC_LANGUAGE=es
```

### Key Features

- ✅ **Bilingual UI** - Spanish (default) and English via `NEXT_PUBLIC_LANGUAGE`
- ✅ **Dual connectivity** - WebSocket (real-time) and REST (streaming)
- ✅ **Hidden mode selector** - Selector hidden in production, visible on `/test` page
- ✅ **Version tracking** - Displayed as "Versión v0.0.1" below input field
- ✅ **Translation system** - Centralized in `lib/translations.ts`
- ✅ **Widget support** - Embeddable via iframe with postMessage API
- ✅ **Route detection** - Automatic behavior based on route (`/`, `/widget`, `/test`)

### Available Routes

| Route | Purpose | Selector Visible? | Use Case |
|-------|---------|-------------------|----------|
| `/` | Main chat interface | ❌ No | Production users |
| `/widget` | Embeddable widget | ❌ No | iframe embedding |
| `/test` | Developer test page | ✅ Yes | Testing both modes |

### Architecture

**Component Hierarchy:**
```
app/page.tsx (standalone)
app/widget/page.tsx (embeddable)
app/test/page.tsx (testing)
  └─> components/chat.tsx (shared)
      ├─> hooks/useChat.ts (mode selector)
      │   ├─> hooks/useWebSocketChat.ts (WebSocket)
      │   └─> hooks/useStreamingChat.ts (REST)
      └─> lib/translations.ts (i18n + version)
```

**Key Implementation Details:**

1. **Route Detection:** `chat.tsx` uses `usePathname()` to detect `/test` route
2. **Translation Loading:** `getTranslations()` reads `NEXT_PUBLIC_LANGUAGE` at runtime
3. **Mode Selection:** `useChat()` hook switches between WebSocket and REST based on config
4. **Widget Inheritance:** Widget uses same `<Chat>` component, inherits all features

### Translation System

**File:** `fe/lib/translations.ts`

**Structure:**
```typescript
export const APP_VERSION = 'v0.0.1';  // Single source of truth

export interface Translations {
  connectionMode: string;
  rest: string;
  websocket: string;
  // ... 11 total strings
}

export const translations: Record<Language, Translations> = {
  es: { /* Spanish strings */ },
  en: { /* English strings */ },
};

export function getTranslations(lang?: string): Translations {
  const language = (lang || process.env.NEXT_PUBLIC_LANGUAGE || 'es') as Language;
  return translations[language] || translations.es;
}
```

**Coverage:** 11 UI strings translated (ES/EN):
- Connection mode labels
- Status messages (connecting, connected)
- Empty state messages
- Input placeholders
- Button labels
- Widget loading states
- Version label

### Modifying Frontend

**To change default language:**
```env
# In fe/.env.local
NEXT_PUBLIC_LANGUAGE=en
```

**To show mode selector everywhere:**
```env
# In fe/.env.local
NEXT_PUBLIC_SHOW_MODE_SELECTOR=true
```

**To change default connection mode:**
```env
# In fe/.env.local
NEXT_PUBLIC_CHAT_MODE=streaming  # or 'websocket'
```

**To update version:**
```typescript
// In fe/lib/translations.ts
export const APP_VERSION = 'v0.0.2';  // Update here only
```

**To add new language:**
```typescript
// 1. Update type in fe/lib/translations.ts
export type Language = 'es' | 'en' | 'pt';

// 2. Add translations
export const translations: Record<Language, Translations> = {
  es: { /* ... */ },
  en: { /* ... */ },
  pt: { /* Add Portuguese translations */ },
};

// 3. Set in .env.local
NEXT_PUBLIC_LANGUAGE=pt
```

### Testing Frontend

**Test Spanish (default):**
```bash
cd fe && npm run dev
# Open http://localhost:3000
# Should see: "Inicia una conversación", "Conectado y listo"
```

**Test English:**
```bash
# Edit .env.local: NEXT_PUBLIC_LANGUAGE=en
cd fe && npm run dev
# Open http://localhost:3000
# Should see: "Start a conversation", "Connected and ready"
```

**Test connection modes:**
```bash
# Open http://localhost:3000/test
# Toggle between REST and WebSocket
# Check Network tab for connection type
```

**Test widget:**
```bash
cd fe && npm run dev
# Open http://localhost:3000/widget
# Should see: "¿Cómo puedo ayudarte?" placeholder
```

### Troubleshooting Frontend

**Mode selector not showing:**
- Intended behavior - hidden by default on production pages
- Visit `/test` page to see selector
- Set `NEXT_PUBLIC_SHOW_MODE_SELECTOR=true` to show everywhere

**Language not changing:**
- Restart dev server after editing `.env.local`
- Clear browser cache (Ctrl+Shift+R)
- Check: `cat fe/.env.local | grep LANGUAGE`

**WebSocket not connecting:**
- Check `NEXT_PUBLIC_WS_URL` in `.env.local`
- Try REST mode: `NEXT_PUBLIC_CHAT_MODE=streaming`
- Check backend: `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super`

---

## Key Files Reference

| File | Purpose | Important Lines |
|------|---------|-----------------|
| **Infrastructure** |
| `infrastructure/bin/app.ts` | CDK entry point, stack orchestration | 112-123 (Agent V2) |
| `infrastructure/config/environments.ts` | All configuration | 20 (profile), 40-50 (models), 90-95 (chunking) |
| `infrastructure/lib/AgentStackV2.ts` | Agent V2 CDK stack | Entire file |
| `agents/main.py` | Agent V2 implementation (256 lines) | 18 (MODEL_ID fallback), 38 (framework truncation), 210 (streaming chunks) |
| `infrastructure/lambdas/ocr-processor/index.py` | OCR Lambda | Entire file |
| **Frontend** |
| `fe/lib/translations.ts` | Translation strings (ES/EN) and version | 5 (APP_VERSION), 19-46 (translations) |
| `fe/components/chat.tsx` | Main chat component (shared by all pages) | 23-29 (route detection), 34-35 (mode selection) |
| `fe/hooks/useChat.ts` | Unified chat hook (mode selector) | 14 (DEFAULT_MODE), 36 (mode switching) |
| `fe/app/page.tsx` | Standalone chat page | Renders Chat component |
| `fe/app/widget/page.tsx` | Embeddable widget page | 23 (getTranslations), 155 (placeholder) |
| `fe/.env.local` | Frontend environment config | All variables |
| **Documentation** |
| `README.md` | User documentation | Reference for commands |
| `fe/README.md` | Frontend-specific documentation | Complete frontend guide |

---

## Additional Documentation

Full technical documentation available in:
- **README.md** - Complete operational guide (backend + frontend overview)
- **fe/README.md** - Frontend-specific guide (Next.js, deployment, customization)
- **docs/DEPLOYMENT_GUIDE.md** - Infrastructure deployment procedures
- **docs/WEBSOCKET_STREAMING_GUIDE.md** - WebSocket API usage
- **docs/SESSION_MEMORY_GUIDE.md** - Conversation memory
- **docs/METADATA_FILTERING_SUCCESS.md** - Multi-tenancy implementation

---

## Recent Changes (2026-04-29)

### Agent V2 Simplification & Optimization

**Code reduction:** 849 lines → 259 lines (~70% reduction)

**Improvements:**
1. ✅ **Removed `<thinking>` tags** from user responses (still in logs)
2. ✅ **Reduced latency** - streaming chunks: 10 words → 3 words
3. ✅ **User-friendly errors** - technical details only in CloudWatch logs
4. ✅ **Token overflow prevention** - aggressive truncation at load time
5. ✅ **Simplified session management** - no complex classes, just dict with last 4 messages
6. ✅ **Clean system prompt** - 590 lines → 28 lines (essential only)

**Removed complexity:**
- ❌ `ConversationMessage`, `SessionConversation`, `ConversationStore` classes
- ❌ Background cleanup threads
- ❌ Multiple truncation strategies
- ❌ Complex session statistics endpoints
- ❌ `get_project_info` tool (unused)

**Key files modified:**
- `agents/main.py` - simplified agent implementation (now 259 lines)
- `scripts/test-websocket.sh` - new WebSocket test script

**Test with:**
```bash
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev
{"action":"sendMessage","data":{"inputText":"¿Cómo me puedes ayudar?","sessionId":"test-123"}}
```

---

**Last Updated:** 2026-04-29  
**Primary Stack:** Agent V2 (Agent Core Runtime with Strand SDK, simplified)  
**Frontend Version:** v0.0.1 (Spanish default, WebSocket default)  
**AWS Account:** 708819485463 (dev)  
**AWS Profile:** ans-super  
**WebSocket URL:** `wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev`
