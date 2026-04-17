"""
Embedder Lambda
Generates embeddings using Titan v2 and stores in S3
"""

import json
import os
import boto3
from typing import Dict, List, Any
from datetime import datetime

# AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
s3 = boto3.client('s3')

# Environment variables
VECTORS_BUCKET = os.environ['VECTORS_BUCKET']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
STAGE = os.environ['STAGE']


def handler(event, context):
    """
    Main handler for embedding generation
    Processes SQS messages containing text chunks
    """
    print(f'Received {len(event["Records"])} messages from SQS')

    successful = []
    failed = []

    for record in event['Records']:
        try:
            # Parse message body
            chunk = json.loads(record['body'])

            chunk_id = chunk['id']
            chunk_text = chunk['text']
            chunk_metadata = chunk['metadata']

            print(f'Processing chunk {chunk_id}')

            # Generate embedding
            embedding = generate_embedding(chunk_text)

            # Store in S3
            store_embedding(chunk_id, chunk_text, embedding, chunk_metadata)

            print(f'Successfully processed chunk {chunk_id}')
            successful.append(chunk_id)

        except Exception as e:
            print(f'Error processing record: {str(e)}')
            print(f'Record: {record}')
            failed.append({
                'itemIdentifier': record['messageId']
            })

    # Return batch item failures for retry
    return {
        'batchItemFailures': failed
    }


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding using Titan Embeddings v2

    Args:
        text: Input text to embed

    Returns:
        List of floats (embedding vector)
    """
    # Prepare request body
    body = json.dumps({
        'inputText': text,
        'dimensions': 1536,
        'normalize': True
    })

    # Invoke Bedrock model
    try:
        response = bedrock_runtime.invoke_model(
            modelId=EMBEDDING_MODEL,
            contentType='application/json',
            accept='application/json',
            body=body
        )

        # Parse response
        response_body = json.loads(response['body'].read())

        # Extract embedding
        embedding = response_body['embedding']

        print(f'Generated embedding with {len(embedding)} dimensions')

        return embedding

    except Exception as e:
        print(f'Error generating embedding: {str(e)}')
        raise


def store_embedding(
    chunk_id: str,
    text: str,
    embedding: List[float],
    metadata: Dict[str, Any]
) -> None:
    """
    Store embedding in S3

    Args:
        chunk_id: Unique chunk identifier
        text: Original text
        embedding: Embedding vector
        metadata: Chunk metadata
    """
    # Create embedding object
    embedding_obj = {
        'id': chunk_id,
        'text': text,
        'embedding': embedding,
        'metadata': {
            **metadata,
            'embedding_model': EMBEDDING_MODEL,
            'embedding_dimensions': len(embedding),
            'indexed_at': datetime.utcnow().isoformat()
        }
    }

    # Store in S3
    key = f'embeddings/{chunk_id}.json'

    try:
        s3.put_object(
            Bucket=VECTORS_BUCKET,
            Key=key,
            Body=json.dumps(embedding_obj),
            ContentType='application/json',
            ServerSideEncryption='aws:kms'
        )

        print(f'Stored embedding at s3://{VECTORS_BUCKET}/{key}')

    except Exception as e:
        print(f'Error storing embedding: {str(e)}')
        raise
