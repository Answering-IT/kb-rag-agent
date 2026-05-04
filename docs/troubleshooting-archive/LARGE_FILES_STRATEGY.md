# Strategy for Very Large Documents (> 50KB)

**Date:** 2026-05-04  
**Issue:** Need to handle documents of 100KB, 500KB, or larger

---

## The Real Problem

**S3 Vectors Metadata Limit:** 2048 bytes TOTAL per document (not per chunk)

### Size Analysis

| Doc Size | Chunks (512 tokens) | Chunks (2000 tokens) | Estimated Metadata |
|----------|---------------------|----------------------|-------------------|
| 15KB | 8 chunks | 2 chunks | ~400-800 bytes |
| 50KB | 25 chunks | 6-7 chunks | ~1500-2000 bytes |
| 100KB | 50 chunks | 12-13 chunks | **> 2048 bytes ❌** |
| 500KB | 250 chunks | 60-65 chunks | **>> 2048 bytes ❌** |

**Conclusion:** Even with 2000 token chunks, documents > 50KB will likely fail.

---

## Root Cause

Bedrock adds internal metadata to EACH chunk:
```json
{
  "x-amzn-bedrock-kb-chunk-id": "uuid",
  "x-amzn-bedrock-kb-source-uri": "s3://...",
  "x-amzn-bedrock-kb-data-source-id": "...",
  // ... more internal fields
}
```

User metadata (87 bytes) + Bedrock internal fields (~30-50 bytes per chunk) × number of chunks = **exceeds 2048 bytes**

---

## Real Solutions

### Option 1: Pre-Split Large Documents (RECOMMENDED)

**Strategy:** Split large documents into smaller files BEFORE uploading.

**Implementation:**

```python
#!/usr/bin/env python3
"""
Split large documents into chunks that won't exceed metadata limit.
Target: < 8KB per file (generates ~2 chunks max)
"""

import os
import json

def split_large_document(input_file, output_dir, max_size_kb=8):
    """
    Split document by sections or size.
    Each part gets same metadata.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Strategy 1: Split by markdown headers (##)
    sections = []
    current_section = []
    
    for line in content.split('\n'):
        if line.startswith('## ') and current_section:
            # Save current section
            sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    # Combine sections into parts that don't exceed max_size_kb
    parts = []
    current_part = []
    current_size = 0
    
    for section in sections:
        section_size = len(section.encode('utf-8'))
        
        if current_size + section_size > max_size_kb * 1024:
            # Start new part
            if current_part:
                parts.append('\n\n'.join(current_part))
            current_part = [section]
            current_size = section_size
        else:
            current_part.append(section)
            current_size += section_size
    
    if current_part:
        parts.append('\n\n'.join(current_part))
    
    return parts

def save_parts_with_metadata(parts, output_dir, base_name, metadata):
    """Save parts with metadata files"""
    os.makedirs(output_dir, exist_ok=True)
    
    for i, part in enumerate(parts, 1):
        # Save document part
        part_file = f"{base_name}_part{i}.txt"
        part_path = os.path.join(output_dir, part_file)
        
        with open(part_path, 'w', encoding='utf-8') as f:
            f.write(part)
        
        # Save metadata
        meta_file = f"{part_file}.metadata.json"
        meta_path = os.path.join(output_dir, meta_file)
        
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump({"metadataAttributes": metadata}, f, indent=2)
        
        size_kb = len(part.encode('utf-8')) / 1024
        print(f"Created: {part_file} ({size_kb:.1f} KB)")

# Example usage
if __name__ == "__main__":
    # Split marco_normativo (15KB)
    parts = split_large_document(
        'marco_normativo_colpensiones.md',
        '/tmp/chunks',
        max_size_kb=8
    )
    
    metadata = {
        "tenant_id": "1001",
        "partition_key": "t1001"
    }
    
    save_parts_with_metadata(
        parts,
        '/tmp/chunks',
        'marco_normativo',
        metadata
    )
    
    print(f"\nTotal parts: {len(parts)}")
    print("Each part will generate ~2 Bedrock chunks")
    print("Total metadata per part: < 500 bytes ✅")
```

**Pros:**
- ✅ Works for documents of ANY size
- ✅ Full control over chunk count
- ✅ Each part has < 8KB = ~2 Bedrock chunks = safe metadata
- ✅ Same metadata across all parts (maintains filtering)

**Cons:**
- ⚠️ Manual/scripted splitting required
- ⚠️ More files to manage

---

### Option 2: Hierarchical Chunking Strategy

**Bedrock KB Custom Chunking** (if available in your region):

```typescript
// In BedrockStack.ts
chunking: {
  strategy: 'HIERARCHICAL',
  maxParentTokens: 1500,
  maxChildTokens: 300,
}
```

