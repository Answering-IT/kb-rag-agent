# Lambda Functions Inventory

This document provides a comprehensive inventory of all Lambda functions in the infrastructure, categorizing them as **Active** (currently used in deployed stacks) or **Legacy** (no longer used but still present in codebase).

**Last Updated**: 2026-04-17

---

## Summary

| Status | Count | Purpose |
|--------|-------|---------|
| ✅ **Active** | 3 | Used in current architecture |
| ⚠️ **Legacy** | 4 | No longer used, candidates for removal |
| **Total** | 7 | |

---

## Active Lambda Functions

### 1. OCR Processor (`ocr-processor`)

**Status**: ✅ **ACTIVE** - Used in DocumentProcessingStack

**Purpose**: Processes uploaded documents using AWS Textract and sends extracted text chunks to SQS queue.

**Stack Reference**: `DocumentProcessingStack.ts` (lines 130-150)

**Trigger**: EventBridge rule on S3 document uploads (`documents/` prefix)

**Key Details**:
- **Runtime**: Python 3.11
- **Handler**: `index.handler`
- **Timeout**: Configured in `ProcessingConfig.lambda.ocrProcessor.timeoutSeconds`
- **Memory**: Configured in `ProcessingConfig.lambda.ocrProcessor.memoryMB`
- **Environment Variables**:
  - `DOCS_BUCKET` - Source documents bucket
  - `CHUNKS_QUEUE_URL` - SQS queue for text chunks
  - `TEXTRACT_SNS_TOPIC_ARN` - SNS topic for Textract completion notifications
  - `STAGE` - Deployment stage (dev/staging/prod)

**Event Sources**:
1. S3 EventBridge notifications (document uploads)
2. SNS notifications from Textract (job completion)

**Workflow**:
```
S3 Upload (EventBridge) → OCR Lambda → Textract Job → SNS Notification → OCR Lambda → SQS Queue
```

**IAM Permissions**:
- S3: Read from docs bucket
- Textract: Start/get document analysis
- SQS: Send messages to chunks queue
- SNS: Receive Textract notifications
- KMS: Encrypt/decrypt with data key

**Outputs**: Text chunks in JSON format sent to SQS queue

---

### 2. Embedder (`embedder`)

**Status**: ⚠️ **ACTIVE** - Used in DocumentProcessingStack, **BUT POTENTIALLY REDUNDANT**

**Purpose**: Generates embeddings using Amazon Titan v2 and stores them in S3 vectors bucket.

**Stack Reference**: `DocumentProcessingStack.ts` (lines 211-240)

**Trigger**: SQS event source (chunks queue)

**Key Details**:
- **Runtime**: Python 3.11
- **Handler**: `index.handler`
- **Timeout**: Configured in `ProcessingConfig.lambda.embedder.timeoutSeconds`
- **Memory**: Configured in `ProcessingConfig.lambda.embedder.memoryMB`
- **Concurrency**: Reserved 10 concurrent executions
- **Environment Variables**:
  - `VECTORS_BUCKET` - S3 bucket for storing embeddings
  - `EMBEDDING_MODEL` - `amazon.titan-embed-text-v2:0`
  - `STAGE` - Deployment stage

**Event Source**: SQS (processes chunks queue with batch size 10)

**Workflow**:
```
SQS Queue → Embedder Lambda → Titan v2 Embedding → S3 vectors bucket
```

**IAM Permissions**:
- SQS: Read/delete messages from chunks queue
- Bedrock: Invoke Titan embedding model
- S3: Write to vectors bucket
- KMS: Encrypt/decrypt

**⚠️ CRITICAL FINDING - POTENTIAL DUPLICATION**:

This Lambda **may be redundant** because:

1. **Bedrock KB generates its own embeddings**: The Bedrock Knowledge Base (BedrockStack.ts lines 98-123) is configured with `embeddingModelArn` pointing to the same Titan v2 model. Bedrock automatically generates embeddings during ingestion jobs.

2. **Different storage locations**:
   - This Embedder Lambda writes to `vectorsBucket` (regular S3 bucket from PrereqsStack)
   - Bedrock KB writes to `VectorBucket` (AWS::S3Vectors from BedrockStack)

3. **Workflow duplication**:
   ```
   CURRENT (DUPLICATED):
   Documents → OCR → Chunks → Embedder → vectorsBucket (UNUSED?)
   Documents → KB Sync → Bedrock Chunking → Bedrock Embedding → VectorBucket (ACTUAL)

   PROPOSED (SIMPLIFIED):
   Documents → OCR (text extraction only) → docs bucket
   docs bucket → KB Sync → Bedrock (chunking + embedding) → VectorBucket
   ```

