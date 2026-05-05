# ProcessApp Agent v2.0

**Modern, modular RAG agent with clean architecture and multi-tenant support**

---

## 📁 Project Structure

```
agents/
├── main.py                    # FastAPI entry point (clean, 100 lines)
├── core/                      # Core agent logic
│   ├── __init__.py
│   ├── config.py             # Configuration management
│   ├── orchestrator.py       # Agent orchestration
│   └── tools/                # Modular tools
│       ├── __init__.py
│       ├── metadata_filter.py    # KB filter builder
│       └── session_manager.py    # Session management
├── prompts/                   # System prompts
│   └── system_prompt.md      # Agent instructions (versioned)
├── scripts/                   # Development scripts
│   ├── local_setup.sh        # Environment setup
│   ├── run_local.sh          # Start agent locally
│   ├── test_local.sh         # Test with different filters
│   └── chat_local.sh         # Interactive chat
├── docs/                      # Documentation
│   └── RETRIEVE_TOOL_GUIDE.md    # Retrieve tool usage
├── _archive/                  # Old code (not used)
│   ├── main_old.py           # Original 260-line main
│   └── metadata_handler.py   # Original metadata handler
├── requirements.txt
├── Dockerfile
└── README.md                  # This file
```

---

## 🚀 Quick Start

### 1. Setup Environment

```bash
cd agents

# Create virtual environment and install dependencies
chmod +x scripts/*.sh
./scripts/local_setup.sh
```

### 2. Configure AWS

```bash
# Set AWS profile (required)
export AWS_PROFILE=ans-super
export AWS_REGION=us-east-1

# Verify credentials
aws sts get-caller-identity --profile $AWS_PROFILE
```

### 3. Run Agent Locally

```bash
# Start agent (http://localhost:8080)
./scripts/run_local.sh

# In another terminal, test it
./scripts/test_local.sh

# Or chat interactively
./scripts/chat_local.sh
```

---

## 🏗️ Architecture

### Clean Separation of Concerns

```
Request → FastAPI → Orchestrator → Agent (Strands) → Bedrock KB
                         ↓
                    Filter Builder
                    Session Manager
```

### Components

#### 1. **main.py** (Entry Point)
- FastAPI endpoints (`/invocations`, `/health`)
- Request parsing
- Response streaming
- **Lines of code:** ~100 (was 260)

#### 2. **core/orchestrator.py** (Brain)
- Coordinates all operations
- Calls filter builder
- Manages sessions
- Streams responses
- **Responsibilities:** Orchestration only

#### 3. **core/tools/metadata_filter.py** (Multi-Tenancy)
- Extracts metadata from requests
- Builds Bedrock KB filters
- Follows Strands test format
- **Input:** Headers + body metadata
- **Output:** `{"andAll": [{"equals": {...}}]}`

#### 4. **core/tools/session_manager.py** (Context)
- Stores conversation history
- Provides context to agent
- Keeps last 6 messages

#### 5. **prompts/system_prompt.md** (Instructions)
- Agent behavior rules
- Tool usage guidelines
- Response examples
- **Versioned** for change tracking

---

## 🔍 How Multi-Tenant Filtering Works

### Metadata Flow

```
1. Client sends request with metadata:
   {
     "inputText": "What's in project 165?",
     "metadata": {
       "tenant_id": "1001",
       "project_id": "165"
     }
   }

2. MetadataFilterBuilder extracts metadata:
   tenant=1001, project=165

3. Builds partition_key:
   partition_key = "t1001_p165"

4. Creates Bedrock filter:
   {
     "andAll": [
       {"equals": {"key": "tenant_id", "value": "1001"}},
       {"equals": {"key": "project_id", "value": "165"}},
       {"equals": {"key": "partition_key", "value": "t1001_p165"}}
     ]
   }

5. Injects filter into agent prompt (internal only)

6. Agent calls retrieve tool with filter

7. Bedrock KB returns only matching documents
```

### Partition Key Format

| Level | Format | Example |
|-------|--------|---------|
| Tenant | `t{tenant}` | `t1001` (not used in filter, just tenant_id) |
| Project | `t{tenant}_p{project}` | `t1001_p165` |
| Task | `t{tenant}_p{project}_t{task}` | `t1001_p165_t174` |

**Why partition_key?**
- Strict hierarchical isolation
- No false positives
- Single field for complex filtering
- S3 metadata compatible

---

## 📝 API Reference

### POST /invocations

**Request:**
```json
{
  "inputText": "What are the pension requirements?",
  "sessionId": "user-123",
  "metadata": {
    "tenant_id": "1001",
    "project_id": "165",
    "task_id": "174"
  }
}
```

**Headers (alternative to body.metadata):**
```
X-Tenant-Id: 1001
X-Project-Id: 165
X-Task-Id: 174
```

**Response (NDJSON stream):**
```json
{"type": "chunk", "data": "Los requisitos "}
{"type": "chunk", "data": "para pensión "}
{"type": "chunk", "data": "son los "}
{"type": "chunk", "data": "siguientes... "}
{"type": "complete", "sessionId": "user-123"}
```

### GET /health

