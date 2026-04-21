# ProcessApp RAG Agent Usage Guide

This guide shows how to deploy and interact with the ProcessApp Bedrock Agent.

**Last Updated**: 2026-04-17

---

## Overview

The ProcessApp Bedrock Agent is an AI assistant powered by Claude 3.5 Sonnet that can answer questions using your document knowledge base. It includes:

- **Knowledge Base Integration**: Searches uploaded documents
- **Content Safety**: Guardrails for PII filtering and content moderation
- **Source Citations**: Provides references to source documents
- **Session Management**: Maintains conversation context

---

## Architecture

```
User Query → Bedrock Agent → Guardrails → Claude 3.5 Sonnet
                ↓
         Knowledge Base Retrieve
                ↓
         S3 Vector Index (embeddings)
                ↓
         Source Documents (S3)
```

**Components**:
- **AgentStack**: Creates Bedrock Agent with KB and guardrail integration
- **Agent Alias**: "live" alias points to DRAFT version
- **IAM Role**: Permissions for model invocation, KB retrieval, guardrail application
- **Knowledge Base**: Auto-connected for document retrieval
- **Guardrails**: Auto-applied for content safety

---

## Deployment

### Deploy All Stacks (Including Agent)

```bash
# Build TypeScript
npm run build

# Deploy all stacks (includes new AgentStack)
npx cdk deploy --all

# Or deploy just the agent stack
npx cdk deploy dev-us-east-1-agent
```

### Verify Deployment

```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent \
  --query 'Stacks[0].Outputs' \
  --output table

# Get agent details
export AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentId`].OutputValue' \
  --output text)

export AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentAliasId`].OutputValue' \
  --output text)

echo "Agent ID: $AGENT_ID"
echo "Agent Alias ID: $AGENT_ALIAS_ID"

# Check agent status
aws bedrock-agent get-agent \
  --agent-id $AGENT_ID \
  --query 'agent.[agentStatus,agentName,foundationModel]' \
  --output json
```

---

## Using the Agent

### Method 1: AWS CLI (Simple Queries)

**Note**: The `invoke-agent` command streams responses, so you need to handle output files.

```bash
# Set session ID (use unique ID per conversation)
export SESSION_ID=$(uuidgen)

# Invoke agent with a query
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $AGENT_ALIAS_ID \
  --session-id $SESSION_ID \
  --input-text "What embedding model does ProcessApp use?" \
  output.txt

# View response
cat output.txt | jq -r '.chunk.bytes' | base64 --decode
```

### Method 2: Python SDK (Recommended)

Create a Python script `query_agent.py`:

```python
#!/usr/bin/env python3
"""
Query ProcessApp RAG Agent
"""

import boto3
import json
import sys
from uuid import uuid4

def query_agent(agent_id: str, agent_alias_id: str, query: str, session_id: str = None):
    """
    Query the Bedrock Agent

    Args:
        agent_id: Agent ID from CloudFormation outputs
        agent_alias_id: Agent Alias ID from CloudFormation outputs
        query: User's question
        session_id: Optional session ID (for conversation continuity)

    Returns:
        Agent's response text
    """
    if session_id is None:
        session_id = str(uuid4())

    client = boto3.client('bedrock-agent-runtime')

    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        inputText=query
    )

    # Stream response chunks
    full_response = ""
    for event in response['completion']:
        if 'chunk' in event:
            chunk = event['chunk']
            if 'bytes' in chunk:
                text = chunk['bytes'].decode('utf-8')
                full_response += text
                print(text, end='', flush=True)

    print()  # New line after streaming
    return full_response

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python query_agent.py <agent-id> <agent-alias-id> <query>")
        sys.exit(1)

    agent_id = sys.argv[1]
    agent_alias_id = sys.argv[2]
    query = ' '.join(sys.argv[3:])

    print(f"Query: {query}")
    print("Response: ", end='')

    response = query_agent(agent_id, agent_alias_id, query)

    print(f"\n\n[Session ID: {uuid4()}]")
```

**Usage**:

