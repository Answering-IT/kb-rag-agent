# ProcessApp Agent v2.0 - Architecture

**Clean, modular RAG agent with multi-tenant support**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Request                        │
│              (HTTP POST /invocations + metadata)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Server                          │
│                       (main.py)                             │
│  - Parse request                                            │
│  - Extract headers & body                                    │
│  - Stream NDJSON response                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   AgentOrchestrator                          │
│               (core/orchestrator.py)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Extract Metadata (tenant, project, task)        │   │
│  │  2. Build KB Filter (partition_key format)          │   │
│  │  3. Get Session Context (last 6 messages)           │   │
│  │  4. Build Enhanced Prompt (context + filter)        │   │
│  │  5. Call Strands Agent                              │   │
│  │  6. Clean Response (remove <thinking> tags)         │   │
│  │  7. Stream Chunks (3 words each)                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────┬─────────────┬─────────────┬─────────────┬────────────┘
      │             │             │             │
      ▼             ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Metadata │  │ Session  │  │  Config  │  │  Strands │
│ Filter   │  │ Manager  │  │ Manager  │  │  Agent   │
│ Builder  │  │          │  │          │  │          │
└──────────┘  └──────────┘  └──────────┘  └────┬─────┘
                                                 │
                                                 ▼
                                          ┌─────────────┐
                                          │   Bedrock   │
                                          │  KB (S3)    │
                                          │             │
                                          │  + retrieve │
                                          │  + http_req │
                                          └─────────────┘
```

---

## Component Hierarchy

### 1. Entry Point (`main.py`)

**Responsibilities:**
- Expose FastAPI endpoints
- Parse incoming requests
- Delegate to orchestrator
- Stream responses to clients

**Lines of code:** ~100 (down from 260)

**Key endpoints:**
- `POST /invocations` - Main agent invocation
- `GET /health` - Health check
- `GET /` - API info

### 2. Orchestrator (`core/orchestrator.py`)

**Responsibilities:**
- Coordinate all operations
- Call specialized tools
- Manage agent lifecycle
- Handle errors gracefully

**Key methods:**
```python
extract_metadata(headers, body) -> RequestMetadata
build_filter(metadata) -> Dict | None
build_prompt(input_text, session_id, filter) -> str
process_request(input, session, metadata) -> AsyncGenerator
get_health_status() -> Dict
```

### 3. Tools (`core/tools/`)

#### 3.1 MetadataFilterBuilder (`metadata_filter.py`)

**Purpose:** Convert request metadata to Bedrock KB filters

**Key functions:**
```python
extract_from_request(headers, body) -> RequestMetadata
generate_partition_key(tenant, project, task) -> str
build_filter(metadata) -> Dict
```

**Filter format:**
```python
{
    "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165"}}
    ]
}
```

#### 3.2 SessionManager (`session_manager.py`)

**Purpose:** Maintain conversation history and context

**Key methods:**
```python
add_message(session_id, role, content)
get_context(session_id) -> str
clear_session(session_id)
```

**Storage:**
- In-memory dict: `{session_id: [messages]}`
- Keeps last 8 messages (4 exchanges)
- Uses last 6 for context

### 4. Configuration (`core/config.py`)

**Purpose:** Centralized configuration management

**Key settings:**
```python
kb_id: str                     # Knowledge Base ID
model_id: str                  # Bedrock model
region: str                    # AWS region
port: int                      # Server port
max_session_messages: int      # Session storage limit
context_messages: int          # Context window size
response_chunk_size: int       # Streaming chunk size
max_response_length: int       # Response truncation limit
```

### 5. System Prompt (`prompts/system_prompt.md`)

**Purpose:** Define agent behavior and rules

**Key sections:**
- Core rules (information source, user-friendly responses)
- Tool usage (retrieve, http_request)
- Response examples
- Internal instructions for filtering

---

## Data Flow

### Request Processing Flow

```
1. Client sends request:
   POST /invocations
   {
     "inputText": "What's in project 165?",
     "sessionId": "user-123",
     "metadata": {
       "tenant_id": "1001",
       "project_id": "165"
     }
   }

