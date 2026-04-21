# Vectorization Process Guide

Understanding how documents are converted to vector embeddings in ProcessApp RAG.

**Last Updated**: 2026-04-17

---

## Overview

Vectorization is the process of converting text into numerical vectors (embeddings) that capture semantic meaning. These vectors enable similarity search and retrieval in the RAG system.

---

## Current Architecture

### Dual Vectorization Process (⚠️ Potential Duplication)

**Process 1: Custom Embedder Lambda**
```
Chunks (SQS) → Embedder Lambda → Titan v2 API → vectorsBucket (Regular S3)
```

**Process 2: Bedrock Native**
```
Documents (S3) → KB Sync → Bedrock Chunking → Titan v2 → VectorBucket (AWS::S3Vectors)
```

**Critical Finding**: Bedrock KB uses VectorBucket (AWS::S3Vectors), NOT the regular vectorsBucket. This means embeddings from Embedder Lambda may be unused.

---

## Embedding Model

### Amazon Titan v2

**Model**: `amazon.titan-embed-text-v2:0`

**Specifications**:
- Dimensions: 1024 (configurable: 256, 512, 1024)
- Max input tokens: 8,192
- Output: Normalized float32 vector
- Distance metric: Cosine similarity

**Performance**:
- Latency: ~100-200ms per chunk
- Throughput: 1000+ requests/second (Bedrock managed)
- Cost: ~$0.0001 per 1K tokens

**Why Titan v2**:
- Optimized for retrieval tasks
- Lower cost than competitors
- Native Bedrock integration
- Multilingual support

---

## Chunking Strategy

### Fixed-Size Chunking

**Configuration** (in BedrockStack):
```typescript
chunkingStrategy: 'FIXED_SIZE',
fixedSizeChunkingConfiguration: {
  maxTokens: 512,
  overlapPercentage: 20,
}
```

**How it works**:
1. Document split into 512-token chunks
2. 20% overlap between consecutive chunks (102 tokens)
3. Preserves context across chunk boundaries

**Example**:
```
Chunk 1: tokens 0-512
Chunk 2: tokens 410-922 (102 overlap)
Chunk 3: tokens 820-1332 (102 overlap)
```

**Trade-offs**:
- Smaller chunks: More precise retrieval, more API calls
- Larger chunks: More context, fewer chunks, potentially less precise
- Overlap: Better context preservation, slight storage increase

---

## S3 Vectors Storage

### What is S3 Vectors?

S3 Vectors (`AWS::S3Vectors`) is a native AWS service for storing and querying vector embeddings directly in S3.

**Key Features**:
- Native S3 integration (no separate cluster)
- Automatic indexing
- Cosine similarity search
- 90% cost reduction vs OpenSearch
- Zero maintenance

**Architecture**:
```
VectorBucket (AWS::S3Vectors)
├── Index (AWS::S3Vectors::Index)
│   ├── Dimension: 1024
│   ├── DistanceMetric: cosine
│   └── DataType: float32
└── Embeddings (managed by AWS)
```

**Storage Format**: Opaque (managed by AWS, optimized for retrieval)

---

## Bedrock Native Vectorization

### How Bedrock Handles Vectors

**During KB Sync**:
1. Bedrock reads documents from S3 Data Source
2. Applies chunking strategy (512 tokens, 20% overlap)
3. Generates embeddings via Titan v2
4. Stores vectors in S3 Vector Index
5. Builds search index automatically

**Advantages**:
- Fully managed (no custom code)
- Optimized by AWS
- Automatic retries
- Consistent chunking
- Built-in error handling

---

## Embedder Lambda (⚠️ Analysis)

### Current Implementation

**Purpose**: Generate embeddings from text chunks and store in regular S3.

**Process**:
```python
def generate_embedding(text: str) -> List[float]:
    body = json.dumps({
        'inputText': text,
        'dimensions': 1536,  # ⚠️ Note: Configured as 1536, but should be 1024
        'normalize': True
    })

    response = bedrock_runtime.invoke_model(
        modelId='amazon.titan-embed-text-v2:0',
        body=body
    )

    return response['embedding']

def store_embedding(chunk_id, text, embedding, metadata):
    s3.put_object(
        Bucket=VECTORS_BUCKET,  # Regular S3 bucket
        Key=f'embeddings/{chunk_id}.json',
        Body=json.dumps({
            'chunk_id': chunk_id,
            'text': text,
            'embedding': embedding,
            'metadata': metadata
        })
    )
```

