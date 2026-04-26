# Session Memory Guide

**Date:** 2026-04-26  
**Status:** ✅ **DEPLOYED AND OPERATIONAL**  
**DynamoDB Table:** `processapp-conversations-dev`

---

## Overview

Session Memory provides conversation context persistence using DynamoDB. The agent remembers previous messages within a session, enabling natural multi-turn conversations.

### Benefits

- **Context Awareness:** Agent remembers what was said earlier in the conversation
- **Natural Dialogue:** Users don't need to repeat information
- **Persistent Storage:** Conversations stored for 90 days with automatic cleanup
- **Multi-Tenant Support:** Conversations are isolated by userId and tenantId
- **Efficient Retrieval:** Fast queries using DynamoDB with GSI support

---

## How It Works

### Architecture

```
User sends message with sessionId
    ↓
Lambda retrieves last 10 messages from DynamoDB
    ↓
Context injected into agent prompt
    ↓
Agent generates response with full conversation context
    ↓
Both user message and assistant response saved to DynamoDB
    ↓
TTL ensures automatic cleanup after 90 days
```

### DynamoDB Schema

**Table Name:** `processapp-conversations-dev`

**Primary Keys:**
- Partition Key: `sessionId` (STRING)
- Sort Key: `timestamp` (NUMBER, milliseconds since epoch)

**Attributes:**
- `sessionId`: Unique session identifier
- `timestamp`: Message timestamp (used for sorting)
- `role`: Message role (`user` or `assistant`)
- `content`: Message content (text)
- `userId`: User ID (optional, for GSI queries)
- `tenantId`: Tenant ID (optional, for isolation)
- `expirationTime`: TTL timestamp (90 days from creation)
- `metadata`: Additional metadata (optional JSON)

**Global Secondary Index:**
- Name: `UserIdIndex`
- Partition Key: `userId`
- Sort Key: `timestamp`
- Use case: Query all conversations for a specific user

---

## Usage Examples

### Example 1: Multi-Turn Conversation

**Session ID:** `session-abc-123`

**Turn 1:**
```json
User: "My name is Alice and I work for Colpensiones"
Assistant: "Nice to meet you, Alice! I understand you work for Colpensiones..."
```

**Turn 2:**
```json
User: "What is my name?"
Assistant: "Your name is Alice, as you mentioned earlier."
```

**Turn 3:**
```json
User: "Where do I work?"
Assistant: "You work for Colpensiones."
```

### Example 2: Project Context

**Turn 1:**
```json
User: "I'm working on project 123"
Assistant: "Got it! Project 123. How can I help you with it?"
```

**Turn 2:**
```json
User: "What's the budget for this project?"
Assistant: "Let me check the budget for project 123..." [calls GetProjectInfo tool]
```

---

## Implementation Details

### SessionMemory Class

**File:** `/infrastructure/lambdas/websocket-handler/session_memory.py`

**Key Methods:**

```python
class SessionMemory:
    def __init__(self, table_name: str, ttl_days: int = 90):
        """Initialize with DynamoDB table name"""
    
    def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Retrieve last N messages from session"""
    
    def save_message(
        self,
        session_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Save message to DynamoDB with TTL"""
    
    def inject_context_in_prompt(
        self,
        question: str,
        session_id: str,
        context_limit: int = 10
    ) -> str:
        """Enhance prompt with conversation history"""
    
    def clear_session(self, session_id: str) -> bool:
        """Delete all messages for a session"""
```

### Integration in WebSocket Handler

**File:** `/infrastructure/lambdas/websocket-handler/message_handler.py`

**Workflow:**

1. **Initialize session memory:**
   ```python
   session_memory = SessionMemory(CONVERSATION_TABLE)
   ```

2. **Retrieve and inject context:**
   ```python
   enhanced_question = session_memory.inject_context_in_prompt(
       question, session_id, context_limit=10
   )
   ```

3. **Stream response:**
   ```python
   full_response = stream_with_filtering(
       apigw, connection_id, enhanced_question, session_id, tenant_context
   )
   ```

4. **Save conversation:**
   ```python
   # Save user message
   session_memory.save_message(
       session_id=session_id,
       role='user',
       content=question,
       user_id=user_id,
       tenant_id=tenant_id
   )
   
   # Save assistant response
   session_memory.save_message(
       session_id=session_id,
       role='assistant',
       content=full_response,
       user_id=user_id,
       tenant_id=tenant_id
   )
   ```

### Context Injection Format

**Input:**
```python
question = "What is my name?"
session_id = "session-123"
```

**Conversation History:**
```
[
  {"role": "user", "content": "My name is Alice"},
  {"role": "assistant", "content": "Nice to meet you, Alice!"}
]
```

**Enhanced Prompt:**
```
Previous conversation:
User: My name is Alice
Assistant: Nice to meet you, Alice!

Current question: What is my name?

Please answer the current question taking into account the previous conversation context.
```

---

## Configuration

### Environment Variables

**WebSocket Handler:**
- `CONVERSATION_TABLE`: DynamoDB table name
- `ENABLE_METADATA_FILTERING`: Enable/disable filtering (`true`/`false`)
- `STAGE`: Deployment stage (`dev`, `staging`, `prod`)

### IAM Permissions

**Lambda Role needs:**
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:UpdateItem"
  ],
  "Resource": [
    "arn:aws:dynamodb:us-east-1:708819485463:table/processapp-conversations-dev",
    "arn:aws:dynamodb:us-east-1:708819485463:table/processapp-conversations-dev/index/*"
  ]
}
```

**Already configured in:** `/infrastructure/lib/WebSocketStack.ts`

---

## Testing

### Manual Test with wscat

```bash
# Run test script
cd /Users/qohatpretel/Answering/kb-rag-agent
./test-data/scripts/test-session-memory-manual.sh
```

### Python Test Script

```bash
# Install websockets
pip3 install websockets

