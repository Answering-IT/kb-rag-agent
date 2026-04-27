"""
OCR Processor Lambda
Processes uploaded documents with Textract and saves extracted text to S3
Bedrock Knowledge Base handles chunking and embedding automatically
"""

import json
import os
import boto3
from datetime import datetime
from typing import Dict, Any

# AWS clients
s3 = boto3.client('s3')
textract = boto3.client('textract')

# Environment variables
DOCS_BUCKET = os.environ['DOCS_BUCKET']
TEXTRACT_SNS_TOPIC_ARN = os.environ['TEXTRACT_SNS_TOPIC_ARN']
TEXTRACT_ROLE_ARN = os.environ.get('TEXTRACT_ROLE_ARN', '')
KMS_KEY_ID = os.environ.get('KMS_KEY_ID', '')
STAGE = os.environ['STAGE']


def handler(event, context):
    """
    Main handler for OCR processing

    Handles two types of events:
    1. S3 EventBridge notification (document uploaded)
    2. SNS notification from Textract (job completed)
    """
    print(f'Received event: {json.dumps(event)}')

    # Check event source
    if 'source' in event and event['source'] == 'aws.s3':
        # S3 upload event
        return handle_s3_upload(event, context)

    elif 'Records' in event and event['Records'][0].get('EventSource') == 'aws:sns':
        # SNS notification from Textract
        return handle_textract_completion(event, context)

    else:
        print(f'Unknown event type: {event}')
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unknown event type'})
        }


def handle_s3_upload(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle S3 document upload event
    Start Textract job for OCR processing
    """
    try:
        # Extract S3 details
        bucket_name = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']

        print(f'Processing document: s3://{bucket_name}/{object_key}')

        # Check file extension
        file_ext = object_key.lower().split('.')[-1]

        if file_ext in ['pdf', 'png', 'jpg', 'jpeg', 'tiff']:
            # Start Textract job for image/PDF documents that need OCR
            job_id = start_textract_job(bucket_name, object_key)
            print(f'Started Textract job: {job_id}')

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Textract job started',
                    'jobId': job_id,
                    'document': f's3://{bucket_name}/{object_key}'
                })
            }

        elif file_ext in ['txt', 'docx', 'md']:
            # Text files don't need OCR processing - Bedrock KB can read them directly
            # But we should generate metadata.json if source has metadata
            print(f'Text file detected, no OCR needed: {object_key}')

            # Generate metadata.json companion file if source has tenant metadata
            generate_metadata_json_for_text_file(bucket_name, object_key)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Text file - no OCR needed',
                    'document': f's3://{bucket_name}/{object_key}'
                })
            }

        else:
            print(f'Unsupported file type: {file_ext}')
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unsupported file type: {file_ext}'})
            }

    except Exception as e:
        print(f'Error processing S3 upload: {str(e)}')
        raise


def handle_textract_completion(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle Textract job completion notification
    Save full text to S3 and send chunks to SQS
    """
    try:
        # Parse SNS message
        sns_message = json.loads(event['Records'][0]['Sns']['Message'])

        job_id = sns_message['JobId']
        status = sns_message['Status']

        print(f'Textract job {job_id} completed with status: {status}')

        if status != 'SUCCEEDED':
            print(f'Textract job failed: {sns_message}')
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f'Textract job failed: {status}'})
            }

        # Get Textract results
        text = get_textract_results(job_id)

        # Get document key from job metadata (if available)
        document_key = sns_message.get('DocumentLocation', {}).get('S3ObjectName', 'unknown')

        # Save full text to S3 for Bedrock KB to read
        # Bedrock will handle chunking and embedding automatically during ingestion
        processed_key = save_processed_text_to_s3(document_key, text)
        print(f'Saved processed text to: {processed_key}')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Textract results processed and saved to S3',
                'jobId': job_id,
                'processedKey': processed_key
            })
        }

    except Exception as e:
        print(f'Error processing Textract completion: {str(e)}')
        raise


def start_textract_job(bucket_name: str, object_key: str) -> str:
    """
    Start asynchronous Textract job
    """
    response = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': object_key
            }
        },
        NotificationChannel={
            'SNSTopicArn': TEXTRACT_SNS_TOPIC_ARN,
            'RoleArn': os.environ.get('TEXTRACT_ROLE_ARN', '')
        }
    )

    return response['JobId']


def get_textract_results(job_id: str) -> str:
    """
    Retrieve Textract job results
    Handles pagination for large documents
    """
    all_text = []
    next_token = None

    while True:
        if next_token:
            response = textract.get_document_text_detection(
                JobId=job_id,
                NextToken=next_token
            )
        else:
            response = textract.get_document_text_detection(JobId=job_id)

        # Extract text from blocks
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                all_text.append(block['Text'])

        next_token = response.get('NextToken')
        if not next_token:
            break

    return '\n'.join(all_text)


