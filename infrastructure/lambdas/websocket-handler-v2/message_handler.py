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
        # Parse message body
        body = json.loads(event.get('body', '{}'))
        question = body.get('question') or body.get('inputText') or body.get('prompt', 'Hello')
        session_id = body.get('sessionId', str(uuid.uuid4()))

        # Ensure session ID is at least 33 characters (AWS requirement)
        if len(session_id) < 33:
            session_id = f"{session_id}-{str(uuid.uuid4())}"

        print(f'[Handler] Question: {question}')
        print(f'[Handler] Session: {session_id}')

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

        # Prepare payload for runtime
        payload = json.dumps({
            'inputText': question,
            'sessionId': session_id
        }).encode('utf-8')

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
