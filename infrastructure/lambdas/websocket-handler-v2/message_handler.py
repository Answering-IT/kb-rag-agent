"""
WebSocket Message Handler - Agent Core Runtime V2
Invokes the Agent Core Runtime via AWS SDK
"""

import json
import os
import boto3
import uuid
from typing import Dict, Any

# AWS clients
apigw_client = None  # Will be initialized per request
agent_core_client = None  # Will be initialized on first use

# Environment variables
RUNTIME_ID = os.environ.get('RUNTIME_ID', '')
REGION = os.environ.get('AWS_REGION', 'us-east-1')
STAGE = os.environ['STAGE']

# Construct runtime ARN
RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{REGION}:{os.environ.get('AWS_ACCOUNT_ID', '708819485463')}:runtime/{RUNTIME_ID}"

print(f'[Init] Runtime ID: {RUNTIME_ID}')
print(f'[Init] Region: {REGION}')
print(f'[Init] Runtime ARN: {RUNTIME_ARN}')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    WebSocket message handler - invokes Agent Core Runtime
    """
    print(f'[Handler] Received event: {json.dumps(event, default=str)}')

    # Extract connection info
    connection_id = event['requestContext']['connectionId']
    domain_name = event['requestContext']['domainName']
    stage = event['requestContext']['stage']

    # Create API Gateway Management API client
    global apigw_client
    apigw_client = boto3.client(
        'apigatewaymanagementapi',
        endpoint_url=f'https://{domain_name}/{stage}'
    )

    try:
        # Parse message body - handle {action, data} structure
        raw_body = json.loads(event.get('body', '{}'))

        # Check if it's wrapped in data object (websocket format)
        if 'data' in raw_body and isinstance(raw_body['data'], dict):
            body = raw_body['data']
        else:
            body = raw_body

        question = body.get('question') or body.get('inputText') or body.get('prompt', 'Hello')
        session_id = body.get('sessionId', str(uuid.uuid4()))

        # Ensure session ID is at least 33 characters (AWS requirement)
        # Use deterministic padding to maintain consistency across connections
        if len(session_id) < 33:
            # Pad with zeros to reach 33 characters (deterministic)
            session_id = session_id + ('-' * (33 - len(session_id)))

        # Extract metadata for KB filtering (snake_case for AWS Bedrock)
        # Core identifiers
        tenant_id = body.get('tenant_id') or body.get('tenantId')
        project_id = body.get('project_id') or body.get('projectId')
        task_id = body.get('task_id') or body.get('taskId')
        subtask_id = body.get('subtask_id') or body.get('subtaskId')

        # Access control
        user_id = body.get('user_id') or body.get('userId')
        user_roles = body.get('user_roles') or body.get('roles') or body.get('userRoles')
        users = body.get('users')
        team_ids = body.get('team_ids') or body.get('teamIds')

        # Knowledge classification
        knowledge_type = body.get('knowledge_type') or body.get('knowledgeType')

        # Document metadata
        attachment_id = body.get('attachment_id') or body.get('attachmentId')
        attachment_type = body.get('attachment_type') or body.get('attachmentType')
        org_document_type = body.get('org_document_type') or body.get('orgDocumentType')
        org_document_sub_type = body.get('org_document_sub_type') or body.get('orgDocumentSubType')
        partition_type = body.get('partition_type') or body.get('partitionType')

        # Complex fields
        task_names = body.get('task_names') or body.get('taskNames')
        user_access_chain = body.get('user_access_chain') or body.get('userAccessChain')

        # Additional custom filters
        metadata = body.get('metadata', {})

        print(f'[Handler] Question: {question}')
        print(f'[Handler] Session: {session_id}')
        print(f'[Handler] Metadata: tenant={tenant_id}, project={project_id}, task={task_id}, '
              f'knowledge_type={knowledge_type}, partition={partition_type}, roles={user_roles}')

        # Send acknowledgment
        send_to_client(connection_id, {
            'type': 'status',
            'message': 'Processing your request...',
            'sessionId': session_id
        })

        # Initialize Bedrock Agent Core client
        global agent_core_client
        if agent_core_client is None:
            agent_core_client = boto3.client('bedrock-agentcore', region_name=REGION)

        print(f'[Handler] Invoking Agent Core Runtime via SDK')
        print(f'[Handler] Runtime ARN: {RUNTIME_ARN}')
        print(f'[Handler] Session ID: {session_id}')

        # Prepare payload for runtime (include metadata for KB filtering in snake_case)
        payload_data = {
            'inputText': question,
            'sessionId': session_id
        }

        # Add metadata if present (for KB filtering - using snake_case for AWS Bedrock)
        # Core identifiers
        if tenant_id:
            payload_data['tenant_id'] = tenant_id
        if project_id:
            payload_data['project_id'] = project_id
        if task_id:
            payload_data['task_id'] = task_id
        if subtask_id:
            payload_data['subtask_id'] = subtask_id

        # Access control
        if user_id:
            payload_data['user_id'] = user_id
        if user_roles:
            payload_data['user_roles'] = user_roles
        if users:
            payload_data['users'] = users
        if team_ids:
            payload_data['team_ids'] = team_ids

        # Knowledge classification
        if knowledge_type:
            payload_data['knowledge_type'] = knowledge_type

        # Document metadata
        if attachment_id:
            payload_data['attachment_id'] = attachment_id
        if attachment_type:
            payload_data['attachment_type'] = attachment_type
        if org_document_type:
            payload_data['org_document_type'] = org_document_type
        if org_document_sub_type:
            payload_data['org_document_sub_type'] = org_document_sub_type
        if partition_type:
            payload_data['partition_type'] = partition_type

        # Complex fields
        if task_names:
            payload_data['task_names'] = task_names
        if user_access_chain:
            payload_data['user_access_chain'] = user_access_chain

        # Additional custom filters
        if metadata:
            payload_data['metadata'] = metadata

        payload = json.dumps(payload_data).encode('utf-8')
        print(f'[Handler] Payload keys: {list(payload_data.keys())}')

        try:
            # Invoke Agent Core Runtime via AWS SDK
            response = agent_core_client.invoke_agent_runtime(
                agentRuntimeArn=RUNTIME_ARN,
                runtimeSessionId=session_id,
                payload=payload
            )

            print(f'[Handler] Runtime invocation successful')

            # Process streaming response
            # Response format: text/event-stream with "data: " prefixed lines
            content_type = response.get('contentType', '')
            print(f'[Handler] Response content type: {content_type}')

            # Read the streaming body
            response_body = response.get('response')

            if response_body:
                # Process the response stream
                full_response = ""

                # Read all data from stream
                for line in response_body.iter_lines():
                    if line:
                        line_str = line.decode('utf-8') if isinstance(line, bytes) else line

                        # Handle event-stream format (data: prefix)
                        if line_str.startswith('data: '):
                            line_str = line_str[6:]  # Remove "data: " prefix

                        try:
                            # Try to parse as JSON
                            chunk_data = json.loads(line_str)

                            # Forward to client
                            print(f'[Handler] Forwarding chunk: {chunk_data.get("type", "unknown")}')
                            send_to_client(connection_id, chunk_data)

                            # Accumulate text
                            if chunk_data.get('type') == 'chunk':
                                full_response += chunk_data.get('data', '')

                        except json.JSONDecodeError:
                            # Plain text response
                            print(f'[Handler] Plain text chunk: {line_str[:50]}...')
                            send_to_client(connection_id, {
                                'type': 'chunk',
                                'data': line_str
                            })
                            full_response += line_str

                print(f'[Handler] Response complete (length: {len(full_response)})')

            else:
                print(f'[Handler] No response body received')
                send_to_client(connection_id, {
                    'type': 'error',
                    'message': 'No response from agent'
                })

        except Exception as e:
            print(f'[Handler] Error invoking runtime: {str(e)}')
            import traceback
            print(f'[Handler] Traceback: {traceback.format_exc()}')

            # Send error to client
            send_to_client(connection_id, {
                'type': 'error',
                'message': f'Failed to invoke agent: {str(e)}'
            })
            raise

        print('[Handler] Response complete')

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }

    except Exception as e:
        print(f'[Handler] Error: {str(e)}')
        error_msg = {
            'type': 'error',
            'message': str(e)
        }
        try:
            send_to_client(connection_id, error_msg)
        except:
            pass

        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def send_to_client(connection_id: str, data: Dict[str, Any]):
    """Send message to WebSocket client"""
    try:
        apigw_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(data).encode('utf-8')
        )
    except apigw_client.exceptions.GoneException:
        print(f'[Handler] Connection {connection_id} is gone')
    except Exception as e:
        print(f'[Handler] Error sending to client: {e}')
        raise
