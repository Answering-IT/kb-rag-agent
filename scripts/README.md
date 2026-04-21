# Test Scripts

This directory contains all test and utility scripts for the ProcessApp RAG system.

## 🧪 Test Scripts

### test-api.py
**Purpose:** Test the API Gateway endpoint

**Usage:**
```bash
export API_KEY="your-api-key"
python3 scripts/test-api.py
```

**Tests:**
- ✅ Simple query
- ✅ Follow-up question (session continuity)
- ✅ OCR document query
- ✅ Company data query
- ✅ PII filter test (guardrails)

**Requirements:**
- API key configured in environment variable
- `requests` library installed

---

### test-agent.py
**Purpose:** Test Bedrock Agent directly via AWS SDK

**Usage:**
```bash
export AWS_PROFILE=default
python3 scripts/test-agent.py
```

**Tests:**
- Direct agent invocation using boto3
- Session management
- Response streaming

**Requirements:**
- AWS credentials configured
- `boto3` library installed
- IAM permissions to invoke Bedrock Agent

---

### test-ocr-agent.py
**Purpose:** Test the OCR flow end-to-end

**Usage:**
```bash
export AWS_PROFILE=default
python3 scripts/test-ocr-agent.py
```

**What it tests:**
1. Upload image/PDF to S3
2. OCR Lambda triggers
3. Textract extracts text
4. Processed text saved to S3
5. KB sync
6. Query agent about OCR document

**Requirements:**
- AWS credentials configured
- `boto3`, `Pillow` libraries installed
- S3 bucket name and KMS key ID configured

---

### test-dos-flujos.py
**Purpose:** Test both document flows (OCR and direct)

**Usage:**
```bash
export AWS_PROFILE=default
python3 scripts/test-dos-flujos.py
```

**What it tests:**
1. **Direct flow:** Upload text document → KB sync → Query
2. **OCR flow:** Upload image → OCR → KB sync → Query

**Requirements:**
- AWS credentials configured
- `boto3` library installed
- Test documents available

---

### create-ocr-image.py
**Purpose:** Generate test images with text for OCR testing

**Usage:**
```bash
python3 scripts/create-ocr-image.py
```

**Output:**
- PNG image with embedded text
- Useful for testing OCR Lambda
- Can customize text content

**Requirements:**
- `Pillow` library installed

---

## 📦 Installation

Install required dependencies:

```bash
# Using pip
pip install boto3 requests Pillow

# Or using requirements.txt
pip install -r requirements.txt
```

## 🔑 Configuration

### For API Tests
```bash
export API_KEY="your-api-key"
```

### For Direct AWS Tests
```bash
export AWS_PROFILE=default
# Or
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
```

## 🚀 Quick Start

**1. Test API Gateway (easiest):**
```bash
export API_KEY="your-api-key"
python3 scripts/test-api.py
```

**2. Test complete OCR flow:**
```bash
export AWS_PROFILE=default
python3 scripts/test-ocr-agent.py
```

**3. Test both flows:**
```bash
export AWS_PROFILE=default
python3 scripts/test-dos-flujos.py
```

## 📊 Test Output

All test scripts provide detailed output:
- ✅ Success indicators
- ❌ Error messages with context
- ⏱️ Timing information
- 📝 Response content

## 🐛 Troubleshooting

### API Key Issues
```bash
# Verify API key is set
echo $API_KEY

# Get API key value
aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text
```

### AWS Credentials Issues
```bash
# Verify AWS credentials
aws sts get-caller-identity

# List available profiles
aws configure list-profiles
```

### Import Errors
```bash
# Install missing dependencies
pip install boto3 requests Pillow
```

## 📚 Documentation

- **Main README:** [../README.md](../README.md)
- **API Documentation:** [../docs/API_USAGE.md](../docs/API_USAGE.md)
- **Testing Guide:** [../docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)

---

**Last Updated:** 2026-04-21
