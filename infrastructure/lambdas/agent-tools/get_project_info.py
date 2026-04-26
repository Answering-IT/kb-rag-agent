"""
Agent Action Group: Get Project Info
Calls ECS service to retrieve project information
"""

import json
import urllib3
from typing import Dict, Any

# HTTP client
http = urllib3.PoolManager()

# ECS service endpoint
BASE_URL = 'https://dev.app.colpensiones.procesapp.com'


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Called by Bedrock Agent via action group execution

    Event format from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "actionGroup": "GetProjectInfo",
        "apiPath": "/getProjectInfo",
        "httpMethod": "POST",
        "requestBody": {
            "content": {
                "application/json": {
                    "properties": [
                        {"name": "orgId", "type": "string", "value": "1"},
                        {"name": "projectId", "type": "string", "value": "123"}
                    ]
                }
            }
        }
    }

    Returns:
    {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "GetProjectInfo",
            "apiPath": "/getProjectInfo",
            "httpMethod": "POST",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": "..."
                }
            }
        }
    }
    """
    print(f'Received event: {json.dumps(event)}')

    try:
        # Extract parameters from request body
        request_body = event.get('requestBody', {})
        content = request_body.get('content', {})
        app_json = content.get('application/json', {})
        properties = app_json.get('properties', [])

        # Convert properties list to dict
        params_dict = {p['name']: p['value'] for p in properties}

        org_id = params_dict.get('orgId')
        project_id = params_dict.get('projectId')

        if not org_id or not project_id:
            return create_error_response(
                event,
                400,
                'Missing required parameters: orgId or projectId'
            )

        print(f'Getting project info for org={org_id}, project={project_id}')

        # Call ECS service
        url = f'{BASE_URL}/organization/{org_id}/projects/{project_id}'
        print(f'Calling: {url}')

        response = http.request(
            'GET',
            url,
            headers={
                'Content-Type': 'application/json',
            },
            timeout=10.0
        )

        print(f'Response status: {response.status}')

        if response.status == 200:
            project_info = json.loads(response.data.decode('utf-8'))
            print(f'Project info retrieved successfully')

            return create_success_response(
                event,
                200,
                json.dumps(project_info)
            )
        else:
            error_message = response.data.decode('utf-8')
            print(f'Error from ECS service: {error_message}')

            return create_error_response(
                event,
                response.status,
                f'ECS service error: {error_message}'
            )

    except urllib3.exceptions.HTTPError as e:
        print(f'HTTP error: {str(e)}')
        return create_error_response(event, 500, f'HTTP error: {str(e)}')

    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        import traceback
        print(f'Traceback: {traceback.format_exc()}')
        return create_error_response(event, 500, f'Unexpected error: {str(e)}')


def create_success_response(
    event: Dict[str, Any],
    status_code: int,
    body: str
) -> Dict[str, Any]:
    """Create successful Bedrock Agent action group response"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'GetProjectInfo'),
            'apiPath': event.get('apiPath', '/getProjectInfo'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': body
                }
            }
        }
    }


def create_error_response(
    event: Dict[str, Any],
    status_code: int,
    error_message: str
) -> Dict[str, Any]:
    """Create error Bedrock Agent action group response"""
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', 'GetProjectInfo'),
            'apiPath': event.get('apiPath', '/getProjectInfo'),
            'httpMethod': event.get('httpMethod', 'POST'),
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': error_message})
                }
            }
        }
    }
