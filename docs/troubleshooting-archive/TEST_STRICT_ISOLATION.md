# Test Case - Strict Metadata Isolation with partition_key

**Date:** 2026-05-03  
**Version:** 2.0 (with partition_key)  
**Change:** Implemented strict filtering to prevent cross-project data leakage

---

## 🔧 Changes Made

### Problem

Previous filtering allowed documents from project 165 to appear when filtering by project 6636.

**Root cause:** Bedrock KB metadata filtering with `equals` operator doesn't validate field existence strictly.

### Solution

Added `partition_key` field to all documents for strict isolation:

**Format:**
- Project-level: `t{tenant_id}_p{project_id}`
- Task-level: `t{tenant_id}_p{project_id}_t{task_id}`

**Examples:**
- Luis (project 165): `partition_key = "t1001_p165"`
- Luis achievements (task 174): `partition_key = "t1001_p165_t174"`
- Juan Daniel (project 6636): `partition_key = "t1001_p6636"`

---

## 📊 Filtering Logic (STRICT)

### 1. Tenant Only
**Input:** `{tenant_id: "1001"}`  
**Filter:** `tenant_id = "1001"` (no partition filter)  
**Returns:** All docs from tenant 1001

**Use case:** Admin viewing all tenant data

---

### 2. Tenant + Project
**Input:** `{tenant_id: "1001", project_id: "165"}`  
**Filter:** 
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "165"}},
    {"equals": {"key": "partition_key", "value": "t1001_p165"}}
  ]
}
```
**Returns:** ONLY project-level docs (partition = `t1001_p165`)  
**Excludes:** Task-level docs (partition = `t1001_p165_t*`)

**Use case:** Project overview, excluding task details

---

### 3. Tenant + Project + Task
**Input:** `{tenant_id: "1001", project_id: "165", task_id: "174"}`  
**Filter:**
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "partition_key", "value": "t1001_p165_t174"}}
  ]
}
```
**Returns:** ONLY task-level docs (partition = `t1001_p165_t174`)  
**Excludes:** Project-level docs (partition = `t1001_p165`)

**Use case:** Task-specific work, no access to general project info

---

## 🧪 Test Scenarios

### Test 1: Tenant Only (All Tenant Docs)

| Question | Metadata | Expected Result |
|----------|----------|-----------------|
| ¿Quién es Luis Fernández? | `{tenant_id: "1001"}` | ✅ Find Luis (any project) |
| ¿Quién es Juan Daniel? | `{tenant_id: "1001"}` | ✅ Find Juan Daniel (any project) |

---

### Test 2: Project 165 (Luis's Project, STRICT)

| Question | Metadata | Expected Result |
|----------|----------|-----------------|
| ¿Dónde nació Luis? | `{tenant_id: "1001", project_id: "165"}` | ✅ Find birthplace (project-level) |
| ¿Quién es Juan Daniel? | `{tenant_id: "1001", project_id: "165"}` | ❌ NOT found (different project) |
| ¿Qué hazañas hizo Luis? | `{tenant_id: "1001", project_id: "165"}` | ❌ NOT found (task-level data) |

**Key point:** Project filter excludes task-level data

---

### Test 3: Project 6636 (Juan Daniel's Project, STRICT)

| Question | Metadata | Expected Result |
|----------|----------|-----------------|
| ¿Quién es Juan Daniel? | `{tenant_id: "1001", project_id: "6636"}` | ✅ Find Juan Daniel |
| ¿Quién es Luis? | `{tenant_id: "1001", project_id: "6636"}` | ❌ NOT found (different project) |

**Key point:** Project 6636 does NOT see project 165 data

---

### Test 4: Task 174 (Luis's Achievements, STRICT)

| Question | Metadata | Expected Result |
|----------|----------|-----------------|
| ¿Qué hazañas hizo Luis? | `{tenant_id: "1001", project_id: "165", task_id: "174"}` | ✅ Find achievements (task-level) |
| ¿Dónde nació Luis? | `{tenant_id: "1001", project_id: "165", task_id: "174"}` | ❌ NOT found (project-level data) |

**Key point:** Task filter ONLY accesses task-specific data, NOT project data

---

### Test 5: Wrong Task (STRICT)

| Question | Metadata | Expected Result |
|----------|----------|-----------------|
| ¿Qué hazañas hizo Luis? | `{tenant_id: "1001", project_id: "165", task_id: "999"}` | ❌ NOT found (task 174 only) |

