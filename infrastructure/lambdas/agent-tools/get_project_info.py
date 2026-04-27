"""
GetProjectInfo Action Group Lambda
Called by Bedrock Agent to retrieve project information from ECS service
"""

import json
import os
import urllib3
from typing import Dict, Any

# Create HTTP client (reuse across invocations)
http = urllib3.PoolManager()

# ECS service endpoint
ECS_BASE_URL = os.environ.get('ECS_BASE_URL', 'https://dev.app.colpensiones.procesapp.com')


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GetProjectInfo action group

    Event format from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {
            "name": "processapp-agent-dev",
            "id": "QWTVV3BY3G",
            "alias": "QZITGFMONE",
            "version": "DRAFT"
        },
        "sessionId": "session-123",
        "sessionAttributes": {},
        "promptSessionAttributes": {},
        "inputText": "What's the budget for project 123?",
        "apiPath": "/organization/{orgId}/projects/{projectId}",
        "httpMethod": "GET",
        "parameters": [
            {"name": "orgId", "type": "string", "value": "1"},
            {"name": "projectId", "type": "string", "value": "123"}
        ]
    }

    Expected response format:
    {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": "GetProjectInfo",
            "apiPath": "/organization/{orgId}/projects/{projectId}",
            "httpMethod": "GET",
            "httpStatusCode": 200,
            "responseBody": {
                "application/json": {
                    "body": "{...json data...}"
                }
            }
        }
    }
    """
    print(f"Received event: {json.dumps(event)}")

    try:
        # Extract parameters
        api_path = event.get('apiPath', '')
        http_method = event.get('httpMethod', 'GET')
        parameters = event.get('parameters', [])

        # Parse parameters into dict
        params_dict = {p['name']: p['value'] for p in parameters}
        org_id = params_dict.get('orgId')
        project_id = params_dict.get('projectId')

        print(f"Fetching project info - orgId: {org_id}, projectId: {project_id}")

        # Build full URL to ECS service
        url = f"{ECS_BASE_URL}/organization/{org_id}/projects/{project_id}"

        print(f"Calling ECS endpoint: {url}")

        # Call ECS service
        response = http.request(http_method, url, timeout=10.0)

        # Parse response
        response_body = response.data.decode('utf-8')
        status_code = response.status

        print(f"ECS response status: {status_code}")
        print(f"ECS response body: {response_body[:500]}")  # Log first 500 chars

        # Return response in Bedrock Agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': 'GetProjectInfo',
                'apiPath': api_path,
                'httpMethod': http_method,
                'httpStatusCode': status_code,
                'responseBody': {
                    'application/json': {
                        'body': response_body
                    }
                }
            }
        }

    except urllib3.exceptions.HTTPError as e:
        print(f"HTTP error calling ECS: {str(e)}")
        return error_response(api_path, http_method, 502, f"HTTP error: {str(e)}")

    except Exception as e:
        print(f"Error in GetProjectInfo: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return error_response(api_path, http_method, 500, f"Internal error: {str(e)}")


def error_response(api_path: str, http_method: str, status_code: int, error_message: str) -> Dict[str, Any]:
    """
    Return error response in Bedrock Agent format
    """
    return {
        'messageVersion': '1.0',
        'response': {
            'actionGroup': 'GetProjectInfo',
            'apiPath': api_path,
            'httpMethod': http_method,
            'httpStatusCode': status_code,
            'responseBody': {
                'application/json': {
                    'body': json.dumps({'error': error_message})
                }
            }
        }
    }
