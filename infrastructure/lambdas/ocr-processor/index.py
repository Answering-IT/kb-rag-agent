"""
OCR Processor Lambda
Processes uploaded documents with Textract and sends chunks to SQS
"""

import json
import os
import boto3
import uuid
from datetime import datetime
from typing import Dict, List, Any

# AWS clients
s3 = boto3.client('s3')
textract = boto3.client('textract')
sqs = boto3.client('sqs')

# Environment variables
DOCS_BUCKET = os.environ['DOCS_BUCKET']
CHUNKS_QUEUE_URL = os.environ['CHUNKS_QUEUE_URL']
TEXTRACT_SNS_TOPIC_ARN = os.environ['TEXTRACT_SNS_TOPIC_ARN']
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
            # Start Textract job for image/PDF
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

        elif file_ext in ['txt', 'docx']:
            # Process text files directly
            text = extract_text_from_s3(bucket_name, object_key)
            chunks = chunk_text(text, object_key)
            send_chunks_to_queue(chunks)

            print(f'Processed {len(chunks)} chunks from text file')

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Text file processed',
                    'chunks': len(chunks),
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
    Retrieve results and send chunks to SQS
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

        # Chunk the text
        chunks = chunk_text(text, document_key)

        # Send chunks to SQS
        send_chunks_to_queue(chunks)

        print(f'Processed {len(chunks)} chunks from Textract job {job_id}')

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Textract results processed',
                'jobId': job_id,
                'chunks': len(chunks)
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


def extract_text_from_s3(bucket_name: str, object_key: str) -> str:
    """
    Extract text from S3 object (for .txt files)
    """
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    text = response['Body'].read().decode('utf-8')
    return text


def chunk_text(text: str, document_key: str, chunk_size: int = 512) -> List[Dict[str, Any]]:
    """
    Split text into chunks

    Args:
        text: Full document text
        document_key: S3 key of source document
        chunk_size: Target token count per chunk (approximate)

    Returns:
        List of chunk dictionaries
    """
    # Simple word-based chunking (rough approximation of tokens)
    words = text.split()
    chunks = []

    # Approximate: 1 token ≈ 0.75 words
    words_per_chunk = int(chunk_size * 0.75)
    overlap_words = int(words_per_chunk * 0.2)  # 20% overlap

    i = 0
    chunk_index = 0

    while i < len(words):
        # Extract chunk
        chunk_words = words[i:i + words_per_chunk]
        chunk_text = ' '.join(chunk_words)

        # Create chunk metadata
        chunk = {
            'id': str(uuid.uuid4()),
            'text': chunk_text,
            'metadata': {
                'source': document_key,
                'chunk_index': chunk_index,
                'total_words': len(chunk_words),
                'timestamp': datetime.utcnow().isoformat(),
                'stage': STAGE
            }
        }

        chunks.append(chunk)

        # Move to next chunk with overlap
        i += words_per_chunk - overlap_words
        chunk_index += 1

    return chunks


def send_chunks_to_queue(chunks: List[Dict[str, Any]]) -> None:
    """
    Send chunks to SQS queue for embedding generation
    """
    for chunk in chunks:
        try:
            sqs.send_message(
                QueueUrl=CHUNKS_QUEUE_URL,
                MessageBody=json.dumps(chunk),
                MessageAttributes={
                    'ChunkId': {
                        'StringValue': chunk['id'],
                        'DataType': 'String'
                    },
                    'Source': {
                        'StringValue': chunk['metadata']['source'],
                        'DataType': 'String'
                    }
                }
            )
        except Exception as e:
            print(f'Error sending chunk {chunk["id"]} to SQS: {str(e)}')
            raise
