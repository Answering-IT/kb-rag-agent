#!/usr/bin/env python3
"""
Add partition_key to all documents in S3 for strict metadata filtering.

partition_key format:
- Project-level: t{tenant_id}_p{project_id}
- Task-level: t{tenant_id}_p{project_id}_t{task_id}

This enables strict filtering without false positives.
"""

import boto3
import json
from pathlib import Path

BUCKET = "processapp-docs-v2-dev-708819485463"
PROFILE = "ans-super"

def generate_partition_key(metadata):
    """Generate partition_key from metadata"""
    tenant_id = metadata.get("tenant_id")
    project_id = metadata.get("project_id")
    task_id = metadata.get("task_id")

    if not tenant_id or not project_id:
        print(f"  ⚠️  Missing tenant_id or project_id: {metadata}")
        return None

    # Format: t{tenant}_p{project}[_t{task}]
    key = f"t{tenant_id}_p{project_id}"
    if task_id:
        key += f"_t{task_id}"

    return key

def process_metadata_file(s3, bucket, key):
    """Process a single metadata file and add partition_key"""
    print(f"\n📄 Processing: {key}")

    try:
        # Download metadata
        response = s3.get_object(Bucket=bucket, Key=key)
        metadata_json = json.loads(response['Body'].read().decode('utf-8'))

        # Extract current metadata
        meta_attrs = metadata_json.get("metadataAttributes", {})
        print(f"   Current: {meta_attrs}")

        # Check if partition_key already exists
        if "partition_key" in meta_attrs:
            print(f"   ✅ Already has partition_key: {meta_attrs['partition_key']}")
            return

        # Generate partition_key
        partition_key = generate_partition_key(meta_attrs)
        if not partition_key:
            print(f"   ❌ Cannot generate partition_key")
            return

        # Add partition_key
        meta_attrs["partition_key"] = partition_key
        metadata_json["metadataAttributes"] = meta_attrs

        print(f"   ✅ Adding partition_key: {partition_key}")

        # Upload updated metadata
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(metadata_json, indent=2),
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId='e6a714f6-70a7-47bf-a9ee-55d871d33cc6'
        )

        print(f"   ✅ Updated: {key}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

def main():
    session = boto3.Session(profile_name=PROFILE)
    s3 = session.client('s3')

    print("="*80)
    print("ADD PARTITION KEYS TO S3 METADATA")
    print("="*80)

    # List all metadata files
    paginator = s3.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix='tenant/')

    metadata_files = []
    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            if key.endswith('.metadata.json'):
                metadata_files.append(key)

    print(f"\n📊 Found {len(metadata_files)} metadata files")

    # Process each file
    for key in metadata_files:
        process_metadata_file(s3, BUCKET, key)

    print("\n" + "="*80)
    print("✅ MIGRATION COMPLETE")
    print("="*80)
    print(f"\nProcessed {len(metadata_files)} files")
    print("\nNext step: Start ingestion job to reindex all documents")
    print("aws bedrock-agent start-ingestion-job \\")
    print("  --knowledge-base-id R80HXGRLHO \\")
    print("  --data-source-id 6H96SSTEHT \\")
    print("  --profile ans-super")

if __name__ == "__main__":
    main()