```bash
# Install boto3
pip install boto3

# Run query
python query_agent.py $AGENT_ID $AGENT_ALIAS_ID "What is the cost advantage of S3 Vectors?"

# Multi-word queries
python query_agent.py $AGENT_ID $AGENT_ALIAS_ID "How does ProcessApp achieve multi-tenancy?"
```

### Method 3: Interactive Session Script

Create `interactive_agent.py`:

```python
#!/usr/bin/env python3
"""
Interactive session with ProcessApp Agent
"""

import boto3
import json
import sys
from uuid import uuid4

def interactive_session(agent_id: str, agent_alias_id: str):
    """
    Run interactive session with the agent
    """
    client = boto3.client('bedrock-agent-runtime')
    session_id = str(uuid4())

    print("ProcessApp RAG Agent Interactive Session")
    print(f"Session ID: {session_id}")
    print("Type 'exit' or 'quit' to end the session\n")

    while True:
        try:
            query = input("You: ").strip()

            if query.lower() in ['exit', 'quit', 'q']:
                print("Ending session. Goodbye!")
                break

            if not query:
                continue

            # Invoke agent
            response = client.invoke_agent(
                agentId=agent_id,
                agentAliasId=agent_alias_id,
                sessionId=session_id,
                inputText=query
            )

            # Stream response
            print("Agent: ", end='', flush=True)
            for event in response['completion']:
                if 'chunk' in event:
                    chunk = event['chunk']
                    if 'bytes' in chunk:
                        text = chunk['bytes'].decode('utf-8')
                        print(text, end='', flush=True)
            print("\n")

        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python interactive_agent.py <agent-id> <agent-alias-id>")
        sys.exit(1)

    agent_id = sys.argv[1]
    agent_alias_id = sys.argv[2]

    interactive_session(agent_id, agent_alias_id)
```

**Usage**:

```bash
python interactive_agent.py $AGENT_ID $AGENT_ALIAS_ID
```

---

## Example Queries

Based on test documents in `docs/test-fixtures/test-documents/`:

### Technical Queries

```
Q: What embedding model does ProcessApp use?
A: ProcessApp uses Amazon Titan v2 with 1024 dimensions for generating embeddings.

Q: What is the cost advantage of S3 Vectors?
A: S3 Vectors provide approximately 90% cost reduction compared to OpenSearch.

Q: How often does the Knowledge Base sync?
A: The Knowledge Base syncs every 6 hours automatically, or can be triggered manually.

Q: What are the main infrastructure stacks?
A: The main stacks are PrereqsStack, BedrockStack, DocumentProcessingStack,
   GuardrailsStack, MonitoringStack, and AgentStack.
```

### Architecture Queries

```
Q: How does ProcessApp achieve multi-tenancy?
A: ProcessApp uses stage-based isolation with separate S3 buckets, IAM roles,
   and KMS keys per stage (dev, staging, prod).

Q: What OCR service is used?
A: ProcessApp uses AWS Textract with TABLES and FORMS features for optical
   character recognition.

Q: What PII types does the guardrail detect?
A: The guardrail detects SSN, credit cards, email addresses, phone numbers,
   person names, organizations, addresses, and dates of birth.
```

### Security Queries

```
Q: What security features are in place?
A: ProcessApp includes KMS encryption for all S3 buckets, Bedrock Guardrails
   for PII detection and content filtering, IAM least privilege access, and
   content safety policies.
```

---

## Session Management

### Session ID Behavior

- **New Session**: Each unique session ID starts fresh (no conversation history)
- **Continuing Session**: Reuse session ID to maintain conversation context
- **Session Timeout**: Sessions expire after 15 minutes of inactivity (configurable)

### Example: Multi-turn Conversation

```python
# First query
session_id = str(uuid4())
query_agent(agent_id, agent_alias_id, "What is ProcessApp?", session_id)

# Follow-up query (same session)
query_agent(agent_id, agent_alias_id, "What technologies does it use?", session_id)
# Agent will understand "it" refers to ProcessApp from previous query
```

---

## Troubleshooting

