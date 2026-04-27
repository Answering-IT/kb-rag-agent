# Phase 2 Implementation: Agent Core with Strand Agents SDK

## Overview

Phase 2 implements a **custom agent** using:
- **Strand Agents SDK** (TypeScript framework for building AI agents)
- **AWS Agent Core Runtime** (managed compute for custom agents)
- **Agent Core Memory** (automatic conversation history)

This runs **in parallel** with Phase 1 (no disruption to existing agent).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Agent Core + Strand                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐        ┌──────────────────┐            │
│  │ Agent Code     │───────▶│ Agent Core       │            │
│  │ (Strand SDK)   │        │ Runtime          │            │
│  │ - TypeScript   │        │ - Managed compute│            │
│  │ - Tools (Zod)  │        │ - Auto-scaling   │            │
│  │ - BedrockModel │        │ - HTTPS endpoint │            │
│  └────────────────┘        └──────────────────┘            │
│         │                            │                       │
│         │                            │                       │
│         ▼                            ▼                       │
│  ┌────────────────┐        ┌──────────────────┐            │
│  │ Tools          │        │ Agent Core       │            │
│  │ - getProjectInfo        │ Memory           │            │
│  │ - searchKnowledge       │ - 90-day retention│           │
│  └────────────────┘        └──────────────────┘            │
│         │                                                    │
│         │                                                    │
│         ▼                                                    │
│  ┌────────────────┐        ┌──────────────────┐            │
│  │ ECS Service    │        │ Bedrock KB       │            │
│  │ (HTTP endpoint)│        │ (same as Phase 1)│            │
│  └────────────────┘        └──────────────────┘            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Agent Code (`/agents/processapp-agent`)

**Technology Stack:**
- TypeScript + Strand Agents SDK
- Express.js for HTTP server
- Zod for schema validation
- AWS SDK for Bedrock

**Structure:**
```
agents/processapp-agent/
├── package.json          # Dependencies (@strands-agents/sdk)
├── tsconfig.json         # TypeScript config
├── src/
│   └── index.ts          # Agent implementation
└── README.md             # Documentation
```

**Key Features:**
- Type-safe tools using Zod schemas
- BedrockModel integration (Claude 3.5 Sonnet)
- Automatic tool calling via Strand
- MCP protocol support
- HTTP endpoints: `/health`, `/invoke`, `/stream`, `/mcp`

**Tools Implemented:**

1. **getProjectInfo**
   - Calls ECS HTTP endpoint
   - Parameters: orgId, projectId
   - Returns project data

2. **searchKnowledge**
   - Queries Bedrock Knowledge Base
   - Parameters: query
   - Returns relevant documents

### 2. Infrastructure (`/infrastructure/lib/AgentStackV2.ts`)

**CDK Stack Components:**

```typescript
AgentStackV2
├── Runtime Role (IAM)
│   ├── Invoke Bedrock models
│   ├── Retrieve from Knowledge Base
│   ├── Access Agent Core Memory
│   └── Write CloudWatch logs
│
├── Agent Core Memory
│   ├── 90-day retention
│   └── Automatic summarization
│
├── Runtime Artifact
│   ├── Direct code deployment (no Docker)
│   └── Auto-package and upload to S3
│
└── Agent Core Runtime
    ├── Managed compute environment
    ├── HTTPS endpoint (AWS Sig4 auth)
    ├── Environment variables (KB_ID, MODEL_ID, etc.)
    ├── X-Ray tracing enabled
    └── Public network (can switch to VPC)
```

## Differences from Phase 1

| Aspect | Phase 1 (Bedrock Agent) | Phase 2 (Agent Core) |
|--------|------------------------|----------------------|
| **Agent Logic** | AWS-managed | Custom (Strand SDK) |
| **Tools** | Lambda Action Groups | Native tool() functions |
| **Memory** | DynamoDB (manual) | Agent Core Memory (automatic) |
| **Invocation** | API Gateway + Lambda | Direct HTTPS endpoint |
| **Architecture** | API Gateway → Lambda → Bedrock | Runtime → Bedrock |
| **Framework** | N/A (AWS managed) | Strand Agents SDK |
| **Latency** | Higher (Lambda cold start) | Lower (managed runtime) |
| **Cost** | Lambda + API Gateway | Runtime only |

## Benefits of Phase 2

✅ **Full Control**: Custom agent logic in TypeScript
✅ **Simpler Architecture**: No Lambda, no API Gateway
✅ **Native Tool Calling**: Strand SDK handles orchestration
✅ **Better DX**: Type-safe tools with Zod
✅ **Lower Latency**: Managed runtime, no cold starts
✅ **Automatic Memory**: No manual DynamoDB management
✅ **MCP Support**: Connect to external MCP servers
✅ **Better Observability**: X-Ray tracing, structured logs

## Deployment

### Prerequisites

1. Install agent dependencies:
```bash
cd agents/processapp-agent
npm install
npm run build
```

2. Build infrastructure:
```bash
cd infrastructure
npm run build
```

### Deploy Phase 2

```bash
cd infrastructure
npx cdk deploy dev-us-east-1-agent-v2 --profile default
```

**Outputs:**
- `RuntimeIdV2`: Agent Core Runtime ID
- `RuntimeArnV2`: Runtime ARN for invocation
- `RuntimeNameV2`: Runtime name
- `MemoryIdV2`: Memory ID
- `MemoryArnV2`: Memory ARN

### Invoke the Agent

**Using AWS SDK (Python):**
```python
import boto3
import json

bedrock = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock.invoke_agent_runtime(
    agentRuntimeId='<RUNTIME_ID>',  # From CDK output
    inputText='What is project 1?',
    sessionId='user-123'
)

# Process streaming response
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'))
```

