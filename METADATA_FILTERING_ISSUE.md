# Metadata Filtering Issue - Project Isolation

**Date:** 2026-05-03  
**Issue:** Documents from project 165 are visible when filtering by project 6636

---

## Problem Description

When filtering by `tenant_id=1001, project_id=6636`:
- ❌ **Actual:** Returns Luis Fernández (from project 165)
- ✅ **Expected:** Should NOT return Luis (he's in project 165, not 6636)

---

## Root Cause

AWS Bedrock Knowledge Base metadata filtering uses `equals` with `andAll`/`orAll` operators.

**Current filter structure:**
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "6636"}}
  ]
}
```

**Problem:** This filter matches documents where:
- `tenant_id` equals "1001" **AND**
- `project_id` equals "6636"

But Bedrock's `equals` operator **does NOT validate that the field exists or matches exactly**.

### Example Scenarios:

| Document Metadata | Filter | Matches? | Why |
|-------------------|--------|----------|-----|
| `{tenant_id: "1001", project_id: "165"}` | `{tenant_id: "1001", project_id: "6636"}` | ❌ YES (BUG) | Should not match, but does |
| `{tenant_id: "1001", project_id: "6636"}` | `{tenant_id: "1001", project_id: "6636"}` | ✅ YES | Correct |
| `{tenant_id: "1001"}` | `{tenant_id: "1001", project_id: "6636"}` | ❌ YES (BUG) | Should not match, but does |

**Key insight:** Documents without `project_id` field are also matched, and documents with different `project_id` might also match depending on Bedrock's internal implementation.

---

## Bedrock Limitations

AWS Bedrock Knowledge Base metadata filtering **does not support:**
- ❌ Negation (`NOT project_id = "165"`)
- ❌ Field existence checks (`project_id EXISTS`)
- ❌ Strict matching (`project_id == "6636" AND no other project_id`)
- ❌ Exclusion filters

**Only supported operators:**
- ✅ `equals` - Exact match
- ✅ `andAll` - Combine conditions with AND
- ✅ `orAll` - Combine conditions with OR
- ✅ `greaterThan`, `lessThan` - Numeric comparisons
- ✅ `in` - Match any value in list

---

## Solutions

### Option 1: Composite Key (Recommended)

Add a composite field that includes the hierarchy:

**Project-level document:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "scope": "tenant:1001|project:165"  // Composite key
  }
}
```

**Task-level document:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "task_id": "174",
    "scope": "tenant:1001|project:165|task:174"  // Composite key
  }
}
```

**Filter:**
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "165"}},
    {"equals": {"key": "scope", "value": "tenant:1001|project:165"}}
  ]
}
```

**Pros:**
- ✅ Strict matching
- ✅ No false positives

**Cons:**
- ❌ Requires re-uploading all documents with new metadata
- ❌ Increases metadata size slightly

---

### Option 2: Use `in` Operator with Explicit Values

Instead of `equals`, use `in` with explicit allowed values:

**Filter for project 165:**
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"in": {"key": "project_id", "value": ["165"]}}  // Only 165
  ]
}
```

**Problem:** This still has the same issue - doesn't validate field existence.

---

### Option 3: Add `partition_key` Field (Best Practice)

Use a dedicated partition field for filtering:

**Project-level document:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "partition_key": "t1001_p165"  // Unique partition
  }
}
```

**Task-level document:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "task_id": "174",
    "partition_key": "t1001_p165_t174"  // Unique partition
  }
}
```

**Filter:**
```json
{
  "equals": {"key": "partition_key", "value": "t1001_p165"}
}
```

**Pros:**
- ✅ Single field filter (most efficient)
- ✅ Guaranteed uniqueness
- ✅ No false positives

**Cons:**
- ❌ Requires re-uploading all documents
- ❌ Need to generate partition_key on upload

---

### Option 4: Multiple OR Conditions (Workaround)

For hierarchical access (project docs + task docs):

**Filter for task 174 (should access project + task docs):**
```json
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "165"}},
    {"orAll": [
      {"equals": {"key": "partition_key", "value": "t1001_p165"}},
      {"equals": {"key": "partition_key", "value": "t1001_p165_t174"}}
    ]}
  ]
}
```

This allows accessing both project-level and task-level docs.

---

## Recommended Solution: partition_key

**Implementation Plan:**

1. **Add `partition_key` to all documents:**
   - Format: `t{tenant_id}_p{project_id}[_t{task_id}]`
   - Examples:
     - Project doc: `t1001_p165`
     - Task doc: `t1001_p165_t174`

2. **Update metadata_handler.py:**
   - Build `partition_key` based on provided metadata
   - Generate list of allowed partition keys for hierarchical access

3. **Filter logic:**
   - **Tenant only:** `tenant_id = 1001` (no partition filter)
   - **Project:** `partition_key = t1001_p165` OR `partition_key starts with t1001_p165_`
   - **Task:** `partition_key = t1001_p165` OR `partition_key = t1001_p165_t174`

4. **Migration:**
   - Script to add `partition_key` to all existing S3 metadata files
   - Re-run ingestion job

---

## Next Steps

1. Create migration script to add `partition_key` to all documents
2. Update `metadata_handler.py` to build partition-based filters
3. Test with existing data
4. Document new metadata structure

---

## References

- AWS Bedrock KB Metadata Filtering: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-metadata.html
- Supported filter operators: `equals`, `andAll`, `orAll`, `greaterThan`, `lessThan`, `in`
- No support for: negation, field existence, exclusion