**Recommendation**:
- **Phase 2 validation required** to confirm Bedrock KB does NOT read from the regular `vectorsBucket`
- If confirmed, this Lambda should be **eliminated** in Phase 2.5 to reduce costs and complexity
- Estimated savings: ~50% reduction in Lambda invocations and Bedrock embedding API calls

**Cost Impact**:
- Each document is currently embedded TWICE (once by this Lambda, once by Bedrock KB)
- Eliminating this Lambda would save both Lambda execution costs and Bedrock embedding costs

---

### 3. Guardrail Creator (`guardrail-creator`)

**Status**: ✅ **ACTIVE** - Used in GuardrailsStack

**Purpose**: CloudFormation custom resource for creating and managing Bedrock Guardrails.

**Stack Reference**: `GuardrailsStack.ts` (lines 60-78)

**Trigger**: CloudFormation custom resource (lifecycle events: Create/Update/Delete)

**Key Details**:
- **Runtime**: Python 3.11
- **Handler**: `index.handler`
- **Timeout**: 5 minutes
- **Memory**: 256 MB
- **Environment Variables**:
  - `STAGE` - Deployment stage

**Purpose**: Creates Bedrock Guardrails with:
- PII detection and blocking (SSN, credit cards, email, phone, etc.)
- Content filtering (hate speech, violence, sexual content, insults)
- Topic blocking (configurable)
- Custom word filters

**Workflow**:
```
CloudFormation Event → Custom Resource Provider → Guardrail Creator Lambda → Bedrock API
```

**IAM Permissions**:
- Bedrock: Create/update/delete guardrails
- Bedrock: Create guardrail versions
- Logs: Write to CloudWatch

**Outputs**:
- `GuardrailId` - Used by AgentStack
- `GuardrailArn` - Full ARN of the guardrail
- `Version` - Guardrail version number

**Note**: This Lambda is essential because Bedrock Guardrails are not yet fully supported in native CloudFormation. It implements the CloudFormation custom resource protocol (`cfnresponse`).

---

## Legacy Lambda Functions

The following Lambda functions are **no longer used** in the current architecture. They were part of the initial implementation but have been replaced by native CDK constructs or Bedrock features.

### 4. KB Creator (`kb-creator`)

**Status**: ❌ **LEGACY** - Not used

**Original Purpose**: CloudFormation custom resource for creating Bedrock Knowledge Base via boto3 API.

**Why Legacy**:
- Replaced by native CDK construct `bedrock.CfnKnowledgeBase` in BedrockStack.ts (line 98)
- Native construct provides better type safety and CloudFormation integration

**Stack Reference**: None (not referenced in any active stack)

**Can be removed**: ✅ Yes, after Phase 1 verification

**Removal Priority**: Medium - Safe to remove after confirming no external references

---

### 5. Data Source Creator (`data-source-creator`)

**Status**: ❌ **LEGACY** - Not used

**Original Purpose**: CloudFormation custom resource for creating Bedrock Data Sources.

**Why Legacy**:
- Replaced by native CDK construct `bedrock.CfnDataSource` in BedrockStack.ts (line 134)
- Native construct is more maintainable and has better CloudFormation integration

**Stack Reference**: None (not referenced in any active stack)

**Can be removed**: ✅ Yes, after Phase 1 verification

**Removal Priority**: Medium - Safe to remove after confirming no external references

---

### 6. Vector Indexer (`vector-indexer`)

**Status**: ❌ **LEGACY** - Not used

**Original Purpose**: Index vectors in S3 for RAG retrieval.

**Why Legacy**:
- Replaced by native S3 Vectors (AWS::S3Vectors::Index) in BedrockStack.ts (line 69)
- Bedrock KB handles indexing automatically during ingestion jobs
- No manual indexing required with S3 Vectors

**Stack Reference**: None (not referenced in any active stack)

**Can be removed**: ✅ Yes, after Phase 1 verification

**Removal Priority**: Medium - Safe to remove after confirming no external references

---

### 7. S3 Vector Manager (`s3-vector-manager`)

**Status**: ❌ **LEGACY** - Not used

**Original Purpose**: Manage S3 vector storage operations.

