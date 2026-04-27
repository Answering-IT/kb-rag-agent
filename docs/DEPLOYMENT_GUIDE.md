# ProcessApp RAG Agent - Complete Deployment Guide

Comprehensive guide for deploying ProcessApp RAG Agent to AWS.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Deploy Infrastructure](#deploy-infrastructure)
4. [Deploy Agent V2](#deploy-agent-v2)
5. [Configure Knowledge Base](#configure-knowledge-base)
6. [Testing](#testing)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Rollback Procedures](#rollback-procedures)

---

## Prerequisites

### AWS Account Setup
- **Account ID:** 708819485463
- **Region:** us-east-1 (primary)
- **Profile:** ans-super (recommended) or default
- **Required Services:** Bedrock, S3, Lambda, API Gateway, CloudWatch

### Development Tools
```bash
# Node.js (v18+) - for CDK
node --version

# Python (3.11+) - for agent runtime
python3 --version

# AWS CDK
npm install -g aws-cdk

# AWS CLI v2
aws --version
```

### AWS Permissions Required
```yaml
IAM Permissions Needed:
  - cloudformation:* (for CDK deployments)
  - s3:* (for document storage)
  - bedrock:* (for agents and KB)
  - lambda:* (for handlers)
  - apigateway:* (for WebSocket)
  - logs:* (for CloudWatch)
  - iam:* (for role creation)
  - kms:* (for encryption)
```

---

## Initial Setup

### 1. Configure AWS Credentials

```bash
# Configure AWS profile
aws configure --profile ans-super
```

Enter:
- **AWS Access Key ID:** [your-key]
- **AWS Secret Access Key:** [your-secret]
- **Default region name:** us-east-1
- **Default output format:** json

Verify:
```bash
aws sts get-caller-identity --profile ans-super
```

Expected:
```json
{
  "UserId": "...",
  "Account": "708819485463",
  "Arn": "arn:aws:iam::708819485463:user/..."
}
```

### 2. Clone Repository

```bash
git clone <repository-url> kb-rag-agent
cd kb-rag-agent
```

### 3. Install Dependencies

```bash
# CDK dependencies
cd infrastructure
npm install

# Agent dependencies
cd ../agents
pip install -r requirements.txt

# Test dependencies
cd ..
pip install -r requirements-test.txt
```

---

## Deploy Infrastructure

### Stack Overview

```
1. PrereqsStack          - S3, KMS, IAM roles
2. SecurityStack         - Security policies
3. BedrockStack          - Knowledge Base
4. DocumentProcessingStack - OCR Lambda
5. GuardrailsStack       - PII filtering
6. SessionMemoryStack    - DynamoDB (V1)
7. AgentStack            - Bedrock Agent (V1)
8. APIStack              - REST API (V1)
9. WebSocketStack        - WebSocket (V1)
10. AgentStackV2         - Agent Core Runtime (V2) ⭐
11. WebSocketStackV2     - WebSocket for V2 ⭐
12. MonitoringStack      - CloudWatch dashboards
```

**⭐ Primary stacks for Agent V2**

### Deploy All Stacks (First Time)

```bash
cd infrastructure

# Build TypeScript
npm run build

# Bootstrap CDK (first time only)
npx cdk bootstrap aws://708819485463/us-east-1 --profile ans-super

# Deploy all stacks
npx cdk deploy --all --profile ans-super --require-approval never
```

**Duration:** ~30-45 minutes for complete deployment

### Deploy Specific Stacks

```bash
# Prerequisites only
npx cdk deploy dev-us-east-1-prereqs --profile ans-super

# Agent V2 only
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super

# WebSocket V2 only
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super

# Monitoring only
npx cdk deploy dev-us-east-1-monitoring --profile ans-super
```

### Deployment Order (Manual)

If deploying individually, follow this order:

```bash
# 1. Core infrastructure
npx cdk deploy dev-us-east-1-prereqs --profile ans-super
npx cdk deploy dev-us-east-1-security --profile ans-super
npx cdk deploy dev-us-east-1-bedrock --profile ans-super

# 2. Processing and rules
npx cdk deploy dev-us-east-1-document-processing --profile ans-super
npx cdk deploy dev-us-east-1-guardrails --profile ans-super

# 3. Agent V2 (primary)
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super

# 4. Optional: Agent V1
npx cdk deploy dev-us-east-1-session-memory --profile ans-super
npx cdk deploy dev-us-east-1-agent --profile ans-super
npx cdk deploy dev-us-east-1-api --profile ans-super
npx cdk deploy dev-us-east-1-websocket --profile ans-super

# 5. Monitoring
npx cdk deploy dev-us-east-1-monitoring --profile ans-super
```

---

## Deploy Agent V2

### Agent Code Structure

```
agents/
├── main.py           # Agent implementation
├── requirements.txt  # Python dependencies
└── Dockerfile       # Container image
```

### Update Agent Code

1. **Edit tools** in `agents/main.py`:
```python
@tool
def search_knowledge_base(query: str) -> str:
    """Search the ProcessApp knowledge base"""
    # Your implementation

@tool
def get_project_info(org_id: str, project_id: str) -> str:
    """Get project information from ECS service"""
    # Your implementation
```

2. **Update dependencies** in `agents/requirements.txt`

3. **Deploy:**
```bash
cd infrastructure
npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
```

**Duration:** ~5-10 minutes (Docker build + ECR push + Runtime update)

### WebSocket Handler

Location: `infrastructure/lambdas/websocket-handler-v2/message_handler.py`

Update and deploy:
```bash
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super
```

**Duration:** ~2-3 minutes

---

## Configure Knowledge Base

### 1. Get Knowledge Base Details

```bash
# List Knowledge Bases
aws bedrock-agent list-knowledge-bases \
  --query 'knowledgeBaseSummaries[?contains(name, `processapp`)]' \
  --profile ans-super

# Get KB ID from output
KB_ID=R80HXGRLHO
```

### 2. Upload Documents

```bash
BUCKET="processapp-docs-v2-dev-708819485463"
KMS_KEY="e6a714f6-70a7-47bf-a9ee-55d871d33cc6"

# Upload document
aws s3 cp document.pdf \
  s3://${BUCKET}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY} \
  --profile ans-super

# With metadata (for multi-tenant filtering)
aws s3api put-object \
  --bucket ${BUCKET} \
  --key documents/tenant1/doc.pdf \
  --body doc.pdf \
  --server-side-encryption aws:kms \
  --ssekms-key-id ${KMS_KEY} \
  --metadata tenantId=1,projectId=123,roles=admin \
  --profile ans-super
```

### 3. Sync Knowledge Base

```bash
# Get Data Source ID
DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text \
  --profile ans-super)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --description "Manual sync $(date)" \
  --profile ans-super
```

### 4. Monitor Ingestion

```bash
# Get latest job
JOB_ID=$(aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --max-results 1 \
  --query 'ingestionJobSummaries[0].ingestionJobId' \
  --output text \
  --profile ans-super)

# Check status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id ${JOB_ID} \
  --query 'ingestionJob.status' \
  --profile ans-super
```

Status values: `STARTING` | `IN_PROGRESS` | `COMPLETE` | `FAILED`

---

## Testing

### 1. Quick Connectivity Test

```bash
python3 scripts/quick-ws-test.py
```

Expected:
```
✅ Connected!
✅ WebSocket handshake successful!
💬 Response: [agent response with KB results]
✅ Complete!
```

### 2. Comprehensive Test

```bash
python3 scripts/test-tools.py
```

Tests:
- Knowledge Base search
- Project Info tool
- Short-term memory

### 3. E2E Test Suite

```bash
# Run all E2E tests
python3 -m pytest e2e/ -v

# Run specific component
python3 -m pytest e2e/agent-v2/ -v
python3 -m pytest e2e/ingestion/ -v
```

### 4. Manual WebSocket Test

```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c wss://1j1xzo7n4h.execute-api.us-east-1.amazonaws.com/dev

# Send message
{"question":"What documents do you have?","sessionId":"test-12345678901234567890123456789012"}
```

---

## Monitoring

### CloudWatch Dashboards

```bash
# Open CloudWatch Console
open https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

Dashboards created:
- `processapp-agent-v2-dev` - Agent runtime metrics
- `processapp-websocket-v2-dev` - WebSocket metrics

### Real-time Logs

```bash
# Agent Runtime logs
aws logs tail \
  /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super

# WebSocket Lambda logs
aws logs tail /aws/lambda/processapp-ws-message-v2-dev \
  --follow --profile ans-super

# Knowledge Base ingestion logs
aws logs tail /aws/bedrock/knowledgebases/R80HXGRLHO \
  --follow --profile ans-super
```

### Search Logs

```bash
# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/processapp-ws-message-v2-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --profile ans-super

# Search by session ID
aws logs filter-log-events \
  --log-group-name /aws/lambda/processapp-ws-message-v2-dev \
  --filter-pattern "session-123" \
  --profile ans-super
```

### Key Metrics to Monitor

```yaml
Agent Runtime:
  - Invocation count (healthy: >0/day)
  - Error rate (healthy: <1%)
  - Response latency (healthy: <5s p99)
  - Memory usage (healthy: <512MB)

WebSocket:
  - Connection count (track concurrent users)
  - Message count (throughput)
  - Error rate (healthy: <1%)
  - Lambda duration (healthy: <10s)

Knowledge Base:
  - Query count
  - Retrieval latency (healthy: <2s)
  - Document count (verify after ingestion)
```

---

## Troubleshooting

### Deployment Fails

**Issue:** CDK deployment fails with "Resource already exists"

**Solution:**
```bash
# Check existing stacks
npx cdk list --profile ans-super

# Destroy failed stack
npx cdk destroy dev-us-east-1-agent-v2 --profile ans-super

# Redeploy
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
```

### WebSocket Connection Fails

**Issue:** Cannot connect to WebSocket

**Solution:**
```bash
# Check WebSocket API status
aws apigatewayv2 get-api --api-id 1j1xzo7n4h --profile ans-super

# Check Lambda function
aws lambda get-function \
  --function-name processapp-ws-message-v2-dev \
  --profile ans-super

# Redeploy WebSocket stack
npx cdk deploy dev-us-east-1-websocket-v2 --profile ans-super
```

### Agent Not Responding

**Issue:** Agent returns errors or timeouts

**Solution:**
```bash
# Check Agent Runtime status
aws bedrock-agentcore list-runtimes --profile ans-super

# Check logs
aws logs tail \
  /aws/bedrock-agentcore/runtimes/processapp_agent_runtime_v2_dev-9b2dszEtqw-DEFAULT \
  --follow --profile ans-super

# Redeploy agent
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super
```

### Knowledge Base Returns No Results

**Issue:** Queries return empty results

**Solution:**
```bash
# Check documents in S3
aws s3 ls s3://processapp-docs-v2-dev-708819485463/documents/ \
  --recursive --profile ans-super

# Check ingestion job status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id <DS_ID> \
  --max-results 5 \
  --profile ans-super

# Trigger sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id <DS_ID> \
  --profile ans-super
```

---

## Rollback Procedures

### Rollback Agent V2

```bash
# Get stack drift
npx cdk diff dev-us-east-1-agent-v2 --profile ans-super

# Rollback to previous version
npx cdk deploy dev-us-east-1-agent-v2 \
  --previous-parameters \
  --profile ans-super
```

### Complete Rollback

```bash
# Destroy Agent V2
npx cdk destroy dev-us-east-1-websocket-v2 --profile ans-super
npx cdk destroy dev-us-east-1-agent-v2 --profile ans-super

# Redeploy stable version
git checkout <stable-commit>
cd infrastructure
npm run build
npx cdk deploy dev-us-east-1-agent-v2 dev-us-east-1-websocket-v2 \
  --profile ans-super
```

### Emergency: Disable Agent

```bash
# Stop Lambda function (WebSocket handler)
aws lambda update-function-configuration \
  --function-name processapp-ws-message-v2-dev \
  --environment Variables={DISABLED=true} \
  --profile ans-super
```

---

## Production Checklist

Before going to production:

- [ ] All E2E tests passing
- [ ] Load testing completed (50+ concurrent users)
- [ ] Security review completed
- [ ] Backup strategy defined
- [ ] Monitoring dashboards configured
- [ ] Alerting rules configured
- [ ] Runbook documented
- [ ] On-call rotation established
- [ ] Disaster recovery tested
- [ ] Cost optimization review completed

---

## Additional Resources

- **Architecture:** [README.md](../README.md)
- **Quick Start:** [QUICK_START.md](../QUICK_START.md)
- **Testing:** [TEST_WEBSOCKET.md](../TEST_WEBSOCKET.md)
- **E2E Tests:** [e2e/README.md](../e2e/README.md)
- **AWS Bedrock Docs:** https://docs.aws.amazon.com/bedrock/
- **Strand SDK Docs:** https://strandsagents.com/docs/

---

**Last Updated:** 2026-04-26  
**Maintainer:** ProcessApp DevOps Team  
**Support:** support@processapp.com
