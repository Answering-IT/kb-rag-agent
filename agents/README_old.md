# ProcessApp Agent v2 - Strand Agents SDK

Custom AI agent for ProcessApp using Strand Agents SDK on AWS Agent Core Runtime.

## Overview

This agent uses:
- **Strand Agents SDK** - TypeScript framework for building AI agents
- **AWS Agent Core** - Managed compute runtime
- **BedrockModel** - Claude 3.5 Sonnet
- **Zod** - Type-safe tool schemas

## Features

✅ **Type-Safe Tools** - Zod schemas for input validation  
✅ **Automatic Tool Calling** - Strand SDK orchestration  
✅ **MCP Protocol** - Native support  
✅ **Streaming Responses** - Real-time output  
✅ **Knowledge Base Integration** - Query ProcessApp documents  
✅ **HTTP Tool Calling** - External ECS service integration  

## Architecture

```
┌─────────────────────────────────────────┐
│ Strand Agent (this code)                │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────────┐                  │
│  │ BedrockModel     │                  │
│  │ (Claude Sonnet)  │                  │
│  └──────────────────┘                  │
│           │                              │
│           ▼                              │
│  ┌──────────────────┐                  │
│  │ Agent            │                  │
│  │ - systemPrompt   │                  │
│  │ - tools[]        │                  │
│  └──────────────────┘                  │
│           │                              │
│           ├─────────────┐               │
│           │             │               │
│           ▼             ▼               │
│  ┌──────────────┐  ┌──────────────┐   │
│  │ getProjectInfo│  │ searchKnowledge│  │
│  │ (HTTP → ECS) │  │ (Bedrock KB)  │   │
│  └──────────────┘  └──────────────┘   │
│                                          │
│  Endpoints:                              │
│  - POST /invoke  (agent invocation)     │
│  - POST /stream  (streaming)            │
│  - POST /mcp     (MCP protocol)         │
│  - GET  /health  (health check)         │
│                                          │
└─────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
npm install
```

### Build

```bash
npm run build
```

### Run Locally

```bash
npm start
```

### Test

```bash
# Health check
curl http://localhost:8080/health

# Invoke agent
curl -X POST http://localhost:8080/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "What is project 1?",
    "sessionId": "test-123"
  }'
```

## Tools

### 1. getProjectInfo

Retrieves project information from ECS service.

**Schema:**
```typescript
z.object({
  orgId: z.string().describe('Organization ID (default: 1)'),
  projectId: z.string().describe('Project ID'),
})
```

**Example:**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "getProjectInfo",
      "arguments": {"orgId": "1", "projectId": "123"}
    }
  }'
```

### 2. searchKnowledge

Searches ProcessApp Knowledge Base for documents.

**Schema:**
```typescript
z.object({
  query: z.string().describe('Search query'),
})
```

**Example:**
```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "searchKnowledge",
      "arguments": {"query": "process documentation"}
    }
  }'
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | HTTP server port | `8080` |
| `MODEL_ID` | Bedrock model ID | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `KB_ID` | Knowledge Base ID | (required) |
| `AWS_REGION` | AWS region | `us-east-1` |
| `ECS_BASE_URL` | ECS service endpoint | `https://dev.app.colpensiones.procesapp.com` |
| `STAGE` | Deployment stage | (required) |

## Deployment

Deployed via CDK using Agent Core Runtime:

```typescript
const agentCode = agentcore.AgentRuntimeArtifact.fromCodeAsset({
  path: path.join(__dirname, '../../agents'),
  runtime: agentcore.AgentCoreRuntime.PYTHON_3_12,
  entrypoint: ['node', 'dist/agent.js'],
});

const runtime = new agentcore.Runtime(this, 'AgentRuntime', {
  runtimeName: 'processapp-agent-v2',
  agentRuntimeArtifact: agentCode,
  environmentVariables: {
    KB_ID: props.knowledgeBaseId,
    MODEL_ID: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
  },
});
```

**Deploy:**
```bash
cd ../../infrastructure
npx cdk deploy dev-us-east-1-agent-v2 --profile default
```

## API Endpoints

### POST /invoke

Invoke agent with text input.

**Request:**
```json
{
  "inputText": "What documents do you have?",
  "sessionId": "user-123"
}
```

**Response:**
```json
{
  "response": "I found 5 documents about...",
  "sessionId": "user-123",
  "toolsUsed": ["searchKnowledge"]
}
```

### POST /stream

Streaming agent invocation (Server-Sent Events).

**Request:**
```json
{
  "inputText": "Tell me about the process",
  "sessionId": "user-123"
}
```

**Response:**
```
data: {"type":"chunk","data":"I found..."}
data: {"type":"chunk","data":"information..."}
data: {"type":"done","sessionId":"user-123"}
```

### POST /mcp

MCP protocol endpoint.

**List Tools:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list"
}
```

**Call Tool:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "getProjectInfo",
    "arguments": {"orgId": "1", "projectId": "123"}
  }
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "processapp-agent-v2",
  "framework": "Strand Agents SDK",
  "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "kb": "configured"
}
```

## Dependencies

```json
{
  "@strands-agents/sdk": "^1.0.0",
  "@aws-sdk/client-bedrock-agent-runtime": "^3.0.0",
  "express": "^4.18.0",
  "zod": "^3.22.0"
}
```

## Development

### Project Structure

```
agents/
├── agent.ts              # Main agent entry point (Bedrock Agent Core)
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript config
├── src/
│   ├── index.ts          # Simple HTTP server version
│   ├── mcp-server.ts     # MCP server implementation
│   └── agent-with-memory.ts  # Agent with memory integration
├── dist/                 # Compiled JavaScript (generated)
└── README.md             # This file
```

### Code Style

- TypeScript with ES2022 target
- ESM modules
- Type-safe with Zod schemas
- Express.js for HTTP server

## Monitoring

### CloudWatch Logs

```bash
aws logs tail /aws/bedrock/agentcore/runtime/<RUNTIME_ID> --follow
```

### X-Ray Traces

View in AWS X-Ray console to see:
- Tool execution times
- Model invocation latency
- Knowledge Base query performance

## Troubleshooting

### Agent not starting

**Check:**
1. Code compiled: `npm run build`
2. Dependencies installed: `npm install`
3. Environment variables set

### Tools not being called

**Debug:**
- Check agent logs in CloudWatch
- Verify tool schema matches input
- Test tool directly via `/mcp` endpoint

### KB queries failing

**Check:**
- `KB_ID` environment variable set
- IAM permissions for Knowledge Base
- Knowledge Base has documents ingested

## Resources

- [Strand Agents SDK](https://github.com/strands-agents/sdk-typescript)
- [Agent Core CDK](https://github.com/aws/aws-cdk/tree/main/packages/%40aws-cdk/aws-bedrock-agentcore-alpha)
- [Phase 2 Implementation Guide](../../PHASE2-IMPLEMENTATION.md)

---

**Framework**: Strand Agents SDK  
**Runtime**: AWS Agent Core  
**Model**: Claude 3.5 Sonnet  
**Phase**: 2
