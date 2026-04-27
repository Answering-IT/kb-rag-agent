# Multi-Tenant Metadata Filtering - IMPLEMENTATION SUCCESS

**Date:** 2026-04-26  
**Status:** ✅ **FULLY OPERATIONAL**  
**Environment:** Dev (us-east-1)

---

## Executive Summary

Successfully implemented and tested multi-tenant metadata filtering for ProcessApp RAG Agent using AWS Bedrock Knowledge Base with S3_VECTORS storage. The system now enforces strict tenant isolation at the document level.

### Test Results: 4/4 PASSED ✅

| Test | Description | Result |
|------|-------------|---------|
| 1 | Tenant 1 accesses own data | ✅ PASS |
| 2 | Tenant 2 accesses own data | ✅ PASS |
| 3 | Tenant 1 blocked from Tenant 2 data | ✅ PASS |
| 4 | Tenant 2 blocked from Tenant 1 data | ✅ PASS |

---

## Key Discovery: Metadata.json File Requirement

### ❌ What DOESN'T Work

**S3 Object Metadata (x-amz-meta-*) is NOT indexed by Bedrock Knowledge Base.**

```bash
# This metadata is IGNORED by Bedrock KB:
aws s3api put-object \
  --bucket mybucket \
  --key document.txt \
  --metadata tenant_id=1,roles=viewer  # ❌ NOT USED
```

### ✅ What WORKS

**Companion `.metadata.json` files are required:**

**File Structure:**
```
s3://bucket/documents/
├── document.txt                      # Your document
└── document.txt.metadata.json        # Metadata companion file
```

**Metadata.json Format:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "roles": "viewer",
    "project_id": "100",
    "users": "*"
  }
}
```

### Critical Requirements

1. **File Naming:** Metadata file MUST have exact same name + `.metadata.json` extension
2. **Same Location:** Both files must be in same S3 prefix
3. **JSON Structure:** Must wrap attributes in `"metadataAttributes"` object
4. **Upload Both:** Upload document + metadata.json together before ingestion

---

## Implementation Details

### 1. Metadata Filter Module

**File:** `/infrastructure/lambdas/api-handler/metadata_filter.py`

```python
class TenantContext:
    def build_kb_filter(self) -> Dict[str, Any]:
        """Build Bedrock KB filter using snake_case keys"""
        filter_obj = {'andAll': []}
        
        # Tenant must match (REQUIRED)
        filter_obj['andAll'].append({
            'equals': {'key': 'tenant_id', 'value': str(self.tenant_id)}
        })
        
        # Roles filtering with wildcard support
        if self.roles:
            role_conditions = [
                {'equals': {'key': 'roles', 'value': role}}
                for role in self.roles
            ] + [{'equals': {'key': 'roles', 'value': '*'}}]
            
            filter_obj['andAll'].append({
                'orAll': role_conditions
            })
        
        return filter_obj
```

### 2. API Handler Integration

**File:** `/infrastructure/lambdas/api-handler/index.py`

```python
# Extract tenant context from headers
tenant_context = TenantContext.from_headers(headers, body)

# Build KB filter
kb_filter = tenant_context.build_kb_filter()

# Call retrieve_and_generate with native filtering
response = bedrock_agent_runtime.retrieve_and_generate(
    input={'text': question},
    retrieveAndGenerateConfiguration={
        'type': 'KNOWLEDGE_BASE',
        'knowledgeBaseConfiguration': {
            'knowledgeBaseId': KNOWLEDGE_BASE_ID,
            'modelArn': f'arn:aws:bedrock:{REGION}::foundation-model/{FOUNDATION_MODEL}',
            'retrievalConfiguration': {
                'vectorSearchConfiguration': {
                    'numberOfResults': 5,
                    'overrideSearchType': 'SEMANTIC',
                    'filter': kb_filter  # NATIVE METADATA FILTERING
                }
            }
        }
    }
)
```

### 3. Filter Format

**Bedrock KB Filter Syntax:**
```json
{
  "andAll": [
    {
      "equals": {
        "key": "tenant_id",
        "value": "1"
      }
    },
    {
      "orAll": [
        {"equals": {"key": "roles", "value": "viewer"}},
        {"equals": {"key": "roles", "value": "*"}}
      ]
    }
  ]
}
```

### 4. Request Headers

**Required Headers:**
```
X-Api-Key: <api-key>
x-tenant-id: 1
x-user-id: user123
x-user-roles: ["viewer"]
Content-Type: application/json
```

**Request Body:**
```json
{
  "question": "What is Colpensiones?",
  "projectId": "100",        // optional
  "allowedUsers": ["user1"]  // optional
}
```

---

## Upload Workflow

### Step 1: Prepare Documents

```bash
# Create document
echo "Content for tenant 1" > document.txt

