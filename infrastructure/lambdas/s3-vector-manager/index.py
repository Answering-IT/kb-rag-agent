"""
S3 Vector Manager - CloudFormation Custom Resource
Creates S3 Vector Bucket and Index via boto3 API
"""

import json
import boto3
from typing import Dict, Any

s3vectors = boto3.client('s3vectors')


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
            response_data = create_vector_resources(properties)
            return {
                'PhysicalResourceId': response_data['VectorBucketName'],
                'Data': response_data
            }

        elif request_type == 'Update':
            physical_id = event.get('PhysicalResourceId', '')
            response_data = update_vector_resources(physical_id, properties)
            return {
                'PhysicalResourceId': response_data['VectorBucketName'],
                'Data': response_data
            }

        elif request_type == 'Delete':
            physical_id = event.get('PhysicalResourceId', '')
            delete_vector_resources(physical_id, properties)
            return {
                'PhysicalResourceId': physical_id
            }

    except Exception as e:
        print(f'Error: {str(e)}')
        raise  # Let Provider framework handle the error


def create_vector_resources(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create S3 Vector Bucket and Index
    """
    vector_bucket_name = properties['VectorBucketName']
    index_name = properties['IndexName']
    dimension = int(properties['Dimension'])
    distance_metric = properties.get('DistanceMetric', 'COSINE')
    data_type = properties.get('DataType', 'FLOAT32')
    kms_key_arn = properties.get('KmsKeyArn')

    print(f'Creating S3 Vector Bucket: {vector_bucket_name}')

    # Build create vector bucket request
    vector_bucket_params = {
        'VectorBucketName': vector_bucket_name
    }

    # Add encryption if KMS key provided
    if kms_key_arn:
        vector_bucket_params['EncryptionConfiguration'] = {
            'ServerSideEncryptionConfiguration': {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'aws:kms',
                            'KMSMasterKeyID': kms_key_arn
                        }
                    }
                ]
            }
        }

    # Create vector bucket
    bucket_response = s3vectors.create_vector_bucket(**vector_bucket_params)
    bucket_arn = bucket_response['VectorBucketArn']

    print(f'Created Vector Bucket: {bucket_arn}')

    # Create vector index
    print(f'Creating Vector Index: {index_name}')

    index_response = s3vectors.create_index(
        VectorBucketName=vector_bucket_name,
        IndexName=index_name,
        DataType=data_type,
        Dimension=dimension,
        DistanceMetric=distance_metric
    )

    index_arn = index_response['IndexArn']

    print(f'Created Vector Index: {index_arn}')

    # Return only essential fields to avoid 4KB CloudFormation response limit
    return {
        'VectorBucketName': vector_bucket_name,
        'VectorBucketArn': bucket_arn,
        'IndexName': index_name,
        'IndexArn': index_arn
    }


def update_vector_resources(bucket_name: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update S3 Vector Bucket - limited operations supported
    """
    print(f'Update requested for Vector Bucket: {bucket_name}')

    # S3 Vector buckets have limited update operations
    # For most changes, a replacement is needed
    # Just return current state
    index_name = properties['IndexName']

    # Get current bucket ARN
    bucket_info = s3vectors.get_vector_bucket(VectorBucketName=bucket_name)
    bucket_arn = bucket_info['VectorBucketArn']

    # Get current index ARN
    index_info = s3vectors.get_index(
        VectorBucketName=bucket_name,
        IndexName=index_name
    )
    index_arn = index_info['IndexArn']

    return {
        'VectorBucketName': bucket_name,
        'VectorBucketArn': bucket_arn,
        'IndexName': index_name,
        'IndexArn': index_arn
    }


def delete_vector_resources(bucket_name: str, properties: Dict[str, Any]) -> None:
    """
    Delete S3 Vector Index and Bucket
    """
    index_name = properties.get('IndexName')

    try:
        if index_name:
            print(f'Deleting Vector Index: {index_name}')
            s3vectors.delete_index(
                VectorBucketName=bucket_name,
                IndexName=index_name
            )
            print(f'Deleted Vector Index: {index_name}')
    except Exception as e:
        print(f'Error deleting index: {str(e)}')
        # Continue to delete bucket even if index deletion fails

    try:
        print(f'Deleting Vector Bucket: {bucket_name}')
        s3vectors.delete_vector_bucket(VectorBucketName=bucket_name)
        print(f'Deleted Vector Bucket: {bucket_name}')
    except Exception as e:
        print(f'Error deleting vector bucket: {str(e)}')
        # Don't fail on delete errors