**Key point:** Task 999 does NOT see task 174 data

---

## 🗂️ Document Structure

### Luis Fernández (Project 165)

**Project-level document:**
```
s3://bucket/tenant/1001/project/165/luis-fernandez-datos.txt
Metadata: {
  "tenant_id": "1001",
  "project_id": "165",
  "partition_key": "t1001_p165"
}
Content: Nació en 1968, Santa Marta, 58 años
```

**Task-level document:**
```
s3://bucket/tenant/1001/project/165/tasks/174/luis-fernandez-hazanas.txt
Metadata: {
  "tenant_id": "1001",
  "project_id": "165",
  "task_id": "174",
  "partition_key": "t1001_p165_t174"
}
Content: 40 km sin zapatos, 12 km parado de manos
```

---

### Juan Daniel Pérez (Project 6636)

**Project-level document:**
```
s3://bucket/tenant/1001/project/6636/juan-daniel-perez-datos.txt
Metadata: {
  "tenant_id": "1001",
  "project_id": "6636",
  "partition_key": "t1001_p6636"
}
Content: Ingeniero civil, 31 años, actividades de mar
```

---

## 🚀 How to Run Tests

### Quick Test (wscat)

```bash
# Test 1: Project 165 - should find Luis
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

{"action":"sendMessage","data":{"inputText":"¿Dónde nació Luis Fernández?","sessionId":"test","tenant_id":"1001","project_id":"165"}}
# Expected: "Nació en Santa Marta"

# Test 2: Project 6636 - should NOT find Luis
{"action":"sendMessage","data":{"inputText":"¿Quién es Luis Fernández?","sessionId":"test","tenant_id":"1001","project_id":"6636"}}
# Expected: "Lo siento, no tengo información disponible"

# Test 3: Task 174 - should find achievements
{"action":"sendMessage","data":{"inputText":"¿Qué hazañas ha realizado Luis?","sessionId":"test","tenant_id":"1001","project_id":"165","task_id":"174"}}
# Expected: "40 kilómetros descalzo... 12 kilómetros parado de manos"

# Test 4: Task 174 - should NOT find birthplace (project-level data)
{"action":"sendMessage","data":{"inputText":"¿Dónde nació Luis?","sessionId":"test","tenant_id":"1001","project_id":"165","task_id":"174"}}
# Expected: "Lo siento, no tengo información disponible"
```

### Automated Test

```bash
./scripts/test-strict-isolation.sh
```

---

## ✅ Success Criteria

| Test | Criteria | Status |
|------|----------|--------|
| Cross-project isolation | Project 6636 does NOT see project 165 data | ⏳ To verify |
| Project vs Task separation | Project filter excludes task data | ⏳ To verify |
| Task vs Project separation | Task filter excludes project data | ⏳ To verify |
| Task isolation | Task 999 does NOT see task 174 data | ⏳ To verify |
| Tenant-level access | Tenant filter sees all projects | ⏳ To verify |
| No info leakage | Agent never mentions filters/metadata | ⏳ To verify |

---

## 📝 Implementation Details

### Files Modified

1. **agents/metadata_handler.py**
   - Updated `build_filter()` to use `partition_key`
   - Strict filtering: project vs task separation

2. **scripts/add-partition-keys.py**
   - Migration script to add `partition_key` to all documents
   - Executed successfully (15 documents updated)

3. **Bedrock Knowledge Base**
   - Reindexed with new metadata (Job: URCJAAOQFL)
   - Status: COMPLETE (15 modified, 0 failed)

---

## 🔒 Security Benefits

**Before (with bug):**
- ❌ Project 6636 could see project 165 data
- ❌ False positives in search results
- ❌ Data leakage between projects

**After (with partition_key):**
- ✅ Strict project isolation
- ✅ Strict task isolation
- ✅ No false positives
- ✅ Zero data leakage

---

## 📚 References

- **METADATA_FILTERING_ISSUE.md** - Problem analysis and solution
- **scripts/add-partition-keys.py** - Migration script
- **scripts/test-strict-isolation.sh** - Automated test suite

---

**Status:** ✅ Deployed and ready for testing  
**Deployment:** 2026-05-04 03:11:08 (dev-us-east-1-agent-v2)  
**Ingestion Job:** URCJAAOQFL (COMPLETE)  
**Next Step:** Manual testing to verify strict isolation works correctly
