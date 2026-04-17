"""
Knowledge Base Creator - CloudFormation Custom Resource
Creates Bedrock Knowledge Base via boto3 API
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
            response_data = create_knowledge_base(properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

        elif request_type == 'Update':
            response_data = update_knowledge_base(event['PhysicalResourceId'], properties)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)

        elif request_type == 'Delete':
            delete_knowledge_base(event['PhysicalResourceId'])
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

    except Exception as e:
        print(f'Error: {str(e)}')
        cfnresponse.send(event, context, cfnresponse.FAILED, {
            'Error': str(e)
        })


def create_knowledge_base(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create Bedrock Knowledge Base
    """
    name = properties['Name']
    description = properties.get('Description', '')
    role_arn = properties['RoleArn']
    storage_config = properties['StorageConfiguration']
    kb_config = properties['KnowledgeBaseConfiguration']

    print(f'Creating Knowledge Base: {name}')

    response = bedrock_agent.create_knowledge_base(
        name=name,
        description=description,
        roleArn=role_arn,
        knowledgeBaseConfiguration=kb_config,
        storageConfiguration=storage_config
    )

    kb_id = response['knowledgeBase']['knowledgeBaseId']
    kb_arn = response['knowledgeBase']['knowledgeBaseArn']

    print(f'Created Knowledge Base: {kb_id}')

    return {
        'KnowledgeBaseId': kb_id,
        'KnowledgeBaseArn': kb_arn,
        'PhysicalResourceId': kb_id
    }


def update_knowledge_base(kb_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Bedrock Knowledge Base
    """
    name = properties['Name']
    description = properties.get('Description', '')
    role_arn = properties['RoleArn']
    kb_config = properties['KnowledgeBaseConfiguration']

    print(f'Updating Knowledge Base: {kb_id}')

    response = bedrock_agent.update_knowledge_base(
        knowledgeBaseId=kb_id,
        name=name,
        description=description,
        roleArn=role_arn,
        knowledgeBaseConfiguration=kb_config
    )

    kb_arn = response['knowledgeBase']['knowledgeBaseArn']

    print(f'Updated Knowledge Base: {kb_id}')

    return {
        'KnowledgeBaseId': kb_id,
        'KnowledgeBaseArn': kb_arn,
        'PhysicalResourceId': kb_id
    }


def delete_knowledge_base(kb_id: str) -> None:
    """
    Delete Bedrock Knowledge Base
    """
    print(f'Deleting Knowledge Base: {kb_id}')

    try:
        bedrock_agent.delete_knowledge_base(knowledgeBaseId=kb_id)
        print(f'Deleted Knowledge Base: {kb_id}')
    except Exception as e:
        print(f'Error deleting Knowledge Base: {str(e)}')
        # Don't fail on delete errors (resource might already be deleted)