**Using AWS SDK (JavaScript/TypeScript):**
```typescript
import { BedrockAgentRuntimeClient, InvokeAgentRuntimeCommand } from '@aws-sdk/client-bedrock-agent-runtime';

const client = new BedrockAgentRuntimeClient({ region: 'us-east-1' });

const command = new InvokeAgentRuntimeCommand({
  agentRuntimeId: '<RUNTIME_ID>',
  inputText: 'What is project 1?',
  sessionId: 'user-123'
});

const response = await client.send(command);

// Process streaming response
for await (const event of response.completion) {
  if (event.chunk) {
    console.log(event.chunk.bytes.toString());
  }
}
```

**Direct HTTP (if needed):**
```bash
curl -X POST https://<runtime-endpoint> \
  --aws-sigv4 "aws:amz:us-east-1:bedrock" \
  -H "Content-Type: application/json" \
  -d '{
    "inputText": "What is project 1?",
    "sessionId": "user-123"
  }'
```

## Testing

### 1. Health Check

The agent exposes a health endpoint:
```bash
# After deployment, check CloudWatch logs for the port
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "processapp-agent-v2",
  "framework": "Strand Agents SDK",
  "model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
  "kb": "configured"
}
```

### 2. Tool Testing

**Test getProjectInfo:**
```python
response = bedrock.invoke_agent_runtime(
    agentRuntimeId=runtime_id,
    inputText='What is the information for project 1 in organization 1?',
    sessionId='test-123'
)
```

Expected: Agent calls getProjectInfo tool, retrieves data from ECS endpoint

**Test searchKnowledge:**
```python
response = bedrock.invoke_agent_runtime(
    agentRuntimeId=runtime_id,
    inputText='What documents do you have about processes?',
    sessionId='test-123'
)
```

Expected: Agent searches Knowledge Base, returns relevant documents

### 3. Memory Testing

```python
# First message
response1 = bedrock.invoke_agent_runtime(
    agentRuntimeId=runtime_id,
    inputText='My name is Alice',
    sessionId='memory-test'
)

# Second message (should remember context)
response2 = bedrock.invoke_agent_runtime(
    agentRuntimeId=runtime_id,
    inputText='What is my name?',
    sessionId='memory-test'  # Same session
)
```

Expected: Agent remembers "Alice" from previous message

## Monitoring

### CloudWatch Logs

```bash
# View runtime logs
aws logs tail /aws/bedrock/agentcore/runtime/<RUNTIME_ID> --follow --profile default
```

### X-Ray Traces

Navigate to AWS X-Ray console to view traces:
- Tool execution times
- Bedrock model invocation latency
- Knowledge Base query performance

### Metrics

```bash
# Custom CloudWatch metrics (if configured)
aws cloudwatch get-metric-statistics \
  --namespace AgentCore \
  --metric-name InvocationCount \
  --dimensions Name=RuntimeId,Value=<RUNTIME_ID> \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Troubleshooting

### Issue: Runtime fails to start

**Check:**
1. Agent code compiled: `cd agents/processapp-agent && npm run build`
2. CDK deployed successfully: Check CloudFormation events
3. Runtime logs: Check CloudWatch logs for errors

**Solution:**
```bash
cd agents/processapp-agent
npm install
npm run build
cd ../../infrastructure
npx cdk deploy dev-us-east-1-agent-v2 --profile default
```

### Issue: Tool not being called

**Check:**
1. Tool definition in agent code
2. Zod schema validation
3. Agent logs for tool call attempts

**Debug:**
```typescript
// Add logging in tool callback
callback: async (input) => {
  console.log('[Tool] Called with:', input);
  // ... rest of callback
}
```

### Issue: Memory not persisting

**Check:**
1. Same sessionId used across invocations
2. Memory IAM permissions granted
3. Session not expired (90-day limit)

## Cost Estimate

### Phase 2 Monthly Cost (approximate)

| Component | Usage | Cost |
|-----------|-------|------|
| Agent Core Runtime | ~10k invocations | ~$20 |
| Agent Core Memory | 1GB storage | ~$5 |
| Bedrock Model (Sonnet) | ~10k invocations, 500 tokens avg | ~$150 |
| Knowledge Base (same) | Shared with Phase 1 | $0 |
| CloudWatch Logs | 10GB | ~$5 |
| **Total** | | **~$180/month** |

**Comparison:**
- Phase 1: ~$220/month (includes Lambda, API Gateway, DynamoDB)
- Phase 2: ~$180/month (savings: ~$40/month)

## Next Steps

1. ✅ **Implemented**: Agent Core Runtime with Strand SDK
2. ✅ **Implemented**: Agent Core Memory (90-day retention)
3. ✅ **Implemented**: Tools (getProjectInfo, searchKnowledge)
4. ⏳ **Pending**: Deploy and test end-to-end
5. ⏳ **Pending**: Performance comparison with Phase 1
6. ⏳ **Pending**: Gradual migration strategy
7. ⏳ **Pending**: Deprecate Phase 1 after validation

## Documentation

- [Strand Agents SDK](https://github.com/strands-agents/sdk-typescript)
- [Agent Core CDK Alpha](https://github.com/aws/aws-cdk/tree/main/packages/%40aws-cdk/aws-bedrock-agentcore-alpha)
- [Agent Core Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [Phase 2 Plan](/infrastructure/plans/phase-2-agent-core.md)

## Support

For questions or issues:
- Check CloudWatch logs
- Review X-Ray traces
- Consult Strand SDK documentation
- Review Phase 1 implementation for comparison

---

**Last Updated**: 2026-04-26
**Status**: Ready for deployment
**Phase**: 2 (Agent Core with Strand)
