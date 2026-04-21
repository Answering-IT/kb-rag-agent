# ProcessApp RAG API - Quick Reference

## Endpoint

```
POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query
```

## Authentication

```bash
# Get API Key
aws apigateway get-api-key --api-key 6a0h023lec --include-value --query 'value' --output text

# Use in requests
x-api-key: YOUR_API_KEY
```

## Request

```json
{
  "question": "Your question here",
  "sessionId": "optional-for-conversation-continuity"
}
```

## Response

```json
{
  "answer": "Agent's response",
  "sessionId": "abc-123-def",
  "status": "success"
}
```

## Examples

### curl
```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_KEY" \
  -d '{"question": "What documents do you have?"}'
```

### Python
```python
import requests

response = requests.post(
    "https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query",
    headers={"Content-Type": "application/json", "x-api-key": "YOUR_KEY"},
    json={"question": "What documents do you have?"}
)
print(response.json()['answer'])
```

### JavaScript
```javascript
const axios = require('axios');

const response = await axios.post(
  'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query',
  { question: 'What documents do you have?' },
  { headers: { 'x-api-key': 'YOUR_KEY' } }
);
console.log(response.data.answer);
```

### TypeScript
```typescript
const response = await fetch(
  'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query',
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': 'YOUR_KEY' },
    body: JSON.stringify({ question: 'What documents do you have?' })
  }
);
const data = await response.json();
console.log(data.answer);
```

## Rate Limits

| Limit | Value |
|-------|-------|
| Rate | 100 req/s |
| Burst | 200 concurrent |
| Quota | 10,000 req/month |
| Timeout | 30 seconds |

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request (missing question field) |
| 403 | Forbidden (invalid API key) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error (agent invocation failed) |

## Test Script

```bash
export API_KEY="your-api-key"
python3 scripts/test-api.py
```

## Monitoring

```bash
# API Gateway logs
aws logs tail /aws/apigateway/processapp-dev --follow

# Lambda handler logs
aws logs tail /aws/lambda/processapp-api-handler-dev --follow
```

## Full Documentation

- **Complete API Reference**: [docs/API_USAGE.md](docs/API_USAGE.md)
- **Main README**: [README.md](README.md)
- **Architecture**: [docs/ARCHITECTURE_DIAGRAM.md](docs/ARCHITECTURE_DIAGRAM.md)

## Stack Information

- **Stack Name**: dev-us-east-1-api
- **Region**: us-east-1
- **Stage**: dev
- **API Key ID**: 6a0h023lec
- **Lambda**: processapp-api-handler-dev
- **Agent ID**: QWTVV3BY3G
- **Agent Alias**: QZITGFMONE

---

**Quick Start:**
1. Get API key from admin
2. Set as environment variable: `export API_KEY="..."`
3. Make POST request to `/query` endpoint
4. Include `x-api-key` header
5. Send JSON with `question` field

Done! 🚀
