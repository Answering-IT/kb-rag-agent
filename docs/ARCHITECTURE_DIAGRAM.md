# ProcessApp RAG Infrastructure - Architecture Diagrams

Comprehensive architecture documentation for the ProcessApp RAG (Retrieval-Augmented Generation) system.

**Last Updated**: 2026-04-17
**Version**: 1.0 (Current Architecture with Embedder Lambda)

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Main Architecture Diagram](#main-architecture-diagram)
3. [Document Ingestion Pipeline](#document-ingestion-pipeline)
4. [Query Flow Diagram](#query-flow-diagram)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Architecture](#security-architecture)
7. [Multi-Tenant Isolation](#multi-tenant-isolation)
8. [Cost Optimization Architecture](#cost-optimization-architecture)
9. [Component Details](#component-details)

---

## System Overview

ProcessApp RAG is a serverless, multi-tenant RAG system built on AWS Bedrock, featuring:

- **7 CloudFormation Stacks**: PrereqsStack, SecurityStack, BedrockStack, DocumentProcessingStack, GuardrailsStack, AgentStack, MonitoringStack
- **Foundation Model**: Claude 3.5 Sonnet for query responses
- **Embedding Model**: Amazon Titan v2 (1024 dimensions)
- **Vector Storage**: S3 Vectors (90% cheaper than OpenSearch)
- **Content Safety**: Bedrock Guardrails with PII filtering
- **OCR Processing**: AWS Textract for document extraction
- **Orchestration**: Bedrock Agent Core for query management

**Key Architecture Decisions**:
- S3 Vectors over OpenSearch (cost optimization)
- Serverless-first (Lambda, EventBridge, S3)
- Multi-region ready (currently single-region)
- Stage-based multi-tenancy (dev/staging/prod isolation)

---

## Main Architecture Diagram

### Complete System Architecture

```mermaid
graph TB
    %% User Layer
    subgraph "User Layer"
        CLI[AWS CLI / SDK]
        WebApp[Web Application<br/>Future]
        API[API Gateway<br/>Future]
    end

    %% Agent Layer
    subgraph "Agent & Orchestration Layer"
        Agent[Bedrock Agent<br/>Claude 3.5 Sonnet]
        Guardrails[Bedrock Guardrails<br/>PII + Content Filters]
    end

    %% RAG Core
    subgraph "RAG Core - Knowledge Layer"
        KB[Bedrock Knowledge Base<br/>S3 Vectors Storage]
        VectorIndex[S3 Vector Index<br/>AWS::S3Vectors]
        DataSource[S3 Data Source<br/>documents/ prefix]
    end

    %% Document Processing
    subgraph "Document Processing Pipeline"
        DocsUpload[S3 Docs Bucket<br/>User Upload]
        EventBridge[EventBridge Rule<br/>Document Upload Event]
        OCRLambda[OCR Processor Lambda<br/>Textract Integration]
        SQSQueue[SQS Chunks Queue<br/>Text Chunks]
        EmbedderLambda[Embedder Lambda<br/>Titan v2]
        VectorsBucket[Vectors Bucket<br/>Regular S3<br/>⚠️ See Note]
    end

    %% Sync Process
    subgraph "Knowledge Base Sync"
        SyncSchedule[EventBridge Schedule<br/>Every 6 hours]
        SyncLambda[KB Sync Lambda<br/>Trigger Ingestion]
        BedrockIngestion[Bedrock Ingestion Job<br/>Chunking + Embedding]
    end

    %% Monitoring
    subgraph "Monitoring & Observability"
        CloudWatch[CloudWatch Logs<br/>All Lambda Logs]
        Dashboard[CloudWatch Dashboard<br/>Metrics]
        Alarms[CloudWatch Alarms<br/>Budgets]
        XRay[X-Ray Tracing<br/>Performance]
    end

    %% Security
    subgraph "Security Layer"
        KMS[KMS Encryption Key<br/>Data Encryption]
        IAMRoles[IAM Roles<br/>Least Privilege]
        S3Policies[S3 Bucket Policies<br/>Block Public Access]
    end

    %% Connections - User to Agent
    CLI -->|invoke-agent| Agent
    WebApp -.->|Future| API
    API -.->|Future| Agent

    %% Agent Flow
    Agent --> Guardrails
    Guardrails -->|Safe Content| Agent
    Agent -->|Query| KB
    KB -->|Retrieve| VectorIndex
    KB -->|Read Docs| DataSource

    %% Ingestion Flow - Current Architecture
    DocsUpload -->|Object Created| EventBridge
    EventBridge -->|Trigger| OCRLambda
    OCRLambda -->|Extract Text| OCRLambda
    OCRLambda -->|Send Chunks| SQSQueue
    SQSQueue -->|Process| EmbedderLambda
    EmbedderLambda -->|Generate Embeddings| EmbedderLambda
    EmbedderLambda -->|Store| VectorsBucket

    %% Bedrock Native Ingestion
    DocsUpload -->|Source| DataSource
    SyncSchedule -->|Trigger| SyncLambda
    SyncLambda -->|Start Ingestion| BedrockIngestion
    BedrockIngestion -->|Chunk + Embed| VectorIndex

    %% Monitoring Connections
    Agent -.->|Logs| CloudWatch
    OCRLambda -.->|Logs| CloudWatch
    EmbedderLambda -.->|Logs| CloudWatch
    KB -.->|Logs| CloudWatch
    CloudWatch -->|Display| Dashboard
    CloudWatch -->|Trigger| Alarms
    Agent -.->|Trace| XRay

    %% Security Connections
    KMS -.->|Encrypt| DocsUpload
    KMS -.->|Encrypt| VectorsBucket
    KMS -.->|Encrypt| SQSQueue
    IAMRoles -.->|Control| Agent
    IAMRoles -.->|Control| KB
    IAMRoles -.->|Control| OCRLambda
    S3Policies -.->|Protect| DocsUpload

    %% Styling
    classDef userLayer fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef agentLayer fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef ragLayer fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef processingLayer fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef monitoringLayer fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef securityLayer fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef warning fill:#ffebee,stroke:#b71c1c,stroke-width:3px

    class CLI,WebApp,API userLayer
    class Agent,Guardrails agentLayer
    class KB,VectorIndex,DataSource ragLayer
    class DocsUpload,EventBridge,OCRLambda,SQSQueue,EmbedderLambda,SyncSchedule,SyncLambda,BedrockIngestion processingLayer
    class CloudWatch,Dashboard,Alarms,XRay monitoringLayer
    class KMS,IAMRoles,S3Policies securityLayer
    class VectorsBucket warning
```

**⚠️ Architecture Note**: The `VectorsBucket` (regular S3) stores embeddings from the Embedder Lambda, but Bedrock KB uses `VectorIndex` (AWS::S3Vectors) instead. This creates potential duplication. See [Architecture Simplification Proposal](#architecture-simplification-proposal) below.

---

## Document Ingestion Pipeline

### Current Ingestion Flow (with Embedder Lambda)

```mermaid
sequenceDiagram
    participant User
    participant S3 as S3 Docs Bucket
    participant EB as EventBridge
    participant OCR as OCR Lambda
    participant Textract
    participant SNS as SNS Topic
    participant SQS as SQS Queue
    participant Embedder as Embedder Lambda
    participant Bedrock as Bedrock Runtime
    participant VectorsS3 as Vectors Bucket (S3)
    participant Sync as KB Sync Lambda
    participant KB as Bedrock KB
    participant VectorIdx as Vector Index

    User->>S3: Upload document (PDF/DOCX/TXT)
    S3->>EB: S3 Object Created event
    EB->>OCR: Trigger OCR Lambda

    alt Document requires OCR (PDF/Image)
        OCR->>Textract: Start document analysis
        Textract->>SNS: Job complete notification
        SNS->>OCR: Receive notification
        OCR->>OCR: Extract text, create chunks
    else Text-native document
        OCR->>OCR: Read text, create chunks
    end

    OCR->>SQS: Send text chunks
    SQS->>Embedder: Batch process (10 chunks)
    Embedder->>Bedrock: Generate embeddings (Titan v2)
    Bedrock-->>Embedder: Return embeddings
    Embedder->>VectorsS3: Store embeddings

    Note over VectorsS3: ⚠️ Embeddings stored here<br/>but NOT used by Bedrock KB

    rect rgb(255, 245, 230)
        Note over Sync,VectorIdx: Bedrock Native Pipeline (Parallel)
        Sync->>KB: Trigger ingestion job (schedule or manual)
        KB->>S3: Read original documents
        KB->>KB: Chunk documents (512 tokens, 20% overlap)
        KB->>Bedrock: Generate embeddings (Titan v2)
        Bedrock-->>KB: Return embeddings
        KB->>VectorIdx: Store vectors in S3 Vector Index
    end

    Note over Embedder,VectorIdx: ⚠️ DUPLICATION: Embeddings generated TWICE<br/>1. By Embedder Lambda → VectorsS3<br/>2. By Bedrock KB → VectorIdx
```

**Processing Time**:
- OCR (PDF with images): 30-120 seconds
- OCR (text PDF/DOCX): 5-15 seconds
- Embedding generation (per chunk): 1-2 seconds
- KB sync: 2-10 minutes (depending on document count)

---

## Query Flow Diagram

### Agent Query Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Agent as Bedrock Agent
    participant Guardrail as Guardrails
    participant KB as Knowledge Base
    participant VectorIdx as Vector Index
    participant S3 as S3 Docs
    participant Claude as Claude 3.5 Sonnet

    User->>Agent: invoke-agent (query text)
    Agent->>Guardrail: Validate input
    Guardrail-->>Agent: Input safe (or blocked)

    alt Input blocked by guardrail
        Agent-->>User: "Content violates policy"
    else Input safe
        Agent->>KB: Retrieve relevant docs
        KB->>VectorIdx: Semantic search (embeddings)
        VectorIdx-->>KB: Top 5 relevant chunks
        KB->>S3: Fetch full document content
        S3-->>KB: Document text
        KB-->>Agent: Retrieved context + citations

        Agent->>Claude: Generate response<br/>(query + context)
        Claude-->>Agent: Generated answer

        Agent->>Guardrail: Validate output
        Guardrail-->>Agent: Output safe (or filtered)

        Agent-->>User: Final response + sources
    end
```

**Query Latency Breakdown**:
- Guardrail validation (input): 50-100ms
- KB retrieval: 200-500ms
- Document fetch: 50-100ms
- Claude 3.5 Sonnet generation: 1-3 seconds
- Guardrail validation (output): 50-100ms
- **Total**: ~2-4 seconds

---

## Monitoring and Observability

### Monitoring Architecture

```mermaid
graph LR
    subgraph "Data Sources"
        Agent[Bedrock Agent]
        OCR[OCR Lambda]
        Embedder[Embedder Lambda]
        KB[Knowledge Base]
        Sync[KB Sync Lambda]
    end

    subgraph "CloudWatch"
        Logs[CloudWatch Logs<br/>Log Groups]
        Metrics[CloudWatch Metrics<br/>Custom + AWS]
        Dashboard[CloudWatch Dashboard<br/>Visualizations]
        Alarms[CloudWatch Alarms<br/>Thresholds]
    end

    subgraph "X-Ray"
        Traces[X-Ray Traces<br/>Service Map]
        Analytics[X-Ray Analytics<br/>Performance]
    end

    subgraph "Cost Management"
        Budget[AWS Budgets<br/>Cost Alerts]
        CostExplorer[Cost Explorer<br/>Analysis]
    end

    subgraph "Actions"
        SNS[SNS Topic<br/>Alerts]
        Email[Email Notifications]
        Slack[Slack Integration<br/>Future]
    end

    Agent --> Logs
    OCR --> Logs
    Embedder --> Logs
    KB --> Logs
    Sync --> Logs

    Agent --> Metrics
    OCR --> Metrics
    Embedder --> Metrics
    KB --> Metrics

    Agent --> Traces
    OCR --> Traces
    Embedder --> Traces

    Logs --> Dashboard
    Metrics --> Dashboard
    Metrics --> Alarms

    Traces --> Analytics

    Alarms --> SNS
    Budget --> SNS
    SNS --> Email
    SNS -.-> Slack

    Metrics --> CostExplorer
```

**Key Metrics Monitored**:
- Lambda invocations (OCR, Embedder, Sync)
- Lambda errors and throttles
- Agent invocation count
- Agent response latency
- KB query latency
- SQS queue depth
- Daily costs by service

---

## Security Architecture

### Security Layers

```mermaid
graph TB
    subgraph "Data Protection"
        KMS[KMS Encryption<br/>Customer Managed Key]
        S3Enc[S3 Server-Side<br/>Encryption]
        SQSEnc[SQS Encryption<br/>KMS]
        SNSEnc[SNS Encryption<br/>KMS]
    end

    subgraph "Access Control"
        IAM[IAM Roles<br/>Least Privilege]
        BucketPolicy[S3 Bucket Policies<br/>Block Public Access]
        ResourcePolicy[Resource-Based<br/>Policies]
    end

    subgraph "Content Safety"
        Guardrails[Bedrock Guardrails]
        PIIFilter[PII Detection<br/>& Blocking]
        ContentFilter[Content Filters<br/>Hate/Violence/Sexual]
        TopicBlock[Topic Blocking<br/>Financial/Medical/Legal]
    end

    subgraph "Network Security"
        VPCEndpoints[VPC Endpoints<br/>Future]
        PrivateLink[PrivateLink<br/>Bedrock Access]
    end

    subgraph "Audit & Compliance"
        CloudTrail[CloudTrail<br/>API Logging]
        ConfigRules[AWS Config<br/>Compliance]
        GuardDuty[GuardDuty<br/>Threat Detection]
    end

    KMS --> S3Enc
    KMS --> SQSEnc
    KMS --> SNSEnc

    IAM --> BucketPolicy
    IAM --> ResourcePolicy

    Guardrails --> PIIFilter
    Guardrails --> ContentFilter
    Guardrails --> TopicBlock

    VPCEndpoints -.-> PrivateLink

    CloudTrail --> ConfigRules
    CloudTrail --> GuardDuty

    style PIIFilter fill:#ffebee,stroke:#c62828
    style ContentFilter fill:#ffebee,stroke:#c62828
    style TopicBlock fill:#ffebee,stroke:#c62828
```

**PII Entities Detected**:
- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- Person names
- Organizations
- Physical addresses
- Dates of birth

**Content Filter Levels**:
- Sexual content: HIGH
- Violence: HIGH
- Hate speech: HIGH
- Insults: MEDIUM
- Misconduct: MEDIUM
- Prompt attacks: HIGH

---

## Multi-Tenant Isolation

### Stage-Based Isolation Architecture

```mermaid
graph TB
    subgraph "Development Stage"
        DevDocs[S3: processapp-docs-v2-dev-708819485463]
        DevVectors[S3: processapp-vectors-v2-dev-708819485463]
        DevKB[Bedrock KB: processapp-kb-dev]
        DevAgent[Agent: processapp-agent-dev]
        DevKMS[KMS: alias/processapp-bedrock-data-dev]
    end

    subgraph "Staging Stage (Future)"
        StagingDocs[S3: processapp-docs-v2-staging-708819485463]
        StagingVectors[S3: processapp-vectors-v2-staging-708819485463]
        StagingKB[Bedrock KB: processapp-kb-staging]
        StagingAgent[Agent: processapp-agent-staging]
        StagingKMS[KMS: alias/processapp-bedrock-data-staging]
    end

    subgraph "Production Stage (Future)"
        ProdDocs[S3: processapp-docs-v2-prod-708819485463]
        ProdVectors[S3: processapp-vectors-v2-prod-708819485463]
        ProdKB[Bedrock KB: processapp-kb-prod]
        ProdAgent[Agent: processapp-agent-prod]
        ProdKMS[KMS: alias/processapp-bedrock-data-prod]
    end

    style DevDocs fill:#e3f2fd
    style DevVectors fill:#e3f2fd
    style DevKB fill:#e3f2fd
    style DevAgent fill:#e3f2fd

    style StagingDocs fill:#fff3e0
    style StagingVectors fill:#fff3e0
    style StagingKB fill:#fff3e0
    style StagingAgent fill:#fff3e0

    style ProdDocs fill:#e8f5e9
    style ProdVectors fill:#e8f5e9
    style ProdKB fill:#e8f5e9
    style ProdAgent fill:#e8f5e9
```

**Isolation Guarantees**:
- Separate S3 buckets per stage
- Separate IAM roles per stage
- Separate KMS keys per stage
- Separate CloudWatch log groups per stage
- No cross-stage resource access

**Resource Naming Convention**:
```
processapp-{resource}-{version}-{stage}-{accountId}
```

Examples:
- `processapp-docs-v2-dev-708819485463`
- `processapp-kb-dev`
- `processapp-agent-role-dev`

---

## Cost Optimization Architecture

### S3 Vectors vs OpenSearch Cost Comparison

```mermaid
graph LR
    subgraph "OpenSearch Architecture (OLD)"
        OSCluster[OpenSearch Cluster<br/>t3.medium x 2]
        OSStorage[EBS Storage<br/>100 GB]
        OSSnapshot[Snapshots<br/>Automated]
        OSCost["💰 Cost: $150-200/month<br/>+ Management overhead"]
    end

    subgraph "S3 Vectors Architecture (CURRENT)"
        S3Bucket[S3 Vector Bucket<br/>AWS::S3Vectors]
        S3Index[Vector Index<br/>Native]
        S3Storage[S3 Storage<br/>Intelligent Tiering]
        S3Cost["💰 Cost: $15-25/month<br/>90% reduction<br/>Zero management"]
    end

    style OSCost fill:#ffebee,stroke:#c62828,stroke-width:3px
    style S3Cost fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
```

**Cost Breakdown (1000 documents, 10K queries/month)**:

| Component | OpenSearch | S3 Vectors | Savings |
|-----------|------------|------------|---------|
| Compute | $120/month | $0 (serverless) | $120 |
| Storage | $30/month | $3/month | $27 |
| Data transfer | $10/month | $2/month | $8 |
| Management | Manual | Automatic | Time saved |
| **Total** | **$160/month** | **$5/month** | **~97%** |

---

## Architecture Simplification Proposal

### BEFORE: Current Architecture (with Duplication)

```mermaid
graph TB
    Upload[Document Upload]

    subgraph "Pipeline 1: Custom Embedding"
        OCR1[OCR Lambda]
        SQS1[SQS Queue]
        Embedder[Embedder Lambda]
        VectorsS3[Vectors Bucket<br/>Regular S3]
    end

    subgraph "Pipeline 2: Bedrock Native"
        KBSync[KB Sync]
        BedrockChunk[Bedrock Chunking]
        BedrockEmbed[Bedrock Embedding]
        VectorIdx[VectorBucket<br/>AWS::S3Vectors]
    end

    Upload --> OCR1
    Upload --> KBSync
    OCR1 --> SQS1
    SQS1 --> Embedder
    Embedder --> VectorsS3

    KBSync --> BedrockChunk
    BedrockChunk --> BedrockEmbed
    BedrockEmbed --> VectorIdx

    style VectorsS3 fill:#ffebee,stroke:#c62828,stroke-width:3px
    style Embedder fill:#ffebee,stroke:#c62828,stroke-width:2px
    style SQS1 fill:#ffebee,stroke:#c62828,stroke-width:2px
```

**Problems**:
- ❌ Embeddings generated TWICE (Lambda + Bedrock)
- ❌ `VectorsBucket` (regular S3) NOT used by Bedrock KB
- ❌ Extra components (Embedder, SQS)
- ❌ ~50% higher costs
- ❌ More points of failure

### AFTER: Simplified Architecture (Proposal)

```mermaid
graph TB
    Upload[Document Upload]
    Router{Smart Routing<br/>by File Type}

    subgraph "OCR Processing (Conditional)"
        OCR2[OCR Lambda<br/>Text Extraction ONLY]
        Processed[documents/processed/]
    end

    subgraph "Bedrock Native Pipeline (Single)"
        DataSource[Data Source<br/>documents/ + documents/processed/]
        KBSync2[KB Sync]
        Bedrock[Bedrock<br/>Chunking + Embedding + Index]
        VectorIdx2[VectorBucket<br/>AWS::S3Vectors]
    end

    Upload --> Router
    Router -->|PDF/Image<br/>Requires OCR| OCR2
    Router -->|Text Native<br/>TXT/DOCX| DataSource
    OCR2 --> Processed
    Processed --> DataSource
    DataSource --> KBSync2
    KBSync2 --> Bedrock
    Bedrock --> VectorIdx2

    style Bedrock fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
    style VectorIdx2 fill:#e8f5e9,stroke:#2e7d32,stroke-width:3px
```

**Benefits**:
- ✅ Embeddings generated ONCE (Bedrock only)
- ✅ Single pipeline (simpler architecture)
- ✅ Fewer components (no Embedder, no SQS)
- ✅ ~50% cost reduction
- ✅ Fewer failure points
- ✅ Faster processing (Bedrock optimized)

**To Implement**: See Phase 2.5 in main plan

---

## Component Details

### Stack Dependencies

```mermaid
graph TD
    Prereqs[PrereqsStack<br/>S3, IAM, KMS]
    Security[SecurityStack<br/>Policies]
    Bedrock[BedrockStack<br/>KB, Vectors]
    DocProcessing[DocumentProcessingStack<br/>Lambdas, SQS]
    Guardrails[GuardrailsStack<br/>Content Safety]
    Agent[AgentStack<br/>Bedrock Agent]
    Monitoring[MonitoringStack<br/>CloudWatch]

    Prereqs --> Security
    Security --> Bedrock
    Security --> DocProcessing
    Bedrock --> Agent
    Guardrails --> Agent
    Bedrock --> Monitoring
    DocProcessing --> Monitoring

    style Prereqs fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    style Agent fill:#f3e5f5,stroke:#6a1b9a,stroke-width:3px
```

### Resource Count by Stack

| Stack | Resources | Key Components |
|-------|-----------|----------------|
| PrereqsStack | 8 | S3 buckets (2), IAM roles (3), KMS key, Log groups (2) |
| SecurityStack | 6 | IAM policies, S3 bucket policies |
| BedrockStack | 5 | KB, Data Source, Vector Index, VectorBucket, Sync Lambda |
| DocumentProcessingStack | 8 | OCR Lambda, Embedder Lambda, SQS (2), SNS, EventBridge (2) |
| GuardrailsStack | 4 | Guardrail, Version, Custom resource Lambdas (2) |
| AgentStack | 4 | Agent, Agent Alias, IAM role, Policies |
| MonitoringStack | 12 | Dashboard, Alarms (5), Metric filters (6) |
| **Total** | **47** | CloudFormation resources |

### Deployment Order

1. **PrereqsStack** (no dependencies)
2. **SecurityStack** (depends on PrereqsStack)
3. **BedrockStack** (depends on SecurityStack)
4. **DocumentProcessingStack** (depends on SecurityStack)
5. **GuardrailsStack** (no dependencies, can be parallel)
6. **AgentStack** (depends on BedrockStack + GuardrailsStack)
7. **MonitoringStack** (depends on BedrockStack + DocumentProcessingStack)

**Deployment Time**: ~15-20 minutes for all stacks

---

## References

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [S3 Vectors Announcement](https://aws.amazon.com/blogs/aws/introducing-s3-vector-storage/)
- [Bedrock Agent Core](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AWS Textract](https://docs.aws.amazon.com/textract/)
- Implementation: `infrastructure/lib/`
- Configuration: `infrastructure/config/environments.ts`

---

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-17 | 1.0 | Initial architecture documentation |
| TBD | 2.0 | After Phase 2.5 simplification (if implemented) |

---

**Status**: Current architecture documentation
**Next Update**: After Phase 2.5 (architectural simplification) if implemented