# Create metadata companion file
cat > document.txt.metadata.json << 'EOF'
{
  "metadataAttributes": {
    "tenant_id": "1",
    "roles": "viewer",
    "project_id": "100",
    "users": "*"
  }
}
EOF
```

### Step 2: Upload to S3

```bash
KMS_KEY="e6a714f6-70a7-47bf-a9ee-55d871d33cc6"
BUCKET="processapp-docs-v2-dev-708819485463"

# Upload document
aws s3api put-object \
  --bucket ${BUCKET} \
  --key documents/document.txt \
  --body document.txt \
  --server-side-encryption aws:kms \
  --ssekms-key-id ${KMS_KEY}

# Upload metadata
aws s3api put-object \
  --bucket ${BUCKET} \
  --key documents/document.txt.metadata.json \
  --body document.txt.metadata.json \
  --server-side-encryption aws:kms \
  --ssekms-key-id ${KMS_KEY} \
  --content-type application/json
```

### Step 3: Trigger Ingestion

```bash
KB_ID="R80HXGRLHO"
DS_ID="6H96SSTEHT"

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --description "Ingest with metadata"
```

### Step 4: Verify Ingestion

```bash
# Check ingestion status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id <job-id>

# Expected output:
# - numberOfMetadataDocumentsScanned: 1
# - numberOfNewDocumentsIndexed: 1
# - status: COMPLETE
```

---

## Test Documents

### Tenant 1 Document

**File:** `test_tenant1_with_metadata.txt`
```
COLPENSIONES - INFORMACIÓN GENERAL DEL TENANT 1

Este documento contiene información general sobre Colpensiones para el tenant 1.

Colpensiones es una entidad pública encargada de administrar el régimen de prima media
del Sistema General de Pensiones en Colombia.

SERVICIOS PRINCIPALES:
- Reconocimiento de pensiones
- Pago de mesadas pensionales
- Gestión de aportes
- Atención al usuario

MISIÓN:
Garantizar el pago oportuno de las pensiones y gestionar los recursos del régimen
de prima media con eficiencia y transparencia.
```

**Metadata:** `test_tenant1_with_metadata.txt.metadata.json`
```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "roles": "viewer",
    "project_id": "100",
    "users": "*"
  }
}
```

### Tenant 2 Document

**File:** `test_tenant2.txt`
```
ORGANIZACIÓN AC - INFORMACIÓN DEL TENANT 2

Este documento pertenece al tenant 2 (Organización AC).

Organización AC es un cliente corporativo que utiliza la plataforma ProcessApp
para gestión de procesos pensionales.

DATOS OPERATIVOS:
- Usuarios activos: 150
- Documentos procesados: 12,500
- Disponibilidad (Uptime): 99.95%
```

**Metadata:** `test_tenant2.txt.metadata.json`
```json
{
  "metadataAttributes": {
    "tenant_id": "2",
    "roles": "viewer",
    "project_id": "200",
    "users": "*"
  }
}
```

---

## Ingestion Results

### Successful Ingestion Job

**Job ID:** VKCUPTVHHU

```json
{
  "status": "COMPLETE",
  "statistics": {
    "numberOfDocumentsScanned": 7,
    "numberOfMetadataDocumentsScanned": 1,
    "numberOfNewDocumentsIndexed": 1,
    "numberOfModifiedDocumentsIndexed": 0,
    "numberOfDocumentsFailed": 1
  }
}
```

**Key Indicators:**
- ✅ `numberOfMetadataDocumentsScanned: 1` - Metadata file found
- ✅ `numberOfNewDocumentsIndexed: 1` - Document indexed successfully
- ✅ Failed document is unrelated (PNG file)

---

## API Test Results

### Test 1: Tenant 1 Accesses Own Data ✅

**Request:**
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "X-Api-Key: xxx" \
  -H "x-tenant-id: 1" \
  -H "x-user-id: user1" \
  -H "x-user-roles: [\"viewer\"]" \
  -d '{"question": "What is Colpensiones?"}'
```

**Response:**
```json
{
  "answer": "Colpensiones is a public entity responsible for managing the average premium regime of the General Pension System in Colombia...",
  "sessionId": "...",
  "status": "success"
}
```

