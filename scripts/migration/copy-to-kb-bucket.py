#!/usr/bin/env python3
"""
Script para copiar archivos con metadata de Colpensiones al bucket del Knowledge Base.

Copia de: s3://dev-files-colpensiones/organizations/1/...
A: s3://processapp-docs-v2-dev-708819485463/organization/1/...

Copia ARCHIVOS + sus .metadata.json
"""

import subprocess
import json
from datetime import datetime
from typing import List, Dict

# Configuración
SOURCE_BUCKET = 'dev-files-colpensiones'
DEST_BUCKET = 'processapp-docs-v2-dev-708819485463'
AWS_PROFILE = 'ans-super'
KMS_KEY = 'e6a714f6-70a7-47bf-a9ee-55d871d33cc6'

def copy_project_files(project_id: int, dry_run: bool = True) -> Dict:
    """Copiar archivos de un proyecto al bucket del KB"""

    # Estructura real: organizations/1/projects/{project_id}/
    source_prefix = f'organizations/1/projects/{project_id}/'
    dest_prefix = f'organization/1/projects/{project_id}/'

    source_path = f's3://{SOURCE_BUCKET}/{source_prefix}'
    dest_path = f's3://{DEST_BUCKET}/{dest_prefix}'

    if dry_run:
        print(f"  [DRY RUN] Would copy: {source_path} → {dest_path}")
        return {'project_id': project_id, 'dry_run': True}

    try:
        # Usar aws s3 sync para copiar recursivamente con metadata
        # Solo copiar proyectos que están en STANDARD storage (no archive tier)
        cmd = [
            '/opt/homebrew/bin/aws', 's3', 'sync',
            source_path,
            dest_path,
            '--profile', AWS_PROFILE,
            '--sse', 'aws:kms',
            '--sse-kms-key-id', KMS_KEY,
            '--storage-class', 'STANDARD'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Contar archivos copiados desde stdout
            lines = [l for l in result.stdout.strip().split('\n') if l.startswith('copy:')]
            file_count = len(lines)

            return {
                'project_id': project_id,
                'status': 'success',
                'files_copied': file_count,
                'output': result.stdout[:500]
            }
        else:
            return {
                'project_id': project_id,
                'status': 'error',
                'error': result.stderr[:500]
            }

    except Exception as e:
        return {
            'project_id': project_id,
            'status': 'error',
            'error': str(e)
        }

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Copiar archivos de Colpensiones al bucket del Knowledge Base'
    )
    parser.add_argument(
        '--projects',
        type=str,
        required=True,
        help='Project IDs (e.g., "1,2,4,5" or "1-10")'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - no copy'
    )

    args = parser.parse_args()

    # Parse project IDs
    if '-' in args.projects:
        start, end = map(int, args.projects.split('-'))
        project_ids = list(range(start, end + 1))
    else:
        project_ids = [int(x.strip()) for x in args.projects.split(',')]

    print(f"\n{'='*60}")
    print(f"Copy Colpensiones Files to KB Bucket")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"Projects: {len(project_ids)}")
    print(f"Source: {SOURCE_BUCKET}/organizations/...")
    print(f"Dest: {DEST_BUCKET}/organization/...")
    print(f"{'='*60}\n")

    results = []

    for idx, project_id in enumerate(project_ids, 1):
        print(f"[{idx}/{len(project_ids)}] Project {project_id}")
        result = copy_project_files(project_id, args.dry_run)
        results.append(result)

        if not args.dry_run:
            status = result.get('status', 'unknown')
            if status == 'success':
                print(f"  ✅ Copied {result.get('files_copied', 0)} files")
            elif status == 'error':
                print(f"  ❌ Error: {result.get('error', 'unknown')[:100]}")

    # Summary
    if not args.dry_run:
        successful = [r for r in results if r.get('status') == 'success']
        failed = [r for r in results if r.get('status') == 'error']
        total_files = sum(r.get('files_copied', 0) for r in successful)

        print(f"\n{'='*60}")
        print(f"📊 Copy Summary")
        print(f"{'='*60}")
        print(f"✅ Projects copied: {len(successful)}")
        print(f"❌ Projects failed: {len(failed)}")
        print(f"📄 Total files copied: {total_files}")
        print(f"{'='*60}\n")

        # Save report
        report_file = f'/tmp/copy-report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump({
                'total_projects': len(project_ids),
                'successful': len(successful),
                'failed': len(failed),
                'total_files': total_files,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)

        print(f"📄 Report saved: {report_file}\n")

if __name__ == '__main__':
    main()
