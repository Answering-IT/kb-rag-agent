# Automatic Chunking Lambda Architecture

**Date:** 2026-05-04  
**Solution:** Pre-process large documents with Lambda before Bedrock KB ingestion

---

## Problem with Current Approach

**Current Flow:**
```
S3 Upload → Bedrock KB (auto-chunk) → S3 Vectors
```

**Issues:**
- ❌ Bedrock adds internal metadata we can't control
- ❌ Large documents generate many chunks → metadata overflow (> 2048 bytes)
- ❌ Manual file splitting required
- ❌ Not scalable

---

## Proposed Architecture

**New Flow:**
```
S3 Upload (original) → Lambda (chunk) → S3 Chunks (processed) → Bedrock KB (no chunking) → S3 Vectors
```

**Benefits:**
- ✅ Upload original files (any size)
- ✅ Automatic chunking via Lambda
- ✅ Full control over chunk size and metadata
- ✅ Minimal metadata per chunk (< 100 bytes)
- ✅ Bedrock KB disabled chunking (just embeddings)
- ✅ Scalable for files of any size

---

## Architecture Details

### S3 Bucket Structure

```
s3://bucket/
├── originals/                    # Original files uploaded by user
│   └── tenant/1001/
│       └── project/165/
│           ├── documento.pdf     # Original (15KB, 500KB, any size)
│           └── documento.pdf.metadata.json
│
└── chunks/                       # Processed chunks for Bedrock KB
    └── tenant/1001/
        └── project/165/
            ├── documento_chunk_1.txt
            ├── documento_chunk_1.txt.metadata.json
            ├── documento_chunk_2.txt
            ├── documento_chunk_2.txt.metadata.json
            └── ...
```

### Lambda Function: Document Chunker

**Trigger:** S3 event on `originals/` prefix

**Process:**
1. Detect new file upload
2. Read original file + metadata
3. Extract text (OCR if needed)
4. Split into chunks (8KB each)
5. Create chunk files with minimal metadata
6. Upload chunks to `chunks/` prefix
7. Delete original from `originals/` (optional)

**Metadata per chunk:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "partition_key": "t1001_p165",
    "chunk_id": "1"
  }
}
```

**Total:** ~80 bytes per chunk (safe!)

---

## Bedrock KB Configuration

**Disable chunking:**
```typescript
// In BedrockStack.ts - Data Source configuration
chunkingConfiguration: {
  chunkingStrategy: 'NONE',  // ← No chunking, files are pre-chunked
}
```

**KB only does:**
- Generate embeddings
- Store in S3 Vectors
- No chunking overhead

---

## Implementation

### 1. Lambda Function

**File:** `infrastructure/lambdas/document-chunker/index.py`

```python
import boto3
import json
import os
from typing import List, Dict

s3 = boto3.client('s3')
CHUNK_SIZE_KB = 8
CHUNKS_BUCKET = os.environ['CHUNKS_BUCKET']

def lambda_handler(event, context):
    """
    Process uploaded document and create chunks.
    """
    # Get uploaded file from S3 event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Skip if not in originals/ or is metadata file
        if not key.startswith('originals/') or key.endswith('.metadata.json'):
            continue
        
        print(f"Processing: {key}")
        
        # Read original file
        obj = s3.get_object(Bucket=bucket, Key=key)
        content = obj['Body'].read().decode('utf-8')
        
        # Read metadata
        metadata_key = f"{key}.metadata.json"
        metadata = {}
        try:
            meta_obj = s3.get_object(Bucket=bucket, Key=metadata_key)
            metadata = json.loads(meta_obj['Body'].read().decode('utf-8'))
            metadata = metadata.get('metadataAttributes', {})
        except:
            print(f"No metadata found for {key}")
        
        # Chunk document
        chunks = chunk_document(content, CHUNK_SIZE_KB)
        
        # Upload chunks
        base_path = key.replace('originals/', 'chunks/')
        base_name = os.path.splitext(base_path)[0]
        
        for i, chunk in enumerate(chunks, 1):
            chunk_key = f"{base_name}_chunk_{i}.txt"
            chunk_metadata = create_chunk_metadata(metadata, i, len(chunks))
            
            # Upload chunk
            s3.put_object(
                Bucket=CHUNKS_BUCKET,
                Key=chunk_key,
                Body=chunk,
                ServerSideEncryption='aws:kms'
            )
            
            # Upload chunk metadata
            s3.put_object(
                Bucket=CHUNKS_BUCKET,
                Key=f"{chunk_key}.metadata.json",
                Body=json.dumps({"metadataAttributes": chunk_metadata}, indent=2),
                ServerSideEncryption='aws:kms'
            )
            
            print(f"Created chunk {i}/{len(chunks)}: {chunk_key}")
        
        print(f"✅ Processed {key} → {len(chunks)} chunks")

def chunk_document(content: str, max_size_kb: int) -> List[str]:
    """Split document into chunks by size."""
    max_bytes = max_size_kb * 1024
    chunks = []
    
    # Split by paragraphs
    paragraphs = content.split('\n\n')
    
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_bytes = len(para.encode('utf-8'))
        
        if current_size + para_bytes > max_bytes:
            if current_chunk:
                chunks.append('\n\n'.join(current_chunk))
            current_chunk = [para]
            current_size = para_bytes
        else:
            current_chunk.append(para)
            current_size += para_bytes
    
    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))
    
    return chunks