def save_processed_text_to_s3(original_key: str, text: str) -> str:
    """
    Save processed text to S3 for Bedrock KB to read
    Also creates companion metadata.json file from source document metadata

    Writes OCR-extracted text directly to documents/processed/ prefix
    where Bedrock KB can discover and index it.

    Args:
        original_key: Original S3 key (e.g., "documents/test.png")
        text: Extracted text to save

    Returns:
        S3 key where text was saved
    """
    # Extract filename without extension
    filename = original_key.split('/')[-1]
    base_name = '.'.join(filename.split('.')[:-1])  # Remove extension

    # Write directly to processed location
    # Note: Using documents/processed/ subdirectory to keep organized
    processed_key = f'documents/processed-{base_name}.txt'

    try:
        # Read source document metadata
        source_metadata = {}
        try:
            head_response = s3.head_object(Bucket=DOCS_BUCKET, Key=original_key)
            source_metadata = head_response.get('Metadata', {})
            print(f'Source metadata: {source_metadata}')
        except Exception as e:
            print(f'Warning: Could not read source metadata: {e}')

        # Prepare put_object parameters for processed text
        put_params = {
            'Bucket': DOCS_BUCKET,
            'Key': processed_key,
            'Body': text.encode('utf-8'),
            'ContentType': 'text/plain',
            'Metadata': {
                'source': original_key,
                'processor': 'textract-ocr',
                'timestamp': datetime.utcnow().isoformat(),
                'stage': STAGE
            }
        }

        # Add KMS encryption if key is available (required by bucket policy)
        if KMS_KEY_ID:
            put_params['ServerSideEncryption'] = 'aws:kms'
            put_params['SSEKMSKeyId'] = KMS_KEY_ID

        # Save processed text
        s3.put_object(**put_params)
        print(f'Saved processed text to: {processed_key}')

        # Create companion metadata.json file for Bedrock KB
        # Bedrock KB requires metadata in a separate .metadata.json file
        if source_metadata:
            metadata_json_key = f'{processed_key}.metadata.json'

            # Build metadataAttributes from source metadata
            # Extract tenant-specific metadata (tenant_id, roles, project_id, users)
            metadata_attributes = {}

            # Map common metadata keys to Bedrock format
            metadata_mapping = {
                'tenant_id': source_metadata.get('tenant_id'),
                'tenantid': source_metadata.get('tenantid'),
                'roles': source_metadata.get('roles'),
                'project_id': source_metadata.get('project_id'),
                'projectid': source_metadata.get('projectid'),
                'users': source_metadata.get('users'),
            }

            # Add non-None values to metadata_attributes
            for key, value in metadata_mapping.items():
                if value:
                    # Normalize to snake_case
                    normalized_key = key.replace('tenantid', 'tenant_id').replace('projectid', 'project_id')
                    metadata_attributes[normalized_key] = value

            if metadata_attributes:
                # Create metadata.json with metadataAttributes wrapper
                metadata_json = {
                    'metadataAttributes': metadata_attributes
                }

                metadata_put_params = {
                    'Bucket': DOCS_BUCKET,
                    'Key': metadata_json_key,
                    'Body': json.dumps(metadata_json, indent=2).encode('utf-8'),
                    'ContentType': 'application/json'
                }

                if KMS_KEY_ID:
                    metadata_put_params['ServerSideEncryption'] = 'aws:kms'
                    metadata_put_params['SSEKMSKeyId'] = KMS_KEY_ID

                s3.put_object(**metadata_put_params)
                print(f'Created metadata.json: {metadata_json_key}')
                print(f'Metadata content: {metadata_json}')
            else:
                print(f'Warning: No tenant metadata found in source document, skipping metadata.json creation')

        return processed_key

    except Exception as e:
        print(f'Error saving processed text to S3: {str(e)}')
        raise


def generate_metadata_json_for_text_file(bucket_name: str, object_key: str):
    """
    Generate companion metadata.json file for text files that don't need OCR

    Reads S3 object metadata from source file and creates .metadata.json
    companion file required by Bedrock Knowledge Base.

    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key (e.g., "documents/file.txt")
    """
    try:
        # Read source document metadata
        head_response = s3.head_object(Bucket=bucket_name, Key=object_key)
        source_metadata = head_response.get('Metadata', {})

        if not source_metadata:
            print(f'No metadata found for {object_key}, skipping metadata.json creation')
            return

        print(f'Source metadata for {object_key}: {source_metadata}')

        # Build metadataAttributes from source metadata
        metadata_attributes = {}

        # Map common metadata keys to Bedrock format (snake_case)
        metadata_mapping = {
            'tenant_id': source_metadata.get('tenant_id') or source_metadata.get('tenantid'),
            'roles': source_metadata.get('roles'),
            'project_id': source_metadata.get('project_id') or source_metadata.get('projectid'),
            'users': source_metadata.get('users'),
        }

        # Add non-None values to metadata_attributes
        for key, value in metadata_mapping.items():
            if value:
                metadata_attributes[key] = value

        if not metadata_attributes:
            print(f'No tenant metadata found for {object_key}, skipping metadata.json creation')
            return

        # Create metadata.json companion file
        metadata_json_key = f'{object_key}.metadata.json'

        metadata_json = {
            'metadataAttributes': metadata_attributes
        }

        put_params = {
            'Bucket': bucket_name,
            'Key': metadata_json_key,
            'Body': json.dumps(metadata_json, indent=2).encode('utf-8'),
            'ContentType': 'application/json'
        }

        # Add KMS encryption if available
        if KMS_KEY_ID:
            put_params['ServerSideEncryption'] = 'aws:kms'
            put_params['SSEKMSKeyId'] = KMS_KEY_ID

        s3.put_object(**put_params)
        print(f'✅ Created metadata.json: {metadata_json_key}')
        print(f'   Content: {metadata_json}')

    except Exception as e:
        print(f'Error generating metadata.json for {object_key}: {str(e)}')
        # Don't raise - this is non-critical, the document can still be indexed


# NOTE: Chunking and embedding are now handled entirely by Bedrock Knowledge Base
# The OCR processor only needs to extract text and save it to S3
