# RAG Synchronization Guide

Understanding how the Knowledge Base stays synchronized with documents.

**Last Updated**: 2026-04-17

---

## Overview

Knowledge Base synchronization is the process of indexing new documents and updating the vector index so they become searchable via the RAG agent.

---

## Synchronization Architecture

### Components

```
┌─────────────────┐
│  S3 Data Source │ (documents/ prefix)
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
┌────────▼────────┐  ┌──────▼────────┐
│ EventBridge     │  │ Manual Trigger│
│ Schedule        │  │ (CLI/Lambda)  │
│ Every 6 hours   │  │               │
└────────┬────────┘  └──────┬────────┘
         │                  │
         └──────────┬───────┘
                    │
           ┌────────▼────────┐
           │  KB Sync Lambda │
           └────────┬────────┘
                    │
         ┌──────────▼───────────┐
         │ Bedrock Ingestion Job│
         │  - Read documents    │
         │  - Chunk text        │
         │  - Generate embeddings│
         │  - Index vectors     │
         └──────────┬───────────┘
                    │
           ┌────────▼────────┐
           │ S3 Vector Index │
           │ (searchable)    │
           └─────────────────┘
```

---

## Scheduled Sync

### EventBridge Schedule

**Configuration** (in BedrockStack):
```typescript
schedule: events.Schedule.expression('rate(6 hours)')
```

**Execution Times**:
- 00:00 UTC
- 06:00 UTC
- 12:00 UTC
- 18:00 UTC

**Why 6 hours?**
- Balances freshness with cost
- Suitable for most use cases
- Configurable per requirements

**Adjusting Schedule**:

Edit `config/environments.ts`:
```typescript
export const KnowledgeBaseConfig = {
  // Every hour:
  syncSchedule: 'rate(1 hour)',

  // Every 12 hours:
  syncSchedule: 'rate(12 hours)',

  // Daily at 2 AM:
  syncSchedule: 'cron(0 2 * * ? *)',
};
```

---

## Manual Sync

### Trigger via AWS CLI

```bash
# Set environment variables
export KB_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text)

export DS_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID

# Capture job ID
export JOB_ID=<ingestion-job-id-from-response>
```

### Monitor Sync Progress

```bash
# Get job status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID

# Watch status (updates every 10 seconds)
watch -n 10 "aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID \
  --query 'ingestionJob.[status,statistics]' \
  --output json"
```

### Invoke Sync Lambda Directly

```bash
export SYNC_LAMBDA=processapp-kb-sync-dev

aws lambda invoke \
  --function-name $SYNC_LAMBDA \
  --payload '{}' \
  response.json

cat response.json | jq .
```

---

## Ingestion Job Lifecycle

### Job Stages

```
STARTING → IN_PROGRESS → COMPLETE
                ↓
              FAILED
```

**STARTING**: Job is being initialized
**IN_PROGRESS**: Documents being processed
**COMPLETE**: All documents indexed successfully
**FAILED**: Job encountered errors

### Job Statistics

```json
{
  "status": "COMPLETE",
  "statistics": {
    "numberOfDocumentsScanned": 150,
    "numberOfDocumentsIndexed": 148,
    "numberOfDocumentsFailed": 2,
    "numberOfDocumentsDeleted": 0,
    "numberOfDocumentsIgnored": 0
  }
}
```

**Key Metrics**:
- `numberOfDocumentsScanned`: Total docs found
- `numberOfDocumentsIndexed`: Successfully processed
- `numberOfDocumentsFailed`: Errors encountered
- `numberOfDocumentsDeleted`: Removed from index
- `numberOfDocumentsIgnored`: Skipped (unchanged)

---

## Incremental Sync

### How It Works

Bedrock KB performs **incremental synchronization**:

1. **First Sync** (Full):
   - All documents in `documents/` prefix
   - Complete indexing
   - Can take 10-30 minutes

2. **Subsequent Syncs** (Incremental):
   - Only new/modified documents
   - Checks S3 object metadata (LastModified, ETag)
   - Faster (2-5 minutes)

3. **Deleted Documents**:
   - Detected by comparing index with S3
   - Removed from index automatically

**Benefits**:
- Faster sync times
- Lower costs
- Automatic change detection

---

## Data Source Configuration

### S3 Data Source Settings

**Configuration** (in BedrockStack):
```typescript
dataSourceConfiguration: {
  type: 'S3',
  s3Configuration: {
    bucketArn: props.docsBucket.bucketArn,
    inclusionPrefixes: ['documents/'],
  },
},
```

**Inclusion Prefixes**:
- Currently: `['documents/']`
- Can add: `['documents/', 'documents/processed/']` (for OCR output)
- Supports multiple prefixes for organization

**Exclusion Patterns** (future):
```typescript
exclusionPrefixes: ['documents/temp/', 'documents/archive/']
```

---

## Sync Performance

### Processing Times

| Documents | First Sync | Incremental Sync |
|-----------|------------|------------------|
| 10 | 30-60 seconds | 10-20 seconds |
| 100 | 2-5 minutes | 30-90 seconds |
| 1,000 | 10-20 minutes | 2-5 minutes |
| 10,000 | 1-2 hours | 10-20 minutes |

