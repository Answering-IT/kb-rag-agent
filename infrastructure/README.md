# ProcessApp RAG Infrastructure

Cost-effective RAG application infrastructure using AWS CDK with Bedrock Agent Core Runtime, Knowledge Bases, and S3 vector storage.

## Architecture Overview

```
S3 Docs → EventBridge → Lambda (OCR) → Textract
                            ↓
                        Titan v2 Embeddings
                            ↓
                        S3 Vectors → Bedrock Knowledge Base
                                          ↓
                                    Agent Core Runtime (Strand SDK)
                                          ↓
                                    Bedrock Nova Pro
                                          ↓
                                    Streaming API (Lambda Function URL)
                                          ↓
                                    Next.js Frontend
```

## Features

- **Agent Core Runtime**: Custom agent using Strand SDK with tool calling
- **Normative Framework**: Pre-loaded Colombian pension regulations (Colpensiones)
- **Streaming API**: REST endpoint with streaming response (Lambda Function URL)
- **Cost-Optimized Storage**: S3 Intelligent-Tiering + S3-based vectors (90% cheaper than OpenSearch)
- **Document Processing**: Textract OCR, chunking (512 tokens, 20% overlap)
- **Embeddings**: Titan Embeddings v2 with storage optimization (-50% cost)
- **Knowledge Base**: Bedrock KB for RAG orchestration
- **PII Protection**: Bedrock Guardrails (EMAIL, PHONE, SSN, CREDIT_CARD)
- **Monitoring**: CloudWatch dashboards, alarms, cost tracking
- **Multi-Region Ready**: Initially us-east-1, expandable to other regions

## Prerequisites

- **AWS CLI** configured with profile `ans-super`
- **Node.js** v18+ and npm
- **AWS CDK** v2.100.0+
- **AWS Account**: 708819485463
- **IAM Permissions**: Administrator or equivalent

## Quick Start

### 1. Install Dependencies

```bash
cd infrastructure
npm install
```

### 2. Bootstrap CDK

```bash
cdk bootstrap aws://708819485463/us-east-1 --profile ans-super
```

### 3. Compile and Deploy

```bash
npm run build
cdk deploy --all --profile ans-super --require-approval never
```

This will deploy the following stacks:
- `dev-us-east-1-prereqs` - Global S3 buckets, IAM roles, KMS keys
- `dev-us-east-1-security` - Security policies
- `dev-us-east-1-bedrock` - Knowledge Base with S3 vector storage
- `dev-us-east-1-document-processing` - OCR Lambda with Textract
- `dev-us-east-1-guardrails` - PII filtering guardrails
- `dev-us-east-1-agent-v2` - Agent Core Runtime with Strand SDK
- `dev-us-east-1-streaming-api` - Lambda Function URL for streaming chat
- `dev-us-east-1-monitoring` - CloudWatch dashboards and alarms

**Deployment time**: ~15-20 minutes

### 4. Test the API

```bash
# Get the streaming API URL from outputs
STREAMING_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-streaming-api \
  --query 'Stacks[0].Outputs[?OutputKey==`StreamingChatURL`].OutputValue' \
  --output text \
  --profile ans-super)

# Test with curl
curl -X POST "$STREAMING_URL" \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué es Colpensiones?","sessionId":"test-123"}'
```

### 5. Verify Deployment

```bash
# List deployed stacks
cdk list

# Get outputs
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-deployment-stage-bedrock \
  --query 'Stacks[0].Outputs' \
  --profile default
```

## Project Structure

