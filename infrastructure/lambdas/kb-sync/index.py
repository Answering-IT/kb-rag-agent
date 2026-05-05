"""
Knowledge Base Sync Lambda
Triggers ingestion job for Bedrock Knowledge Base data source.
"""

import boto3
import os
import json

bedrock_agent = boto3.client('bedrock-agent')

def handler(event, context):  # noqa: ARG001
    """
    Trigger Knowledge Base ingestion job.

    Environment Variables:
        KNOWLEDGE_BASE_ID: Bedrock Knowledge Base ID
        DATA_SOURCE_ID: Data Source ID to sync

    Returns:
        dict: Response with ingestion job ID
    """
    kb_id = os.environ['KNOWLEDGE_BASE_ID']
    ds_id = os.environ['DATA_SOURCE_ID']

    print(f'Starting sync for KB: {kb_id}, DataSource: {ds_id}')

    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )

        print(f'Sync started: {json.dumps(response, default=str)}')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Sync started successfully',
                'ingestionJobId': response.get('ingestionJob', {}).get('ingestionJobId')
            })
        }
    except Exception as e:
        print(f'Error starting sync: {str(e)}')
        raise
