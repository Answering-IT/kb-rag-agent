# Document Ingestion Guide

Complete guide for uploading and processing documents in the ProcessApp RAG system.

**Last Updated**: 2026-04-17

---

## Overview

Document ingestion is the process of uploading documents to S3, processing them (OCR if needed), and preparing them for indexing in the Knowledge Base.

### Supported Document Types

| Format | Extension | OCR Required | Processing Time |
|--------|-----------|--------------|-----------------|
| PDF (text) | .pdf | No | 5-15 seconds |
| PDF (scanned) | .pdf | Yes | 30-120 seconds |
| Word Document | .docx | No | 5-10 seconds |
| Plain Text | .txt | No | 1-5 seconds |
| Markdown | .md | No | 1-5 seconds |
| HTML | .html | No | 2-8 seconds |
| Images | .png, .jpg, .tiff | Yes | 10-60 seconds |

---

## Upload Methods

### Method 1: AWS CLI

```bash
# Set environment variables
export DOCS_BUCKET=processapp-docs-v2-dev-708819485463

# Upload single document
aws s3 cp document.pdf s3://${DOCS_BUCKET}/documents/

# Upload directory
aws s3 cp documents/ s3://${DOCS_BUCKET}/documents/ --recursive

# Upload with metadata
aws s3 cp document.pdf s3://${DOCS_BUCKET}/documents/ \
  --metadata author="John Doe",category="technical"
```

### Method 2: AWS SDK (Python)

```python
import boto3

s3 = boto3.client('s3')
bucket = 'processapp-docs-v2-dev-708819485463'

# Upload file
s3.upload_file('document.pdf', bucket, 'documents/document.pdf')

# Upload with metadata
s3.upload_file(
    'document.pdf',
    bucket,
    'documents/document.pdf',
    ExtraArgs={
        'Metadata': {
            'author': 'John Doe',
            'category': 'technical'
        }
    }
)
```

---

## Processing Pipeline

### Step 1: Upload Triggers EventBridge

```
S3 Upload → EventBridge Rule (Object Created) → OCR Lambda
```

**EventBridge Rule**:
- Monitors: `processapp-docs-v2-dev-*` bucket
- Event type: `Object Created`
- Filter: Objects with prefix `documents/`

### Step 2: OCR Processing (If Required)

**OCR Lambda determines if document needs OCR**:

```python
file_ext = object_key.lower().split('.')[-1]

if file_ext in ['pdf', 'png', 'jpg', 'jpeg', 'tiff']:
    # May need OCR (PDF could be text or scanned)
    job_id = start_textract_job(bucket, object_key)
else:
    # Text-native formats (txt, docx, md)
    # Skip OCR, go directly to KB sync
```

**Textract Features**:
- `TABLES`: Extract table structures
- `FORMS`: Extract key-value pairs
- Async processing via SNS notifications

### Step 3: Text Extraction

**For OCR documents**:
1. Textract analyzes document
2. SNS notifies OCR Lambda when complete
3. Lambda extracts all text blocks
4. Lambda chunks text
5. Chunks sent to SQS queue

**For text-native documents**:
1. Read text directly
2. Minimal processing
3. Ready for KB sync

### Step 4: Embedding Generation (Current Architecture)

```
SQS Queue → Embedder Lambda → Titan v2 → vectorsBucket (S3)
```

**⚠️ Note**: This step may be redundant. Bedrock KB generates its own embeddings during sync. See LAMBDA_INVENTORY.md for details.

### Step 5: Knowledge Base Sync

```
Sync Lambda → Bedrock Ingestion Job → Chunking + Embedding → Vector Index
```

**Automatic sync**: Every 6 hours
**Manual sync**: Via CLI or Lambda invocation

---

## Best Practices

### 1. Document Naming

✅ **Good**:
- `technical-specs-v1.0.pdf`
- `user-manual-2024-01-15.docx`
- `policy-document-rev3.txt`

❌ **Avoid**:
- `document.pdf` (too generic)
- `file 1 (copy).pdf` (spaces, special chars)
- `doc!@#$.pdf` (special characters)

### 2. Document Organization

```
documents/
├── technical/
│   ├── architecture.pdf
│   └── api-specs.md
├── policies/
│   ├── data-retention.docx
│   └── security-policy.pdf
└── manuals/
    ├── user-guide.pdf
    └── admin-guide.pdf
```

### 3. Metadata Usage

**Add meaningful metadata**:
```bash
aws s3 cp document.pdf s3://${DOCS_BUCKET}/documents/ \
  --metadata \
    author="Technical Team" \
    category="architecture" \
    version="2.0" \
    last-reviewed="2024-01-15"
```

**Benefits**:
- Better organization
- Enhanced search
- Document tracking
- Audit capabilities

---

## Monitoring Ingestion

### Check OCR Lambda Logs

```bash
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow
```

### Monitor SQS Queue

```bash
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages
```

### Check Ingestion Jobs

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>
```

---

## Troubleshooting

### Issue: Document Not Processed

**Check**:
1. Document in correct prefix (`documents/`)
2. EventBridge rule enabled
3. Lambda has permissions
4. CloudWatch logs for errors

### Issue: OCR Fails

**Common causes**:
- PDF is encrypted
- Image quality too low
- Textract service limits reached

**Solution**:
- Check Textract limits
- Improve image quality
- Retry after delay

---

## References

- [VECTORIZATION.md](VECTORIZATION.md) - Embedding process
- [RAG_SYNCHRONIZATION.md](RAG_SYNCHRONIZATION.md) - KB sync
- [AWS Textract](https://docs.aws.amazon.com/textract/)

---

**Status**: Current ingestion pipeline documented