```
infrastructure/
├── bin/
│   └── app.ts                    # Main entry point
├── config/
│   ├── environments.ts           # Account, region, model config
│   ├── bedrock.config.ts         # KB and embedding config
│   └── security.config.ts        # IAM, KMS, guardrails
├── lib/
│   ├── PrereqsStack.ts           # Global S3 buckets, IAM roles
│   ├── SecurityStack.ts          # KMS keys, policies
│   ├── S3VectorStoreStack.ts     # Vector indexing
│   ├── BedrockStack.ts           # Knowledge Base
│   ├── DocumentProcessingStack.ts # OCR, embeddings
│   ├── GuardrailsStack.ts        # PII filtering
│   └── MonitoringStack.ts        # CloudWatch
├── lambdas/
│   ├── ocr-processor/            # Textract OCR
│   ├── embedder/                 # Titan v2 embeddings
│   ├── kb-creator/               # Custom resource for KB
│   ├── data-source-creator/      # Custom resource for DS
│   ├── guardrail-creator/        # Custom resource for Guardrails
│   └── vector-indexer/           # S3 vector index updater
├── cdk.json                      # CDK configuration
├── package.json                  # NPM dependencies
└── tsconfig.json                 # TypeScript config
```

## Configuration

### Update Account Settings

Edit `config/environments.ts`:

```typescript
export const SDLCAccounts: SDLCAccount[] = [
  {
    id: '708819485463',     // Your AWS account ID
    stage: 'dev',
    profile: 'default',
  },
];
```

### Update Regions

```typescript
export const TargetRegions: string[] = ['us-east-1'];
```

### Update Bedrock Models

```typescript
export const BedrockConfig = {
  embeddingModel: 'amazon.titan-embed-text-v2:0',
  llmModel: 'anthropic.claude-sonnet-3-5-v2:0',
};
```

## Usage

### Upload Documents

```bash
# Upload a test document
aws s3 cp document.pdf s3://processapp-docs-dev-708819485463/documents/ \
  --profile default
```

### Monitor Processing

```bash
# Check OCR Lambda logs
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile default

# Check embedder Lambda logs
aws logs tail /aws/lambda/processapp-embedder-dev --follow --profile default

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url $(aws cloudformation describe-stacks \
    --stack-name dev-us-east-1-deployment-stage-document-processing \
    --query 'Stacks[0].Outputs[?OutputKey==`ChunksQueueUrl`].OutputValue' \
    --output text --profile default) \
  --attribute-names ApproximateNumberOfMessages \
  --profile default
```

### Query Knowledge Base

```python
import boto3

bedrock_agent = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

# Get KB ID from CloudFormation outputs
kb_id = 'YOUR_KB_ID'

# Query
response = bedrock_agent.retrieve(
    knowledgeBaseId=kb_id,
    retrievalQuery={'text': 'What is this document about?'},
    retrievalConfiguration={
        'vectorSearchConfiguration': {'numberOfResults': 5}
    }
)

# Print results
for result in response['retrievalResults']:
    print(f"Score: {result['score']}")
    print(f"Content: {result['content']['text']}")
    print(f"Source: {result['location']['s3Location']['uri']}")
    print("---")
```

### Trigger Manual KB Sync

```bash
# Get sync function name
SYNC_FUNCTION=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-deployment-stage-bedrock \
  --query 'Stacks[0].Outputs[?OutputKey==`SyncFunctionArn`].OutputValue' \
  --output text --profile default | awk -F: '{print $NF}')

# Invoke sync
aws lambda invoke \
  --function-name $SYNC_FUNCTION \
  --profile default \
  response.json

cat response.json
```

## Monitoring

### CloudWatch Dashboard

Access at:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=ProcessApp-RAG-dev
```

Metrics tracked:
- Lambda invocations, errors, duration
- SQS queue depth
- Knowledge Base query latency
- Estimated monthly costs

### Alarms

Alarms configured for:
- Lambda error rate > 5%
- KB query latency > 2000ms
- SQS queue depth > 1000 messages
- Monthly cost > 80% of budget ($50 for dev)

Subscribe to alarm topic:
```bash
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-deployment-stage-monitoring \
  --query 'Stacks[0].Outputs[?OutputKey==`AlarmTopicArn`].OutputValue' \
  --output text --profile default)

aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --profile default
```

### Cost Tracking

View current costs:
```bash
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=Application \
  --profile default