def create_chunk_metadata(base_metadata: Dict, chunk_num: int, total_chunks: int) -> Dict:
    """Create minimal metadata for chunk."""
    # Keep only essential fields
    chunk_meta = {
        "tenant_id": base_metadata.get("tenant_id"),
        "partition_key": base_metadata.get("partition_key"),
    }
    
    # Add project_id, task_id if present
    if "project_id" in base_metadata:
        chunk_meta["project_id"] = base_metadata["project_id"]
    if "task_id" in base_metadata:
        chunk_meta["task_id"] = base_metadata["task_id"]
    
    # Optional: add chunk tracking (only if needed)
    # chunk_meta["chunk_id"] = str(chunk_num)
    
    return chunk_meta
```

### 2. CDK Stack

**File:** `infrastructure/lib/DocumentChunkerStack.ts`

```typescript
import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as s3n from 'aws-cdk-lib/aws-s3-notifications';
import * as iam from 'aws-cdk-lib/aws-iam';

export class DocumentChunkerStack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props: any) {
    super(scope, id, props);

    // Lambda function
    const chunkerLambda = new lambda.Function(this, 'DocumentChunker', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'index.lambda_handler',
      code: lambda.Code.fromAsset('lambdas/document-chunker'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: {
        CHUNKS_BUCKET: props.docsBucket.bucketName,
        CHUNK_SIZE_KB: '8',
      },
    });

    // Grant permissions
    props.docsBucket.grantReadWrite(chunkerLambda);

    // S3 trigger on originals/ prefix
    props.docsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(chunkerLambda),
      { prefix: 'originals/', suffix: '.md' }  // Trigger on .md files
    );

    props.docsBucket.addEventNotification(
      s3.EventType.OBJECT_CREATED,
      new s3n.LambdaDestination(chunkerLambda),
      { prefix: 'originals/', suffix: '.txt' }  // Trigger on .txt files
    );
  }
}
```

### 3. Update Bedrock KB Data Source

**File:** `infrastructure/lib/BedrockStack.ts`

```typescript
// Change data source to point to chunks/ prefix
const dataSource = new bedrock.CfnDataSource(this, 'DataSource', {
  knowledgeBaseId: this.knowledgeBase.attrKnowledgeBaseId,
  name: dataSourceName,
  dataSourceConfiguration: {
    type: 'S3',
    s3Configuration: {
      bucketArn: props.docsBucket.bucketArn,
      inclusionPrefixes: ['chunks/'],  // ← Only ingest chunks, not originals
    },
  },
  
  // DISABLE chunking (files are pre-chunked)
  vectorIngestionConfiguration: {
    chunkingConfiguration: {
      chunkingStrategy: 'NONE',  // ← No chunking!
    },
  },
});
```

---

## Migration Plan

### Phase 1: Deploy Lambda

```bash
cd infrastructure
npx cdk deploy dev-us-east-1-document-chunker --profile ans-super
```

### Phase 2: Update Bedrock KB

```bash
# Point KB to chunks/ prefix and disable chunking
npx cdk deploy dev-us-east-1-bedrock --profile ans-super
```

### Phase 3: Upload Test File

```bash
# Upload to originals/ (triggers Lambda)
aws s3 cp documento.md \
  s3://bucket/originals/tenant/1001/project/165/documento.md \
  --sse aws:kms \
  --profile ans-super

aws s3 cp documento.md.metadata.json \
  s3://bucket/originals/tenant/1001/project/165/documento.md.metadata.json \
  --sse aws:kms \
  --profile ans-super

# Lambda automatically creates chunks in chunks/ prefix
# Bedrock KB ingests chunks (no chunking needed)
```

### Phase 4: Monitor

```bash
# Check Lambda logs
aws logs tail /aws/lambda/document-chunker --follow --profile ans-super

# Check chunks created
aws s3 ls s3://bucket/chunks/tenant/1001/project/165/ --profile ans-super

# Trigger KB ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --profile ans-super
```

---

## Benefits

| Aspect | Before (auto-chunk) | After (Lambda chunk) |
|--------|---------------------|----------------------|
| File size limit | < 50KB | Unlimited |
| Metadata control | ❌ No | ✅ Full control |
| Metadata per doc | > 2048 bytes | < 100 bytes |
| Manual splitting | ✅ Required | ❌ Not needed |
| Scalability | ❌ Limited | ✅ Unlimited |
| Original files | ❌ Must split | ✅ Keep intact |

---

## Cost Impact

**Lambda:**
- Executions: ~$0.20 per 1M requests
- Compute: ~$0.0000166667 per GB-second
- Example: 1000 docs/day × 5 seconds = $0.25/month

**S3:**
- Storage doubles (originals + chunks)
- Example: 10GB originals + 10GB chunks = $0.46/month

**Total:** < $1/month additional cost

---

## Alternative: Process Only Large Files

**Hybrid approach:**

```python
# In Lambda
file_size_kb = len(content.encode('utf-8')) / 1024

if file_size_kb < 10:
    # Small file: copy to chunks/ as-is (no chunking)
    copy_to_chunks(key, content, metadata)
else:
    # Large file: chunk it
    chunks = chunk_document(content, CHUNK_SIZE_KB)
    upload_chunks(chunks, key, metadata)
```

This avoids unnecessary chunking for small files.

---

## Next Steps

1. Create `lambdas/document-chunker/index.py`
2. Create `DocumentChunkerStack.ts`
3. Update `BedrockStack.ts` (disable chunking, point to chunks/)
4. Deploy stacks
5. Test with marco_normativo.md (15KB)
6. Validate metadata < 2048 bytes
7. Test with larger files (100KB, 500KB)

---

**Recommendation:** Implement this Lambda-based chunking approach for production. It's the only scalable solution for large documents.