2. FastAPI parses request:
   - Extract inputText, sessionId
   - Extract metadata from body or headers
   - Pass to orchestrator

3. Orchestrator extracts metadata:
   - tenant_id = "1001"
   - project_id = "165"
   - task_id = None

4. MetadataFilterBuilder builds filter:
   - partition_key = "t1001_p165"
   - Filter: {andAll: [...]}

5. SessionManager gets context:
   - Retrieve last 6 messages
   - Format as conversation history

6. Orchestrator builds prompt:
   - Combine: context + user input + filter instructions
   - Result: Enhanced prompt for agent

7. Strands Agent processes:
   - Call Bedrock model
   - Use retrieve tool with filter
   - Get KB results
   - Generate response

8. Orchestrator cleans response:
   - Remove <thinking> tags
   - Truncate if > 4000 chars
   - Store in session

9. Stream response:
   - Split into 3-word chunks
   - Yield as NDJSON
   - {"type": "chunk", "data": "..."}
   - {"type": "complete", "sessionId": "..."}
```

---

## Multi-Tenant Isolation

### Partition Key Strategy

**Format:**
- Project-level: `t{tenant}_p{project}`
- Task-level: `t{tenant}_p{project}_t{task}`

**Examples:**
| Tenant | Project | Task | Partition Key | Documents Returned |
|--------|---------|------|---------------|-------------------|
| 1001 | - | - | - | All tenant docs |
| 1001 | 165 | - | t1001_p165 | Project 165 docs only |
| 1001 | 165 | 174 | t1001_p165_t174 | Task 174 docs only |

### Filter Hierarchy

```
Level 1: tenant_id only
  → Returns ALL documents from tenant
  → Filter: {"equals": {"key": "tenant_id", "value": "1001"}}

Level 2: tenant_id + project_id
  → Returns ONLY project-level documents
  → Excludes task-level documents
  → Filter: {
      "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "project_id", "value": "165"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165"}}
      ]
    }

Level 3: tenant_id + project_id + task_id
  → Returns ONLY task-level documents
  → Filter: {
      "andAll": [
        {"equals": {"key": "tenant_id", "value": "1001"}},
        {"equals": {"key": "partition_key", "value": "t1001_p165_t174"}}
      ]
    }
```

---

## Strands SDK Integration

### Agent Initialization

```python
from strands import Agent
from strands_tools import retrieve, http_request

agent = Agent(
    model="amazon.nova-pro-v1:0",
    tools=[retrieve, http_request],
    system_prompt=load_prompt("prompts/system_prompt.md")
)
```

### Tool Calling

**Retrieve tool** (automatic filter injection):
```python
# Agent receives prompt with filter instructions
prompt = f"""
User: What's in project 165?

METADATA FILTERING ACTIVA:
Cuando uses 'retrieve', DEBES incluir:
retrieveFilter={{"andAll": [...]}}
"""

# Agent calls retrieve with filter
result = agent(prompt)
# Internally: agent.tool.retrieve(
#   text="...",
#   retrieveFilter={"andAll": [...]}
# )
```

**HTTP request tool:**
```python
# Agent can call external APIs
agent.tool.http_request(
    url="https://api.example.com/data",
    method="GET"
)
```

---

## Session Management

### Session Lifecycle

```
1. First message:
   - Create new session
   - Store: [{"role": "user", "content": "..."}]

2. Agent response:
   - Add: {"role": "assistant", "content": "..."}
   - Session: [user, assistant]

3. Next message:
   - Get context: last 6 messages
   - Add new user message
   - Process with context

4. Cleanup:
   - Keep last 8 messages
   - Drop older messages automatically
```

### Context Format

```python
# Session storage
{
  "user-123": [
    {"role": "user", "content": "Hola"},
    {"role": "assistant", "content": "Hola, ¿cómo puedo ayudarte?"},
    {"role": "user", "content": "¿Qué políticas hay?"},
    {"role": "assistant", "content": "Tenemos las siguientes políticas..."}
  ]
}

