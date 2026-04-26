"""
WebSocket Disconnect Handler
Handles WebSocket disconnections and cleanup
"""

import json
import os
from typing import Dict, Any

STAGE = os.environ['STAGE']


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket disconnect event

    This is called when a client closes the WebSocket connection
    """
    connection_id = event['requestContext']['connectionId']
    print(f'WebSocket disconnected: {connection_id}')

    # You can add cleanup logic here (e.g., remove from DynamoDB tracking table)
    # For now, just log the disconnection

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Disconnected',
            'connectionId': connection_id,
            'stage': STAGE
        })
    }