### Critical Questions (from LAMBDA_INVENTORY.md)

1. **Does Bedrock KB read from vectorsBucket (regular S3)?**
   - **Evidence**: NO. BedrockStack.ts shows KB uses `s3VectorsConfiguration.indexArn`, not regular S3.

2. **Does Bedrock KB generate its own embeddings?**
   - **Evidence**: YES. KB configuration includes `embeddingModelArn` (Titan v2).

3. **Is vectorsBucket actually used?**
   - **Evidence**: Only by Embedder Lambda, not by Bedrock KB.

**Conclusion**: Embedder Lambda appears redundant. Bedrock KB handles vectorization natively.

---

## Vector Search Process

### Retrieval Flow

```
User Query → Agent → KB Retrieve
                      ↓
                Query Embedding (Titan v2)
                      ↓
           Vector Index (Cosine Similarity)
                      ↓
                Top K Chunks (K=5)
                      ↓
              Fetch Full Documents
                      ↓
            Return Context + Citations
```

**Search Parameters**:
- `numberOfResults`: 5 (top 5 most relevant chunks)
- `searchType`: HYBRID (semantic + keyword)
- `overrideSearchType`: Configurable

**Hybrid Search**:
- Semantic: Vector similarity (embeddings)
- Keyword: BM25 text matching
- Combined: Best of both worlds

---

## Performance Metrics

### Embedding Generation

| Metric | Value |
|--------|-------|
| Latency (per chunk) | 100-200ms |
| Throughput | 1000+ requests/sec |
| Concurrent requests | Unlimited (Bedrock managed) |
| Cost per 1K tokens | ~$0.0001 |

### Vector Search

| Metric | Value |
|--------|-------|
| Query latency | 200-500ms |
| Top K retrieval | K=5 (configurable) |
| Search type | Hybrid (semantic + keyword) |

---

## Cost Analysis

### Current Architecture (with Embedder Lambda)

**Per 1000 documents** (avg 10 chunks each):
- Embedder Lambda invocations: ~10,000 × $0.0000002 = $0.002
- Bedrock embeddings (Lambda): 10,000 × $0.0001 = $1.00
- Bedrock embeddings (KB Sync): 10,000 × $0.0001 = $1.00
- **Total embeddings cost**: $2.00 (DOUBLED)

### Proposed Architecture (Bedrock only)

**Per 1000 documents**:
- Bedrock embeddings (KB Sync only): 10,000 × $0.0001 = $1.00
- **Total embeddings cost**: $1.00 (50% REDUCTION)

**Savings**: $1.00 per 1000 documents (~50%)

---

## Optimization Recommendations

### 1. Chunking Strategy

**Current**: 512 tokens, 20% overlap
**Consider**:
- Smaller chunks (256 tokens) for more precise retrieval
- Larger chunks (1024 tokens) for more context
- Dynamic chunking based on document structure

### 2. Embedding Dimensions

**Current**: 1024 dimensions
**Consider**:
- 256 dimensions: Faster, cheaper, slightly less accurate
- 512 dimensions: Good balance
- 1024 dimensions: Most accurate, higher cost

### 3. Search Type

**Current**: HYBRID
**Alternatives**:
- `SEMANTIC`: Pure vector search (best for conceptual queries)
- `HYBRID`: Balanced (default)

---

## Troubleshooting

### Issue: Embeddings Not Generated

**Check**:
```bash
# Check Embedder Lambda logs
aws logs tail /aws/lambda/processapp-embedder-dev --follow

# Check for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/processapp-embedder-dev \
  --filter-pattern "ERROR"
```

### Issue: Vector Search Returns No Results

**Possible causes**:
- Documents not yet indexed (wait for KB sync)
- Query too specific
- Embeddings corrupted

**Solution**:
- Trigger manual KB sync
- Try broader queries
- Check KB ingestion job status

---

## References

- [Titan Embeddings Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embeddings.html)
- [S3 Vectors Blog](https://aws.amazon.com/blogs/aws/introducing-s3-vector-storage/)
- [LAMBDA_INVENTORY.md](../LAMBDA_INVENTORY.md) - Embedder analysis

---

**Status**: Current vectorization process documented with optimization recommendations
