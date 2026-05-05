#!/usr/bin/env python3
"""
Step 4: Validate Migration

Validates that all files have proper metadata in the destination bucket.

Output: migration/logs/validation_report.json
"""

import boto3
import json
from collections import defaultdict
from config import (
    AWS_PROFILE, AWS_REGION, DESTINATION_BUCKET,
    TENANT_ID, LOGS_DIR, OUTPUT_DIR, IGNORED_EXTENSIONS
)
from utils import load_json, save_json, should_ignore_file
from pathlib import Path


def validate_metadata_file(s3_client, bucket: str, file_key: str) -> dict:
    """
    Validate that a file has proper metadata.

    Returns:
        {
            "has_metadata": True/False,
            "metadata_valid": True/False,
            "required_fields": ["tenant_id", "partition_key", ...],
            "missing_fields": [...],
            "errors": [...]
        }
    """
    metadata_key = f"{file_key}.metadata.json"
    result = {
        "has_metadata": False,
        "metadata_valid": False,
        "required_fields": ["tenant_id", "partition_key"],
        "missing_fields": [],
        "errors": []
    }

    try:
        # Check if metadata file exists
        response = s3_client.get_object(Bucket=bucket, Key=metadata_key)
        result["has_metadata"] = True

        # Parse metadata
        metadata_content = response['Body'].read().decode('utf-8')
        metadata = json.loads(metadata_content)

        # Validate structure
        if "metadataAttributes" not in metadata:
            result["errors"].append("Missing 'metadataAttributes' wrapper")
            return result

        attrs = metadata["metadataAttributes"]

        # Check required fields
        for field in result["required_fields"]:
            if field not in attrs:
                result["missing_fields"].append(field)

        if not result["missing_fields"]:
            result["metadata_valid"] = True

    except s3_client.exceptions.NoSuchKey:
        result["errors"].append("Metadata file not found")
    except json.JSONDecodeError as e:
        result["has_metadata"] = True
        result["errors"].append(f"Invalid JSON: {e}")
    except Exception as e:
        result["errors"].append(f"Validation error: {e}")

    return result


def main():
    print("=" * 80)
    print("STEP 4: VALIDATE MIGRATION")
    print("=" * 80)
    print()

    # Load project list
    project_list_file = f"{OUTPUT_DIR}/project_list.json"
    project_list = load_json(project_list_file)

    if not project_list:
        print(f"❌ Project list not found: {project_list_file}")
        return

    project_ids = [p["project_id"] for p in project_list]
    print(f"📋 Validating {len(project_ids)} projects")
    print()

    # Initialize S3 client
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    s3_client = session.client('s3')

    # Statistics
    stats = defaultdict(int)
    validation_results = []

    # Process each project
    for proj_idx, project_id in enumerate(project_ids, 1):
        print(f"[{proj_idx}/{len(project_ids)}] Validating Project {project_id}...", end=" ")

        prefix = f"organizations/{TENANT_ID}/projects/{project_id}/"

        # List all files
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=DESTINATION_BUCKET, Prefix=prefix)

        project_files = []
        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                # Skip directories and metadata files themselves
                if not key.endswith('/') and not key.endswith('.metadata.json'):
                    project_files.append(key)

        project_stats = defaultdict(int)

        # Validate each file
        for file_key in project_files:
            file_name = Path(file_key).name

            # Skip ignored files
            if should_ignore_file(file_name, IGNORED_EXTENSIONS):
                stats["ignored"] += 1
                project_stats["ignored"] += 1
                continue

            validation = validate_metadata_file(s3_client, DESTINATION_BUCKET, file_key)

            if validation["metadata_valid"]:
                stats["valid"] += 1
                project_stats["valid"] += 1
            elif validation["has_metadata"]:
                stats["invalid"] += 1
                project_stats["invalid"] += 1
                validation_results.append({
                    "file": file_key,
                    "status": "invalid",
                    "issues": validation["errors"] + [f"Missing: {', '.join(validation['missing_fields'])}"]
                })
            else:
                stats["missing"] += 1
                project_stats["missing"] += 1
                validation_results.append({
                    "file": file_key,
                    "status": "missing",
                    "issues": validation["errors"]
                })

        # Print project summary
        total = project_stats["valid"] + project_stats["invalid"] + project_stats["missing"]
        if total > 0:
            print(f"✅ {project_stats['valid']}/{total} valid", end="")
            if project_stats["invalid"] > 0:
                print(f", ⚠️  {project_stats['invalid']} invalid", end="")
            if project_stats["missing"] > 0:
                print(f", ❌ {project_stats['missing']} missing", end="")
            print()
        else:
            print("(no files)")

    # Save validation report
    report = {
        "summary": {
            "total_files": stats["valid"] + stats["invalid"] + stats["missing"],
            "valid": stats["valid"],
            "invalid": stats["invalid"],
            "missing": stats["missing"],
            "ignored": stats["ignored"]
        },
        "issues": validation_results
    }

    report_file = f"{LOGS_DIR}/validation_report.json"
    save_json(report, report_file)

    # Print summary
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total files checked: {report['summary']['total_files']}")
    print(f"✅ Valid metadata: {stats['valid']}")
    print(f"⚠️  Invalid metadata: {stats['invalid']}")
    print(f"❌ Missing metadata: {stats['missing']}")
    print(f"⏭️  Ignored files: {stats['ignored']}")

    if validation_results:
        print(f"\n⚠️  Found {len(validation_results)} issues")
        print(f"📝 Details saved to: {report_file}")

        # Print first 10 issues
        print("\n📋 Sample issues (first 10):")
        for i, issue in enumerate(validation_results[:10], 1):
            print(f"   {i}. {issue['file']}")
            print(f"      Status: {issue['status']}")
            print(f"      Issues: {', '.join(issue['issues'])}")

        if len(validation_results) > 10:
            print(f"   ... and {len(validation_results) - 10} more (see report)")
    else:
        print("\n✅ All files have valid metadata!")

    print()


if __name__ == "__main__":
    main()
