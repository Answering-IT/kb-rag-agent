"""
Guardrail Creator - CloudFormation Custom Resource
Creates Bedrock Guardrail via boto3 API
"""

import json
import boto3
from typing import Dict, Any

bedrock = boto3.client('bedrock')


def handler(event, context):
    """
    CloudFormation custom resource handler for CDK Provider framework
    Returns response object instead of calling cfnresponse
    """
    print(f'Event: {json.dumps(event)}')

    request_type = event['RequestType']
    properties = event['ResourceProperties']

    try:
        if request_type == 'Create':
            response_data = create_guardrail(properties)
            return {
                'PhysicalResourceId': response_data['GuardrailId'],
                'Data': response_data
            }

        elif request_type == 'Update':
            physical_id = event.get('PhysicalResourceId', '')
            response_data = update_guardrail(physical_id, properties)
            return {
                'PhysicalResourceId': response_data['GuardrailId'],
                'Data': response_data
            }

        elif request_type == 'Delete':
            physical_id = event.get('PhysicalResourceId', '')
            delete_guardrail(physical_id)
            return {
                'PhysicalResourceId': physical_id
            }

    except Exception as e:
        print(f'Error: {str(e)}')
        raise  # Let Provider framework handle the error


def create_guardrail(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create Bedrock Guardrail
    """
    name = properties['Name']
    description = properties.get('Description', '')
    blocked_input = properties.get('BlockedInputMessaging', '')
    blocked_output = properties.get('BlockedOutputsMessaging', '')

    content_policy = properties.get('ContentPolicyConfig', {})
    sensitive_info_policy = properties.get('SensitiveInformationPolicyConfig', {})
    topic_policy = properties.get('TopicPolicyConfig', {})
    word_policy = properties.get('WordPolicyConfig', {})

    print(f'Creating Guardrail: {name}')

    # Build create request
    request_params = {
        'name': name,
        'description': description,
        'blockedInputMessaging': blocked_input,
        'blockedOutputsMessaging': blocked_output
    }

    # Add policies if provided
    if content_policy:
        request_params['contentPolicyConfig'] = content_policy

    if sensitive_info_policy:
        request_params['sensitiveInformationPolicyConfig'] = sensitive_info_policy

    if topic_policy:
        request_params['topicPolicyConfig'] = topic_policy

    if word_policy:
        request_params['wordPolicyConfig'] = word_policy

    response = bedrock.create_guardrail(**request_params)

    guardrail_id = response['guardrailId']
    guardrail_arn = response['guardrailArn']

    print(f'Created Guardrail: {guardrail_id}, ARN: {guardrail_arn}')

    # Return only essential fields to avoid 4KB CloudFormation response limit
    return {
        'GuardrailId': guardrail_id,
        'GuardrailArn': guardrail_arn
    }


def update_guardrail(guardrail_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update Bedrock Guardrail
    """
    name = properties['Name']
    description = properties.get('Description', '')
    blocked_input = properties.get('BlockedInputMessaging', '')
    blocked_output = properties.get('BlockedOutputsMessaging', '')

    content_policy = properties.get('ContentPolicyConfig', {})
    sensitive_info_policy = properties.get('SensitiveInformationPolicyConfig', {})
    topic_policy = properties.get('TopicPolicyConfig', {})
    word_policy = properties.get('WordPolicyConfig', {})

    print(f'Updating Guardrail: {guardrail_id}')

    # Build update request
    request_params = {
        'guardrailIdentifier': guardrail_id,
        'name': name,
        'description': description,
        'blockedInputMessaging': blocked_input,
        'blockedOutputsMessaging': blocked_output
    }

    # Add policies if provided
    if content_policy:
        request_params['contentPolicyConfig'] = content_policy

    if sensitive_info_policy:
        request_params['sensitiveInformationPolicyConfig'] = sensitive_info_policy

    if topic_policy:
        request_params['topicPolicyConfig'] = topic_policy

    if word_policy:
        request_params['wordPolicyConfig'] = word_policy

    response = bedrock.update_guardrail(**request_params)

    guardrail_arn = response['guardrailArn']

    print(f'Updated Guardrail: {guardrail_id}')

    return {
        'GuardrailId': guardrail_id,
        'GuardrailArn': guardrail_arn
    }


def delete_guardrail(guardrail_id: str) -> None:
    """
    Delete Bedrock Guardrail
    """
    print(f'Deleting Guardrail: {guardrail_id}')

    try:
        bedrock.delete_guardrail(guardrailIdentifier=guardrail_id)
        print(f'Deleted Guardrail: {guardrail_id}')
    except Exception as e:
        print(f'Error deleting Guardrail: {str(e)}')
        # Don't fail on delete errors