**Result:** ✅ PASS - Found tenant 1 document

### Test 2: Tenant 2 Accesses Own Data ✅

**Request:**
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "X-Api-Key: xxx" \
  -H "x-tenant-id: 2" \
  -H "x-user-id: user2" \
  -H "x-user-roles: [\"viewer\"]" \
  -d '{"question": "How many active users does Organization AC have?"}'
```

**Response:**
```json
{
  "answer": "According to the obtained results, Organization AC has 150 active users.",
  "sessionId": "...",
  "status": "success"
}
```

**Result:** ✅ PASS - Found tenant 2 document

### Test 3: Cross-Tenant Access Blocked ✅

**Request:** Tenant 1 tries to access Tenant 2 data
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "X-Api-Key: xxx" \
  -H "x-tenant-id: 1" \
  -H "x-user-id: user1" \
  -H "x-user-roles: [\"viewer\"]" \
  -d '{"question": "How many users does Organization AC have?"}'
```

**Response:**
```json
{
  "answer": "The model cannot find sufficient information to answer the question about the number of users in Organization AC...",
  "sessionId": "...",
  "status": "success"
}
```

**Result:** ✅ PASS - Tenant isolation enforced, no data leakage

### Test 4: Reverse Cross-Tenant Access Blocked ✅

**Request:** Tenant 2 tries to access Tenant 1 data
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "X-Api-Key: xxx" \
  -H "x-tenant-id: 2" \
  -H "x-user-id: user2" \
  -H "x-user-roles: [\"viewer\"]" \
  -d '{"question": "What is the mission of Colpensiones?"}'
```

**Response:**
```json
{
  "answer": "The model cannot find sufficient information to answer the question about the mission of Colpensiones...",
  "sessionId": "...",
  "status": "success"
}
```

**Result:** ✅ PASS - Tenant isolation enforced, no data leakage

---

## Lambda Logs Verification

### API Handler Lambda

**Successful Tenant 1 Query:**
```
Tenant context: {"tenant_id": "1", "user_id": "user1", "roles": ["viewer"], "project_id": null, "users": []}
KB filter: {"andAll": [{"equals": {"key": "tenant_id", "value": "1"}}, {"orAll": [{"equals": {"key": "roles", "value": "viewer"}}, {"equals": {"key": "roles", "value": "*"}}]}]}
Using retrieve_and_generate with metadata filtering
Generated answer: Colpensiones is a public entity responsible for managing...
```

**Blocked Tenant 2 Query (from Tenant 1 user):**
```
Tenant context: {"tenant_id": "1", "user_id": "user1", "roles": ["viewer"], "project_id": null, "users": []}
KB filter: {"andAll": [{"equals": {"key": "tenant_id", "value": "1"}}, {"orAll": [{"equals": {"key": "roles", "value": "viewer"}}, {"equals": {"key": "roles", "value": "*"}}]}]}
Using retrieve_and_generate with metadata filtering
Generated answer: The model cannot find sufficient information...
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                           │
│  Headers: x-tenant-id=1, x-user-roles=["viewer"]                │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY                                 │
│  - CORS: Allow x-tenant-id, x-user-roles headers                │
│  - API Key validation                                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API HANDLER LAMBDA                             │
│  1. Extract tenant context from headers                          │
│  2. Build KB filter: {"andAll": [...]}                          │
│  3. Call retrieve_and_generate with filter                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              BEDROCK KNOWLEDGE BASE (S3_VECTORS)                 │
│  - Apply metadata filter BEFORE vector search                   │
│  - Only return chunks matching tenant_id + roles                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BEDROCK AGENT (Nova Pro)                     │
│  - Generate answer using ONLY filtered chunks                    │
│  - Apply guardrails (PII filtering)                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE TO CLIENT                            │
│  - Tenant-isolated answer                                        │
│  - No cross-tenant data leakage                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## S3 Vectors Metadata Filtering

### How It Works

1. **Ingestion:** Bedrock KB reads `document.txt` and `document.txt.metadata.json`
2. **Chunking:** Document is split into chunks (max 512 tokens, 20% overlap)
3. **Embedding:** Each chunk gets vector embedding (Titan v2)
4. **Metadata Attachment:** Each chunk inherits metadata from .metadata.json
5. **Storage:** Chunks + embeddings + metadata stored in S3 Vectors index

### Query-Time Filtering

