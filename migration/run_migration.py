#!/usr/bin/env python3
"""
Master Migration Script

Executes all migration steps in sequence:
1. List recent projects
2. Fetch API metadata
3. Copy files with metadata
4. Validate migration

Usage:
    python3 migration/run_migration.py [--dry-run] [--skip-step STEP]
"""

import sys
import subprocess
from pathlib import Path

STEPS = [
    {
        "name": "List Recent Projects",
        "script": "step1_list_projects.py",
        "description": "Lists the 200 most recent projects from legacy bucket"
    },
    {
        "name": "Fetch API Metadata",
        "script": "step2_fetch_api_metadata.py",
        "description": "Fetches attachment metadata from API and caches locally"
    },
    {
        "name": "Copy Files with Metadata",
        "script": "step3_copy_with_metadata.py",
        "description": "Copies files to destination bucket with proper metadata"
    },
    {
        "name": "Validate Migration",
        "script": "step4_validate.py",
        "description": "Validates that all files have proper metadata"
    }
]


def run_step(step_num: int, dry_run: bool = False) -> bool:
    """
    Run a single migration step.

    Returns:
        True if successful, False otherwise
    """
    if step_num < 1 or step_num > len(STEPS):
        print(f"❌ Invalid step number: {step_num}")
        return False

    step = STEPS[step_num - 1]
    script_path = Path(__file__).parent / step["script"]

    print("\n" + "=" * 80)
    print(f"STEP {step_num}: {step['name']}")
    print("=" * 80)
    print(f"Description: {step['description']}")
    print(f"Script: {step['script']}")
    print()

    # Build command
    cmd = [sys.executable, str(script_path)]
    if dry_run and step_num == 3:  # Only step 3 supports dry-run
        cmd.append("--dry-run")

    # Run script
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ Step {step_num} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Step {step_num} failed with exit code {e.returncode}")
        return False


def main():
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    skip_steps = []

    for i, arg in enumerate(sys.argv):
        if arg == "--skip-step" and i + 1 < len(sys.argv):
            try:
                skip_steps.append(int(sys.argv[i + 1]))
            except ValueError:
                print(f"⚠️  Invalid step number: {sys.argv[i + 1]}")

    print("=" * 80)
    print("🚀 MIGRATION MASTER SCRIPT")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'PRODUCTION'}")
    if skip_steps:
        print(f"Skipping steps: {', '.join(map(str, skip_steps))}")
    print()

    # Show plan
    print("📋 Migration Plan:")
    for i, step in enumerate(STEPS, 1):
        status = "⏭️  SKIP" if i in skip_steps else "▶️  RUN"
        print(f"   {status} Step {i}: {step['name']}")
    print()

    # Confirm
    if not dry_run:
        response = input("⚠️  This will modify S3 buckets. Continue? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Migration cancelled")
            return

    # Run steps
    for step_num in range(1, len(STEPS) + 1):
        if step_num in skip_steps:
            print(f"\n⏭️  Skipping Step {step_num}")
            continue

        success = run_step(step_num, dry_run=dry_run)

        if not success:
            print(f"\n❌ Migration stopped at Step {step_num}")
            print("   Fix the errors and re-run with --skip-step to continue")
            return

    # Final summary
    print("\n" + "=" * 80)
    print("🎉 MIGRATION COMPLETE!")
    print("=" * 80)
    print("Next steps:")
    print("   1. Review validation report: migration/logs/validation_report.json")
    print("   2. Trigger KB ingestion job:")
    print("      aws bedrock-agent start-ingestion-job \\")
    print("        --knowledge-base-id BLJTRDGQI0 \\")
    print("        --data-source-id B1OGNN9EMU \\")
    print("        --profile ans-super")
    print()


if __name__ == "__main__":
    main()
