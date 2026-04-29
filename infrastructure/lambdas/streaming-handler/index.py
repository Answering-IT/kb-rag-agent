import boto3
import json
import os
from io import BytesIO

# Config
RUNTIME_ID = os.environ['AGENT_ID']
RUNTIME_ARN = f"arn:aws:bedrock-agentcore:{os.environ.get('AWS_REGION', 'us-east-1')}:{os.environ['AWS_ACCOUNT_ID']}:runtime/{RUNTIME_ID}"

# Client
client = boto3.client('bedrock-agentcore', region_name=os.environ.get('AWS_REGION', 'us-east-1'))


class StreamingBody:
    """
    Wrapper for streaming response body
    Implements iterator protocol for Lambda Response Streaming
    """
    def __init__(self, agent_response, session_id, prompt):
        self.agent_response = agent_response
        self.session_id = session_id
        self.prompt = prompt

    def __iter__(self):
        """Iterate over response chunks"""
        try:
            for line in self.agent_response.get('response').iter_lines():
                if line:
                    text = line.decode('utf-8')

                    # Remove "data: " prefix if present
                    if text.startswith('data: '):
                        text = text[6:]

                    # Try parse as JSON, extract chunk text
                    try:
                        data = json.loads(text)
                        if data.get('type') == 'chunk':
                            chunk_text = data.get('data', '')
                            if chunk_text:
                                yield chunk_text.encode('utf-8')
                    except:
                        # Plain text
                        if text.strip():
                            yield text.encode('utf-8')
        except Exception as e:
            yield f"Error: {str(e)}".encode('utf-8')


def lambda_handler(event, context):
    """
    Lambda Response Streaming handler
    Returns StreamingBody for RESPONSE_STREAM mode
    """
    # Parse body
    body = json.loads(event.get("body", "{}"))
    prompt = body.get("prompt", body.get("question", "Hola"))
    session_id = body.get("sessionId", body.get("session_id", "550e8400-e29b-41d4-a716-446655440000"))

    try:
        # Invoke agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn=RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=json.dumps({'inputText': prompt, 'sessionId': session_id}).encode('utf-8')
        )

        # Return streaming response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/plain',
                'Cache-Control': 'no-cache'
            },
            'body': StreamingBody(response, session_id, prompt)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/plain'},
            'body': f'Error: {str(e)}'
        }
