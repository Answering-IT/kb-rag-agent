"""
WebSocket Message Handler - Bedrock Agent Streaming
Handles incoming WebSocket messages and streams Bedrock Agent responses in real-time
"""

import json
import os
import boto3
import uuid
from typing import Dict, Any

# Import session memory module
from session_memory import SessionMemory

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
CONVERSATION_TABLE = os.environ.get('CONVERSATION_TABLE', '')

# Initialize session memory (if table is configured)
session_memory = SessionMemory(CONVERSATION_TABLE) if CONVERSATION_TABLE else None


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    WebSocket message handler with Bedrock Agent streaming

    Expected message format:
    {
        "action": "query",
        "question": "What is Colpensiones?",
        "sessionId": "optional-session-id",
        "tenantId": "1",
        "userId": "user123",
        "roles": ["viewer"],
        "projectId": "100",
        "users": ["user123"]
    }

    Streams response chunks to WebSocket connection:
    {
        "type": "chunk",
        "data": "text chunk...",
        "sessionId": "session-123"
    }

    Final message:
    {
        "type": "complete",
        "sessionId": "session-123",
        "totalChunks": 10
    }
    """
    print(f'Received WebSocket event: {json.dumps(event)}')

    # Extract connection info
    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']

    # Create API Gateway Management API client for sending messages
    apigw = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{domain_name}/{stage}'
    )

    try:
        # Parse message body
        body = json.loads(event.get('body', '{}'))

        action = body.get('action', 'query')
        question = body.get('question')
        session_id = body.get('sessionId', str(uuid.uuid4()))

        if not question:
            send_error(apigw, connection_id, 'Missing required field: question')
            return {'statusCode': 400}

        print(f'Processing question: {question}')
        print(f'Session ID: {session_id}')
        print(f'Connection ID: {connection_id}')

        # Extract tenant context for filtering
        tenant_context = extract_tenant_context(body)

        if ENABLE_FILTERING and not tenant_context.get('tenant_id'):
            send_error(apigw, connection_id, 'Missing required field: tenantId')
            return {'statusCode': 400}

        # Send acknowledgment
        send_message(apigw, connection_id, {
            'type': 'status',
            'message': 'Processing your question...',
            'sessionId': session_id
        })

        # Inject conversation context if session memory is enabled
        enhanced_question = question
        if session_memory:
            enhanced_question = session_memory.inject_context_in_prompt(
                question, session_id, context_limit=10
            )
            print(f'Enhanced question with context: {enhanced_question[:200]}...')

        # Stream response from Bedrock Agent
        # Note: retrieve_and_generate (filtering) cannot use action groups
        # invoke_agent (no filtering) can use action groups but doesn't filter
        # For now, we prioritize action groups over filtering
        full_response = ""

        # Check if question might need action groups (project info queries)
        needs_action_group = any(keyword in question.lower() for keyword in [
            'proyecto', 'project', 'presupuesto', 'budget', 'estado', 'status',
            'usuarios asignados', 'assigned users', 'id 1', 'id 2', 'id 3'
        ])

        if needs_action_group:
            # Use invoke_agent to enable action groups (no filtering)
            print(f'Using invoke_agent (action groups enabled, no filtering)')
            full_response = stream_from_agent(
                apigw, connection_id, enhanced_question, session_id
            )
        elif ENABLE_FILTERING and KNOWLEDGE_BASE_ID:
            # Use retrieve_and_generate with filtering (no action groups)
            full_response = stream_with_filtering(
                apigw, connection_id, enhanced_question, session_id, tenant_context
            )
        else:
            # Fallback to invoke_agent
            full_response = stream_from_agent(
                apigw, connection_id, enhanced_question, session_id
            )

        # Save conversation to DynamoDB
        if session_memory and full_response:
            user_id = tenant_context.get('user_id')
            tenant_id = tenant_context.get('tenant_id')

            # Save user message
            session_memory.save_message(
                session_id=session_id,
                role='user',
                content=question,  # Save original question, not enhanced
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

        return {'statusCode': 200}

    except Exception as e:
        print(f'Error processing message: {str(e)}')
        import traceback
        print(f'Traceback: {traceback.format_exc()}')

        try:
            send_error(apigw, connection_id, f'Error: {str(e)}')
        except:
            pass

        return {'statusCode': 500}


def stream_with_filtering(
    apigw, connection_id: str, question: str, session_id: str, tenant_context: Dict
) -> str:
    """
    Stream response from Bedrock KB with metadata filtering
    Uses retrieve_and_generate for native filtering

    Returns:
        Full response text for saving to session memory
    """
    print(f'Streaming with filtering - Tenant: {tenant_context.get("tenant_id")}')

    # Build KB filter
    kb_filter = build_kb_filter(tenant_context)
    print(f'KB filter: {json.dumps(kb_filter)}')

    try:
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
                            'overrideSearchType': 'SEMANTIC',
                            'filter': kb_filter
                        }
                    }
                }
            }
        )

        # retrieve_and_generate doesn't stream, so send as single chunk
        answer = response.get('output', {}).get('text', '')

        # Simulate streaming by sending in smaller chunks
        chunk_size = 100  # characters per chunk
        chunks = [answer[i:i+chunk_size] for i in range(0, len(answer), chunk_size)]

        for i, chunk in enumerate(chunks):
            send_message(apigw, connection_id, {
                'type': 'chunk',
                'data': chunk,
                'sessionId': session_id,
                'chunkIndex': i
            })

        # Send completion
        send_message(apigw, connection_id, {
            'type': 'complete',
            'sessionId': session_id,
            'totalChunks': len(chunks)
        })

        return answer  # Return full response for session memory

    except Exception as e:
        print(f'Error in streaming with filtering: {str(e)}')
        send_error(apigw, connection_id, f'Filtering error: {str(e)}')
        raise


def stream_from_agent(apigw, connection_id: str, question: str, session_id: str) -> str:
    """
    Stream response from Bedrock Agent (without filtering)
    Uses invoke_agent for true streaming

    Returns:
        Full response text for saving to session memory
    """
    print(f'Streaming from agent without filtering')

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=question,
            enableTrace=False  # Disable trace to reduce overhead
        )

        # Stream response chunks
        full_response = ""
        chunk_index = 0
        for event_chunk in response['completion']:
            if 'chunk' in event_chunk:
                chunk = event_chunk['chunk']
                if 'bytes' in chunk:
                    text = chunk['bytes'].decode('utf-8')
                    full_response += text

                    send_message(apigw, connection_id, {
                        'type': 'chunk',
                        'data': text,
                        'sessionId': session_id,
                        'chunkIndex': chunk_index
                    })

                    chunk_index += 1

        # Send completion
        send_message(apigw, connection_id, {
            'type': 'complete',
            'sessionId': session_id,
            'totalChunks': chunk_index
        })

        return full_response  # Return full response for session memory

    except Exception as e:
        print(f'Error in streaming from agent: {str(e)}')
        send_error(apigw, connection_id, f'Agent error: {str(e)}')
        raise


def build_kb_filter(tenant_context: Dict) -> Dict[str, Any]:
    """
    Build Bedrock KB filter from tenant context
    """
    filter_obj = {'andAll': []}

    # 1. Tenant must match (REQUIRED)
    tenant_id = tenant_context.get('tenant_id')
    if tenant_id:
        filter_obj['andAll'].append({
            'equals': {'key': 'tenant_id', 'value': str(tenant_id)}
        })

    # 2. Roles filtering
    roles = tenant_context.get('roles', [])
    if roles:
        role_conditions = [
            {'equals': {'key': 'roles', 'value': role}}
            for role in roles
        ]
        role_conditions.append({'equals': {'key': 'roles', 'value': '*'}})

        filter_obj['andAll'].append({
            'orAll': role_conditions
        })

    # 3. Project filtering
    project_id = tenant_context.get('project_id')
    if project_id:
        filter_obj['andAll'].append({
            'orAll': [
                {'equals': {'key': 'project_id', 'value': str(project_id)}},
                {'equals': {'key': 'project_id', 'value': '*'}}
            ]
        })

    # 4. User list filtering
    users = tenant_context.get('users', [])
    if users:
        user_conditions = [
            {'equals': {'key': 'users', 'value': user}}
            for user in users
        ]
        user_conditions.append({'equals': {'key': 'users', 'value': '*'}})

        filter_obj['andAll'].append({
            'orAll': user_conditions
        })

    return filter_obj


def extract_tenant_context(body: Dict) -> Dict[str, Any]:
    """
    Extract tenant context from WebSocket message body
    """
    return {
        'tenant_id': body.get('tenantId'),
        'user_id': body.get('userId'),
        'roles': body.get('roles', []),
        'project_id': body.get('projectId'),
        'users': body.get('users', []),
    }


def send_message(apigw, connection_id: str, message: Dict):
    """
    Send message to WebSocket connection
    """
    try:
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message).encode('utf-8')
        )
    except apigw.exceptions.GoneException:
        print(f'Connection {connection_id} is gone')
    except Exception as e:
        print(f'Error sending message to {connection_id}: {str(e)}')
        raise


def send_error(apigw, connection_id: str, error_message: str):
    """
    Send error message to WebSocket connection
    """
    send_message(apigw, connection_id, {
        'type': 'error',
        'error': error_message
    })
