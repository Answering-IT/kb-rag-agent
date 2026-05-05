# Current Deployment IDs

Last updated: 2026-05-05

## Infrastructure IDs

### Bedrock Knowledge Base
- **Knowledge Base ID:** BLJTRDGQI0
- **Data Source ID:** B1OGNN9EMU
- **Vector Index ARN:** arn:aws:s3vectors:us-east-1:708819485463:bucket/processapp-vectors-dev-708819485463/index/processapp-kb-v3-dev-vector-index
- **Sync Function ARN:** arn:aws:lambda:us-east-1:708819485463:function:processapp-kb-sync-dev

### Agent Core Runtime (Agent V2)
- **Runtime ID:** processapp_agent_runtime_dev-l9vO3UDmJ4
- **Runtime ARN:** arn:aws:bedrock-agentcore:us-east-1:708819485463:runtime/processapp_agent_runtime_dev-l9vO3UDmJ4
- **Runtime Name:** processapp_agent_runtime_dev
- **Memory ID:** processapp_agent_memory_dev-DDbbNMBApu
- **Memory ARN:** arn:aws:bedrock-agentcore:us-east-1:708819485463:memory/processapp_agent_memory_dev-DDbbNMBApu
- **Log Group:** /aws/bedrock/agentcore/runtime/processapp_agent_runtime_dev
- **Endpoint URL:** https://processapp_endpoint_dev.bedrock-agentcore.us-east-1.amazonaws.com

### WebSocket API
- **WebSocket URL:** wss://6aqhp0u2zk.execute-api.us-east-1.amazonaws.com/dev
- **WebSocket API ID:** 6aqhp0u2zk
- **Message Handler ARN:** arn:aws:lambda:us-east-1:708819485463:function:processapp-ws-message-dev
- **Connect Handler:** processapp-ws-connect-dev
- **Disconnect Handler:** processapp-ws-disconnect-dev

### S3 Buckets
- **Documents Bucket:** processapp-docs-v2-dev-708819485463
- **Vectors Bucket:** processapp-vectors-dev-708819485463

### IAM Roles
- **Bedrock KB Role:** processapp-kb-role-dev
- **Runtime Role:** processapp-runtime-role-dev
- **WebSocket Handler Role:** processapp-ws-handler-role-dev

### KMS
- **KMS Key ID:** e6a714f6-70a7-47bf-a9ee-55d871d33cc6

## Configuration

### Agent V2 Environment Variables
```bash
KB_ID=BLJTRDGQI0
MODEL_ID=amazon.nova-pro-v1:0
MEMORY_ID=processapp_agent_memory_dev-DDbbNMBApu
REGION=us-east-1
STAGE=dev
ECS_BASE_URL=https://dev.app.colpensiones.procesapp.com
PORT=8080
```

### WebSocket Handler Environment Variables
```bash
RUNTIME_ID=processapp_agent_runtime_dev-l9vO3UDmJ4
KNOWLEDGE_BASE_ID=BLJTRDGQI0
STAGE=dev
AWS_ACCOUNT_ID=708819485463
```

## Quick Commands

### View Agent Logs
```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_dev --follow --profile ans-super
```

### Test WebSocket
```bash
wscat -c wss://6aqhp0u2zk.execute-api.us-east-1.amazonaws.com/dev
{"action":"sendMessage","data":{"inputText":"¿Cómo me puedes ayudar?","sessionId":"test-123"}}
```

### Get Stack Outputs
```bash
aws cloudformation describe-stacks --stack-name dev-us-east-1-agent-v2 --query 'Stacks[0].Outputs' --profile ans-super
aws cloudformation describe-stacks --stack-name dev-us-east-1-bedrock --query 'Stacks[0].Outputs' --profile ans-super
aws cloudformation describe-stacks --stack-name dev-us-east-1-websocket-v2 --query 'Stacks[0].Outputs' --profile ans-super
```

### Trigger Knowledge Base Sync
```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id BLJTRDGQI0 \
  --data-source-id B1OGNN9EMU \
  --profile ans-super
```

## Notes

- All resources are deployed in **us-east-1** region
- AWS Profile: **ans-super**
- Account: **708819485463**
- Stage: **dev**
- All stack names have been cleaned up (removed -v* suffixes)
- Infrastructure fully redeployed on 2026-05-05 with clean resource names
