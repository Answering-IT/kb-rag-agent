# ProcessApp RAG API - Usage Guide

REST API for querying the Bedrock Agent via HTTP endpoints.

**API Endpoint**: `https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query`
**Authentication**: API Key required (via `x-api-key` header)

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Reference](#api-reference)
4. [Code Examples](#code-examples)
5. [Error Handling](#error-handling)
6. [Rate Limits](#rate-limits)

---

## Quick Start

### Get Your API Key

```bash
# Retrieve API key value (requires apigateway:GET permission)
aws apigateway get-api-key \
  --api-key 6a0h023lec \
  --include-value \
  --query 'value' \
  --output text

# Save it as environment variable
export API_KEY="<your-api-key>"
```

**Note**: If you get "AccessDeniedException", ask an administrator with API Gateway permissions to retrieve the key for you.

### Make Your First Request

```bash
curl -X POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query \
  -H "Content-Type: application/json" \
  -H "x-api-key: ${API_KEY}" \
  -d '{"question": "What documents do you have?"}'
```

Expected response:
```json
{
  "answer": "I have documents about...",
  "sessionId": "abc-123-def",
  "status": "success"
}
```

---

## Authentication

All requests require an API key passed via the `x-api-key` header.

**Header Format:**
```
x-api-key: <your-api-key-value>
```

**Example:**
```bash
curl -H "x-api-key: AbCdEf123456..." https://...
```

---

## API Reference

### POST /query

Ask a question to the Bedrock Agent.

**Endpoint:**
```
POST https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query
```

**Headers:**
```
Content-Type: application/json
x-api-key: <your-api-key>
```

**Request Body:**
```json
{
  "question": "What was the security incident date?",
  "sessionId": "optional-session-123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question` | string | Yes | Question to ask the agent |
| `sessionId` | string | No | Session ID for conversation continuity. If not provided, a new session is created. |

**Response (200 OK):**
```json
{
  "answer": "The security incident occurred on April 18, 2026.",
  "sessionId": "abc-123-def-456",
  "status": "success"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `answer` | string | Agent's response |
| `sessionId` | string | Session ID (use for follow-up questions) |
| `status` | string | "success" if successful |

**Error Response (4xx/5xx):**
```json
{
  "error": "Error message",
  "status": "error"
}
```

---

## Code Examples

### Python (requests)

```python
import requests
import json

API_ENDPOINT = "https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query"
API_KEY = "your-api-key-here"

def ask_agent(question, session_id=None):
    """Ask a question to the agent"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }

    payload = {
        "question": question
    }

    if session_id:
        payload["sessionId"] = session_id

    response = requests.post(API_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()

    return response.json()

# Example usage
result = ask_agent("What documents do you have?")
print(f"Answer: {result['answer']}")
print(f"Session ID: {result['sessionId']}")

# Follow-up question using same session
follow_up = ask_agent(
    "Tell me more about the first one",
    session_id=result['sessionId']
)
print(f"Follow-up: {follow_up['answer']}")
```

### JavaScript (Node.js with axios)

```javascript
const axios = require('axios');

const API_ENDPOINT = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query';
const API_KEY = 'your-api-key-here';

async function askAgent(question, sessionId = null) {
  const payload = { question };
  if (sessionId) payload.sessionId = sessionId;

  const response = await axios.post(API_ENDPOINT, payload, {
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY
    }
  });

  return response.data;
}

// Example usage
(async () => {
  const result = await askAgent('What documents do you have?');
  console.log('Answer:', result.answer);
  console.log('Session ID:', result.sessionId);

  // Follow-up
  const followUp = await askAgent(
    'Tell me more',
    result.sessionId
  );
  console.log('Follow-up:', followUp.answer);
})();
```

### curl (Bash)

```bash
#!/bin/bash

API_ENDPOINT="https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query"
API_KEY="your-api-key-here"

# Simple query
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"question": "What was the incident date?"}' \
  | jq .

# With session ID for conversation
SESSION_ID=$(curl -s -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d '{"question": "What documents do you have?"}' \
  | jq -r '.sessionId')

echo "Session ID: $SESSION_ID"

# Follow-up question
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -H "x-api-key: $API_KEY" \
  -d "{\"question\": \"Tell me more\", \"sessionId\": \"$SESSION_ID\"}" \
  | jq .
```

### TypeScript (fetch API)

```typescript
interface QueryRequest {
  question: string;
  sessionId?: string;
}

interface QueryResponse {
  answer: string;
  sessionId: string;
  status: 'success' | 'error';
  error?: string;
}

const API_ENDPOINT = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query';
const API_KEY = 'your-api-key-here';

async function askAgent(
  question: string,
  sessionId?: string
): Promise<QueryResponse> {
  const payload: QueryRequest = { question };
  if (sessionId) payload.sessionId = sessionId;

  const response = await fetch(API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': API_KEY
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Example usage
(async () => {
  const result = await askAgent('What documents do you have?');
  console.log('Answer:', result.answer);

  const followUp = await askAgent(
    'Tell me more about the first one',
    result.sessionId
  );
  console.log('Follow-up:', followUp.answer);
})();
```

---

## Error Handling

### Common Error Codes

| Status Code | Error | Solution |
|-------------|-------|----------|
| 400 | `Missing required field: question` | Include "question" in request body |
| 400 | `Invalid JSON` | Check request body is valid JSON |
| 403 | `Forbidden` | Check API key is correct and included in `x-api-key` header |
| 429 | `Too Many Requests` | You've exceeded rate limit. Wait and retry. |
| 500 | `Agent invocation failed` | Check CloudWatch logs or contact support |

### Python Error Handling Example

```python
import requests

def ask_agent_safe(question, session_id=None):
    """Ask agent with error handling"""
    try:
        response = requests.post(
            API_ENDPOINT,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json={"question": question, "sessionId": session_id},
            timeout=30
        )

        if response.status_code == 403:
            return {"error": "Invalid API key"}
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded. Please wait."}
        elif response.status_code >= 500:
            return {"error": "Server error. Please try again later."}

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        return {"error": "Request timeout"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
```

---

## Rate Limits

The API has the following rate limits:

| Limit Type | Value |
|------------|-------|
| **Rate Limit** | 100 requests/second |
| **Burst Limit** | 200 concurrent requests |
| **Quota** | 10,000 requests/month |

**Rate Limit Headers:**

Response headers include rate limit information:
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9950
X-RateLimit-Reset: 1672531200
```

**Handling Rate Limits:**

If you receive a `429 Too Many Requests` response:
1. Wait for the time specified in `Retry-After` header
2. Implement exponential backoff
3. Consider caching responses

**Example with Retry:**

```python
import time

def ask_with_retry(question, max_retries=3):
    """Ask with automatic retry on rate limit"""
    for attempt in range(max_retries):
        result = ask_agent_safe(question)

        if 'error' not in result:
            return result

        if 'Rate limit' in result['error']:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
        else:
            return result

    return {"error": "Max retries exceeded"}
```

---

## CORS Configuration

The API supports CORS for web applications:

**Allowed Origins:** `*` (all origins)
**Allowed Methods:** `GET, POST, OPTIONS`
**Allowed Headers:** `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`

**Browser Example (fetch):**

```javascript
// Works from any domain
fetch('https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-api-key': 'your-api-key'
  },
  body: JSON.stringify({
    question: 'What documents do you have?'
  })
})
.then(r => r.json())
.then(data => console.log(data.answer));
```

---

## Monitoring & Logs

### CloudWatch Logs

API Gateway logs are available at:
```
/aws/apigateway/processapp-dev
```

Lambda handler logs:
```
/aws/lambda/processapp-api-handler-dev
```

**View recent logs:**
```bash
aws logs tail /aws/lambda/processapp-api-handler-dev --follow
```

### Metrics

Monitor API performance in CloudWatch:
- **Latency** - Response time
- **Count** - Request count
- **4XXError** - Client errors
- **5XXError** - Server errors

---

## Security Best Practices

1. **Protect API Key**
   - Store in environment variables, never in code
   - Rotate regularly
   - Use secrets manager in production

2. **Use HTTPS Only**
   - API only accepts HTTPS requests
   - HTTP requests are rejected

3. **Validate Responses**
   - Always check `status` field
   - Handle errors gracefully

4. **Session Management**
   - Don't share session IDs between users
   - Sessions expire after 15 minutes of inactivity

---

## Troubleshooting

### Issue: "Forbidden" (403)

**Cause:** Invalid or missing API key

**Solution:**
```bash
# Check if API key header is included
curl -v https://... -H "x-api-key: YOUR_KEY"

# Verify key value is correct (no extra spaces)
echo $API_KEY | tr -d ' \n'
```

### Issue: Request Timeout

**Cause:** Agent processing takes too long (>30s)

**Solution:**
- Simplify your question
- Check Knowledge Base has documents indexed
- Review CloudWatch logs for errors

### Issue: "Agent invocation failed"

**Cause:** Bedrock Agent error

**Solution:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/processapp-api-handler-dev --since 5m

# Check agent status
aws bedrock-agent get-agent --agent-id QWTVV3BY3G
```

---

## Advanced Usage

### Streaming Responses (Future)

Currently, responses are returned synchronously. Streaming support may be added in future versions:

```python
# Future API (not yet implemented)
for chunk in ask_agent_stream("What documents do you have?"):
    print(chunk, end='', flush=True)
```

### Batch Queries (Future)

For multiple questions, currently make separate requests. Batch API may be added:

```python
# Future API (not yet implemented)
results = ask_agent_batch([
    "Question 1?",
    "Question 2?",
    "Question 3?"
])
```

---

## Additional Resources

- [Main README](../README.md)
- [Architecture Diagrams](./ARCHITECTURE_DIAGRAM.md)
- [Testing Guide](./TESTING_GUIDE.md)
- [AWS API Gateway Documentation](https://docs.aws.amazon.com/apigateway/)

---

## Support

For issues or questions:
1. Check CloudWatch logs first
2. Review this documentation
3. Contact your infrastructure team
