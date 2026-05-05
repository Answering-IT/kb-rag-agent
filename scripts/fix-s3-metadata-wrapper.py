#!/usr/bin/env python3
"""
Fix S3 metadata files to include AWS Bedrock KB wrapper.

Converts:
  {"tenant_id": "100001", "partition_key": "t100001"}

To:
  {"metadataAttributes": {"tenant_id": "100001", "partition_key": "t100001"}}
"""

import boto3
import json
from pathlib import Path

# Configuration
BUCKET = "processapp-docs-v2-dev-708819485463"
PREFIX = "organizations/"
AWS_PROFILE = "ans-super"
DRY_RUN = False  # Set to True to preview changes without applying them

def fix_metadata_file(s3_client, bucket: str, key: str, dry_run: bool = False):
    """Download, fix, and re-upload a metadata file with KB wrapper."""

    print(f"\n📄 Processing: {key}")

    # Download current content
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        metadata_obj = json.loads(content)

        print(f"   Current: {json.dumps(metadata_obj, indent=2)}")

        # Check if already has wrapper
        if "metadataAttributes" in metadata_obj:
            print("   ✅ Already has wrapper - skipping")
            return False

        # Add wrapper
        fixed_metadata = {
            "metadataAttributes": metadata_obj
        }

        print(f"   Fixed:   {json.dumps(fixed_metadata, indent=2)}")

        if not dry_run:
            # Upload fixed version
            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(fixed_metadata, indent=2),
                ContentType='application/json',
                ServerSideEncryption='aws:kms',
                SSEKMSKeyId='e6a714f6-70a7-47bf-a9ee-55d871d33cc6'
            )
            print("   ✅ Fixed and uploaded")
        else:
            print("   🔍 DRY RUN - would fix")

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    session = boto3.Session(profile_name=AWS_PROFILE)
    s3_client = session.client('s3')

    print(f"🔧 Fixing S3 metadata files in s3://{BUCKET}/{PREFIX}")
    print(f"   Dry run: {DRY_RUN}")
    print("=" * 80)

    # List all metadata files
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=BUCKET, Prefix=PREFIX)

    fixed_count = 0
    skipped_count = 0

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']

            # Only process .metadata.json files
            if not key.endswith('.metadata.json'):
                continue

            if fix_metadata_file(s3_client, BUCKET, key, dry_run=DRY_RUN):
                fixed_count += 1
            else:
                skipped_count += 1

    print("\n" + "=" * 80)
    print(f"✅ Summary:")
    print(f"   Fixed:   {fixed_count} files")
    print(f"   Skipped: {skipped_count} files")

    if DRY_RUN:
        print("\n⚠️  DRY RUN MODE - No changes were made")
        print("   Set DRY_RUN = False in the script to apply changes")

if __name__ == "__main__":
    main()
