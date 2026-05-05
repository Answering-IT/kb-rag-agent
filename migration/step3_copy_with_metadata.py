#!/usr/bin/env python3
"""
Step 3: Copy Files with Metadata

Copies files from legacy bucket to new bucket with proper metadata.
- Fetches attachment info from cached API responses
- Generates metadata JSON for each file
- Copies file + metadata to destination bucket
- Skips ZIP files (no metadata needed)

Input:
    - migration/output/project_list.json
    - migration/cache/{partition}.json
Output:
    - Files + metadata in destination bucket
    - migration/logs/migration_log.json
"""

import boto3
import json
import time
from pathlib import Path
from collections import defaultdict
from config import (
    AWS_PROFILE, AWS_REGION, SOURCE_BUCKET, DESTINATION_BUCKET,
    KMS_KEY_ID, TENANT_ID, S3_RATE_LIMIT_DELAY,
    CACHE_DIR, OUTPUT_DIR, LOGS_DIR, ALLOWED_EXTENSIONS, IGNORED_EXTENSIONS
)
from utils import (
    parse_s3_path, generate_metadata_json, get_partition_from_path,
    save_json, load_json, should_ignore_file
)


def find_attachment_metadata(file_path: str, file_name: str, cache_dir: str) -> dict:
    """
    Find attachment metadata from cached API responses.

    Args:
        file_path: Full S3 path (e.g., "organizations/1/projects/949/file.pdf")
        file_name: Just the filename (e.g., "file.pdf")
        cache_dir: Path to cache directory

    Returns:
        {
            "attachmentId": 670,
            "name": "file.pdf",
            "type": "NORMAL",
            "path": "organizations/1/projects/949",
            ...
        } or None if not found
    """
    partition = get_partition_from_path(file_path)
    if not partition:
        return None

    cache_file = f"{cache_dir}/{partition}.json"
    cached_data = load_json(cache_file)

    if not cached_data:
        return None

    # Find matching attachment by name
    for attachment in cached_data:
        if attachment.get("name") == file_name:
            return attachment

    return None


def copy_file_with_metadata(
    s3_client,
    source_key: str,
    dest_key: str,
    metadata_json: dict,
    dry_run: bool = False
) -> bool:
    """
    Copy file and create metadata file in destination bucket.

    Returns:
        True if successful, False otherwise
    """
    if dry_run:
        print(f"   [DRY RUN] Would copy: {source_key} -> {dest_key}")
        return True

    try:
        # Copy file
        copy_source = {'Bucket': SOURCE_BUCKET, 'Key': source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=DESTINATION_BUCKET,
            Key=dest_key,
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID
        )

        # Create metadata file
        metadata_key = f"{dest_key}.metadata.json"
        s3_client.put_object(
            Bucket=DESTINATION_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata_json, indent=2),
            ContentType='application/json',
            ServerSideEncryption='aws:kms',
            SSEKMSKeyId=KMS_KEY_ID
        )

        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


def main(dry_run: bool = False):
    print("=" * 80)
    print("STEP 3: COPY FILES WITH METADATA" + (" (DRY RUN)" if dry_run else ""))
    print("=" * 80)
    print()

    # Load project list
    project_list_file = f"{OUTPUT_DIR}/project_list.json"
    project_list = load_json(project_list_file)

    if not project_list:
        print(f"❌ Project list not found: {project_list_file}")
        return

    project_ids = [p["project_id"] for p in project_list]
    print(f"📋 Processing {len(project_ids)} projects")
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client('s3')

    # Statistics
    stats = defaultdict(int)
    migration_log = []

    # Process each project
    for proj_idx, project_id in enumerate(project_ids, 1):
        print(f"\n[{proj_idx}/{len(project_ids)}] Processing Project {project_id}")
        print("-" * 60)

        prefix = f"organizations/{TENANT_ID}/projects/{project_id}/"

        # List all files in project
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=SOURCE_BUCKET, Prefix=prefix)

        project_files = []
        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                # Skip directories and existing metadata files
                if not key.endswith('/') and not key.endswith('.metadata.json'):
                    project_files.append(key)

        print(f"   Found {len(project_files)} files")

        # Process each file
        for file_idx, source_key in enumerate(project_files, 1):
            file_name = Path(source_key).name

            # Check if should be ignored (ZIP files)
            if should_ignore_file(file_name, IGNORED_EXTENSIONS):
                print(f"   [{file_idx}/{len(project_files)}] ⏭️  SKIP (ignored): {file_name}")
                stats["ignored"] += 1
                migration_log.append({
                    "source_key": source_key,
                    "status": "ignored",
                    "reason": "File extension in IGNORED_EXTENSIONS"
                })
                continue

            print(f"   [{file_idx}/{len(project_files)}] {file_name}...", end=" ")

            # Parse path to get IDs
            parsed = parse_s3_path(source_key, TENANT_ID)

            # Try to find attachment metadata from API cache
            attachment_meta = find_attachment_metadata(source_key, file_name, CACHE_DIR)

            if attachment_meta:
                # Use full metadata from API
                metadata_json = generate_metadata_json(
                    tenant_id=parsed["tenant_id"],
                    project_id=parsed["project_id"],
                    task_id=parsed["task_id"],
                    subtask_id=parsed["subtask_id"],
                    attachment_id=str(attachment_meta.get("attachmentId")),
                    file_name=attachment_meta.get("name"),
                    attachment_type=attachment_meta.get("type"),
                    project_path=attachment_meta.get("path")
                )
                print("✅ (with API metadata)", end=" ")
                stats["with_api"] += 1
            else:
                # Fallback: generate metadata from path only
                metadata_json = generate_metadata_json(
                    tenant_id=parsed["tenant_id"],
                    project_id=parsed["project_id"],
                    task_id=parsed["task_id"],
                    subtask_id=parsed["subtask_id"]
                )
                print("⚠️  (fallback metadata)", end=" ")
                stats["fallback"] += 1

            # Destination key (same path structure)
            dest_key = source_key

            # Copy file + metadata
            success = copy_file_with_metadata(
                s3_client,
                source_key,
                dest_key,
                metadata_json,
                dry_run=dry_run
            )

            if success:
                print("→ Copied")
                stats["success"] += 1
                migration_log.append({
                    "source_key": source_key,
                    "dest_key": dest_key,
                    "status": "success",
                    "metadata_source": "api" if attachment_meta else "fallback",
                    "partition_key": metadata_json["metadataAttributes"]["partition_key"]
                })
            else:
                stats["error"] += 1
                migration_log.append({
                    "source_key": source_key,
                    "status": "error"
                })

            # Rate limiting
            if not dry_run:
                time.sleep(S3_RATE_LIMIT_DELAY)

    # Save migration log
    log_file = f"{LOGS_DIR}/migration_log.json"
    save_json(migration_log, log_file)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {stats['success'] + stats['error'] + stats['ignored']}")
    print(f"✅ Successfully migrated: {stats['success']}")
    print(f"   - With API metadata: {stats['with_api']}")
    print(f"   - Fallback metadata: {stats['fallback']}")
    print(f"⏭️  Ignored (ZIP files): {stats['ignored']}")
    print(f"❌ Errors: {stats['error']}")
    print(f"\n📝 Migration log saved to: {log_file}")
    print()


if __name__ == "__main__":
    import sys

    # Check for --dry-run flag
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("🔍 Running in DRY RUN mode (no changes will be made)\n")

    main(dry_run=dry_run)
