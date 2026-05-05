#!/usr/bin/env python3
"""
Step 1: List Recent Projects

Lists all projects in the legacy bucket and selects the most recent 200
based on last modified date.

Output: migration/output/project_list.json
"""

import boto3
import json
from datetime import datetime
from collections import defaultdict
from config import (
    AWS_PROFILE, AWS_REGION, SOURCE_BUCKET, SOURCE_PREFIX,
    MAX_PROJECTS, OUTPUT_DIR
)
from utils import save_json

def list_all_projects(s3_client, bucket: str, prefix: str) -> dict:
    """
    List all projects and their last modified dates.

    Returns:
        {
            "949": "2025-01-22T18:14:16.634655",
            "950": "2025-01-23T10:30:45.123456",
            ...
        }
    """
    print(f"📂 Listing projects in s3://{bucket}/{prefix}")

    projects = defaultdict(lambda: None)
    paginator = s3_client.get_paginator('list_objects_v2')

    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    for page in pages:
        if 'Contents' not in page:
            continue

        for obj in page['Contents']:
            key = obj['Key']
            last_modified = obj['LastModified']

            # Extract project_id from path
            # Format: organizations/1/projects/{project_id}/...
            parts = key.split('/')
            if len(parts) >= 4 and parts[2] == "projects":
                project_id = parts[3]

                # Keep the most recent last_modified for each project
                if projects[project_id] is None or last_modified > projects[project_id]:
                    projects[project_id] = last_modified

    print(f"✅ Found {len(projects)} unique projects")
    return projects


def select_recent_projects(projects: dict, max_count: int) -> list:
    """
    Select most recent projects based on last modified date.

    Returns:
        [
            {"project_id": "949", "last_modified": "2025-01-22T18:14:16.634655"},
            ...
        ]
    """
    # Sort by last_modified (descending)
    sorted_projects = sorted(
        projects.items(),
        key=lambda x: x[1],
        reverse=True
    )

    # Take top N
    recent = sorted_projects[:max_count]

    # Convert to list of dicts
    result = [
        {
            "project_id": project_id,
            "last_modified": last_modified.isoformat()
        }
        for project_id, last_modified in recent
    ]

    print(f"📊 Selected {len(result)} most recent projects")
    return result


def main():
    print("=" * 80)
    print("STEP 1: LIST RECENT PROJECTS")
    print("=" * 80)
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client('s3')

    # List all projects
    projects = list_all_projects(s3_client, SOURCE_BUCKET, SOURCE_PREFIX)

    if not projects:
        print("❌ No projects found")
        return

    # Select recent projects
    recent_projects = select_recent_projects(projects, MAX_PROJECTS)

    # Save to JSON
    output_file = f"{OUTPUT_DIR}/project_list.json"
    save_json(recent_projects, output_file)

    print(f"\n✅ Saved project list to: {output_file}")
    print(f"📊 Total projects to migrate: {len(recent_projects)}")

    # Print sample
    print("\n📋 Sample (first 10 projects):")
    for i, project in enumerate(recent_projects[:10], 1):
        print(f"   {i}. Project {project['project_id']} (last modified: {project['last_modified']})")

    if len(recent_projects) > 10:
        print(f"   ... and {len(recent_projects) - 10} more")

    print()


if __name__ == "__main__":
    main()