**Response:**
```json
{
  "status": "healthy",
  "model": "amazon.nova-pro-v1:0",
  "region": "us-east-1",
  "kb_id": "R80HXGRLHO",
  "tools": ["retrieve", "http_request"],
  "provider": "bedrock",
  "sessions": 5,
  "version": "2.0.0"
}
```

---

## 🧪 Testing

### Run All Tests

```bash
# Start agent first
./scripts/run_local.sh

# In another terminal
./scripts/test_local.sh
```

### Tests Included

1. **No filters** - Unrestricted access (all documents)
2. **Tenant only** - All tenant documents
3. **Tenant + Project** - Project-level documents only
4. **Tenant + Project + Task** - Task-level documents only
5. **Complex metadata** - Multiple fields

### Interactive Chat

```bash
./scripts/chat_local.sh

# Select filtering mode:
#   1) No filtering
#   2) Tenant only
#   3) Tenant + Project
#   4) Tenant + Project + Task
```

---

## 📚 Documentation

- **[RETRIEVE_TOOL_GUIDE.md](docs/RETRIEVE_TOOL_GUIDE.md)** - Complete retrieve tool reference
- **[system_prompt.md](prompts/system_prompt.md)** - Agent instructions
- **[CLAUDE.md](../CLAUDE.md)** - Project documentation for Claude Code

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KB_ID` | Knowledge Base ID | From AWS |
| `MODEL_ID` | Bedrock model | `amazon.nova-pro-v1:0` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `PORT` | Server port | `8080` |
| `DEBUG` | Debug mode | `false` |
| `AWS_PROFILE` | AWS credentials profile | `ans-super` |

### Modify in `core/config.py`

```python
class AgentConfig:
    max_session_messages = 8     # Keep last 8 messages
    context_messages = 6         # Use last 6 for context
    response_chunk_size = 3      # Words per chunk
    max_response_length = 4000   # Max response chars
```

---

## 🚢 Deployment

### Docker Build

```bash
# Build image
docker build -t processapp-agent:2.0 .

# Run locally
docker run -p 8080:8080 \
  -e KB_ID=R80HXGRLHO \
  -e MODEL_ID=amazon.nova-pro-v1:0 \
  -e AWS_REGION=us-east-1 \
  processapp-agent:2.0
```

### AWS CDK Deployment

```bash
cd ../infrastructure
npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
```

---

## 🐛 Debugging

### Enable Debug Logs

```bash
export DEBUG=true
./scripts/run_local.sh
```

### Check Filter Output

Look for these log lines:

```
[Filter] ✅ tenant_id: 1001
[Filter] ✅ project_id: 165
[Filter] ✅ partition_key (project): t1001_p165
[Filter] Built filter with 3 conditions
```

### Common Issues

**1. Import errors**
```bash
# Solution: Run setup script
./scripts/local_setup.sh
source venv/bin/activate
```

**2. KB_ID not found**
```bash
# Solution: Check AWS credentials
export AWS_PROFILE=ans-super
aws bedrock-agent list-knowledge-bases --profile $AWS_PROFILE
```

**3. No results from retrieve**
```bash
# Check filters in logs
# Verify documents have correct metadata in S3
aws s3api head-object \
  --bucket processapp-docs-v2-dev-708819485463 \
  --key documents/your-doc.txt \
  --profile ans-super
```

---

## 📊 Metrics

### Code Reduction

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| main.py | 260 lines | 100 lines | **62%** |
| Metadata logic | Inline 389 lines | Modular 120 lines | **69%** |
| Total core code | 649 lines | 450 lines | **31%** |

### Benefits

- ✅ **Cleaner code** - Separation of concerns
- ✅ **Easier testing** - Modular components
- ✅ **Better logs** - Structured output
- ✅ **Maintainable** - Clear file structure
- ✅ **Documented** - Inline docs + guides

---

## 🔄 Migration from v1.0

If you have the old `main.py` (260 lines):

1. **Backup is in** `_archive/main_old.py`
2. **Functionality is identical** - Same API, same behavior
3. **Filters work the same** - Uses same format
4. **No infrastructure changes** - Works with existing CDK deployment

**To verify:**
```bash
# Old agent (if you have it)
python3 _archive/main_old.py

# New agent
python3 main.py

# Both should work identically
```

---

## 📞 Support

- **GitHub Issues:** [kb-rag-agent/issues](https://github.com/yourusername/kb-rag-agent/issues)
- **Documentation:** `docs/` folder
- **CLAUDE.md:** For Claude Code IDE integration

---

## 📜 Version History

### v2.0.0 (2026-05-04) - Current

- ✅ Modular architecture with `core/` package
- ✅ Separated prompts into `prompts/`
- ✅ Clean orchestrator pattern
- ✅ Improved filter builder with Strands format
- ✅ Session management module
- ✅ Comprehensive documentation
- ✅ Testing scripts organized in `scripts/`

### v1.0.0 (2026-04-29)

- Original implementation (260 lines in main.py)
- Inline metadata handling
- Working multi-tenant filtering
- Archived in `_archive/`

---

**Built with:**
- [Strands SDK](https://github.com/strands-agents/strands) - Agent framework
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - LLM inference
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Amazon Nova Pro](https://aws.amazon.com/bedrock/nova/) - Foundation model
