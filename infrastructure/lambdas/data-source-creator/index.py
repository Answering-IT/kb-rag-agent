"""
Data Source Creator - CloudFormation Custom Resource
Creates Bedrock Data Source via boto3 API
"""

import json
import boto3
import cfnresponse
from typing import Dict, Any

bedrock_agent = boto3.client('bedrock-agent')


def handler(event, context):
    """
    CloudFormation custom resource handler
    """
    print(f'Event: {json.dumps(event)}')

    request_type = event['RequestType']
    properties = event['ResourceProperties']

    try:
        if request_type == 'Create':
            response_data = create_data_source(properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

        elif request_type == 'Update':
            kb_id = properties['KnowledgeBaseId']
            ds_id = event['PhysicalResourceId'].split('/')[-1]
            response_data = update_data_source(kb_id, ds_id, properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

        elif request_type == 'Delete':
            kb_id = properties['KnowledgeBaseId']
            ds_id = event['PhysicalResourceId'].split('/')[-1]
            delete_data_source(kb_id, ds_id)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

    except Exception as e:
        print(f'Error: {str(e)}')
        cfnresponse.send(event, context, cfnresponse.FAILED, {
            'Error': str(e)
        })


def create_data_source(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create Bedrock Data Source
    """
    name = properties['Name']
    description = properties.get('Description', '')
    kb_id = properties['KnowledgeBaseId']
    ds_config = properties['DataSourceConfiguration']
    vector_config = properties.get('VectorIngestionConfiguration', {})

    print(f'Creating Data Source: {name} for KB: {kb_id}')

    response = bedrock_agent.create_data_source(
        knowledgeBaseId=kb_id,
        name=name,
        description=description,
        dataSourceConfiguration=ds_config,
        vectorIngestionConfiguration=vector_config
    )

    ds_id = response['dataSource']['dataSourceId']
    ds_status = response['dataSource']['status']

    print(f'Created Data Source: {ds_id} with status: {ds_status}')

    return {
        'DataSourceId': ds_id,
        'DataSourceStatus': ds_status,
        'PhysicalResourceId': f'{kb_id}/{ds_id}'
    }


def update_data_source(kb_id: str, ds_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Bedrock Data Source
    """
    name = properties['Name']
    description = properties.get('Description', '')
    ds_config = properties['DataSourceConfiguration']
    vector_config = properties.get('VectorIngestionConfiguration', {})

    print(f'Updating Data Source: {ds_id} for KB: {kb_id}')

    response = bedrock_agent.update_data_source(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        name=name,
        description=description,
        dataSourceConfiguration=ds_config,
        vectorIngestionConfiguration=vector_config
    )

    ds_status = response['dataSource']['status']

    print(f'Updated Data Source: {ds_id} with status: {ds_status}')

    return {
        'DataSourceId': ds_id,
        'DataSourceStatus': ds_status,
        'PhysicalResourceId': f'{kb_id}/{ds_id}'
    }


def delete_data_source(kb_id: str, ds_id: str) -> None:
    """
    Delete Bedrock Data Source
    """
    print(f'Deleting Data Source: {ds_id} from KB: {kb_id}')

    try:
        bedrock_agent.delete_data_source(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id
        )
        print(f'Deleted Data Source: {ds_id}')
    except Exception as e:
        print(f'Error deleting Data Source: {str(e)}')
        # Don't fail on delete errors
