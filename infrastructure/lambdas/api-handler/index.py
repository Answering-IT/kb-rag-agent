"""
API Handler Lambda
Exposes Bedrock Agent via HTTP endpoint with multi-tenant metadata filtering
"""

import json
import os
import boto3
import uuid
from typing import Dict, Any

# Import metadata filter
from metadata_filter import TenantContext

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Environment variables
AGENT_ID = os.environ['AGENT_ID']
AGENT_ALIAS_ID = os.environ['AGENT_ALIAS_ID']
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')
FOUNDATION_MODEL = os.environ.get('FOUNDATION_MODEL', 'amazon.nova-pro-v1:0')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
STAGE = os.environ['STAGE']
ENABLE_FILTERING = os.environ.get('ENABLE_METADATA_FILTERING', 'true').lower() == 'true'


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gateway Lambda handler with multi-tenant filtering

    Expected request headers:
    - x-tenant-id: Tenant/organization ID (REQUIRED if filtering enabled)
    - x-user-id: User identifier
    - x-user-roles: JSON array of user roles

    Expected request body:
    {
        "question": "What documents do you have?",
        "sessionId": "optional-session-id",
        "projectId": "optional-project-id",
        "allowedUsers": ["optional", "user", "list"]
    }

    Response:
    {
        "answer": "I have documents about...",
        "sessionId": "session-123",
        "status": "success"
    }
    """
    print(f'Received event: {json.dumps(event)}')

    # Handle OPTIONS for CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {'message': 'OK'})

    # Parse request
    try:
        headers = event.get('headers', {})
        body = json.loads(event.get('body', '{}'))
        question = body.get('question')
        session_id = body.get('sessionId', str(uuid.uuid4()))

        if not question:
            return cors_response(400, {
                'error': 'Missing required field: question',
                'status': 'error'
            })

        print(f'Processing question: {question}')
        print(f'Session ID: {session_id}')

    except json.JSONDecodeError as e:
        return cors_response(400, {
            'error': f'Invalid JSON: {str(e)}',
            'status': 'error'
        })

    # Extract tenant context for filtering
    tenant_context = None
    kb_filter = None

    if ENABLE_FILTERING:
        try:
            tenant_context = TenantContext.from_headers(headers, body)

            if not tenant_context.tenant_id:
                return cors_response(400, {
                    'error': 'Missing required header: x-tenant-id',
                    'status': 'error'
                })

            # Build KB filter
            kb_filter = tenant_context.build_kb_filter()
            print(f'Tenant context: {json.dumps(tenant_context.to_dict())}')
            print(f'KB filter: {json.dumps(kb_filter)}')

        except Exception as e:
            print(f'Error building tenant filter: {str(e)}')
            return cors_response(400, {
                'error': f'Invalid tenant context: {str(e)}',
                'status': 'error'
            })

    # Invoke Bedrock Agent with filtering
    try:
        if ENABLE_FILTERING and kb_filter and KNOWLEDGE_BASE_ID:
            # Use retrieve_and_generate with metadata filtering
            print('Using retrieve_and_generate with metadata filtering')
            response = bedrock_agent_runtime.retrieve_and_generate(
                input={'text': question},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                        'modelArn': f'arn:aws:bedrock:{REGION}::foundation-model/{FOUNDATION_MODEL}',
                        'retrievalConfiguration': {
                            'vectorSearchConfiguration': {
                                'numberOfResults': 5,
                                'overrideSearchType': 'SEMANTIC',  # S3_VECTORS only supports SEMANTIC
                                'filter': kb_filter  # NATIVE METADATA FILTERING
                            }
                        }
                    }
                }
                # sessionConfiguration omitted - not needed
            )

            answer = response.get('output', {}).get('text', '')
            session_id = response.get('sessionId', session_id)

        else:
            # Fallback to invoke_agent (no filtering)
            print('Using invoke_agent (no filtering)')
            response = bedrock_agent_runtime.invoke_agent(
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                sessionId=session_id,
                inputText=question
            )

            # Process response stream
            answer = ""
            for event_chunk in response['completion']:
                if 'chunk' in event_chunk:
                    chunk = event_chunk['chunk']
                    if 'bytes' in chunk:
                        answer += chunk['bytes'].decode('utf-8')

        print(f'Generated answer: {answer[:100]}...')

        return cors_response(200, {
            'answer': answer,
            'sessionId': session_id,
            'status': 'success'
        })

    except Exception as e:
        print(f'Error invoking agent: {str(e)}')
        import traceback
        print(f'Traceback: {traceback.format_exc()}')
        return cors_response(500, {
            'error': f'Agent invocation failed: {str(e)}',
            'status': 'error'
        })


def cors_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create API Gateway response with CORS headers
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Configure as needed
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,x-tenant-id,x-user-id,x-user-roles',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