**Factors Affecting Speed**:
- Document size
- Document complexity
- Number of new/modified docs
- Bedrock service capacity

---

## Monitoring Sync

### CloudWatch Logs

```bash
# View sync Lambda logs
aws logs tail /aws/lambda/processapp-kb-sync-dev --follow

# View Bedrock KB logs
aws logs tail /aws/bedrock/knowledgebases/dev --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock/knowledgebases/dev \
  --filter-pattern "ERROR"
```

### List Recent Ingestion Jobs

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --max-results 10 \
  --query 'ingestionJobSummaries[*].[ingestionJobId,status,startedAt,statistics.numberOfDocumentsIndexed]' \
  --output table
```

---

## Troubleshooting

### Issue: Ingestion Job Fails

**Symptoms**:
- Status: FAILED
- `numberOfDocumentsFailed` > 0

**Diagnosis**:
```bash
# Get failure reasons
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID \
  --query 'ingestionJob.failureReasons' \
  --output json
```

**Common Causes**:
1. **Unsupported file format**: Only PDF, TXT, MD, HTML, DOC, DOCX
2. **Empty documents**: Documents with no text
3. **Permission issues**: Bedrock role lacks S3 access
4. **Document too large**: Max 50 MB per document
5. **Corrupted files**: PDF encryption, damaged files

**Solutions**:
- Check document format
- Verify S3 permissions
- Review Bedrock KB role policies
- Check document size limits

### Issue: Documents Not Appearing in Queries

**Symptoms**:
- Ingestion job COMPLETE
- But queries return no results

**Check**:
```bash
# Verify documents indexed
aws bedrock-agent get-data-source \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --query 'dataSource.status'

# Test retrieve API directly
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id $KB_ID \
  --retrieval-query "text=test query" \
  --output json
```

**Possible Causes**:
- Sync not complete (wait for status: COMPLETE)
- Query too specific
- Documents in wrong S3 prefix
- Data Source configuration issue

**Solutions**:
- Wait for sync to complete
- Try broader queries
- Verify document location in S3
- Check Data Source `inclusionPrefixes`

### Issue: Sync Takes Too Long

**Symptoms**:
- Ingestion job IN_PROGRESS for hours

**Check**:
```bash
# Check number of documents
aws s3 ls s3://$DOCS_BUCKET/documents/ --recursive | wc -l

# Check document sizes
aws s3 ls s3://$DOCS_BUCKET/documents/ --recursive --human-readable
```

**Solutions**:
- For large batches (1000+ docs), expect longer times
- Consider splitting into smaller batches
- Remove unnecessary documents
- Optimize document sizes

---

## Best Practices

### 1. Sync Timing

**Recommended**:
- Development: Every hour (for quick testing)
- Staging: Every 6 hours
- Production: Every 12-24 hours (unless real-time required)

### 2. Document Organization

**Good Structure**:
```
documents/
├── category-a/
├── category-b/
└── archive/  (excluded from sync)
```

**Configure Multiple Prefixes**:
```typescript
inclusionPrefixes: [
  'documents/category-a/',
  'documents/category-b/',
]
```

### 3. Monitoring

**Set up CloudWatch Alarms**:
- Ingestion job failures
- Sync duration > threshold
- Failed document count > 0

**Example Alarm**:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name kb-sync-failures \
  --metric-name IngestionJobFailed \
  --namespace ProcessApp/RAG \
  --statistic Sum \
  --period 3600 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

### 4. Cost Optimization

**Reduce Sync Frequency**:
- If documents update infrequently, sync less often
- Use manual triggers for on-demand indexing

**Batch Updates**:
- Upload multiple documents before triggering sync
- Avoid sync after each document upload

---

## Automation Examples

### Trigger Sync After Bulk Upload

```python
import boto3

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-agent')

bucket = 'processapp-docs-v2-dev-708819485463'
kb_id = '<KB_ID>'
ds_id = '<DS_ID>'

# Upload multiple documents
for doc in documents:
    s3.upload_file(doc, bucket, f'documents/{doc}')

# Trigger single sync after all uploads
response = bedrock.start_ingestion_job(
    knowledgeBaseId=kb_id,
    dataSourceId=ds_id
)

print(f"Ingestion job started: {response['ingestionJob']['ingestionJobId']}")
```

### Monitor Sync Status

```python
import boto3
import time

bedrock = boto3.client('bedrock-agent')

def wait_for_sync(kb_id, ds_id, job_id):
    while True:
        response = bedrock.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=job_id
        )

        status = response['ingestionJob']['status']
        print(f"Status: {status}")

        if status in ['COMPLETE', 'FAILED']:
            return response

        time.sleep(10)

# Usage
result = wait_for_sync(kb_id, ds_id, job_id)
print(f"Final status: {result['ingestionJob']['status']}")
print(f"Documents indexed: {result['ingestionJob']['statistics']['numberOfDocumentsIndexed']}")
```

---

## References

- [Bedrock KB Sync API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_StartIngestionJob.html)
- [DOCUMENT_INGESTION.md](DOCUMENT_INGESTION.md)
- [VECTORIZATION.md](VECTORIZATION.md)

---

**Status**: Current synchronization process documented
