#!/usr/bin/env python3
"""
Step 2: Fetch Attachment Metadata from API

Fetches attachment metadata from the API for each project/task/subtask
and caches the responses locally.

Input: migration/output/project_list.json
Output: migration/cache/{partition}.json
"""

import boto3
import json
import time
import requests
from pathlib import Path
from collections import defaultdict
from config import (
    AWS_PROFILE, AWS_REGION, SOURCE_BUCKET, SOURCE_PREFIX,
    API_BASE_URL, TENANT_ID, API_RATE_LIMIT_DELAY,
    CACHE_DIR, OUTPUT_DIR
)
from utils import get_partition_from_path, load_json, save_json


def list_all_files(s3_client, bucket: str, project_ids: list) -> list:
    """
    List all files for given projects.

    Returns:
        [
            "organizations/1/projects/949/file.pdf",
            "organizations/1/projects/949/tasks/5/file.txt",
            ...
        ]
    """
    print(f"📂 Listing files for {len(project_ids)} projects...")

    all_files = []

    for project_id in project_ids:
        prefix = f"organizations/{TENANT_ID}/projects/{project_id}/"

        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                # Skip directories and metadata files
                if not key.endswith('/') and not key.endswith('.metadata.json'):
                    all_files.append(key)

    print(f"✅ Found {len(all_files)} files")
    return all_files


def extract_partitions(files: list) -> set:
    """
    Extract unique partitions from file paths.

    Returns:
        {"PROJECT-949", "TASK-5", "SUBTASK-10", ...}
    """
    partitions = set()

    for file_path in files:
        partition = get_partition_from_path(file_path)
        if partition:
            partitions.add(partition)

    return partitions


def fetch_partition_metadata(partition: str) -> list:
    """
    Fetch metadata from API for a given partition.

    Args:
        partition: "PROJECT-949", "TASK-5", etc.

    Returns:
        List of attachment metadata dicts
    """
    url = f"{API_BASE_URL}/organization/{TENANT_ID}/attachments/{partition}/migration"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  API error for {partition}: {e}")
        return []


def main():
    print("=" * 80)
    print("STEP 2: FETCH API METADATA")
    print("=" * 80)
    print()

    # Load project list
    project_list_file = f"{OUTPUT_DIR}/project_list.json"
    project_list = load_json(project_list_file)

    if not project_list:
        print(f"❌ Project list not found: {project_list_file}")
        print("   Run step1_list_projects.py first")
        return

    project_ids = [p["project_id"] for p in project_list]
    print(f"📋 Processing {len(project_ids)} projects")
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client('s3')

    # List all files
    all_files = list_all_files(s3_client, SOURCE_BUCKET, project_ids)

    if not all_files:
        print("❌ No files found")
        return

    # Extract unique partitions
    partitions = extract_partitions(all_files)
    print(f"🔑 Found {len(partitions)} unique partitions to query")
    print()

    # Fetch metadata for each partition
    print("📡 Fetching metadata from API...")

    success_count = 0
    error_count = 0
    cache_stats = defaultdict(int)

    for i, partition in enumerate(sorted(partitions), 1):
        print(f"[{i}/{len(partitions)}] Fetching {partition}...", end=" ")

        # Check cache first
        cache_file = f"{CACHE_DIR}/{partition}.json"
        if Path(cache_file).exists():
            print("(cached)")
            cache_stats["cached"] += 1
            continue

        # Fetch from API
        metadata = fetch_partition_metadata(partition)

        if metadata:
            # Save to cache
            save_json(metadata, cache_file)
            print(f"✅ ({len(metadata)} attachments)")
            success_count += 1
            cache_stats["fetched"] += 1
        else:
            print("⚠️  (no data)")
            error_count += 1
            cache_stats["empty"] += 1

        # Rate limiting
        time.sleep(API_RATE_LIMIT_DELAY)

    print()
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total partitions: {len(partitions)}")
    print(f"Successfully fetched: {success_count}")
    print(f"From cache: {cache_stats['cached']}")
    print(f"Empty responses: {error_count}")
    print(f"\n✅ Cache saved to: {CACHE_DIR}/")
    print()


if __name__ == "__main__":
    main()
