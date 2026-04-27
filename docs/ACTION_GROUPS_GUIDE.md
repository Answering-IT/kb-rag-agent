# Action Groups Guide

**Date:** 2026-04-26  
**Status:** ✅ **DEPLOYED AND OPERATIONAL**  
**Lambda ARN:** `arn:aws:lambda:us-east-1:708819485463:function:processapp-get-project-info-dev`

---

## Overview

Action groups allow the Bedrock Agent to call external APIs and services. Currently implemented: `GetProjectInfo` tool to retrieve project information from ECS service.

### Benefits

- **Extended Capabilities:** Agent can access live data from external systems
- **Real-time Information:** Get current project status, budget, and users
- **Tool Orchestration:** Agent decides when to use tools based on user questions
- **Scalable:** Easy to add more tools (GetUserInfo, GetDocumentStatus, etc.)

---

## Action Group: GetProjectInfo

**Purpose:** Retrieve project information from ECS service API

**Endpoint:** `GET /organization/{orgId}/projects/{projectId}`

**ECS Base URL:** `https://dev.app.colpensiones.procesapp.com`

### OpenAPI Schema (Embedded)

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Project Information API",
    "version": "1.0.0"
  },
  "paths": {
    "/organization/{orgId}/projects/{projectId}": {
      "get": {
        "operationId": "getProjectInfo",
        "parameters": [
          {
            "name": "orgId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          },
          {
            "name": "projectId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ]
      }
    }
  }
}
```

---

## Testing the Action Group

### Test with Agent SDK

```python
import boto3
import uuid

bedrock = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock.invoke_agent(
    agentId='QWTVV3BY3G',
    agentAliasId='QZITGFMONE',
    sessionId=str(uuid.uuid4()),
    inputText='What is the budget for project 123 in organization 1?'
)

# Agent will automatically call GetProjectInfo tool
for event in response['completion']:
    if 'chunk' in event:
        print(event['chunk']['bytes'].decode('utf-8'), end='', flush=True)
```

### Expected Behavior

**User asks:** "What is the budget for project 123?"

**Agent flow:**
1. Determines it needs project information
2. Calls GetProjectInfo Lambda with orgId=1, projectId=123
3. Lambda calls ECS endpoint
4. Lambda returns project data
5. Agent incorporates data into natural language response

**Agent responds:** "The budget for project 123 is $50,000. The project is currently active and has 5 users assigned."

---

## Lambda Implementation

**File:** `/infrastructure/lambdas/agent-tools/get_project_info.py`

**Key Components:**

```python
def handler(event, context):
    """
    Event format from Bedrock Agent:
    {
      "apiPath": "/organization/{orgId}/projects/{projectId}",
      "httpMethod": "GET",
      "parameters": [
        {"name": "orgId", "value": "1"},
        {"name": "projectId", "value": "123"}
      ]
    }
    """
    # Extract parameters
    params = {p['name']: p['value'] for p in event['parameters']}
    url = f"{ECS_BASE_URL}/organization/{params['orgId']}/projects/{params['projectId']}"
    
    # Call ECS service
    response = http.request('GET', url)
    
    # Return in Bedrock Agent format
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'GetProjectInfo',
            'httpStatusCode': response.status,
            'responseBody': {
                'application/json': {
                    'body': response.data.decode('utf-8')
                }
            }
        }
    }
