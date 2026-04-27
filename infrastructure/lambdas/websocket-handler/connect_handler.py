"""
WebSocket Connect Handler
Handles new WebSocket connections
"""

import json
import os
from typing import Dict, Any

STAGE = os.environ['STAGE']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket connect event

    This is called when a client establishes a WebSocket connection
    """
    connection_id = event['requestContext']['connectionId']
    print(f'New WebSocket connection: {connection_id}')

    # You can add connection tracking here (e.g., store in DynamoDB)
    # For now, just log and accept the connection

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Connected',
            'connectionId': connection_id,
            'stage': STAGE
        })
    }
