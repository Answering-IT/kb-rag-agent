# ProcessApp RAG Pipeline Testing Guide

This guide provides step-by-step instructions for validating the RAG pipeline and detecting architectural duplication.

**Purpose**: Determine whether the Embedder Lambda and regular `vectorsBucket` are necessary, or if Bedrock KB can handle all vectorization natively.

**Last Updated**: 2026-04-17

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Documents](#test-documents)
3. [Test A: Current Pipeline (with Embedder Lambda)](#test-a-current-pipeline-with-embedder-lambda)
4. [Test B: Bedrock Native Pipeline](#test-b-bedrock-native-pipeline)
5. [Comparative Analysis](#comparative-analysis)
6. [Decision Criteria](#decision-criteria)
7. [Troubleshooting](#troubleshooting)
8. [Appendix: Useful Commands](#appendix-useful-commands)

---

## Prerequisites

### AWS CLI Setup

```bash
# Verify AWS CLI is installed and configured
aws --version
aws sts get-caller-identity

# Set environment variables
export AWS_REGION=us-east-1
export STAGE=dev
export ACCOUNT_ID=708819485463
export DOCS_BUCKET=processapp-docs-v2-dev-${ACCOUNT_ID}
export VECTORS_BUCKET=processapp-vectors-v2-dev-${ACCOUNT_ID}  # Regular S3
export VECTOR_BUCKET_S3V=processapp-vectors-dev-${ACCOUNT_ID}   # AWS::S3Vectors
```

### Get Resource IDs

```bash
# Get Knowledge Base ID
export KB_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query "Stacks[0].Outputs[?OutputKey=='KnowledgeBaseId'].OutputValue" \
  --output text)

echo "Knowledge Base ID: $KB_ID"

# Get Data Source ID
export DS_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query "Stacks[0].Outputs[?OutputKey=='DataSourceId'].OutputValue" \
  --output text)

echo "Data Source ID: $DS_ID"

# Get SQS Queue URL
export QUEUE_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-document-processing \
  --query "Stacks[0].Outputs[?OutputKey=='ChunksQueueUrl'].OutputValue" \
  --output text)

echo "Chunks Queue URL: $QUEUE_URL"

# Get Lambda Function Names
export OCR_LAMBDA=processapp-ocr-processor-dev
export EMBEDDER_LAMBDA=processapp-embedder-dev

# Verify resources exist
aws bedrock-agent get-knowledge-base --knowledge-base-id $KB_ID
aws bedrock-agent get-data-source --knowledge-base-id $KB_ID --data-source-id $DS_ID
aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names All
```

---

## Test Documents

Test documents are located in `docs/test-fixtures/test-documents/`:

1. **test-sample.txt** - Plain text (no OCR needed)
2. **test-sample-docx.txt** - Simulated Word document (no OCR needed)
3. **test-sample-pdf.txt** - Simulated PDF (OCR pipeline test)

**Note**: For real PDF testing with OCR, create an actual PDF with scanned images or use a document scanner.

### Document Metadata

See `docs/test-fixtures/test-documents/manifest.json` for:
- Unique identifiers for each document
- Expected pipelines
- Validation queries
- Success criteria

---

## Test A: Current Pipeline (with Embedder Lambda)

**Objective**: Validate the current architecture and determine if embeddings from Embedder Lambda are used by Bedrock KB.

**Hypothesis**: Embeddings written to regular `vectorsBucket` by Embedder Lambda are NOT used by Bedrock KB.

### Step 1: Upload Test Document

```bash
# Upload plain text document
aws s3 cp docs/test-fixtures/test-documents/test-sample.txt \
  s3://${DOCS_BUCKET}/documents/test-sample.txt

echo "Document uploaded at: $(date)"
```

### Step 2: Monitor OCR Lambda

```bash
# Tail OCR Lambda logs (open in separate terminal)
aws logs tail /aws/lambda/${OCR_LAMBDA} --follow --format short

# Expected output:
# - "Received event" with S3 EventBridge notification
# - "Processing document: s3://.../test-sample.txt"
# - For TXT files: Should skip Textract or process quickly
# - "Successfully processed" or "Textract job started"
```

### Step 3: Check SQS Queue

```bash
# Check if chunks were sent to SQS
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible

# Expected output:
# ApproximateNumberOfMessages: > 0 (messages waiting)
# ApproximateNumberOfMessagesNotVisible: > 0 (messages being processed)

# Receive a sample message (peek, don't delete)
aws sqs receive-message \
  --queue-url $QUEUE_URL \
  --max-number-of-messages 1 \
  --visibility-timeout 10

# Expected: JSON with chunk_id, text, metadata
```

### Step 4: Monitor Embedder Lambda

```bash
# Tail Embedder Lambda logs (open in separate terminal)
aws logs tail /aws/lambda/${EMBEDDER_LAMBDA} --follow --format short

# Expected output:
# - "Received X messages from SQS"
# - "Processing chunk {chunk_id}"
# - "Successfully processed chunk {chunk_id}"
# - Or errors if processing fails
```

### Step 5: Verify Embeddings in Regular vectorsBucket

```bash
# List embeddings in regular S3 bucket
aws s3 ls s3://${VECTORS_BUCKET}/embeddings/ --recursive

# Expected output:
# If embeddings are being created:
# embeddings/{date}/{chunk_id}.json

# Check a sample embedding file
aws s3 cp s3://${VECTORS_BUCKET}/embeddings/{sample-file}.json - | jq .

# Expected structure:
# {
#   "chunk_id": "...",
#   "embedding": [0.123, -0.456, ...],  # 1024 dimensions
#   "text": "...",
#   "metadata": {...}
# }
```

### Step 6: Check Bedrock KB Ingestion Jobs

```bash
# List recent ingestion jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --max-results 5 \
  --query 'ingestionJobSummaries[*].[ingestionJobId,status,startedAt]' \
  --output table

# If no recent job, trigger manual sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID

# Monitor ingestion job status
export JOB_ID=<ingestion-job-id-from-above>

aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID

# Expected output:
# status: IN_PROGRESS → COMPLETE
# statistics: { numberOfDocumentsScanned, numberOfDocumentsIndexed }
```

### Step 7: ⚠️ CRITICAL - Verify What Bedrock Reads

**Question**: Does Bedrock KB read embeddings from the regular `vectorsBucket`?

**Investigation**:

```bash
# Check Bedrock KB storage configuration
aws bedrock-agent get-knowledge-base --knowledge-base-id $KB_ID \
  --query 'knowledgeBase.storageConfiguration' \
  --output json

# Expected output:
# {
#   "type": "S3_VECTORS",
#   "s3VectorsConfiguration": {
#     "indexArn": "arn:aws:s3vectors:us-east-1:708819485463:index/..."
#   }
# }

# Key finding: storageConfiguration points to S3 Vectors Index, NOT regular S3 bucket
```

**Check CloudFormation**:

```bash
# Get BedrockStack template
aws cloudformation get-template \
  --stack-name dev-us-east-1-bedrock \
  --query 'TemplateBody' \
  | jq '.Resources.KnowledgeBase.Properties.StorageConfiguration'

# Confirm: Points to VectorIndex (AWS::S3Vectors), not vectorsBucket
```

### Step 8: Test Query

```bash
# Test retrieve API (direct KB query, no agent needed)
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query "text=What embedding model does ProcessApp use?" \
  --output json

# Expected output:
# {
#   "retrievalResults": [
#     {
#       "content": { "text": "...Amazon Titan v2 with 1024 dimensions..." },
#       "score": 0.85,
#       "location": { "s3Location": {...} }
#     }
#   ]
# }

# If results are returned, KB is working
# But WHERE did the embeddings come from? (This is what we're testing!)
```

### Test A Results to Document

Record the following:

1. ✅ Did OCR Lambda process the document?
2. ✅ Were chunks sent to SQS?
3. ✅ Did Embedder Lambda create embeddings?
4. ✅ Are embeddings visible in `vectorsBucket` (regular S3)?
5. ⚠️ Does Bedrock KB storage config point to regular S3 or S3 Vectors?
6. ✅ Did KB ingestion job complete successfully?
7. ✅ Do queries return correct results?

**Critical Finding**: If KB storage config points ONLY to S3 Vectors (not regular S3), then embeddings from Embedder Lambda are **unused**.

---

## Test B: Bedrock Native Pipeline

**Objective**: Validate that Bedrock KB can process documents and generate embeddings WITHOUT the Embedder Lambda.

**Hypothesis**: Bedrock KB generates embeddings automatically during ingestion, making the Embedder Lambda redundant.

### Step 1: Upload New Test Document

```bash
# Use a different document to avoid caching
aws s3 cp docs/test-fixtures/test-documents/test-sample-docx.txt \
  s3://${DOCS_BUCKET}/documents/test-sample-docx.txt

echo "Document uploaded at: $(date)"
```

### Step 2: Manually Trigger KB Sync

**Important**: For this test, we want to observe ONLY Bedrock's native processing, so we manually trigger sync.

```bash
# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID

# Capture job ID
export JOB_ID=$(aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --max-results 1 \
  --query 'ingestionJobSummaries[0].ingestionJobId' \
  --output text)

echo "Ingestion Job ID: $JOB_ID"
```

### Step 3: Monitor Ingestion Job

```bash
# Poll ingestion job status every 10 seconds
watch -n 10 "aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID \
  --query '[status, statistics]' \
  --output json"

# Expected progression:
# status: STARTING → IN_PROGRESS → COMPLETE

# Final output should show:
# {
#   "status": "COMPLETE",
#   "statistics": {
#     "numberOfDocumentsScanned": 1,
#     "numberOfDocumentsIndexed": 1,
#     "numberOfDocumentsFailed": 0
#   }
# }
```

### Step 4: Verify Vectors in VectorBucket (AWS::S3Vectors)

**Note**: AWS::S3Vectors is a managed service, so direct S3 access is limited. We verify indirectly.

```bash
# We CANNOT directly list S3 Vectors (managed by AWS)
# But we can verify via CloudFormation that VectorBucket exists

aws cloudformation describe-stack-resources \
  --stack-name dev-us-east-1-bedrock \
  --query 'StackResources[?ResourceType==`AWS::S3Vectors::VectorBucket`]' \
  --output table

# Expected: VectorBucket resource exists

# Verify Vector Index
aws cloudformation describe-stack-resources \
  --stack-name dev-us-east-1-bedrock \
  --query 'StackResources[?ResourceType==`AWS::S3Vectors::Index`]' \
  --output table

# Expected: VectorIndex resource exists
```

### Step 5: Test Query

```bash
# Query the Knowledge Base
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query "text=What is the development account ID?" \
  --output json

# Expected output:
# {
#   "retrievalResults": [
#     {
#       "content": { "text": "...708819485463..." },
#       "score": > 0.7,
#       "location": { "s3Location": { "uri": "s3://...test-sample-docx.txt" } }
#     }
#   ]
# }

# Try multiple queries from manifest.json
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query "text=How does ProcessApp achieve multi-tenancy?" \
  --output json

aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query "text=What PII types does the guardrail detect?" \
  --output json
```

### Step 6: Verify NO Embedder Lambda Invocations

```bash
# Check Embedder Lambda was NOT invoked
aws logs filter-log-events \
  --log-group-name /aws/lambda/${EMBEDDER_LAMBDA} \
  --start-time $(date -u -d '5 minutes ago' +%s)000 \
  --query 'events[*].message' \
  --output text

# Expected: NO new log entries (or very few if processing old queue messages)

# Check SQS queue is empty or stable
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages

# Expected: 0 or low number (no new chunks for this document)
```

### Test B Results to Document

Record the following:

1. ✅ Did KB ingestion job complete successfully?
2. ✅ Were documents scanned and indexed?
3. ✅ Do queries return correct results?
4. ✅ Was Embedder Lambda NOT invoked?
5. ✅ Does the system work WITHOUT custom embedding generation?

**Critical Finding**: If queries return correct results WITHOUT Embedder Lambda, then it's REDUNDANT.

---

## Comparative Analysis

### Side-by-Side Comparison

| Aspect | Test A (Current) | Test B (Native) |
|--------|------------------|-----------------|
| **OCR Lambda** | ✅ Invoked | ✅ Invoked (if PDF/image) |
| **SQS Queue** | ✅ Chunks sent | ❌ Not used |
| **Embedder Lambda** | ✅ Invoked | ❌ Not invoked |
| **Embeddings in regular S3** | ✅ Created | ❌ Not created |
| **Bedrock Ingestion** | ✅ Runs | ✅ Runs |
| **Embeddings in S3 Vectors** | ✅ Created by Bedrock | ✅ Created by Bedrock |
| **Query Results** | ✅ Works | ✅ Works |
| **Total Embedding Calls** | 2x (Lambda + Bedrock) | 1x (Bedrock only) |

### Cost Comparison

**Test A (Current Architecture)**:
- OCR Lambda: $0.20 per 1000 invocations
- Embedder Lambda: $0.50 per 1000 invocations
- Bedrock Embeddings (Lambda): ~$0.0001 per 1K tokens × 2 = $0.0002
- Bedrock Embeddings (KB Sync): ~$0.0001 per 1K tokens × 2 = $0.0002
- SQS Messages: $0.40 per 1M requests
- **Total per 1000 docs**: ~$0.70 + $0.40 (embeddings DOUBLED)

**Test B (Simplified Architecture)**:
- OCR Lambda: $0.20 per 1000 invocations (text extraction only)
- Embedder Lambda: **$0** (eliminated)
- Bedrock Embeddings (KB Sync only): ~$0.0001 per 1K tokens × 2 = $0.0002
- SQS Messages: **$0** (eliminated)
- **Total per 1000 docs**: ~$0.20 + $0.20 (embeddings ONCE)

**Estimated Savings**: ~50% reduction in processing costs

### Performance Comparison

| Metric | Test A | Test B |
|--------|--------|--------|
| **End-to-end latency** | Higher (multiple steps) | Lower (single pipeline) |
| **Components** | 5 (OCR, SQS, Embedder, KB, Vectors) | 2 (OCR optional, KB) |
| **Points of failure** | More (Lambda errors, SQS delays) | Fewer (Bedrock managed) |
| **Complexity** | Higher (custom code) | Lower (AWS-managed) |

---

## Decision Criteria

### Proceed with Phase 2.5 Simplification IF:

✅ **All of the following are TRUE**:

1. Test B queries return correct results
2. Test B does NOT use Embedder Lambda
3. Bedrock KB storage config points to S3 Vectors (not regular S3)
4. Test A embeddings in regular `vectorsBucket` are NOT read by Bedrock
5. No functional difference between Test A and Test B query results

### Do NOT Proceed with Simplification IF:

❌ **Any of the following are TRUE**:

1. Test B queries fail or return incorrect results
2. Bedrock KB somehow reads from regular `vectorsBucket`
3. Test A results are significantly better than Test B
4. There's evidence that custom embeddings are used

---

## Troubleshooting

### Issue 1: OCR Lambda Not Triggered

**Symptoms**:
- No logs in CloudWatch for OCR Lambda
- Document uploaded but not processed

**Diagnosis**:
```bash
# Check EventBridge rule
aws events list-rules --name-prefix processapp-document-upload

# Check rule targets
aws events list-targets-by-rule --rule processapp-document-upload-dev

# Verify S3 EventBridge notification is enabled
aws s3api get-bucket-notification-configuration --bucket $DOCS_BUCKET
```

**Solutions**:
- Verify S3 bucket has EventBridge enabled
- Check IAM permissions for Lambda
- Ensure document is in correct prefix (`documents/`)

### Issue 2: Embedder Lambda Errors

**Symptoms**:
- Messages stuck in SQS queue
- Lambda errors in CloudWatch

**Diagnosis**:
```bash
# Check Lambda errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/${EMBEDDER_LAMBDA} \
  --filter-pattern "ERROR"

# Check DLQ
export DLQ_URL=$(aws sqs list-queues --queue-name-prefix processapp-chunks-dlq --query 'QueueUrls[0]' --output text)
aws sqs get-queue-attributes --queue-url $DLQ_URL --attribute-names All
```

**Solutions**:
- Check Bedrock model permissions
- Verify KMS key access
- Check S3 bucket permissions

### Issue 3: KB Ingestion Job Fails

**Symptoms**:
- Ingestion job status: FAILED
- Documents not indexed

**Diagnosis**:
```bash
# Get failure reason
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID \
  --query 'ingestionJob.[status,failureReasons]' \
  --output json

# Check Bedrock KB logs
aws logs filter-log-events \
  --log-group-name /aws/bedrock/knowledgebases/dev \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

**Solutions**:
- Verify S3 bucket permissions for Bedrock role
- Check document format (supported: PDF, TXT, MD, HTML, DOC, DOCX)
- Ensure documents are not empty
- Verify KMS key grants for Bedrock

### Issue 4: Queries Return Empty Results

**Symptoms**:
- `retrievalResults` is empty
- No matches found

**Diagnosis**:
```bash
# Check if documents were actually indexed
aws bedrock-agent get-knowledge-base --knowledge-base-id $KB_ID \
  --query 'knowledgeBase.[status,storageConfiguration]'

# Verify Data Source has documents
aws bedrock-agent get-data-source \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --query 'dataSource.[status,dataDeletionPolicy]'

# List ingestion jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID
```

**Solutions**:
- Wait for ingestion job to complete
- Trigger manual sync if scheduled sync hasn't run
- Check query text matches document content
- Try simpler queries first

### Issue 5: Permission Denied Errors

**Symptoms**:
- `AccessDeniedException` from AWS CLI
- Lambda execution failures

**Diagnosis**:
```bash
# Check your IAM permissions
aws sts get-caller-identity

# Test specific permissions
aws bedrock-agent get-knowledge-base --knowledge-base-id $KB_ID
aws s3 ls s3://${DOCS_BUCKET}/
```

**Solutions**:
- Ensure your IAM user/role has required permissions
- Check resource-based policies
- Verify KMS key grants

---

## Appendix: Useful Commands

### Monitor All Components in Parallel

Open multiple terminal windows:

**Terminal 1: OCR Lambda Logs**
```bash
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow
```

**Terminal 2: Embedder Lambda Logs**
```bash
aws logs tail /aws/lambda/processapp-embedder-dev --follow
```

**Terminal 3: SQS Queue Depth**
```bash
watch -n 5 "aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages'"
```

**Terminal 4: Bedrock KB Logs**
```bash
aws logs tail /aws/bedrock/knowledgebases/dev --follow
```

### Cleanup Test Documents

```bash
# Remove test documents from S3
aws s3 rm s3://${DOCS_BUCKET}/documents/test-sample.txt
aws s3 rm s3://${DOCS_BUCKET}/documents/test-sample-docx.txt
aws s3 rm s3://${DOCS_BUCKET}/documents/test-sample-pdf.txt

# Remove embeddings (if they exist)
aws s3 rm s3://${VECTORS_BUCKET}/embeddings/ --recursive

# Clear SQS queue (if needed)
aws sqs purge-queue --queue-url $QUEUE_URL
```

### Get Stack Outputs

```bash
# All outputs from a stack
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs' \
  --output table
```

### Check Lambda Invocations (Metrics)

```bash
# OCR Lambda invocations (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=processapp-ocr-processor-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Embedder Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=processapp-embedder-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## Conclusion

After completing Test A and Test B:

1. Document all findings in this file
2. Compare results using the tables in Comparative Analysis
3. Make decision based on Decision Criteria
4. If proceeding with simplification:
   - Update LAMBDA_INVENTORY.md with decision
   - Proceed to Phase 2.5 implementation
5. If NOT proceeding:
   - Document reasons in LAMBDA_INVENTORY.md
   - Keep current architecture
   - Proceed directly to Phase 3 (Bedrock Agent)

**Next Steps**: See main plan for Phase 2.5 (conditional) or Phase 3.

---

**Document Version**: 1.0
**Last Updated**: 2026-04-17
**Status**: Ready for execution
