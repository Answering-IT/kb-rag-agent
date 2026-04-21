# Deployment Guide

Complete guide for deploying the ProcessApp RAG infrastructure to AWS.

**Last Updated**: 2026-04-17

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Deployment](#deployment)
5. [Post-Deployment Verification](#post-deployment-verification)
6. [Updating Stacks](#updating-stacks)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

| Tool | Minimum Version | Install Command |
|------|----------------|-----------------|
| Node.js | 18.x | [nodejs.org](https://nodejs.org) |
| npm | 9.x | Included with Node.js |
| AWS CLI | 2.x | `brew install awscli` (Mac) |
| AWS CDK | 2.x | `npm install -g aws-cdk` |
| TypeScript | 5.x | Included in project |
| Git | 2.x | `brew install git` (Mac) |

### AWS Prerequisites

1. **AWS Account**:
   - Account ID: 708819485463 (update in config)
   - Admin access or sufficient IAM permissions

2. **IAM Permissions Required**:
   - CloudFormation (full)
   - S3 (full)
   - Lambda (full)
   - IAM (create roles, policies)
   - Bedrock (full)
   - EventBridge (full)
   - SQS, SNS (full)
   - CloudWatch (full)
   - KMS (create keys, grants)

3. **Service Quotas**:
   - Bedrock access enabled
   - Claude 3.5 Sonnet access requested
   - Titan Embeddings v2 access requested
   - Lambda concurrent executions: At least 100
   - S3 buckets: At least 2 per stage

4. **AWS CLI Configuration**:
```bash
# Configure AWS credentials
aws configure

# Verify configuration
aws sts get-caller-identity

# Output should show your account ID
{
  "UserId": "...",
  "Account": "708819485463",
  "Arn": "arn:aws:iam::708819485463:user/..."
}
```

---

## Initial Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd kb-rag-agent/infrastructure
```

### 2. Install Dependencies

```bash
# Install npm packages
npm install

# Verify installation
npm list --depth=0

# Expected output includes:
# ├── aws-cdk-lib@^2.248.0
# ├── constructs@^10.5.0
# └── typescript@~5.9.3
```

### 3. Bootstrap CDK (First Time Only)

```bash
# Bootstrap CDK in your AWS account
npx cdk bootstrap aws://708819485463/us-east-1

# This creates:
# - CDKToolkit CloudFormation stack
# - S3 bucket for CDK assets
# - IAM roles for CDK operations

# Verify bootstrap
aws cloudformation describe-stacks --stack-name CDKToolkit
```

---

## Configuration

### 1. Update Account Configuration

Edit `config/environments.ts`:

```typescript
export const SDLCAccounts: SDLCAccount[] = [
  {
    id: '708819485463',  // ← Update with your account ID
    stage: 'dev',
    profile: 'default',  // ← Update if using named profile
  },
];
```

### 2. Verify Environment Settings

Check all configurations in `config/environments.ts`:

- **BedrockConfig**: Model names, dimensions
- **S3Config**: Bucket prefixes, lifecycle rules
- **ProcessingConfig**: Lambda timeouts, memory
- **KnowledgeBaseConfig**: Sync schedule, search config
- **GuardrailsConfig**: PII entities, content filters
- **AgentConfig**: Instructions, model parameters
- **MonitoringConfig**: Log retention, alarms
- **CostConfig**: Budget limits

### 3. Review Security Settings

Check `config/security.config.ts`:

- KMS key rotation
- S3 encryption settings
- IAM policies
- Resource policies

---

## Deployment

### Build Infrastructure Code

```bash
# Compile TypeScript
npm run build

# Verify no errors
echo $?  # Should output 0
```

### Synthesize CloudFormation Templates

```bash
# Generate CloudFormation templates (no deployment)
npx cdk synth

# Review templates in cdk.out/
ls -la cdk.out/
```

### Deploy Individual Stack

```bash
# Deploy a single stack
npx cdk deploy dev-us-east-1-prereqs

# With approval prompt
npx cdk deploy dev-us-east-1-prereqs --require-approval never
```

### Deploy All Stacks (Recommended)

```bash
# Deploy all stacks in dependency order
npx cdk deploy --all

# Skip approval prompts (use with caution)
npx cdk deploy --all --require-approval never

# With specific profile
npx cdk deploy --all --profile my-aws-profile
```

### Deployment Order (Automatic with --all)

1. **PrereqsStack** (~5 minutes)
   - S3 buckets
   - IAM roles
   - KMS key

2. **SecurityStack** (~2 minutes)
   - IAM policies
   - Bucket policies

3. **BedrockStack** (~3 minutes)
   - Vector bucket and index
   - Knowledge Base
   - Data Source

4. **DocumentProcessingStack** (~3 minutes)
   - OCR Lambda
   - Embedder Lambda
   - SQS/SNS

5. **GuardrailsStack** (~5 minutes)
   - Guardrail creation (custom resource)
   - Version creation

6. **AgentStack** (~2 minutes)
   - Bedrock Agent
   - Agent Alias

7. **MonitoringStack** (~2 minutes)
   - Dashboard
   - Alarms

**Total Time**: ~20-25 minutes

---

## Post-Deployment Verification

### 1. Verify Stack Outputs

```bash
# List all deployed stacks
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --query 'StackSummaries[?starts_with(StackName, `dev-us-east-1`)].StackName' \
  --output table

# Get outputs from a specific stack
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs' \
  --output table
```

### 2. Verify S3 Buckets

```bash
# List buckets
aws s3 ls | grep processapp

# Expected output:
# processapp-docs-v2-dev-708819485463
# processapp-vectors-v2-dev-708819485463
```

### 3. Verify Lambda Functions

```bash
# List Lambda functions
aws lambda list-functions \
  --query 'Functions[?starts_with(FunctionName, `processapp`)].FunctionName' \
  --output table

# Expected functions:
# - processapp-ocr-processor-dev
# - processapp-embedder-dev
# - processapp-guardrail-creator-dev
# - processapp-guardrail-version-dev
# - processapp-kb-sync-dev
```

### 4. Verify Knowledge Base

```bash
# Get KB details
export KB_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs[?OutputKey==`KnowledgeBaseId`].OutputValue' \
  --output text)

aws bedrock-agent get-knowledge-base \
  --knowledge-base-id $KB_ID \
  --output json

# Status should be: ACTIVE
```

### 5. Verify Bedrock Agent

```bash
# Get Agent details
export AGENT_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentId`].OutputValue' \
  --output text)

aws bedrock-agent get-agent \
  --agent-id $AGENT_ID \
  --output json

# Status should be: PREPARED or NOT_PREPARED (both OK)
```

### 6. Test Document Upload

```bash
# Create test document
echo "This is a test document for ProcessApp RAG system." > test.txt

# Upload to S3
export DOCS_BUCKET=processapp-docs-v2-dev-708819485463
aws s3 cp test.txt s3://${DOCS_BUCKET}/documents/

# Check if OCR Lambda was triggered
aws logs tail /aws/lambda/processapp-ocr-processor-dev --since 5m
```

### 7. Trigger KB Sync

```bash
# Get Data Source ID
export DS_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].Outputs[?OutputKey==`DataSourceId`].OutputValue' \
  --output text)

# Start ingestion job
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID

# Monitor status
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --max-results 1
```

### 8. Test Agent Query

```bash
# Get Agent Alias ID
export AGENT_ALIAS_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentAliasId`].OutputValue' \
  --output text)

# Test query
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $AGENT_ALIAS_ID \
  --session-id $(uuidgen) \
  --input-text "What is this document about?" \
  output.txt

# View response
cat output.txt | jq -r '.chunk.bytes' | base64 --decode
```

---

## Updating Stacks

### Update Single Stack

```bash
# Make changes to code
# Build
npm run build

# Deploy updated stack
npx cdk deploy dev-us-east-1-bedrock

# CDK will show diff before deploying
```

### Update All Stacks

```bash
# Deploy all stacks (only changed stacks will update)
npx cdk deploy --all

# View changes before deploying
npx cdk diff dev-us-east-1-bedrock
```

### Update Lambda Code Only

```bash
# After modifying Lambda code
npm run build

# CDK will detect Lambda code change and redeploy
npx cdk deploy dev-us-east-1-document-processing
```

---

## Rollback Procedures

### Rollback Single Stack

```bash
# CloudFormation automatic rollback (if deployment fails)
# No action needed - stack reverts to previous state

# Manual rollback to previous version
aws cloudformation update-stack \
  --stack-name dev-us-east-1-bedrock \
  --use-previous-template

# Or delete and recreate
npx cdk destroy dev-us-east-1-agent
npx cdk deploy dev-us-east-1-agent
```

### Rollback All Stacks

```bash
# Destroy all stacks (CAUTION: Data loss!)
npx cdk destroy --all

# Redeploy from known-good commit
git checkout <good-commit>
npm run build
npx cdk deploy --all
```

### Rollback Lambda Only

```bash
# List Lambda versions
aws lambda list-versions-by-function \
  --function-name processapp-ocr-processor-dev

# Update to previous version
aws lambda update-function-code \
  --function-name processapp-ocr-processor-dev \
  --s3-bucket <cdk-assets-bucket> \
  --s3-key <previous-version-key>
```

---

## Troubleshooting

### Issue: CDK Bootstrap Fails

**Error**: `Unable to resolve AWS account to a partition`

**Solution**:
```bash
# Ensure AWS CLI is configured
aws configure

# Verify credentials
aws sts get-caller-identity

# Try explicit account/region
npx cdk bootstrap aws://708819485463/us-east-1 --profile default
```

### Issue: Stack Deployment Fails

**Error**: `Resource limit exceeded` or `CREATE_FAILED`

**Diagnosis**:
```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-bedrock \
  --max-items 20

# Look for specific error messages
```

**Common Solutions**:
- **Service quota**: Request limit increase
- **IAM permissions**: Add missing permissions
- **Dependency issue**: Deploy prerequisite stacks first
- **Name conflict**: Resource name already exists

### Issue: Bedrock Access Denied

**Error**: `AccessDeniedException` when using Bedrock

**Solution**:
```bash
# Request Bedrock model access in AWS Console
# 1. Go to Bedrock console
# 2. Model access → Request access
# 3. Select: Claude 3.5 Sonnet, Titan Embeddings v2
# 4. Wait for approval (~5 minutes)

# Verify access
aws bedrock list-foundation-models --output table
```

### Issue: Lambda Timeout

**Error**: Lambda times out during execution

**Solution**:

Edit `config/environments.ts`:
```typescript
lambda: {
  ocrProcessor: {
    timeoutSeconds: 600, // Increase from 300
  }
}
```

Redeploy:
```bash
npm run build
npx cdk deploy dev-us-east-1-document-processing
```

### Issue: S3 Bucket Already Exists

**Error**: `Bucket name already exists`

**Solution**:

Option 1: Use existing bucket (if it's yours)
```typescript
// In PrereqsStack.ts
this.docsBucket = s3.Bucket.fromBucketName(
  this, 'DocumentsBucket',
  'existing-bucket-name'
);
```

Option 2: Change bucket prefix
```typescript
// In config/environments.ts
docsBucket: {
  prefix: 'processapp-docs-v3', // Change version
}
```

### Issue: CDK Out of Sync

**Error**: `Resource is not in the expected state`

**Solution**:
```bash
# Refresh CDK state
npx cdk synth --force

# If still broken, destroy and recreate
npx cdk destroy dev-us-east-1-<stack-name>
npx cdk deploy dev-us-east-1-<stack-name>
```

---

## Best Practices

### 1. Use Version Control

```bash
# Always commit before deploying
git add .
git commit -m "Updated bedrock configuration"
git push

# Tag deployments
git tag -a v1.0.0 -m "Production deployment"
git push --tags
```

### 2. Test in Development First

```bash
# Deploy to dev stage first
# Test thoroughly
# Then promote to staging/prod
```

### 3. Monitor Deployments

```bash
# Watch CloudFormation events during deployment
watch -n 5 "aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-bedrock \
  --query 'Stacks[0].StackStatus'"
```

### 4. Backup Before Major Changes

```bash
# Export stack template
aws cloudformation get-template \
  --stack-name dev-us-east-1-bedrock \
  > backup-bedrock-$(date +%Y%m%d).json

# Backup S3 data
aws s3 sync s3://processapp-docs-v2-dev-708819485463 \
  ./backup-docs-$(date +%Y%m%d)/
```

### 5. Use Change Sets for Production

```bash
# Create change set (preview changes)
aws cloudformation create-change-set \
  --stack-name prod-us-east-1-bedrock \
  --change-set-name update-$(date +%Y%m%d) \
  --template-body file://cdk.out/prod-us-east-1-bedrock.template.json

# Review changes
aws cloudformation describe-change-set \
  --stack-name prod-us-east-1-bedrock \
  --change-set-name update-$(date +%Y%m%d)

# Execute if safe
aws cloudformation execute-change-set \
  --stack-name prod-us-east-1-bedrock \
  --change-set-name update-$(date +%Y%m%d)
```

---

## Cleanup

### Delete All Stacks

```bash
# CAUTION: This deletes all resources!

# Delete in reverse dependency order
npx cdk destroy dev-us-east-1-monitoring
npx cdk destroy dev-us-east-1-agent
npx cdk destroy dev-us-east-1-guardrails
npx cdk destroy dev-us-east-1-document-processing
npx cdk destroy dev-us-east-1-bedrock
npx cdk destroy dev-us-east-1-security
npx cdk destroy dev-us-east-1-prereqs

# Or all at once
npx cdk destroy --all
```

### Clean Up S3 Buckets

```bash
# Empty buckets before deletion
aws s3 rm s3://processapp-docs-v2-dev-708819485463 --recursive
aws s3 rm s3://processapp-vectors-v2-dev-708819485463 --recursive

# Delete buckets
aws s3 rb s3://processapp-docs-v2-dev-708819485463
aws s3 rb s3://processapp-vectors-v2-dev-708819485463
```

---

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CloudFormation Best Practices](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/best-practices.html)
- [Bedrock Deployment Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- [SYSTEM_OVERVIEW.md](SYSTEM_OVERVIEW.md)

---

**Status**: Deployment guide complete and ready for use