```

**Dependencies:**
- `urllib3` (built-in to Python 3.11 Lambda runtime)

**Environment Variables:**
- `ECS_BASE_URL`: Base URL for ECS service
- `STAGE`: Deployment stage (dev, staging, prod)

---

## IAM Permissions

### Agent Role Permissions

Agent role (`processapp-agent-role-dev`) has permission to invoke the Lambda:

```typescript
agentRole.addToPolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: ['lambda:InvokeFunction'],
  resources: [getProjectInfoTool.functionArn],
}));
```

### Lambda Permissions

Lambda has permission to be invoked by Bedrock:

```typescript
getProjectInfoTool.addPermission('BedrockInvoke', {
  principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
  action: 'lambda:InvokeFunction',
  sourceAccount: accountId,
  sourceArn: `arn:aws:bedrock:${region}:${accountId}:agent/*`,
});
```

---

## Monitoring & Debugging

### CloudWatch Logs

**Lambda Logs:**
```bash
aws logs tail /aws/lambda/processapp-get-project-info-dev --follow --profile ans-super
```

**Agent Logs:**
```bash
aws logs tail /aws/bedrock/agents/QWTVV3BY3G --follow --profile ans-super
```

### Debugging Action Group Execution

Check logs for:
- `Received event:` - Shows parameters passed from agent
- `Calling ECS endpoint:` - Shows URL being called
- `ECS response status:` - HTTP status code from ECS
- `ECS response body:` - Data returned from ECS

**Common Issues:**

| Issue | Symptom | Fix |
|-------|---------|-----|
| Lambda timeout | Agent gets partial response | Increase Lambda timeout |
| ECS endpoint down | Agent says "cannot retrieve information" | Check ECS service status |
| Invalid parameters | Lambda error in logs | Validate agent is extracting correct values |
| IAM permissions | Agent cannot invoke Lambda | Check agent role policy |

---

## Adding More Action Groups

To add another tool (e.g., GetUserInfo):

1. **Create Lambda function:**
   ```bash
   cp get_project_info.py get_user_info.py
   # Modify handler logic
   ```

2. **Update AgentStack.ts:**
   ```typescript
   actionGroups: [
     { /* GetProjectInfo */ },
     {
       actionGroupName: 'GetUserInfo',
       description: 'Retrieve user information',
       actionGroupState: 'ENABLED',
       actionGroupExecutor: { lambda: getUserInfoTool.functionArn },
       apiSchema: { payload: JSON.stringify({...}) }
     }
   ]
   ```

3. **Deploy:**
   ```bash
   npx cdk deploy dev-us-east-1-agent --profile ans-super
   ```

---

## Performance

| Metric | Target | Current |
|--------|--------|---------|
| Lambda Cold Start | <1s | ~600ms |
| Lambda Warm Execution | <200ms | ~100ms |
| ECS API Response Time | <500ms | Depends on ECS |
| Total Tool Execution | <1.5s | ~700ms |

---

## Cost Estimate

**Monthly Cost (1000 tool calls):**

| Resource | Usage | Cost |
|----------|-------|------|
| Lambda Invocations | 1000 calls | <$1 |
| Lambda Duration | 1000 × 100ms | <$1 |
| Agent Tool Orchestration | 1000 calls | Included in agent cost |
| **Total** | | **<$2/month** |

---

## Next Steps

### Planned Action Groups

1. **GetUserInfo** - Retrieve user profile and permissions
2. **GetDocumentStatus** - Check document processing status
3. **SearchProjects** - Search projects by criteria
4. **UpdateProjectStatus** - Update project status (write operation)

### Enhancements

1. **Caching** - Cache ECS responses to reduce latency
2. **Retry Logic** - Automatic retry on ECS failures
3. **Rate Limiting** - Protect ECS from overload
4. **Authentication** - Add OAuth/JWT for ECS API calls

---

## Resources

**AWS Documentation:**
- [Bedrock Agent Action Groups](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-action.html)
- [Lambda Functions](https://docs.aws.amazon.com/lambda/latest/dg/welcome.html)

**Project Files:**
- Lambda Code: `/infrastructure/lambdas/agent-tools/get_project_info.py`
- Stack Definition: `/infrastructure/lib/AgentStack.ts`
- OpenAPI Schema: Embedded in AgentStack.ts

---

**Last Updated:** 2026-04-26  
**Status:** Deployed and operational  
**Lambda:** `processapp-get-project-info-dev`