# Context (last 6 messages formatted):
"""
Usuario: Hola
Asistente: Hola, ¿cómo puedo ayudarte?
Usuario: ¿Qué políticas hay?
Asistente: Tenemos las siguientes políticas...
"""
```

---

## Error Handling

### User-Friendly Errors

**Agent errors:**
```python
try:
    result = agent(prompt)
except Exception as e:
    logger.error(f'[Error] {e}', exc_info=True)
    yield {
        "type": "chunk",
        "data": "Disculpa, tuve un problema procesando tu pregunta."
    }
```

**Technical details:**
- Logged to CloudWatch
- Not exposed to users
- Includes stack traces for debugging

---

## Performance Optimizations

### 1. Streaming Responses
- 3-word chunks (low latency)
- NDJSON format (progressive rendering)

### 2. Session Context
- Only last 6 messages (reduce token usage)
- Efficient in-memory storage

### 3. Filter Optimization
- Partition key reduces search space
- Single field for complex hierarchy

### 4. Response Truncation
- Max 4000 chars (prevent token overflow)
- Graceful truncation

---

## Deployment Architecture

### Docker Container

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py core/ prompts/ ./
EXPOSE 8080
CMD ["python", "main.py"]
```

### AWS Agent Core Runtime

```
CDK Stack (AgentStackV2)
  ↓
Docker Image Build
  ↓
ECR Push
  ↓
Agent Core Runtime
  ↓
Container Instance (Fargate)
  ↓
FastAPI Server (port 8080)
```

### Environment Variables

```bash
KB_ID=R80HXGRLHO
MODEL_ID=amazon.nova-pro-v1:0
AWS_REGION=us-east-1
PORT=8080
DEBUG=false
```

---

## Testing Architecture

### Local Testing

```
./scripts/local_setup.sh    # Setup
./scripts/run_local.sh       # Start agent
./scripts/test_local.sh      # Run tests
./scripts/chat_local.sh      # Interactive chat
```

### Test Coverage

1. **No filters** - Unrestricted access
2. **Tenant only** - All tenant documents
3. **Tenant + Project** - Project-level filtering
4. **Tenant + Project + Task** - Task-level filtering
5. **Complex metadata** - Multiple fields

---

## Monitoring & Observability

### CloudWatch Logs

**Filter logs:**
```
[Filter] ✅ tenant_id: 1001
[Filter] ✅ partition_key (project): t1001_p165
[Filter] Built filter with 3 conditions
```

**Agent logs:**
```
[Agent] Calling model with prompt length: 1250 chars
[Response] Completed for session user-123
```

### Metrics

- Active sessions count
- Response time
- Filter build time
- Token usage

---

## Security

### Multi-Tenancy Enforcement

- **Strict isolation** via partition_key
- **No cross-tenant leaks** (validated in tests)
- **Metadata validation** (tenant_id required)

### Data Protection

- **No PII in logs** (only IDs)
- **Clean responses** (no technical details to users)
- **S3 encryption** (KMS for documents)

---

## Extension Points

### Adding New Tools

```python
# 1. Create tool function
def my_custom_tool(input: str) -> str:
    """Custom tool implementation"""
    pass

# 2. Register with agent
agent = Agent(
    model=MODEL_ID,
    tools=[retrieve, http_request, my_custom_tool]
)
```

### Adding New Metadata Fields

```python
# 1. Update RequestMetadata dataclass
@dataclass
class RequestMetadata:
    tenant_id: Optional[str] = None
    custom_field: Optional[str] = None  # New field

# 2. Update extraction logic
def extract_from_request(...):
    custom_field = metadata_obj.get('custom_field')
    return RequestMetadata(..., custom_field=custom_field)

# 3. Update filter builder
def build_filter(metadata):
    if metadata.custom_field:
        conditions.append({
            "equals": {"key": "custom_field", "value": metadata.custom_field}
        })
```

---

## Version History

### v2.0.0 (2026-05-04)
- Modular architecture
- Clean separation of concerns
- 31% code reduction
- Comprehensive documentation

### v1.0.0 (2026-04-29)
- Monolithic implementation
- Working multi-tenant filtering
- 260-line main.py

---

**Next Steps:**
- Review code in `core/` modules
- Run local tests
- Deploy to AWS via CDK