**Why Legacy**:
- S3 Vectors are now managed natively by AWS (AWS::S3Vectors::VectorBucket)
- No manual management required
- Bedrock KB handles all vector storage operations

**Stack Reference**: None (not referenced in any active stack)

**Can be removed**: ✅ Yes, after Phase 1 verification

**Removal Priority**: Medium - Safe to remove after confirming no external references

---

## Investigation Results - Vectorization Duplication

### Hypothesis: Embedder Lambda is Redundant

**Background**: During code analysis, we identified two parallel vectorization pipelines:

1. **Custom Pipeline** (via Embedder Lambda):
   ```
   S3 docs → OCR Lambda → SQS chunks → Embedder Lambda → vectorsBucket (regular S3)
   ```

2. **Bedrock Native Pipeline** (via KB Sync):
   ```
   S3 docs → KB Sync → Bedrock (chunking + embedding) → VectorBucket (AWS::S3Vectors)
   ```

### Key Questions to Validate (Phase 2)

1. **Does Bedrock KB read from `vectorsBucket` (regular S3)?**
   - **Expected Answer**: NO
   - **Verification**: Check BedrockStack.ts - KB is configured with `s3VectorsConfiguration.indexArn` pointing to VectorIndex (AWS::S3Vectors), NOT regular S3 bucket
   - **Current Evidence**: BedrockStack.ts line 107 shows KB uses VectorIndex ARN, not vectorsBucket

2. **Does Bedrock KB generate its own embeddings?**
   - **Expected Answer**: YES
   - **Verification**: Check KB configuration - `embeddingModelArn` is set in BedrockStack.ts line 115
   - **Current Evidence**: KB is configured with Titan v2 embedding model, implying Bedrock generates embeddings automatically

3. **Is `vectorsBucket` from PrereqsStack actually used anywhere?**
   - **Expected Answer**: ONLY by Embedder Lambda, which may be unnecessary
   - **Verification**: Grep for references to `vectorsBucket` in all stack files
   - **Current Evidence**: Only DocumentProcessingStack references it for Embedder Lambda

### Proposed Validation Tests (Phase 2)

**Test A: Current Pipeline (with Embedder Lambda)**
```bash
# 1. Upload test document
aws s3 cp test-sample.pdf s3://processapp-docs-v2-dev-708819485463/documents/

# 2. Monitor OCR Lambda
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow

# 3. Check SQS queue
aws sqs get-queue-attributes --queue-url <URL> --attribute-names ApproximateNumberOfMessages

# 4. Verify embeddings in vectorsBucket (regular S3)
aws s3 ls s3://processapp-vectors-v2-dev-708819485463/embeddings/

# 5. Check KB ingestion jobs
aws bedrock-agent list-ingestion-jobs --knowledge-base-id <KB_ID> --data-source-id <DS_ID>

# 6. Query agent (if exists) or KB retrieve API
```

**Test B: Bedrock Native Pipeline (skip Embedder)**
```bash
# 1. Upload test document
aws s3 cp test-sample.pdf s3://processapp-docs-v2-dev-708819485463/documents/

# 2. Manually trigger KB sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>

# 3. Monitor ingestion job
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID> \
  --ingestion-job-id <JOB_ID>

# 4. Verify vectors in VectorBucket (AWS::S3Vectors)
# Note: Cannot list directly, must check via Bedrock API

# 5. Test query via KB retrieve API
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id <KB_ID> \
  --retrieval-query "text=<query>"
```

### Expected Outcome

If Test B works correctly and returns valid results, it confirms:
- ✅ Bedrock KB does NOT need embeddings from Embedder Lambda
- ✅ Bedrock generates its own embeddings automatically
- ✅ `vectorsBucket` (regular S3) is unused by KB
- ✅ Embedder Lambda is redundant

**Action**: Proceed with Phase 2.5 architectural simplification.

---

## Deployment Status

### Currently Deployed (Verified via app.ts)

The following Lambdas are deployed in the active infrastructure:

| Lambda | Stack | Function Name | Status |
|--------|-------|---------------|--------|
| ocr-processor | DocumentProcessingStack | `processapp-ocr-processor-{stage}` | ✅ Active |
| embedder | DocumentProcessingStack | `processapp-embedder-{stage}` | ⚠️ Active (but may be redundant) |
| guardrail-creator | GuardrailsStack | `processapp-guardrail-creator-{stage}` | ✅ Active |

### Not Deployed

The following Lambda directories exist but are not referenced in any stack:

