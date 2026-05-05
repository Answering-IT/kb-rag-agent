# Retrieve Tool Usage Guide
**Version:** 1.0.0  
**Last Updated:** 2026-05-04  
**Reference:** [Strands Tools Tests](https://github.com/strands-agents/tools/blob/d5376f00740491102c50b3b4d6f394e5952044c1/tests/test_retrieve.py#L513)

---

## Overview

The `retrieve` tool from Strands SDK enables searching AWS Bedrock Knowledge Base with powerful metadata filtering capabilities. This guide documents the correct usage based on official Strands tests.

---

## Basic Usage

### Simple Retrieval (No Filters)

```python
from strands_tools import retrieve

# Agent automatically calls retrieve tool
result = agent.tool.retrieve(
    text="What are the vacation policies?",
    knowledgeBaseId="R80HXGRLHO"
)
```

### With Score Threshold

```python
result = agent.tool.retrieve(
    text="pension requirements",
    knowledgeBaseId="R80HXGRLHO",
    score=0.7  # Only results with score >= 0.7
)
```

---

## Metadata Filtering

### Filter Structure

Filters follow AWS Bedrock retrieveFilter format:

```python
{
    "andAll": [
        {"equals": {"key": "field1", "value": "value1"}},
        {"equals": {"key": "field2", "value": "value2"}}
    ]
}
```

### Supported Operators

1. **equals** - Exact match
```python
{"equals": {"key": "tenant_id", "value": "1001"}}
```

2. **andAll** - All conditions must match (minimum 2 items)
```python
{
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "project_id", "value": "165"}}
    ]
}
```

3. **orAll** - At least one condition must match (minimum 2 items)
```python
{
    "orAll": [
        {"equals": {"key": "category", "value": "security"}},
        {"equals": {"key": "category", "value": "compliance"}}
    ]
}
```

---

## Multi-Tenant Filtering Examples

### Example 1: Tenant-Only Filter

**All documents from a specific tenant:**

```python
retrieve_filter = {
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}}
    ]
}

result = agent.tool.retrieve(
    text="What documents are available?",
    retrieveFilter=retrieve_filter
)
```

### Example 2: Tenant + Project Filter

**Only project-level documents (excludes task-level):**

```python
retrieve_filter = {
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "project_id", "value": "165"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165"}}
    ]
}

result = agent.tool.retrieve(
    text="What's in project 165?",
    retrieveFilter=retrieve_filter
)
```

### Example 3: Tenant + Project + Task Filter

**Only task-specific documents:**

```python
retrieve_filter = {
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165_t174"}}
    ]
}

result = agent.tool.retrieve(
    text="What's in task 174?",
    retrieveFilter=retrieve_filter
)
```

---

## Partition Key Format

Our multi-tenant isolation uses `partition_key` for strict hierarchy:

### Format Rules

- **Project-level:** `t{tenant}_p{project}`
- **Task-level:** `t{tenant}_p{project}_t{task}`

### Examples

| Tenant | Project | Task | Partition Key |
|--------|---------|------|---------------|
| 1001 | 165 | - | `t1001_p165` |
| 1001 | 165 | 174 | `t1001_p165_t174` |
| 1001 | 200 | - | `t1001_p200` |
| 2050 | 300 | 450 | `t2050_p300_t450` |

### Why Partition Keys?

1. **Strict isolation** - No false positives from substring matching
2. **Hierarchical access** - Tenant → Project → Task levels
3. **Efficient indexing** - Single field for complex hierarchy
4. **S3 metadata compatible** - Fits in S3 object metadata

---

## Complete Example with All Features

```python
from strands import Agent
from strands_tools import retrieve

# Initialize agent
agent = Agent(
    model="amazon.nova-pro-v1:0",
    tools=[retrieve]
)

# Build filter for tenant 1001, project 165
retrieve_filter = {
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "project_id", "value": "165"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165"}}
    ]
}

# Execute retrieval with all options
result = agent.tool.retrieve(
    text="What are the pension eligibility requirements?",
    knowledgeBaseId="R80HXGRLHO",
    retrieveFilter=retrieve_filter,
    numberOfResults=10,
    score=0.5,  # Minimum score threshold
    enableMetadata=True  # Include metadata in response
)

# Result structure
# {
#     "status": "success",
#     "content": [
#         {
#             "text": "Retrieved 5 results with score >= 0.5\n\n" +
#                     "Score: 0.8500\n" +
#                     "Document ID: doc-001\n" +
#                     "Content: Pension eligibility requires...\n" +
#                     "Metadata: {...}\n\n" +
#                     "..."
#         }
#     ]
# }
```

---

## How Our Agent Uses Filters

### Automatic Filter Injection

In `core/orchestrator.py`, filters are automatically built and injected:

```python
# 1. Extract metadata from request
metadata = orchestrator.extract_metadata(headers, body)

# 2. Build filter
kb_filter = MetadataFilterBuilder.build_filter(metadata)
# Output: {"andAll": [{"equals": {"key": "tenant_id", "value": "1001"}}, ...]}

# 3. Inject into prompt (agent receives it)
prompt = f"""
User question: {input_text}

METADATA FILTERING ACTIVA:
Cuando uses 'retrieve', DEBES incluir:
retrieveFilter={json.dumps(kb_filter)}
"""

# 4. Agent calls retrieve with filter
result = agent(prompt)  # Agent automatically includes retrieveFilter
```

### Request Flow

```
Client Request
    ↓
FastAPI /invocations
    ↓
Extract metadata (tenant, project, task)
    ↓
Build retrieveFilter
    ↓
Inject filter into prompt
    ↓
Agent calls retrieve tool with filter
    ↓
Bedrock KB filters results
    ↓
Stream response to client
```

---

## Testing Filters Locally

### Test Script Example

```bash
#!/bin/bash
# Test tenant + project filter

curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "What documents are in project 165?",
    "sessionId": "test-123",
    "metadata": {
      "tenant_id": "1001",
      "project_id": "165"
    }
  }'
```

### Expected Filter Output (in logs)

```
[Filter] ✅ tenant_id: 1001
[Filter] ✅ project_id: 165
[Filter] ✅ partition_key (project): t1001_p165
[Filter] Built filter with 3 conditions
{
  "andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "165"}},
    {"equals": {"key": "partition_key", "value": "t1001_p165"}}
  ]
}
```

---

## Common Pitfalls

### ❌ Wrong: Using orAll with single condition

```python
# ERROR: orAll/andAll must have at least 2 items
{
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}}
    ]
}
```

**Fix:** Use equals directly or add another condition

```python
# Correct
{"equals": {"key": "tenant_id", "value": "1001"}}

# Or
{
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165"}}
    ]
}
```

### ❌ Wrong: Invalid operator

```python
{
    "invalid_operator": {"key": "tenant_id"}
}
```

**Fix:** Use supported operators: `equals`, `andAll`, `orAll`

### ❌ Wrong: Missing required fields

```python
{"equals": {"key": "tenant_id"}}  # Missing "value"
```

**Fix:** Include both `key` and `value`

```python
{"equals": {"key": "tenant_id", "value": "1001"}}
```

---

## Validation

### Filter Validator (from Strands tests)

```python
def validate_filter(filter_dict):
    """Validate filter structure"""
    if not isinstance(filter_dict, dict):
        raise ValueError("Filter must be a dictionary")

    # Check operators
    valid_operators = {'equals', 'andAll', 'orAll'}
    operators = set(filter_dict.keys())

    if not operators.issubset(valid_operators):
        invalid = operators - valid_operators
        raise ValueError(f"Invalid operators: {invalid}")

    # Validate equals
    if 'equals' in filter_dict:
        equals = filter_dict['equals']
        if 'key' not in equals or 'value' not in equals:
            raise ValueError("equals must have 'key' and 'value'")

    # Validate andAll/orAll
    for op in ['andAll', 'orAll']:
        if op in filter_dict:
            conditions = filter_dict[op]
            if not isinstance(conditions, list):
                raise ValueError(f"{op} must be a list")
            if len(conditions) < 2:
                raise ValueError(f"{op} must contain at least 2 items")

    return True
```

---

## Performance Tips

1. **Use partition_key for hierarchy** - More efficient than multiple field filters
2. **Set appropriate score threshold** - Filter low-quality results early
3. **Limit numberOfResults** - Default is 10, adjust based on needs
4. **Combine filters with AND** - More specific = better performance

---

## References

- [Strands Tools - retrieve.py](https://github.com/strands-agents/tools/blob/main/src/strands_tools/retrieve.py)
- [Strands Tests - test_retrieve.py](https://github.com/strands-agents/tools/blob/main/tests/test_retrieve.py)
- [AWS Bedrock Agent Runtime - Retrieve API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent-runtime_Retrieve.html)
- [ProcessApp Metadata Filtering](./METADATA_FILTERING_SUCCESS.md)

---

**Next Steps:**
1. Review `core/tools/metadata_filter.py` for implementation
2. Run `./test_local.sh` to test filters locally
3. Check CloudWatch logs for filter validation