### Issue 1: Agent Not Found

**Symptoms**:
- `ResourceNotFoundException: Agent not found`

**Solution**:
```bash
# Verify agent exists
aws bedrock-agent list-agents

# Check stack deployment
aws cloudformation describe-stacks --stack-name dev-us-east-1-agent

# Redeploy if needed
npx cdk deploy dev-us-east-1-agent
```

### Issue 2: Knowledge Base Returns No Results

**Symptoms**:
- Agent says "I don't have information about that"
- Empty retrieval results

**Solution**:
```bash
# Check if KB has documents
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>

# Trigger manual sync if needed
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>

# Verify documents in S3
aws s3 ls s3://processapp-docs-v2-dev-708819485463/documents/
```

### Issue 3: Guardrail Blocks Valid Content

**Symptoms**:
- Guardrail blocks legitimate queries
- "Content violates guardrail policy" errors

**Solution**:
```bash
# Check guardrail configuration
aws bedrock get-guardrail \
  --guardrail-identifier <GUARDRAIL_ID>:<VERSION>

# Adjust content filters in config/security.config.ts
# Then redeploy GuardrailsStack
```

### Issue 4: Agent Response Too Slow

**Symptoms**:
- Long wait times for responses
- Timeout errors

**Solution**:
- Check Knowledge Base size (large KBs = slower retrieval)
- Verify KB sync is complete
- Consider reducing `numberOfResults` in KnowledgeBaseConfig
- Use more specific queries (less semantic search overhead)

### Issue 5: Permission Denied

**Symptoms**:
- `AccessDeniedException` when invoking agent

**Solution**:
```bash
# Verify your IAM permissions
aws sts get-caller-identity

# Check agent role permissions
aws iam get-role --role-name processapp-agent-role-dev

# Ensure your user has bedrock:InvokeAgent permission
```

---

## Monitoring Agent Usage

### CloudWatch Logs

```bash
# Agent invocation logs
aws logs tail /aws/bedrock/agents/<agent-id> --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agents/<agent-id> \
  --filter-pattern "ERROR"
```

### Metrics

```bash
# Agent invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=AgentId,Value=$AGENT_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Agent latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Duration \
  --dimensions Name=AgentId,Value=$AGENT_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

---

## Cost Estimation

**Per 1000 Agent Invocations**:

- **Agent Invocations**: Free (no charge for agent orchestration)
- **Model Invocations (Claude 3.5 Sonnet)**:
  - Input: $3 per million tokens
  - Output: $15 per million tokens
  - Typical query: ~1K input tokens, ~500 output tokens
  - Cost: ~$0.003 input + ~$0.0075 output = ~$0.0105 per query
  - **1000 queries**: ~$10.50
- **KB Retrieval**:
  - $0.10 per 1000 requests
  - **1000 queries**: ~$0.10
- **Guardrail Processing**:
  - $0.75 per 1000 text units (1000 chars = 1 unit)
  - Typical: 2 units per query (input + output)
  - **1000 queries**: ~$1.50

**Total estimated cost per 1000 queries**: ~$12.10

---

## Next Steps

1. **Deploy the agent**: `npx cdk deploy dev-us-east-1-agent`
2. **Upload test documents**: Use documents from `docs/test-fixtures/test-documents/`
3. **Trigger KB sync**: Ensure documents are indexed
4. **Test queries**: Use example queries above
5. **Integrate with application**: Use Python SDK or API Gateway
6. **Monitor usage**: Check CloudWatch logs and metrics
7. **Optimize costs**: Adjust model parameters and retrieval settings

---

## References

- [Bedrock Agent Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Bedrock Agent Runtime API](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_Operations_Agents_for_Amazon_Bedrock_Runtime.html)
- [Claude 3.5 Sonnet Model Card](https://docs.anthropic.com/claude/docs/models-overview)
- AgentStack implementation: `infrastructure/lib/AgentStack.ts`
- Agent configuration: `infrastructure/config/environments.ts`

---

**Document Version**: 1.0
**Status**: Ready for deployment and testing
