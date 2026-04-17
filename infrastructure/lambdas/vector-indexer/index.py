"""
Vector Indexer Lambda
Updates vector index manifest and shards when new vectors are created
"""

import json
import os
import boto3
from typing import Dict, List, Any
from datetime import datetime

s3 = boto3.client('s3')

VECTORS_BUCKET = os.environ['VECTORS_BUCKET']
SHARD_SIZE = int(os.environ.get('SHARD_SIZE', '10000'))


def handler(event, context):
    """
    Main handler for vector indexing
    Triggered by S3 EventBridge when new vectors are uploaded
    """
    print(f'Received event: {json.dumps(event)}')

    try:
        # Extract S3 details
        bucket_name = event['detail']['bucket']['name']
        object_key = event['detail']['object']['key']

        if not object_key.startswith('embeddings/'):
            print(f'Ignoring non-embedding object: {object_key}')
            return {'statusCode': 200, 'body': 'Not an embedding'}

        print(f'New embedding created: s3://{bucket_name}/{object_key}')

        # Update index
        update_index(object_key)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Index updated successfully'})
        }

    except Exception as e:
        print(f'Error updating index: {str(e)}')
        raise


def update_index(embedding_key: str) -> None:
    """
    Update the vector index manifest and shards
    """
    # Read current manifest
    manifest = read_manifest()

    # Add new vector to manifest
    vector_id = embedding_key.split('/')[-1].replace('.json', '')

    manifest['totalVectors'] += 1
    manifest['lastUpdated'] = datetime.utcnow().isoformat()

    # Determine which shard this vector belongs to
    shard_number = (manifest['totalVectors'] - 1) // SHARD_SIZE + 1

    # Add to shard
    add_to_shard(shard_number, vector_id, embedding_key)

    # Update manifest with shard info
    if shard_number not in [s['shard'] for s in manifest['shards']]:
        manifest['shards'].append({
            'shard': shard_number,
            'key': f'index/shards/{shard_number:04d}.json',
            'vectors': 1
        })
    else:
        for shard in manifest['shards']:
            if shard['shard'] == shard_number:
                shard['vectors'] += 1

    # Write updated manifest
    write_manifest(manifest)

    print(f'Index updated: total vectors = {manifest["totalVectors"]}, shard = {shard_number}')


def read_manifest() -> Dict[str, Any]:
    """
    Read the index manifest from S3
    """
    try:
        response = s3.get_object(
            Bucket=VECTORS_BUCKET,
            Key='index/manifest.json'
        )
        manifest = json.loads(response['Body'].read().decode('utf-8'))
        return manifest

    except s3.exceptions.NoSuchKey:
        # Create initial manifest if doesn't exist
        return {
            'version': '1.0',
            'created': datetime.utcnow().isoformat(),
            'totalVectors': 0,
            'shards': [],
            'lastUpdated': datetime.utcnow().isoformat()
        }


def write_manifest(manifest: Dict[str, Any]) -> None:
    """
    Write the index manifest to S3
    """
    s3.put_object(
        Bucket=VECTORS_BUCKET,
        Key='index/manifest.json',
        Body=json.dumps(manifest, indent=2),
        ContentType='application/json',
        ServerSideEncryption='aws:kms'
    )


def add_to_shard(shard_number: int, vector_id: str, embedding_key: str) -> None:
    """
    Add vector to shard file
    """
    shard_key = f'index/shards/{shard_number:04d}.json'

    # Read existing shard
    try:
        response = s3.get_object(
            Bucket=VECTORS_BUCKET,
            Key=shard_key
        )
        shard = json.loads(response['Body'].read().decode('utf-8'))
    except s3.exceptions.NoSuchKey:
        # Create new shard
        shard = {
            'shard': shard_number,
            'created': datetime.utcnow().isoformat(),
            'vectors': []
        }

    # Add vector reference
    shard['vectors'].append({
        'id': vector_id,
        'key': embedding_key,
        'indexed': datetime.utcnow().isoformat()
    })

    # Write shard
    s3.put_object(
        Bucket=VECTORS_BUCKET,
        Key=shard_key,
        Body=json.dumps(shard, indent=2),
        ContentType='application/json',
        ServerSideEncryption='aws:kms'
    )

    print(f'Added vector {vector_id} to shard {shard_number}')
