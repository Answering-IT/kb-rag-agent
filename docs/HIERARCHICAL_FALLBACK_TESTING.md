# Hierarchical Fallback Testing Guide

**Last Updated:** 2026-05-05  
**Purpose:** Test hierarchical search fallback strategy with real KB data  
**Related Files:**
- `agents/core/tools/retrieve.py` - Implementation
- `scripts/test-hierarchical-fallback.py` - Test suite

---

## Overview

The hierarchical fallback feature allows the agent to search across organizational levels when project-specific results are insufficient, while maintaining strict tenant isolation.

### Strategy

```
1. Search with specific filter (e.g., t100001_p1 for project 1)
2. If results < MIN_RESULTS_THRESHOLD (2), fallback to parent level (t100001 for tenant)
3. Combine results (project-level prioritized)
4. NEVER fallback across projects (t100001_p1 → t100001_p2 ❌)
```

### Example Scenario

**User in Project 1 asks:** "¿Qué equipos están en semifinales de la Champions?"

**Process:**
1. Search with `partition_key = "t100001_p1"` → 0 results (Luis Díaz doc doesn't mention Champions semis)
2. Fallback to `partition_key = "t100001"` → ✅ Finds `champions.txt`
3. Return: "PSG, Bayern Múnich, Atlético Madrid, Arsenal"

---

## Test Data Structure

### Current KB Documents (3 total)

```
organizations/100001/
├── champions.txt
│   └── partition_key: "t100001"
│   └── Content: Champions League 2025-26, semifinales, PSG vs Bayern 5-4
│
├── projects/1/luis_diaz_biografia.txt
│   └── partition_key: "t100001_p1"
│   └── Content: Luis Díaz biography, Liverpool FC, Porto, Colombia
│
└── projects/2/manuel_neuer_info.txt
    └── partition_key: "t100001_p2"
    └── Content: Manuel Neuer biography, Bayern Múnich, 12 Bundesligas, portero-líbero
```

---

## Test Scenarios

### Test 1: Tenant-only does NOT see project documents ✅

**Purpose:** Verify strict isolation (tenant cannot access project-level docs)

**Setup:**
```python
headers = {"x-tenant-id": "100001"}  # NO project_id
query = "¿Quién es Luis Díaz?"
```

**Expected:**
- ❌ Should NOT find `luis_diaz_biografia.txt`
- Reason: Document has `partition_key="t100001_p1"` (project-level)
- Response: Generic answer or "No tengo información sobre Luis Díaz"

**Validation:**
- Response should NOT mention Liverpool, Porto, or career details

---

### Test 2: Project-specific finds its content ✅

**Purpose:** Verify project-level access works correctly

**Setup:**
```python
headers = {"x-tenant-id": "100001", "x-project-id": "1"}
query = "¿Dónde juega Luis Díaz actualmente?"
```

**Expected:**
- ✅ Should find `luis_diaz_biografia.txt`
- Filter: `partition_key="t100001_p1"`
- Response: "Liverpool FC" (joined in January 2022)

**Validation:**
- Response mentions "Liverpool" or "Liverpool FC"

---

### Test 3: Fallback to tenant-level (Champions info) 🔥

**Purpose:** Verify fallback works when project doc doesn't have answer

**Setup:**
```python
headers = {"x-tenant-id": "100001", "x-project-id": "1"}
query = "¿Qué equipos están en semifinales de la Champions League?"
```

**Expected Process:**
1. Search `partition_key="t100001_p1"` → 0 results (Luis Díaz doc doesn't mention semis)
2. Fallback to `partition_key="t100001"` → ✅ Finds `champions.txt`
3. Response: "PSG, Bayern Múnich, Atlético Madrid, Arsenal"

**Validation:**
- Response mentions at least 2 of: PSG, Bayern, Atlético, Arsenal
- Logs should show: `[Fallback] Only 0 results found, attempting tenant-level fallback`

---

### Test 4: Cross-project isolation (NO fallback to other projects) ✅

**Purpose:** Verify fallback does NOT cross project boundaries

**Setup:**
```python
headers = {"x-tenant-id": "100001", "x-project-id": "1"}
query = "¿Cuántos años tiene Manuel Neuer?"
```

**Expected Process:**
1. Search `partition_key="t100001_p1"` → 0 results (wrong project)
2. Fallback to `partition_key="t100001"` → 0 results (Neuer doc is in project 2)
3. Response: Generic answer or "No tengo información sobre Manuel Neuer"

**Critical:**
- ❌ Should NEVER fallback to `partition_key="t100001_p2"` (cross-project breach)
- ❌ Should NOT mention "40 años" or Bayern career details

**Validation:**
- Response does NOT contain specific Neuer information
- Isolation maintained between projects

---

### Test 5: Mixed results (Bayern query from Neuer's project) 🔥

**Purpose:** Verify combination of project + tenant results

**Setup:**
```python
headers = {"x-tenant-id": "100001", "x-project-id": "2"}
query = "¿Cómo le fue al Bayern en la Champions League?"
```

**Expected Process:**
1. Search `partition_key="t100001_p2"` → 1-2 results (Neuer doc: "2 Champions League titles")
2. Results < threshold (2), trigger fallback
3. Fallback to `partition_key="t100001"` → ✅ Finds `champions.txt` (current semifinal)
4. Combine: Historical context (Neuer) + Current status (semifinals)

**Validation:**
- Response mentions BOTH:
  - Historical context: Neuer's titles or Bayern's success
  - Current context: "semifinales", "PSG", "5-4"

---

### Test 6: Tenant-level access to general info ✅

**Purpose:** Verify tenant-level documents are accessible without fallback

**Setup:**
```python
headers = {"x-tenant-id": "100001"}  # No project_id
query = "¿Cuántos goles metió PSG contra Bayern?"
```

**Expected:**
- ✅ Should find `champions.txt`
- Filter: `partition_key="t100001"`
- Response: "5-4" or "PSG 5 - 4 Bayern"

**Validation:**
- Response mentions score "5-4" or "cinco a cuatro"

---

## Running Tests Locally with Docker

### Prerequisites

- Docker installed and running
- AWS credentials configured (`ans-super` profile)
- Knowledge Base synced with test data

### Step 1: Build Agent Container

```bash
cd agents
docker build -t processapp-agent:test .
```

### Step 2: Run Agent Container

```bash
docker run -d \
  -p 8080:8080 \
  -e AWS_PROFILE=ans-super \
  -e AWS_REGION=us-east-1 \
  -e KB_ID=BLJTRDGQI0 \
  -e MODEL_ID=amazon.nova-pro-v1:0 \
  -v ~/.aws:/root/.aws:ro \
  --name agent-test \
  processapp-agent:test
```

**Environment variables:**
- `AWS_PROFILE=ans-super` - AWS credentials profile
- `AWS_REGION=us-east-1` - KB region
- `KB_ID=BLJTRDGQI0` - Knowledge Base ID
- `MODEL_ID=amazon.nova-pro-v1:0` - LLM model

### Step 3: Verify Agent is Running

```bash
# Check health endpoint
curl http://localhost:8080/health

# Check logs
docker logs agent-test --follow
```

### Step 4: Run Test Suite

```bash
cd /Users/qohatpretel/Answering/kb-rag-agent
python3 scripts/test-hierarchical-fallback.py
```

**Expected output:**
```
================================================================================
🧪 HIERARCHICAL FALLBACK TESTS
================================================================================

✅ Agent is running

[1/6] Test 1: Tenant-only does NOT see project documents
  Query: ¿Quién es Luis Díaz?
  Headers: {'x-tenant-id': '100001'}
  Result: ✅ PASS
    ✅ Correctly did NOT return isolated content
    ℹ️  Reason: luis_diaz_biografia.txt has partition_key='t100001_p1' (project-level)
  Response snippet: No tengo información específica sobre Luis Díaz...

[2/6] Test 2: Project-specific finds its content
  Query: ¿Dónde juega Luis Díaz actualmente?
  Headers: {'x-tenant-id': '100001', 'x-project-id': '1'}
  Result: ✅ PASS
    ✅ Found relevant content (matched: ['liverpool'])
    ℹ️  Reason: luis_diaz_biografia.txt has partition_key='t100001_p1'
  Response snippet: Luis Díaz juega actualmente en el Liverpool FC...

[3/6] Test 3: Fallback to tenant-level (Champions info from project context)
  Query: ¿Qué equipos están en semifinales de la Champions League?
  Headers: {'x-tenant-id': '100001', 'x-project-id': '1'}
  Result: ✅ PASS
    ✅ Found relevant content (matched: ['psg', 'bayern', 'semifinal'])
    ℹ️  Fallback expected: Query is about Champions (tenant-level doc), not Luis Diaz (project doc)
    ℹ️  Reason: champions.txt has partition_key='t100001' (tenant-level)
  Response snippet: Los equipos en semifinales son PSG, Bayern Múnich, Atlético Madrid y Arsenal...

[4/6] Test 4: Cross-project isolation (NO fallback to other projects)
  Query: ¿Cuántos años tiene Manuel Neuer?
  Headers: {'x-tenant-id': '100001', 'x-project-id': '1'}
  Result: ✅ PASS
    ✅ Correctly did NOT return isolated content
    ℹ️  Fallback expected: Fallback should go to t100001 (tenant), NOT t100001_p2 (cross-project)
    ℹ️  Reason: manuel_neuer_info.txt has partition_key='t100001_p2' (different project)
  Response snippet: No tengo información sobre la edad de Manuel Neuer...

[5/6] Test 5: Mixed results (Bayern query from Neuer's project)
  Query: ¿Cómo le fue al Bayern en la Champions League?
  Headers: {'x-tenant-id': '100001', 'x-project-id': '2'}
  Result: ✅ PASS
    ✅ Found relevant content (matched: ['bayern', 'semifinal'])
    ℹ️  Fallback expected: Project doc may have limited results, fallback provides current context
    ℹ️  Reason: manuel_neuer_info.txt (project) + champions.txt (tenant-level)
  Response snippet: Bayern perdió 5-4 contra PSG en las semifinales...

[6/6] Test 6: Tenant-level access to general info
  Query: ¿Cuántos goles metió PSG contra Bayern?
  Headers: {'x-tenant-id': '100001'}
  Result: ✅ PASS
    ✅ Found relevant content (matched: ['5'])
    ℹ️  Reason: champions.txt has partition_key='t100001'
  Response snippet: PSG metió 5 goles contra Bayern en la ida...

================================================================================
📊 SUMMARY
================================================================================
Passed: 6/6

✅ All tests passed!
```

### Step 5: Cleanup

```bash
docker stop agent-test
docker rm agent-test
```

---

## Interpreting Results

### What to look for in logs

**Successful fallback:**
```
[RetrieveWrapper] ✅ Retrieve call succeeded (0 results)
[Fallback] Only 0 results found, attempting tenant-level fallback
[Fallback] Building tenant filter: t100001_p1 → t100001
[Fallback] ✅ Tenant-level search succeeded (3 results)
[Fallback] ✅ Combined results: 0 project + 3 tenant
```

**No fallback needed:**
```
[RetrieveWrapper] ✅ Retrieve call succeeded (4 results)
```

**Cross-project isolation maintained:**
```
[RetrieveWrapper] ✅ Retrieve call succeeded (0 results)
[Fallback] Building tenant filter: t100001_p1 → t100001
[Fallback] ✅ Tenant-level search succeeded (0 results)
# No results at tenant level either - Neuer doc is in project 2
```

---

## Troubleshooting

### Test fails: "Agent not accessible"

**Solution:**
```bash
# Check container is running
docker ps | grep agent-test

# Check logs for errors
docker logs agent-test

# Restart container
docker restart agent-test
```

### Test fails: "Empty response from agent"

**Possible causes:**
1. AWS credentials not mounted correctly
2. Knowledge Base ID incorrect
3. Model ID not found

**Solution:**
```bash
# Check AWS credentials work inside container
docker exec agent-test aws sts get-caller-identity --profile ans-super

# Check environment variables
docker exec agent-test env | grep -E "KB_ID|MODEL_ID|AWS"
```

### Test fails: "Isolation breach" (found forbidden keywords)

**Possible causes:**
1. Metadata filters not applied correctly
2. Fallback logic crossing project boundaries

**Solution:**
```bash
# Check agent logs for filter details
docker logs agent-test | grep -A 5 "Filter"

# Verify KB metadata is correct
aws s3 cp s3://processapp-docs-v2-dev-708819485463/organizations/100001/projects/1/luis_diaz_biografia.txt.metadata.json - --profile ans-super
```

### Fallback not triggering when expected

**Possible causes:**
1. `MIN_RESULTS_THRESHOLD` too low
2. Result counting logic incorrect

**Solution:**
```bash
# Check result counts in logs
docker logs agent-test | grep "results)"

# Adjust threshold in agents/core/tools/retrieve.py
MIN_RESULTS_THRESHOLD = 3  # Increase if fallback not triggering enough
```

---

## Implementation Details

### MIN_RESULTS_THRESHOLD

**Current value:** 2

**Rationale:**
- With only 3 documents in KB, threshold must be low
- threshold=2 allows single-result responses without fallback
- threshold=1 only triggers fallback on empty results

**Tuning:**
```python
# In agents/core/tools/retrieve.py
MIN_RESULTS_THRESHOLD = 2

# If you want more aggressive fallback:
MIN_RESULTS_THRESHOLD = 3  # Fallback if < 3 results

# If you want conservative fallback:
MIN_RESULTS_THRESHOLD = 1  # Only fallback if empty
```

### Fallback Hierarchy

**Valid fallback paths:**
```
t100001_p1_t5_s3 → t100001_p1_t5 → t100001_p1 → t100001 ✅
t100001_p2 → t100001 ✅
```

**Invalid fallback paths:**
```
t100001_p1 → t100001_p2 ❌ (cross-project)
t100001_p1_t5 → t100001_p2 ❌ (cross-project)
```

### Result Combination Strategy

**Current strategy:** Simple append with section marker

```python
combined_text = (
    f"{project_results}\n\n"
    f"[Additional context from organization-level documents]:\n"
    f"{tenant_results}"
)
```

**Alternative strategies (for future):**
- Rank by relevance score (requires parsing Bedrock scores)
- Deduplicate overlapping content
- Limit total results to avoid context overflow

---

## Next Steps

### After local tests pass:

1. **Deploy to dev environment:**
   ```bash
   cd infrastructure
   npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
   ```

2. **Test via WebSocket:**
   ```bash
   wscat -c wss://6aqhp0u2zk.execute-api.us-east-1.amazonaws.com/dev
   {"action":"sendMessage","data":{"inputText":"¿Qué equipos están en semifinales?","sessionId":"test-123","metadata":{"tenant_id":"100001","project_id":"1"}}}
   ```

3. **Monitor CloudWatch logs:**
   ```bash
   aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super | grep -E "Fallback|Filter"
   ```

4. **Update CLAUDE.md** with fallback feature documentation

---

**Last Updated:** 2026-05-05  
**Status:** Ready for local testing  
**Next:** Deploy to dev after local validation