```

## Cost Estimates

### Dev Environment (us-east-1, low volume)

| Service | Monthly Cost |
|---------|--------------|
| S3 (docs + vectors) | $2-5 |
| Titan Embeddings v2 | $5-10 |
| Bedrock Knowledge Base | $2-3 |
| Lambda (processing) | $2-5 |
| Textract | $5-10 |
| Bedrock Guardrails | $1-2 |
| KMS | $1 |
| CloudWatch | $1-2 |
| **Total** | **$20-40/month** |

### Cost Optimization

- S3 Intelligent-Tiering: Automatic optimization (~30% savings)
- Titan v2 storage optimization: -50% cost
- Lambda reserved concurrency: Prevent over-provisioning
- Lifecycle policies: Archive after 90 days
- Budget alarms: Alert at 80% of $50/month

## Troubleshooting

### Issue: CDK Synth Fails

**Error**: `Cannot find module '@aws-cdk/aws-bedrock'`

**Solution**: Bedrock KB doesn't have native L2 constructs yet. We use custom resources.

### Issue: Textract Job Fails

**Error**: `AccessDeniedException: Not authorized to perform textract:StartDocumentTextDetection`

**Solution**: Verify Textract role has S3 read access:
```bash
aws iam get-role-policy \
  --role-name processapp-textract-role-dev \
  --policy-name TextractS3Access \
  --profile default
```

### Issue: Embedder Lambda Timeout

**Error**: `Task timed out after 60.00 seconds`

**Solution**: Increase timeout in `config/environments.ts`:
```typescript
lambda: {
  embedder: {
    timeoutSeconds: 120,  // Increase to 2 minutes
  }
}
```

### Issue: KB Query Returns No Results

**Possible causes**:
1. KB sync not completed
2. No documents indexed
3. Query doesn't match document content

**Debug**:
```bash
# Check KB status
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id YOUR_KB_ID \
  --profile default

# Check ingestion jobs
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id YOUR_KB_ID \
  --data-source-id YOUR_DS_ID \
  --profile default

# Check S3 vectors
aws s3 ls s3://processapp-vectors-dev-708819485463/embeddings/ --profile default
```

### Issue: High Costs

**Debug**:
```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=processapp-embedder-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-31T23:59:59Z \
  --period 86400 \
  --statistics Sum \
  --profile default
```

## Security

### Encryption

- **At rest**: All S3 buckets encrypted with KMS customer-managed keys
- **In transit**: HTTPS enforced via bucket policies
- **KMS rotation**: Automatic annual rotation

### Access Control

- **IAM roles**: Least-privilege policies per service
- **S3 policies**: Block public access, deny unencrypted uploads
- **VPC endpoints**: S3 gateway endpoint (no internet traffic)

### PII Protection

Bedrock Guardrails block:
- EMAIL, PHONE, SSN, CREDIT_CARD
- PERSON, ORGANIZATION, ADDRESS
- Custom regex patterns (SSN, email)

## Cleanup

### Delete All Stacks

```bash
cdk destroy --all --profile default
```

**Note**: S3 buckets with `removalPolicy: RETAIN` (prod) will not be deleted automatically.

### Manual Cleanup

```bash
# Empty S3 buckets
aws s3 rm s3://processapp-docs-dev-708819485463 --recursive --profile default
aws s3 rm s3://processapp-vectors-dev-708819485463 --recursive --profile default

# Delete buckets
aws s3 rb s3://processapp-docs-dev-708819485463 --profile default
aws s3 rb s3://processapp-vectors-dev-708819485463 --profile default
```

## Multi-Region Expansion

### Phase 2: Add us-east-2

1. Update `config/environments.ts`:
```typescript
export const TargetRegions = ['us-east-1', 'us-east-2'];
```

2. Check Bedrock availability:
```bash
aws bedrock list-foundation-models --region us-east-2 --profile default
```

3. Deploy:
```bash
cdk deploy --all --profile default
```

4. Enable cross-region replication (optional):
- S3 CRR for docs/vectors
- Route 53 latency-based routing

## Support

- **Documentation**: See `/docs` directory
- **Issues**: File GitHub issues
- **AWS Support**: Contact AWS support for Bedrock/Textract issues

## License

Internal use only.