| Lambda | Reason Not Deployed |
|--------|---------------------|
| kb-creator | Replaced by `bedrock.CfnKnowledgeBase` |
| data-source-creator | Replaced by `bedrock.CfnDataSource` |
| vector-indexer | Replaced by S3 Vectors native indexing |
| s3-vector-manager | Replaced by AWS-managed S3 Vectors |

---

## Recommendations

### Immediate Actions (Phase 1)

1. ✅ **Deprecation Comments Added**:
   - Add deprecation comments to legacy Lambda directories
   - Document replacement approach in each README

2. ⏳ **Verification Required** (Phase 2):
   - Test both pipelines (with and without Embedder Lambda)
   - Confirm Bedrock KB does not read from `vectorsBucket`
   - Validate queries work with Bedrock-generated embeddings only

### Short-term Actions (Phase 2.5 - Conditional)

If Phase 2 confirms redundancy:

1. **Modify OCR Lambda**:
   - Remove chunking logic
   - Remove SQS message sending
   - Only extract text and write back to docs bucket (`documents/processed/`)

2. **Eliminate Embedder Lambda**:
   - Remove from DocumentProcessingStack.ts
   - Remove SQS chunks queue
   - Remove EventBridge rule for embeddings

3. **Remove vectorsBucket** (regular S3):
   - Remove from PrereqsStack.ts
   - Update SecurityStack to remove related policies
   - Keep only VectorBucket (AWS::S3Vectors) for Bedrock

4. **Implement Smart Routing**:
   - EventBridge routes by file type
   - PDFs/images → OCR Lambda
   - TXT/DOCX → Skip OCR, direct to KB sync

### Long-term Actions

1. **Remove Legacy Lambdas**:
   - After Phase 1 verification, remove directories:
     - `lambdas/kb-creator/`
     - `lambdas/data-source-creator/`
     - `lambdas/vector-indexer/`
     - `lambdas/s3-vector-manager/`

2. **Monitoring Guardrail Creator**:
   - Watch for native CDK support for Bedrock Guardrails
   - When available, migrate from custom resource to native construct

---

## Cost Impact Analysis

### Current Architecture (with Embedder Lambda)

**Per Document**:
- OCR Lambda invocations: 1-2 (upload + Textract completion)
- Embedder Lambda invocations: ~10-50 (depending on chunks)
- Bedrock Embedding API calls: ~10-50 (via Embedder) + ~10-50 (via KB Sync) = **DOUBLED**
- SQS messages: ~10-50

**Monthly Cost Estimate** (1000 documents/month):
- Lambda executions: ~$50-100
- Bedrock embeddings: ~$100-200 (DOUBLED due to redundancy)
- SQS: ~$1-5
- **Total**: ~$151-305/month

### Proposed Architecture (without Embedder Lambda)

**Per Document**:
- OCR Lambda invocations: 1-2 (only text extraction)
- Embedder Lambda invocations: **0** (eliminated)
- Bedrock Embedding API calls: ~10-50 (KB Sync only) = **50% REDUCTION**
- SQS messages: **0** (eliminated)

**Monthly Cost Estimate** (1000 documents/month):
- Lambda executions: ~$25-50 (50% reduction)
- Bedrock embeddings: ~$50-100 (50% reduction)
- SQS: **$0** (eliminated)
- **Total**: ~$75-150/month

**Savings**: ~$76-155/month (~50% cost reduction) + simplified architecture

---

## Next Steps

1. ✅ **Phase 1 Complete**: Repository cleaned, entry point consolidated, inventory documented
2. ⏳ **Phase 2 In Progress**: Create test documents, validate both pipelines
3. ⏳ **Phase 2 Decision**: Based on validation, decide on architectural simplification
4. ⏳ **Phase 2.5 (Conditional)**: If validated, implement simplification
5. ⏳ **Phase 3**: Implement Bedrock Agent Core
6. ⏳ **Phase 4**: Create architecture diagrams
7. ⏳ **Phase 5**: Complete documentation

---

## References

- **Stack Definitions**: `infrastructure/lib/`
- **Lambda Code**: `infrastructure/lambdas/`
- **Configuration**: `infrastructure/config/environments.ts`
- **Security Policies**: `infrastructure/config/security.config.ts`
- **Entry Point**: `infrastructure/bin/app.ts`

---

**Document Version**: 1.0
**Status**: Initial inventory completed, Phase 2 validation pending
