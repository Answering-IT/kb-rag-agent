# ProcessApp RAG - Documentation Index

Complete documentation for the ProcessApp RAG (Retrieval-Augmented Generation) infrastructure.

## 📚 Quick Start Guides

### For Backend Developers
- **[API Quick Reference](API_QUICKREF.md)** - One-page cheat sheet for API endpoint ⭐
- **[API Usage Guide](API_USAGE.md)** - Complete REST API documentation with examples
- **[Test API Script](../scripts/test-api.py)** - Ready-to-use Python test script

### For DevOps / Infrastructure
- **[Main README](../README.md)** - Quick start and overview ⭐
- **[Deployment Guide](DEPLOYMENT.md)** - Step-by-step deployment instructions
- **[System Overview](SYSTEM_OVERVIEW.md)** - Architecture and components

## 📖 Comprehensive Guides

### Architecture & Design
- **[Architecture Diagram](ARCHITECTURE_DIAGRAM.md)** - Visual system architecture with Mermaid diagrams
- **[System Overview](SYSTEM_OVERVIEW.md)** - Detailed technical overview of all components
- **[Lambda Inventory](LAMBDA_INVENTORY.md)** - Status of all Lambda functions (active vs. legacy)

### Document Processing
- **[Document Ingestion](DOCUMENT_INGESTION.md)** - How to upload and process documents
- **[Vectorization](VECTORIZATION.md)** - Automatic embedding and indexing process
- **[RAG Synchronization](RAG_SYNCHRONIZATION.md)** - Knowledge Base sync and maintenance

### Querying & Integration
- **[API Usage](API_USAGE.md)** - REST API reference (recommended for backends)
- **[API Quick Reference](API_QUICKREF.md)** - One-page API cheat sheet
- **[Agent Usage](AGENT_USAGE.md)** - Direct AWS SDK usage (advanced)

### Operations
- **[Deployment](DEPLOYMENT.md)** - CDK deployment procedures
- **[Testing Guide](TESTING_GUIDE.md)** - End-to-end testing procedures
- **[RAG Infrastructure Plan](RAG_INFRASTRUCTURE_PLAN.md)** - Original implementation plan

## 🧪 Test Scripts

Located in the scripts/ directory:

- **[test-api.py](../scripts/test-api.py)** - Test API Gateway endpoint
- **[test-agent.py](../scripts/test-agent.py)** - Test agent via AWS SDK
- **[test-ocr-agent.py](../scripts/test-ocr-agent.py)** - Test OCR flow
- **[test-dos-flujos.py](../scripts/test-dos-flujos.py)** - Test both flows (OCR + direct)
- **[create-ocr-image.py](../scripts/create-ocr-image.py)** - Generate test images

## 📂 Test Fixtures

Test documents and manifests:
- **[test-fixtures/](test-fixtures/)** - Sample documents for testing

## 🚀 Getting Started

### 1. For Backend Developers (Easiest)

1. Read [API Quick Reference](API_QUICKREF.md)
2. Get API key from admin
3. Use the [test-api.py](../scripts/test-api.py) script
4. Integrate into your backend using examples from [API Usage](API_USAGE.md)

### 2. For Infrastructure Engineers

1. Read [Main README](../README.md) - overview and quick start
2. Read [System Overview](SYSTEM_OVERVIEW.md) - understand the architecture
3. Read [Deployment Guide](DEPLOYMENT.md) - deploy the infrastructure
4. Read [Testing Guide](TESTING_GUIDE.md) - validate the deployment

### 3. For Understanding Document Processing

1. [Document Ingestion](DOCUMENT_INGESTION.md) - how documents are uploaded
2. [Vectorization](VECTORIZATION.md) - how embeddings are generated
3. [RAG Synchronization](RAG_SYNCHRONIZATION.md) - how KB is synced

## 🔗 External Resources

- [AWS Bedrock Agent Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AWS Bedrock Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [AWS CDK for TypeScript](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [AWS Textract](https://docs.aws.amazon.com/textract/)

## 📊 Architecture Summary

**8 CDK Stacks Deployed:**
1. PrereqsStack - S3 buckets, KMS, IAM
2. SecurityStack - Policies and permissions
3. BedrockStack - Knowledge Base + S3 Vectors
4. DocumentProcessingStack - OCR Lambda (Textract)
5. GuardrailsStack - Content filters + PII protection
6. AgentStack - Bedrock Agent (Nova Pro model)
7. APIStack - REST API Gateway + Lambda handler ⭐
8. MonitoringStack - CloudWatch dashboards

## 🎯 Most Common Tasks

| Task | Documentation |
|------|---------------|
| Query the agent from my backend | [API Quick Reference](API_QUICKREF.md) |
| Upload and ingest documents | [Document Ingestion](DOCUMENT_INGESTION.md) |
| Deploy the infrastructure | [Deployment Guide](DEPLOYMENT.md) |
| Understand the architecture | [System Overview](SYSTEM_OVERVIEW.md) + [Architecture Diagram](ARCHITECTURE_DIAGRAM.md) |
| Test the system | [Testing Guide](TESTING_GUIDE.md) + [test-api.py](../scripts/test-api.py) |
| Monitor and troubleshoot | [Main README](../README.md#monitoring) |

## 💡 Tips

- **Start here**: [Main README](../README.md) has quick start for all use cases
- **API users**: Go directly to [API Quick Reference](API_QUICKREF.md)
- **Infra engineers**: Start with [System Overview](SYSTEM_OVERVIEW.md)
- **Questions?**: Check troubleshooting sections in each guide

---

**Last Updated:** 2026-04-21
**Version:** 2.0 (with API Gateway)
**Stack:** AWS CDK, Bedrock, S3 Vectors, Textract, API Gateway
