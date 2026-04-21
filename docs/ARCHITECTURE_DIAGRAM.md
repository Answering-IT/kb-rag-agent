# ProcessApp RAG Infrastructure - Architecture Diagrams

Comprehensive architecture documentation for the ProcessApp RAG (Retrieval-Augmented Generation) system.

**Last Updated**: 2026-04-21
**Version**: 2.0 (Simplified Architecture - Bedrock Native Processing)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Main Architecture Diagram](#main-architecture-diagram)
3. [Document Ingestion Pipeline](#document-ingestion-pipeline)
4. [Query Flow Diagram](#query-flow-diagram)
5. [OCR Processing Flow](#ocr-processing-flow)
6. [Security Architecture](#security-architecture)
7. [Component Details](#component-details)
8. [Legacy Components](#legacy-components)

---

## System Overview

ProcessApp RAG is a serverless, multi-tenant RAG system built on AWS Bedrock, featuring:

- **7 CloudFormation Stacks**: PrereqsStack, SecurityStack, BedrockStack, DocumentProcessingStack, GuardrailsStack, AgentStack, MonitoringStack
- **Foundation Model**: Amazon Nova Pro for query responses
- **Embedding Model**: Amazon Titan Embed Text v2 (1024 dimensions)
- **Vector Storage**: S3 Vectors (90% cheaper than OpenSearch)
- **Content Safety**: Bedrock Guardrails with PII filtering
- **OCR Processing**: AWS Textract for document extraction
- **Orchestration**: Bedrock Agent Core for query management

**Key Architecture Decisions**:
- ✅ Bedrock native processing (chunking + embedding handled automatically)
- ✅ S3 Vectors over OpenSearch (cost optimization: $0.024/GB vs $0.24/GB)
- ✅ Serverless-first (Lambda, EventBridge, S3)
- ✅ Simplified OCR flow (extract text → save to S3 → Bedrock processes)
- ✅ Multi-region ready (currently single-region: us-east-1)
- ✅ Stage-based multi-tenancy (dev/staging/prod isolation)

---

## Main Architecture Diagram

### Complete System Architecture (Current Implementation)

```mermaid
graph TB
    %% User Layer
    subgraph "User Interaction"
        CLI[AWS CLI / SDK<br/>Python Scripts]
        Future[Web UI<br/>Future]
    end

    %% Agent Layer
    subgraph "AI Agent Layer"
        Agent[Bedrock Agent Core<br/>Amazon Nova Pro]
        Guardrails[Bedrock Guardrails<br/>PII + Content Filters]
    end

    %% RAG Core
    subgraph "Knowledge Base Layer"
        KB[Bedrock Knowledge Base<br/>Vector Search]
        VectorIndex[S3 Vector Index<br/>AWS::S3Vectors]
        DataSource[S3 Data Source<br/>docs bucket/documents/]
    end

    %% Document Processing - SIMPLIFIED
    subgraph "Document Ingestion Pipeline"
        Upload[User Upload<br/>to S3 docs bucket]
        EventBridge[EventBridge Rule<br/>Object Created Event]

        subgraph "Smart Routing"
            Router{File Type?}
        end

        subgraph "OCR Path"
            OCRLambda[OCR Lambda<br/>Textract]
            ProcessedText[Processed Text<br/>documents/processed-*.txt]
        end

        subgraph "Direct Path"
            DirectDocs[Text Documents<br/>.txt .docx .md]
        end
    end

    %% KB Sync
    subgraph "Bedrock Native Processing"
        SyncSchedule[Scheduled Sync<br/>Every 6h]
        ManualSync[Manual Trigger<br/>via CLI/Lambda]
        BedrockIngestion[Bedrock Ingestion Job<br/>Chunking + Embedding + Indexing]
    end

    %% Monitoring
    subgraph "Observability"
        CloudWatch[CloudWatch Logs]
        Dashboard[Metrics Dashboard]
        XRay[X-Ray Tracing]
    end

    %% Security
    subgraph "Security"
        KMS[KMS Encryption<br/>All data at rest]
        IAM[IAM Roles<br/>Least privilege]
        S3Policy[Bucket Policies<br/>Block public access]
    end

    %% Connections
    CLI -->|Query| Agent
    Agent -->|Apply filters| Guardrails
    Guardrails -->|Generate response| Agent
    Agent -->|Retrieve context| KB
    KB -->|Vector search| VectorIndex
    KB -->|Read documents| DataSource

    Upload --> EventBridge
    EventBridge --> Router
    Router -->|Images/PDFs<br/>.png .jpg .pdf| OCRLambda
    Router -->|Text files<br/>.txt .docx .md| DirectDocs
    OCRLambda --> ProcessedText
    ProcessedText --> DataSource
    DirectDocs --> DataSource

    SyncSchedule --> BedrockIngestion
    ManualSync --> BedrockIngestion
    BedrockIngestion -->|Read from| DataSource
    BedrockIngestion -->|Write to| VectorIndex

    Agent --> CloudWatch
    OCRLambda --> CloudWatch
    BedrockIngestion --> CloudWatch
    CloudWatch --> Dashboard

    KMS -.->|Encrypt| DataSource
    KMS -.->|Encrypt| VectorIndex
    IAM -.->|Permissions| Agent
    IAM -.->|Permissions| OCRLambda
    S3Policy -.->|Protect| DataSource

    %% Styling
    style Agent fill:#e1f5ff
    style KB fill:#e8f5e9
    style OCRLambda fill:#fff4e6
    style BedrockIngestion fill:#e8f5e9
    style Router fill:#fff4e6
```

**Key:**
- 🟦 Blue = AI/ML components
- 🟩 Green = Bedrock native processing
- 🟨 Yellow = Custom Lambda processing

---

## Document Ingestion Pipeline

### Detailed Ingestion Flow

```mermaid
sequenceDiagram
    participant User
    participant S3 as S3 Docs Bucket
    participant EB as EventBridge
    participant OCR as OCR Lambda
    participant Textract
    participant SNS as SNS Topic
    participant KB as Bedrock KB
    participant Vector as Vector Index

    %% Upload
    User->>S3: Upload document<br/>(with KMS encryption)
    S3->>EB: Object Created Event

    %% Route based on file type
    alt Image/PDF (needs OCR)
        EB->>OCR: Trigger Lambda
        OCR->>Textract: Start async job<br/>(PNG, JPG, PDF)
        Textract-->>SNS: Job complete notification
        SNS->>OCR: SNS trigger
        OCR->>Textract: Get results
        OCR->>S3: Save processed text<br/>documents/processed-*.txt
        Note over OCR,S3: Atomic write with KMS
    else Text file (no OCR needed)
        Note over EB: No processing needed<br/>Bedrock reads directly
    end

    %% KB Sync (manual or scheduled)
    User->>KB: Trigger ingestion job<br/>(manual or scheduled)
    KB->>S3: Read all documents/<br/>including processed/
    KB->>KB: Bedrock processing:<br/>1. Chunk (512 tokens)<br/>2. Embed (Titan v2)<br/>3. Index
    KB->>Vector: Write vectors<br/>(S3 Vectors storage)
    Vector-->>KB: Indexing complete
    KB-->>User: Ingestion job status:<br/>COMPLETE
```

### Smart Routing Logic

The system automatically routes documents based on file type:

| File Type | Extension | Processing Path | Output |
|-----------|-----------|-----------------|---------|
| Images | `.png`, `.jpg`, `.jpeg`, `.tiff` | OCR Lambda → Textract | `documents/processed-*.txt` |
| PDF Documents | `.pdf` | OCR Lambda → Textract | `documents/processed-*.txt` |
| Text Documents | `.txt`, `.docx`, `.md` | Direct to Bedrock | Original file read directly |

**Why this approach?**
- ✅ Only process files that need OCR (saves cost)
- ✅ Text files go directly to Bedrock (faster)
- ✅ All vectorization handled by Bedrock (consistent, optimized)

---

## Query Flow Diagram

### Agent Query Processing

```mermaid
sequenceDiagram
    participant User
    participant Agent as Bedrock Agent
    participant Guard as Guardrails
    participant KB as Knowledge Base
    participant Vector as Vector Index
    participant LLM as Amazon Nova Pro

    User->>Agent: Ask question<br/>("What was the incident date?")

    %% Input filtering
    Agent->>Guard: Check input
    Guard->>Guard: Scan for:<br/>- Prompt attacks<br/>- Inappropriate content
    Guard-->>Agent: Input OK

    %% Retrieve context
    Agent->>KB: Retrieve relevant context
    KB->>Vector: Vector similarity search<br/>(semantic search)
    Vector-->>KB: Top K chunks (K=5)
    KB-->>Agent: Context chunks

    %% Generate response
    Agent->>LLM: Generate response with:<br/>- User question<br/>- Retrieved context<br/>- System prompt
    LLM-->>Agent: Generated answer

    %% Output filtering
    Agent->>Guard: Check output
    Guard->>Guard: Scan for:<br/>- PII (names, SSN, etc.)<br/>- Sensitive content
    alt PII detected
        Guard-->>Agent: Block response
        Agent-->>User: "Content blocked by filters"
    else No PII
        Guard-->>Agent: Output OK
        Agent-->>User: Final answer
    end
```

### Guardrails Protection

**Input Filters:**
- ✅ Prompt injection detection
- ✅ Hate speech detection
- ✅ Violence/sexual content detection

**Output Filters:**
- ✅ PII redaction (names, SSN, credit cards, addresses)
- ✅ Content policy enforcement
- ✅ Hallucination detection (via Knowledge Base grounding)

---

## OCR Processing Flow

### Textract Integration Details

```mermaid
flowchart TB
    Start[PNG/PDF/JPG Upload] --> Check{EventBridge<br/>Rule Match}
    Check -->|documents/ prefix| OCRStart[OCR Lambda Triggered]

    OCRStart --> Textract1[Start Textract Job<br/>Async API]
    Textract1 --> SNS[Textract publishes<br/>to SNS topic]
    SNS --> OCRCallback[OCR Lambda<br/>SNS trigger]

    OCRCallback --> GetResults[Get Textract Results<br/>Paginated]
    GetResults --> Extract[Extract text<br/>from LINE blocks]

    Extract --> WriteTemp[Write to S3:<br/>documents/processed-{name}.txt]
    WriteTemp --> Encrypt{KMS<br/>Encryption}
    Encrypt -->|Success| Done[Processing Complete]
    Encrypt -->|Error| Retry[Log error & cleanup]

    Done --> Wait[Wait for KB Sync<br/>Manual or Scheduled]
    Wait --> KBRead[Bedrock reads<br/>processed text]
    KBRead --> Chunk[Bedrock chunks text<br/>512 tokens, 20% overlap]
    Chunk --> Embed[Bedrock generates embeddings<br/>Titan v2]
    Embed --> Index[Store in Vector Index<br/>S3 Vectors]

    style OCRStart fill:#fff4e6
    style Textract1 fill:#e1f5ff
    style Chunk fill:#e8f5e9
    style Embed fill:#e8f5e9
    style Index fill:#e8f5e9
```

**Textract Configuration:**
- **API**: `StartDocumentTextDetection` (async)
- **Features**: LINE detection (text extraction)
- **Notification**: SNS topic triggers Lambda when job completes
- **Average Duration**: 5-10 seconds for typical documents
- **Output Format**: Plain text (UTF-8)

---

## Security Architecture

### Security Layers

```mermaid
graph TB
    subgraph "Data Protection"
        KMS[KMS Customer Managed Key<br/>e6a714f6-...]
        S3Encrypt[S3 Server-Side Encryption<br/>aws:kms]
        InTransit[TLS 1.2+ in transit]
    end

    subgraph "Access Control"
        IAMRoles[IAM Roles<br/>Least Privilege]
        BucketPolicy[S3 Bucket Policies<br/>- Block public access<br/>- Require encryption<br/>- Enforce HTTPS]
        VPCEndpoint[VPC Endpoint<br/>Optional]
    end

    subgraph "Content Safety"
        Guardrails[Bedrock Guardrails<br/>- PII Detection<br/>- Content Filtering<br/>- Prompt Attack Detection]
        Logging[CloudWatch Logs<br/>Audit Trail]
    end

    subgraph "Network Security"
        PrivateLink[AWS PrivateLink<br/>Bedrock Service]
        SecGroups[Security Groups<br/>Future VPC deployment]
    end

    KMS --> S3Encrypt
    S3Encrypt --> BucketPolicy
    IAMRoles --> BucketPolicy
    Guardrails --> Logging
    PrivateLink --> Guardrails
```

**Key Security Features:**
1. **Encryption at Rest**: All S3 objects encrypted with KMS
2. **Encryption in Transit**: TLS 1.2+ for all API calls
3. **PII Protection**: Automatic detection and blocking of sensitive data
4. **Access Logging**: CloudWatch Logs retain all API calls
5. **Least Privilege**: Each component has minimal required permissions

---

## Component Details

### 1. PrereqsStack

**Purpose**: Foundation infrastructure (S3, KMS, IAM)

| Resource | Name | Purpose |
|----------|------|---------|
| S3 Bucket | `processapp-docs-v2-dev-*` | Document storage |
| S3 Bucket | `processapp-vectors-v2-dev-*` | Legacy (not used) |
| KMS Key | `processapp-kms-dev` | Data encryption |
| IAM Role | `processapp-bedrock-kb-role-dev` | Bedrock KB permissions |

### 2. BedrockStack

**Purpose**: Knowledge Base and Vector Index

| Resource | Configuration |
|----------|---------------|
| Knowledge Base | S3 Vectors storage |
| Data Source | S3 bucket, `documents/` prefix |
| Vector Index | AWS::S3Vectors custom resource |
| Chunking | 512 tokens, 20% overlap |
| Embedding Model | Amazon Titan Embed Text v2 |

### 3. DocumentProcessingStack

**Purpose**: OCR processing with Textract

| Component | Configuration |
|-----------|---------------|
| OCR Lambda | Python 3.11, 1024 MB, 60s timeout |
| SNS Topic | Textract completion notifications |
| Textract Role | Allows Textract → SNS publish |
| EventBridge Rule | Triggers on S3 Object Created |

**Environment Variables:**
- `DOCS_BUCKET`: S3 bucket name
- `TEXTRACT_SNS_TOPIC_ARN`: SNS topic for notifications
- `TEXTRACT_ROLE_ARN`: IAM role for Textract
- `KMS_KEY_ID`: Encryption key
- `STAGE`: Deployment stage

### 4. AgentStack

**Purpose**: Bedrock Agent Core for queries

| Component | Configuration |
|-----------|---------------|
| Foundation Model | `amazon.nova-pro-v1:0` |
| Agent Alias | `live` (auto-routes to latest version) |
| Knowledge Base | Connected to RAG KB |
| Guardrails | PII + content filtering |
| Temperature | 0.7 |
| Max Tokens | 4096 |

### 5. GuardrailsStack

**Purpose**: Content safety and PII protection

| Filter Type | Configuration |
|-------------|---------------|
| **PII Entities** | EMAIL, PHONE, NAME, ADDRESS, US_SSN, CREDIT_CARD, US_PASSPORT, US_BANK_ACCOUNT, AGE |
| **Content Filters** | HATE (HIGH), INSULTS (MEDIUM), SEXUAL (HIGH), VIOLENCE (MEDIUM), MISCONDUCT (MEDIUM) |
| **Prompt Attack** | Input: HIGH, Output: NONE (required) |
| **Action** | BLOCK on detection |

---

## Legacy Components

### ⚠️ Components Deployed but NOT Used

The following exist in the infrastructure but are **inactive**:

| Component | Status | Reason |
|-----------|--------|--------|
| **Embedder Lambda** | 🔴 NOT USED | Bedrock generates embeddings natively |
| **SQS Chunks Queue** | 🔴 NOT USED | No chunking needed; Bedrock handles it |
| **vectorsBucket (regular S3)** | 🔴 NOT USED | Only VectorBucket (AWS::S3Vectors) is used |

**Why they exist:**
These were part of the original architecture design (Phase 1) where embedding generation was done manually. After implementing Phase 2.5 (Bedrock native processing), they became obsolete but remain deployed for potential rollback.

**Future Action:**
May be removed in a future infrastructure cleanup to reduce deployment size and CloudFormation complexity.

---

## Cost Breakdown

### Monthly Cost Estimate (1GB of documents, 1000 queries/month)

| Service | Usage | Cost |
|---------|-------|------|
| **S3 Docs Storage** | 1 GB | $0.023 |
| **S3 Vector Storage** | 1 GB vectors | $0.024 |
| **Bedrock Embeddings** | 1M tokens | $0.10 |
| **Bedrock Agent (Nova Pro)** | 1000 queries, 500K tokens | $3.00 |
| **Textract** | 100 pages OCR | $1.50 |
| **Lambda Invocations** | 1000 invocations | $0.20 |
| **CloudWatch Logs** | 5 GB | $0.25 |
| **KMS** | 1 key | $1.00 |
| **TOTAL** | | **~$6.00/month** |

**Cost Optimization:**
- ✅ S3 Vectors: 90% cheaper than OpenSearch ($0.024/GB vs $0.24/GB)
- ✅ Serverless: No idle costs
- ✅ Amazon Nova Pro: More cost-effective than Claude models

---

## Deployment Regions

### Current: Single Region

| Region | Stage | Status |
|--------|-------|--------|
| us-east-1 | dev | ✅ Active |

### Future: Multi-Region

Planned regions for production:
- **us-east-1** (Primary)
- **eu-west-1** (Europe)
- **ap-southeast-1** (APAC)

Multi-region requires:
- Cross-region S3 replication
- DynamoDB global tables (for session state)
- Route53 for DNS failover

---

## Change Log

### Version 2.0 (2026-04-21)
- ✅ Simplified architecture: Bedrock native processing
- ✅ Removed custom chunking/embedding logic
- ✅ OCR Lambda only extracts text (no SQS)
- ✅ Updated model: Amazon Nova Pro
- ✅ Marked legacy components

### Version 1.0 (2026-04-17)
- Initial architecture with Embedder Lambda
- Custom chunking and embedding pipeline
- Claude 3.5 Sonnet model

---

## References

- [AWS Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [S3 Vector Storage](https://aws.amazon.com/blogs/aws/introducing-s3-vector-storage/)
- [AWS Textract](https://docs.aws.amazon.com/textract/latest/dg/what-is.html)
- [Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