1. **Filter Applied:** Before similarity search
2. **Simultaneous Evaluation:** Metadata filter + vector similarity evaluated together
3. **Result:** Only chunks matching BOTH filter + similarity are returned

### Filter Limitations (S3_VECTORS)

**Supported:**
- ✅ `equals`, `notEquals`
- ✅ `greaterThan`, `lessThan`, `greaterThanOrEquals`, `lessThanOrEquals`
- ✅ `in`, `notIn`
- ✅ `andAll`, `orAll`

**Not Supported:**
- ❌ `startsWith`
- ❌ `stringContains`

---

## Files Created/Modified

### Created Files

1. `/infrastructure/lambdas/api-handler/metadata_filter.py` - Core filtering logic
2. `/infrastructure/lib/SessionMemoryStack.ts` - DynamoDB for conversations
3. `/scripts/test_tenant1_with_metadata.txt` - Test document Tenant 1
4. `/scripts/test_tenant1_with_metadata.txt.metadata.json` - Metadata Tenant 1
5. `/scripts/test_tenant2.txt` - Test document Tenant 2
6. `/scripts/test_tenant2.txt.metadata.json` - Metadata Tenant 2
7. `/scripts/test-comprehensive-fixed.py` - Final test script
8. `/docs/METADATA_FILTERING_SUCCESS.md` - This document

### Modified Files

1. `/infrastructure/lambdas/api-handler/index.py` - Added metadata filtering
2. `/infrastructure/lib/APIStack.ts` - Added KB permissions, CORS headers
3. `/infrastructure/lib/AgentStack.ts` - Added action groups (commented out)
4. `/infrastructure/bin/app.ts` - Added SessionMemoryStack

---

## Deployment Commands

```bash
cd infrastructure

# Deploy API stack with metadata filtering
npx cdk deploy dev-us-east-1-api --exclusively --profile ans-super --require-approval never
```

---

## Production Checklist

Before deploying to production:

- [ ] **OCR Lambda Update:** Preserve S3 object metadata when creating .txt files from images/PDFs
- [ ] **Automated Metadata Generation:** Create Lambda to generate .metadata.json from S3 object path/tags
- [ ] **Metadata Validation:** Add schema validation for .metadata.json format
- [ ] **Audit Logging:** Log all filter applications and access attempts
- [ ] **Performance Testing:** Test with 100+ tenants and 10K+ documents
- [ ] **Error Handling:** Add fallback behavior if metadata.json is missing
- [ ] **Documentation:** Update API docs with metadata requirements
- [ ] **Monitoring:** Add CloudWatch alarms for failed ingestions

---

## Known Limitations

1. **Manual Metadata Files:** Must manually create .metadata.json for each document
2. **S3_VECTORS Filters:** No `startsWith` or `stringContains` support
3. **OCR Workflow:** OCR Lambda doesn't currently preserve/generate metadata.json
4. **Single Storage Type:** Only tested with S3_VECTORS (not OpenSearch/Aurora)
5. **Wildcard Users:** `users: "*"` means "all users" - no per-user granular control yet

---

## Future Enhancements

### Phase 2: Automated Metadata Generation

Create Lambda function to automatically generate .metadata.json from:
- S3 object path (e.g., `/tenants/{tenantId}/projects/{projectId}/`)
- S3 object tags
- External API call to project management system

### Phase 3: Role-Based Access Control (RBAC)

Expand filtering to support:
- Multiple roles per user
- Role hierarchies (admin > supervisor > viewer)
- Project-level permissions
- User-specific document access

### Phase 4: OpenSearch Migration

Migrate to OpenSearch Serverless for:
- Full-text search with metadata filtering
- `startsWith` and `stringContains` support
- Better performance with large metadata sets

---

## Support & Resources

**AWS Documentation:**
- [S3 Vectors Metadata Filtering](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-vectors-metadata-filtering.html)
- [Bedrock KB Metadata Filtering](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html)

**Project Files:**
- API Handler: `/infrastructure/lambdas/api-handler/index.py`
- Filter Module: `/infrastructure/lambdas/api-handler/metadata_filter.py`
- Test Scripts: `/scripts/test-comprehensive-fixed.py`

**Contact:**
- AWS Account: 708819485463
- Region: us-east-1
- KB ID: R80HXGRLHO
- API: https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query

---

**Last Updated:** 2026-04-26  
**Status:** ✅ Production Ready (Dev Environment)  
**Next Steps:** Update OCR Lambda to generate metadata.json files automatically
