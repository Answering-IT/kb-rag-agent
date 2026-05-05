#!/usr/bin/env python3
"""
Copiar archivos de Colpensiones al bucket del KB via download/upload.
Necesario porque los archivos están en INTELLIGENT_TIERING archive tier.
"""

import subprocess
import json
import tempfile
import os
from datetime import datetime
from typing import List, Dict

SOURCE_BUCKET = 'dev-files-colpensiones'
DEST_BUCKET = 'processapp-docs-v2-dev-708819485463'
AWS_PROFILE = 'ans-super'
KMS_KEY = 'e6a714f6-70a7-47bf-a9ee-55d871d33cc6'

def list_project_files(project_id: int) -> List[str]:
    """Listar archivos de un proyecto"""
    source_prefix = f'organizations/1/projects/{project_id}/'

    cmd = [
        '/opt/homebrew/bin/aws', 's3', 'ls',
        f's3://{SOURCE_BUCKET}/{source_prefix}',
        '--recursive',
        '--profile', AWS_PROFILE
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return []

    files = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 4:
            key = ' '.join(parts[3:])
            files.append(key)

    return files

def copy_file_via_download(source_key: str, dest_key: str) -> Dict:
    """Copiar un archivo via download/upload"""

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_file = os.path.join(tmpdir, 'file')

            # Download
            download_cmd = [
                '/opt/homebrew/bin/aws', 's3', 'cp',
                f's3://{SOURCE_BUCKET}/{source_key}',
                tmp_file,
                '--profile', AWS_PROFILE
            ]

            result = subprocess.run(download_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': f'Download failed: {result.stderr[:200]}'
                }

            # Upload
            upload_cmd = [
                '/opt/homebrew/bin/aws', 's3', 'cp',
                tmp_file,
                f's3://{DEST_BUCKET}/{dest_key}',
                '--profile', AWS_PROFILE,
                '--sse', 'aws:kms',
                '--sse-kms-key-id', KMS_KEY
            ]

            result = subprocess.run(upload_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return {
                    'status': 'error',
                    'error': f'Upload failed: {result.stderr[:200]}'
                }

            return {'status': 'success'}

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def copy_project(project_id: int, dry_run: bool = True) -> Dict:
    """Copiar todos los archivos de un proyecto"""

    files = list_project_files(project_id)

    if not files:
        return {
            'project_id': project_id,
            'status': 'no_files',
            'files_copied': 0
        }

    if dry_run:
        print(f"  [DRY RUN] Would copy {len(files)} files")
        return {
            'project_id': project_id,
            'status': 'dry_run',
            'files_copied': len(files)
        }

    copied = 0
    failed = 0

    for file_key in files:
        # Cambiar organizations/1/ por organization/1/
        dest_key = file_key.replace('organizations/', 'organization/', 1)

        result = copy_file_via_download(file_key, dest_key)

        if result['status'] == 'success':
            copied += 1
            file_name = file_key.split('/')[-1]
            print(f"    ✅ {file_name}")
        else:
            failed += 1
            print(f"    ❌ {file_key.split('/')[-1]}: {result['error'][:50]}")

    return {
        'project_id': project_id,
        'status': 'success',
        'files_copied': copied,
        'files_failed': failed
    }

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--projects', type=str, required=True)
    parser.add_argument('--dry-run', action='store_true')

    args = parser.parse_args()

    # Parse projects
    if '-' in args.projects:
        start, end = map(int, args.projects.split('-'))
        project_ids = list(range(start, end + 1))
    else:
        project_ids = [int(x.strip()) for x in args.projects.split(',')]

    print(f"\n{'='*60}")
    print(f"Copy via Download/Upload")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"Projects: {len(project_ids)}")
    print(f"{'='*60}\n")

    results = []

    for idx, project_id in enumerate(project_ids, 1):
        print(f"[{idx}/{len(project_ids)}] Project {project_id}")
        result = copy_project(project_id, args.dry_run)
        results.append(result)

    # Summary
    if not args.dry_run:
        total_copied = sum(r.get('files_copied', 0) for r in results)
        total_failed = sum(r.get('files_failed', 0) for r in results)

        print(f"\n{'='*60}")
        print(f"📊 Summary")
        print(f"{'='*60}")
        print(f"✅ Files copied: {total_copied}")
        print(f"❌ Files failed: {total_failed}")
        print(f"{'='*60}\n")

        report_file = f'/tmp/copy-download-report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump({
                'total_copied': total_copied,
                'total_failed': total_failed,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        print(f"📄 Report: {report_file}\n")

if __name__ == '__main__':
    main()
