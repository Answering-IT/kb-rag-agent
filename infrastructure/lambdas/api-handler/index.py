"""
API Handler Lambda
Exposes Bedrock Agent via HTTP endpoint
"""

import json
import os
import boto3
import uuid
from typing import Dict, Any

# AWS clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Environment variables
AGENT_ID = os.environ['AGENT_ID']
AGENT_ALIAS_ID = os.environ['AGENT_ALIAS_ID']
STAGE = os.environ['STAGE']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gateway Lambda handler

    Expected request body:
    {
        "question": "What documents do you have?",
        "sessionId": "optional-session-id"
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

    # Parse request body
    try:
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

    # Invoke Bedrock Agent
    try:
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
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps(body)
    }