# Run automated test
python3 test-data/scripts/test-session-memory.py
```

### DynamoDB Query

**Check stored conversations:**
```bash
aws dynamodb query \
  --table-name processapp-conversations-dev \
  --key-condition-expression "sessionId = :sid" \
  --expression-attribute-values '{":sid":{"S":"session-123"}}' \
  --profile ans-super
```

**Query by user:**
```bash
aws dynamodb query \
  --table-name processapp-conversations-dev \
  --index-name UserIdIndex \
  --key-condition-expression "userId = :uid" \
  --expression-attribute-values '{":uid":{"S":"user123"}}' \
  --profile ans-super
```

**Scan all conversations (dev only):**
```bash
aws dynamodb scan \
  --table-name processapp-conversations-dev \
  --limit 10 \
  --profile ans-super
```

---

## Performance

### Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Context retrieval time | ~50ms | Query with limit 10 |
| Message save time | ~20ms | Single PutItem operation |
| Memory overhead | ~2KB | Per conversation turn |
| DynamoDB capacity | On-demand | Auto-scales with load |

### Optimizations

1. **Limit context history:** Default 10 messages (configurable)
2. **Use GSI for user queries:** Faster than full table scan
3. **TTL for automatic cleanup:** No manual deletion needed
4. **Batch writes:** When saving multiple messages (not yet implemented)

---

## Best Practices

### Session Management

**Do:**
- Generate unique session IDs for new conversations
- Reuse session ID for related follow-up questions
- Set reasonable context limits (5-10 messages)
- Include userId and tenantId for multi-tenant isolation

**Don't:**
- Share session IDs across different users
- Keep session IDs indefinitely (90 day TTL applies)
- Store sensitive information in conversation history
- Exceed DynamoDB throughput limits with excessive writes

### Context Injection

**Effective Context:**
```
User: I'm working on project 123 for Colpensiones
Assistant: Great! I can help with project 123.
User: What's the budget?
```
→ Agent knows which project to query

**Ineffective Context:**
```
User: What's the budget?
```
→ Agent doesn't know which project

### Memory Limits

- **Context window:** Last 10 messages (default)
- **Message size:** Up to 400KB per DynamoDB item
- **Session duration:** No hard limit, TTL handles cleanup
- **Concurrent sessions:** Unlimited per user

---

## Troubleshooting

### Issue: Agent doesn't remember context

**Cause:** Session ID not consistent between messages

**Fix:** Ensure client reuses the same session ID for related questions
```python
# WRONG: New session ID each time
session_id = str(uuid.uuid4())  # Different for each message

# CORRECT: Reuse session ID
session_id = "session-123"  # Same for all messages in conversation
```

### Issue: Context injection not working

**Cause:** CONVERSATION_TABLE environment variable not set

**Fix:** Check Lambda configuration
```bash
aws lambda get-function-configuration \
  --function-name processapp-ws-message-dev \
  --query 'Environment.Variables.CONVERSATION_TABLE' \
  --profile ans-super
```

Should return: `processapp-conversations-dev`

### Issue: DynamoDB write errors

**Cause:** IAM permissions missing

**Fix:** Verify Lambda role has DynamoDB permissions
```bash
aws iam get-role-policy \
  --role-name processapp-ws-handler-role-dev \
  --policy-name ConversationTablePolicy \
  --profile ans-super
```

### Issue: Old conversations not deleted

**Cause:** TTL not enabled or configured incorrectly

**Fix:** Verify TTL attribute
```bash
aws dynamodb describe-time-to-live \
  --table-name processapp-conversations-dev \
  --profile ans-super
```

Should return: `AttributeName: expirationTime, Status: ENABLED`

---

## Cost Estimate

**Monthly Cost (1000 users, 50 messages/user/month):**

| Resource | Usage | Cost |
|----------|-------|------|
| DynamoDB Write Units | 50K writes | ~$0.25 |
| DynamoDB Read Units | 50K reads | ~$0.13 |
| DynamoDB Storage | ~500MB | ~$0.13 |
| **Total** | | **~$0.51/month** |

**Note:** DynamoDB on-demand pricing scales automatically. No pre-provisioning needed.

---

## Future Enhancements

### Planned Features

1. **Conversation Summarization:** Compress long conversations into summaries
2. **Multi-Session Linking:** Connect related sessions for same user
3. **Search Conversations:** Full-text search across conversation history
4. **Analytics:** Conversation metrics and insights
5. **Export:** Download conversation history as JSON/CSV

### Phase 2 Migration

Replace DynamoDB-based memory with **Bedrock CfnMemory** (native agent memory):
- Automatic conversation summarization
- Better integration with agent reasoning
- Reduced latency (no external DB query)
- Simplified architecture

---

## Resources

**AWS Documentation:**
- [DynamoDB TTL](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [DynamoDB GSI](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html)
- [Lambda with DynamoDB](https://docs.aws.amazon.com/lambda/latest/dg/with-ddb.html)

**Project Files:**
- Session Memory Module: `/infrastructure/lambdas/websocket-handler/session_memory.py`
- Message Handler: `/infrastructure/lambdas/websocket-handler/message_handler.py`
- Stack Definition: `/infrastructure/lib/SessionMemoryStack.ts`
- Test Scripts: `/test-data/scripts/test-session-memory*.py`

---

**Last Updated:** 2026-04-26  
**Status:** Deployed and operational  
**DynamoDB Table:** `processapp-conversations-dev`
