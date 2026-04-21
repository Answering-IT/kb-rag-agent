# ⚠️ DEPRECATED - Vector Indexer

**Status**: LEGACY - No longer used in current architecture

## Why Deprecated

This Lambda function was originally used to manually index vectors in S3 for RAG retrieval.

**Replacement**: Native S3 Vectors (AWS::S3Vectors::Index) with automatic Bedrock indexing

See `BedrockStack.ts` line 69 for S3 Vector Index implementation.

## Migration Path

S3 Vectors provide:
- Native vector storage in S3 (90% cost reduction vs OpenSearch)
- Automatic indexing during Bedrock KB ingestion jobs
- No manual indexing required
- Native integration with Bedrock Knowledge Base

## How It Works Now

1. Documents uploaded to S3 docs bucket
2. Bedrock KB sync triggered (every 6 hours or manual)
3. Bedrock automatically:
   - Chunks documents
   - Generates embeddings (Titan v2)
   - Indexes vectors in S3 Vector Index
4. Query via Bedrock Agent or retrieve API

**No manual indexing Lambda needed.**

## Removal Timeline

- **Deprecated**: 2026-04-17
- **Planned Removal**: After Phase 1 verification complete
- **No longer deployed**: Confirmed not referenced in `bin/app.ts`

## References

- Current implementation: `infrastructure/lib/BedrockStack.ts`
- S3 Vectors: AWS::S3Vectors::Index (line 69)
- Lambda inventory: `/LAMBDA_INVENTORY.md`
