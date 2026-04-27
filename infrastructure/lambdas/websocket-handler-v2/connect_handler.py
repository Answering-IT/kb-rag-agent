"""
WebSocket Connect Handler - Agent Core v2
Simplified version for Phase 2
"""

import json


def handler(event, context):
    """
    Handle WebSocket connection
    """
    connection_id = event['requestContext']['connectionId']
    print(f'Client connected: {connection_id}')

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Connected to Agent Core v2'})
    }