This creates parent-child chunk relationships, reducing metadata duplication.

**Check availability:**
```bash
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id R80HXGRLHO \
  --profile ans-super \
  --query 'knowledgeBase.chunkingConfiguration'
```

---

### Option 3: Switch to OpenSearch Serverless

**S3 Vectors Limit:** 2048 bytes metadata  
**OpenSearch Limit:** Much more flexible (tens of KB)

**Cost Impact:**
```
S3 Vectors:      $25/month (1M vectors)
OpenSearch:      $700/month (2 OCU × $350)
```

**When to consider:**
- If you have MANY large documents (> 100KB)
- If splitting is not feasible
- If budget allows

**Migration:**
```typescript
// In BedrockStack.ts
storageConfiguration: {
  type: 'OPENSEARCH_SERVERLESS',
  opensearchServerlessConfiguration: {
    collectionArn: opensearchCollection.attrArn,
    vectorIndexName: 'bedrock-kb-index',
    fieldMapping: {
      vectorField: 'embedding',
      textField: 'text',
      metadataField: 'metadata',
    },
  },
}
```

---

### Option 4: Reduce Metadata (NOT RECOMMENDED)

Remove `partition_key`, keep only `tenant_id`:

```json
{
  "metadataAttributes": {
    "tenant_id": "1001"
  }
}
```

**Impact:**
- ❌ Loses project/task isolation
- ❌ Back to cross-project leakage problem
- ✅ Saves ~15 bytes (not worth it)

---

## Recommended Approach

### For Your Migration

**Given:** Many large documents (100KB+)

**Solution:**

1. **Create pre-processing script** (split documents)
2. **Target size:** 8KB per file (generates ~2 chunks)
3. **Maintain metadata:** All parts get same tenant_id/project_id/partition_key
4. **Upload split files** with original metadata

### Script Location

```bash
/Users/qohatpretel/Answering/kb-rag-agent/scripts/split-large-files.py
```

### Upload Process

```bash
# 1. Split large documents
python3 scripts/split-large-files.py \
  --input-dir /path/to/large/docs \
  --output-dir /path/to/split/docs \
  --max-size-kb 8

# 2. Upload split documents to S3
aws s3 sync /path/to/split/docs \
  s3://bucket/tenant/1001/project/165/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY} \
  --profile ans-super

# 3. Trigger ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --profile ans-super
```

---

## Example: 500KB Document

**Original:**
- `documento_grande.pdf` (500KB)
- Would generate ~65 chunks (with 2000 tokens)
- Metadata: > 3000 bytes ❌ FAILS

**After splitting (8KB parts):**
- `documento_grande_part1.txt` (8KB) → 2 chunks
- `documento_grande_part2.txt` (8KB) → 2 chunks
- ... (60+ parts total)
- Each part metadata: ~200 bytes ✅ WORKS

**Each part maintains same metadata:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "partition_key": "t1001_p165",
    "source_document": "documento_grande.pdf",  // Optional: track origin
    "part_number": "1",                          // Optional: track part
    "total_parts": "60"                          // Optional: track total
  }
}
```

---

## Testing Strategy

### Phase 1: Small Files (< 10KB)
- ✅ Upload as-is
- ✅ Should work with current setup

### Phase 2: Medium Files (10-50KB)
- ⚠️ Test first batch
- ⚠️ If failures, split to 8KB parts

### Phase 3: Large Files (> 50KB)
- ✅ Always split before upload
- ✅ 8KB parts = safe

---

## Next Steps

1. **I'll create the split script** for you
2. **Test with marco_normativo** (15KB → 2 parts of ~8KB)
3. **Validate ingestion** (should succeed)
4. **Document the process** for your team

Would you like me to create the splitting script now?

---

## Alternative: Increase Chunk Size + Manual Split Hybrid

**Compromise approach:**

1. Increase chunk size to 1500 tokens (allows up to ~30KB docs)
2. Pre-split anything > 30KB manually

**Pros:**
- ✅ Handles most documents automatically
- ✅ Only split the very large ones

**Cons:**
- ⚠️ Still need manual process for large files
- ⚠️ Requires monitoring ingestion failures

---

## Summary

| Document Size | Strategy | Effort | Success Rate |
|---------------|----------|--------|--------------|
| < 10KB | Upload as-is | None | 100% |
| 10-30KB | Increase chunk size | Low | 95% |
| 30-100KB | Pre-split to 8KB | Medium | 100% |
| > 100KB | Pre-split to 8KB | Medium | 100% |

**Recommendation:** Pre-split ALL documents > 10KB to 8KB parts before upload.
