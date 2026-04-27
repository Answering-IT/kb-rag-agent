"""
WebSocket Disconnect Handler - Agent Core v2
Simplified version for Phase 2
"""

import json


def handler(event, context):
    """
    Handle WebSocket disconnection
    """
    connection_id = event['requestContext']['connectionId']
    print(f'Client disconnected: {connection_id}')

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Disconnected from Agent Core v2'})
    }
