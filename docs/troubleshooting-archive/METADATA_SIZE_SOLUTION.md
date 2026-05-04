# Metadata Size Limit Solution (2048 bytes)

**Date:** 2026-05-04  
**Issue:** Large documents fail ingestion with "Filterable metadata must have at most 2048 bytes"

---

## Problem Analysis

### What Happened
- Document: `marco_normativo_colpensiones.md` (15KB, 211 lines)
- Metadata: Only 87 bytes (minimal: `tenant_id` + `partition_key`)
- Error: `Filterable metadata must have at most 2048 bytes`

### Root Cause

When Bedrock KB processes a document:
1. **Chunks the document** (current config: 512 tokens per chunk)
2. **Each chunk receives a copy of ALL metadata**
3. **Bedrock adds internal fields** to metadata (not visible to us)
4. **Total metadata = User metadata + Bedrock internal fields**

For a 15KB document:
- Estimated chunks: `15,725 bytes / (512 tokens * 4 chars/token) ≈ 8 chunks`
- Each chunk gets: 87 bytes (user) + ~300-500 bytes (Bedrock internal) ≈ **387-587 bytes per chunk**
- With chunking metadata, Bedrock might be storing: `{"chunk_index": X, "total_chunks": Y, "parent_doc_id": "...", "embedding_metadata": {...}}` 

When **Bedrock tries to store this in S3 Vectors**, the total exceeds 2048 bytes.

---

## Solutions

### Option 1: Increase Chunk Size (RECOMMENDED)

**Current config:**
```typescript
chunking: {
  strategy: 'FIXED_SIZE',
  maxTokens: 512,        // ← Small chunks = many chunks
  overlapPercentage: 20,
}
```

**New config:**
```typescript
chunking: {
  strategy: 'FIXED_SIZE',
  maxTokens: 2000,       // ← Larger chunks = fewer chunks
  overlapPercentage: 10, // ← Less overlap = less redundancy
}
```

**Impact:**
- 15KB document: `15,725 / (2000 * 4) ≈ 2 chunks` (instead of 8)
- Fewer chunks = less metadata duplication
- Stays well under 2048 byte limit

**Trade-offs:**
- ✅ Fewer chunks = better metadata compliance
- ✅ Less storage overhead
- ⚠️ Larger chunks might be less precise for retrieval
- ⚠️ Less context overlap between chunks

---

### Option 2: Remove partition_key (NOT RECOMMENDED)

**Why not:**
- Loses strict isolation (the whole point of partition_key)
- Would go back to the original cross-project data leakage problem
- Only saves ~15 bytes anyway

---

### Option 3: Hierarchical Chunking (ADVANCED)

Split large documents manually before uploading:

```bash
# Split marco_normativo.md into smaller files
marco_normativo_parte1.md (5KB) → 2 chunks
marco_normativo_parte2.md (5KB) → 2 chunks
marco_normativo_parte3.md (5KB) → 2 chunks
```

Each part gets same metadata but fewer chunks per file.

**Trade-offs:**
- ✅ Full control over chunk count
- ❌ Manual process
- ❌ More files to manage

---

### Option 4: Switch to OpenSearch (EXPENSIVE)

S3 Vectors has strict 2048 byte limit. OpenSearch Serverless has more flexible limits.

**Cost comparison (for 1M vectors):**
- S3 Vectors: ~$25/month
- OpenSearch Serverless: ~$700/month

**Verdict:** Not worth it for this issue.

---

## Recommended Implementation

### Step 1: Update Chunk Configuration

Edit `infrastructure/config/environments.ts`:

```typescript
export const ProcessingConfig = {
  chunking: {
    strategy: 'FIXED_SIZE',
    maxTokens: 2000,        // Increased from 512
    overlapPercentage: 10,  // Reduced from 20
  },
  // ...
}
```

### Step 2: Redeploy Knowledge Base

```bash
cd infrastructure
npx cdk deploy dev-us-east-1-bedrock --profile ans-super --require-approval never
```

**Note:** This requires recreating the Knowledge Base (destructive operation).

### Step 3: Re-upload Documents

All documents will be re-chunked with new settings during next ingestion job.

---

## Migration Strategy for Large Documents

If you have many large documents (> 10KB):

### Approach 1: Increase Chunk Size First (Easiest)

1. Update `maxTokens` to 2000
2. Redeploy KB
3. Upload all documents
4. Monitor ingestion jobs for failures

### Approach 2: Pre-chunk Large Documents (Most Control)

For very large documents (> 50KB):

```python
# Split document by sections
def split_large_document(file_path, max_size_kb=10):
    """Split document into smaller parts"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Split by sections (## headers)
    sections = content.split('##')
    
    parts = []
    current_part = ""
    current_size = 0
    
    for section in sections:
        section_size = len(section.encode('utf-8'))
        
        if current_size + section_size > max_size_kb * 1024:
            parts.append(current_part)
            current_part = "##" + section
            current_size = section_size
        else:
            current_part += "##" + section
            current_size += section_size
    
    if current_part:
        parts.append(current_part)
    
    return parts
```

Then upload each part separately with same metadata.

---

## Testing

### Test with marco_normativo

```bash
# Current: Small version (634 bytes) - WORKS
s3://bucket/tenant/1001/marco_normativo_small.txt

# Test: Full version (15KB) - FAILS with current config
s3://bucket/tenant/1001/marco_normativo_colpensiones.md

# After chunk size increase: Full version should work
```

### Monitoring

Check ingestion job stats:
```bash
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --ingestion-job-id <JOB_ID> \
  --profile ans-super
```

Look for:
- `numberOfDocumentsFailed: 0` ✅
- `failureReasons: []` ✅

---

## Recommendation

**For your use case (large migration of documents):**

1. ✅ **Increase chunk size to 2000 tokens** (reduces chunks by 75%)
2. ✅ **Reduce overlap to 10%** (less redundancy)
3. ✅ **Monitor first batch** (test with 10-20 docs first)
4. ✅ **Split extremely large docs** (> 50KB) manually if needed

This should handle most documents without hitting the 2048 byte limit.

---

## Alternative: Metadata-less Chunking

If you absolutely need 512 token chunks AND large documents:

Remove user metadata entirely, rely only on tenant-level filtering:

```json
{
  "metadataAttributes": {
    "tenant_id": "1001"
  }
}
```

Then filter at application level (not at KB level). **Not recommended** - loses strict isolation.

---

## Summary

| Solution | Effort | Impact | Recommendation |
|----------|--------|--------|----------------|
| Increase chunk size | Low | High | ✅ DO THIS |
| Pre-chunk large docs | Medium | Medium | If needed |
| Remove partition_key | Low | High (negative) | ❌ DON'T |
| Switch to OpenSearch | High | Low | ❌ Too expensive |

**Action:** Update `maxTokens: 2000` in `environments.ts` and redeploy KB.
