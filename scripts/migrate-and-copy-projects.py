#!/usr/bin/env python3
"""
Script integrado de migración de proyectos Colpensiones al Knowledge Base.

Proceso:
1. Genera metadata (.metadata.json) para archivos en dev-files-colpensiones
2. Verifica que cada archivo tenga su metadata
3. Copia archivos + metadata a processapp-docs-v2-dev/organization/

Uso:
    python3 migrate-and-copy-projects.py --projects 6548-6647 --dry-run
    python3 migrate-and-copy-projects.py --projects 6548-6647 --tenant-id 1
"""

import subprocess
import requests
import json
import tempfile
import os
from datetime import datetime
from typing import Dict, List, Optional

# Configuración
API_BASE = 'https://dev.app.colpensiones.procesapp.com'
SOURCE_BUCKET = 'dev-files-colpensiones'
DEST_BUCKET = 'processapp-docs-v2-dev-708819485463'
AWS_PROFILE = 'ans-super'
KMS_KEY = 'e6a714f6-70a7-47bf-a9ee-55d871d33cc6'

# ============================================================================
# PASO 1: Generar Metadata
# ============================================================================

def get_attachments(tenant_id: int, partition_id: str) -> List[Dict]:
    """Obtener lista de attachments desde API"""
    url = f"{API_BASE}/organization/{tenant_id}/attachments/{partition_id}/migration"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return []

def get_attachment_metadata_detailed(tenant_id: int, attachment_id: int) -> Optional[Dict]:
    """Obtener metadata detallada, retorna None si no existe"""
    url = f"{API_BASE}/organization/{tenant_id}/attachments/{attachment_id}/metadata"
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except:
        return None

def extract_ids_from_attachment(att: Dict, tenant_id: int) -> Dict:
    """Extraer IDs desde el attachment"""
    metadata = {
        'tenant_id': tenant_id,
        'attachment_id': att.get('attachmentId', 1),
        'file_name': att.get('name', ''),
        'attachment_type': att.get('type', 'NORMAL'),
        'project_path': att.get('path', '')
    }

    path = att.get('path', '')
    path_parts = path.split('/')

    if 'projects' in path_parts:
        idx = path_parts.index('projects')
        if idx + 1 < len(path_parts):
            try:
                metadata['project_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    if 'tasks' in path_parts:
        idx = path_parts.index('tasks')
        if idx + 1 < len(path_parts):
            try:
                metadata['task_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    if 'subtasks' in path_parts:
        idx = path_parts.index('subtasks')
        if idx + 1 < len(path_parts):
            try:
                metadata['subtask_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    return metadata

def build_partition_key(metadata: Dict) -> str:
    """Construir partition_key: t{tenant}_p{project}[_t{task}][_s{subtask}]"""
    parts = [f"t{metadata['tenant_id']}"]

    if metadata.get('project_id'):
        parts.append(f"p{metadata['project_id']}")

    if metadata.get('task_id'):
        parts.append(f"t{metadata['task_id']}")

    if metadata.get('subtask_id'):
        parts.append(f"s{metadata['subtask_id']}")

    return "_".join(parts)

def build_project_path(metadata: Dict) -> str:
    """Construir ruta jerárquica"""
    if metadata.get('project_path'):
        return metadata['project_path']

    paths = [f"organization/{metadata['tenant_id']}"]

    if metadata.get('project_id'):
        paths.append(f"projects/{metadata['project_id']}")

    if metadata.get('task_id'):
        paths.append(f"tasks/{metadata['task_id']}")

    if metadata.get('subtask_id'):
        paths.append(f"subtasks/{metadata['subtask_id']}")

    return "/".join(paths)

def create_metadata_json(metadata: Dict) -> Dict:
    """Crear estructura de metadata"""
    filterable = {"tenant_id": metadata['tenant_id']}

    if metadata.get('project_id') is not None:
        filterable['project_id'] = metadata['project_id']

    if metadata.get('task_id') is not None:
        filterable['task_id'] = metadata['task_id']

    if metadata.get('subtask_id') is not None:
        filterable['subtask_id'] = metadata['subtask_id']

    filterable['partition_key'] = build_partition_key(metadata)

    non_filterable = {
        'attachment_id': metadata.get('attachment_id', 1),
        'file_name': metadata.get('file_name', ''),
        'attachment_type': metadata.get('attachment_type', 'NORMAL'),
        'project_path': build_project_path(metadata)
    }

    return {
        "metadataAttributes": {
            **filterable,
            **non_filterable
        }
    }

def list_files_in_s3_folder(folder_path: str) -> List[str]:
    """Listar archivos reales en S3"""
    try:
        cmd = [
            '/opt/homebrew/bin/aws', 's3', 'ls',
            f's3://{SOURCE_BUCKET}/{folder_path}/',
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
                if not key.endswith('/') and not key.endswith('.metadata.json'):
                    files.append(key)

        return files
    except Exception:
        return []

def create_metadata_file(file_key: str, metadata_json: Dict, dry_run: bool = True) -> bool:
    """Crear archivo .metadata.json en S3"""
    metadata_key = f"{file_key}.metadata.json"

    if dry_run:
        return True

    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(metadata_json, tmp, indent=2)
            tmp_path = tmp.name

        result = subprocess.run(
            ['/opt/homebrew/bin/aws', 's3', 'cp', tmp_path,
             f's3://{SOURCE_BUCKET}/{metadata_key}', '--profile', AWS_PROFILE],
            capture_output=True,
            text=True
        )

        os.unlink(tmp_path)
        return result.returncode == 0
    except Exception:
        return False

def generate_metadata_for_project(tenant_id: int, project_id: int, dry_run: bool = True) -> Dict:
    """Generar metadata para todos los archivos de un proyecto"""
    partition_id = f"PROJECT-{project_id}"

    try:
        attachments = get_attachments(tenant_id, partition_id)
        if not attachments:
            return {'status': 'no_attachments', 'files_processed': 0}

        first_att = attachments[0]
        folder_path = first_att.get('path', '')

        if not folder_path:
            return {'status': 'no_path', 'files_processed': 0}

        s3_files = list_files_in_s3_folder(folder_path)

        if not s3_files:
            return {'status': 'no_files', 'files_processed': 0}

        # Obtener metadata del proyecto
        attachment_id = first_att.get('attachmentId')
        detailed_metadata = None

        if attachment_id:
            detailed_metadata = get_attachment_metadata_detailed(tenant_id, attachment_id)

        if detailed_metadata:
            project_metadata = detailed_metadata
            project_metadata['tenant_id'] = tenant_id
        else:
            project_metadata = extract_ids_from_attachment(first_att, tenant_id)

        # Crear metadata para cada archivo
        processed = 0
        for file_key in s3_files:
            file_name = file_key.split('/')[-1]
            file_metadata = project_metadata.copy()
            file_metadata['file_name'] = file_name

            metadata_json = create_metadata_json(file_metadata)

            if create_metadata_file(file_key, metadata_json, dry_run):
                processed += 1

        return {
            'status': 'success',
            'files_processed': processed,
            'partition_key': metadata_json['metadataAttributes']['partition_key']
        }

    except Exception as e:
        return {'status': 'error', 'error': str(e), 'files_processed': 0}

# ============================================================================
# PASO 2: Verificar y Copiar al KB Bucket
# ============================================================================

def check_files_have_metadata(project_id: int) -> Dict:
    """Verificar que todos los archivos tengan su .metadata.json"""
    folder_path = f'organizations/1/projects/{project_id}/'

    try:
        cmd = [
            '/opt/homebrew/bin/aws', 's3', 'ls',
            f's3://{SOURCE_BUCKET}/{folder_path}',
            '--recursive',
            '--profile', AWS_PROFILE
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            return {'valid': False, 'reason': 'folder_not_found'}

        files = []
        metadata_files = []

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                key = ' '.join(parts[3:])
                if key.endswith('.metadata.json'):
                    metadata_files.append(key.replace('.metadata.json', ''))
                elif not key.endswith('/'):
                    files.append(key)

        # Verificar que cada archivo tenga su metadata
        missing_metadata = []
        for file_key in files:
            if file_key not in metadata_files:
                missing_metadata.append(file_key.split('/')[-1])

        if missing_metadata:
            return {
                'valid': False,
                'reason': 'missing_metadata',
                'missing': missing_metadata,
                'total_files': len(files)
            }

        return {
            'valid': True,
            'total_files': len(files),
            'total_pairs': len(files)
        }

    except Exception as e:
        return {'valid': False, 'reason': str(e)}

def copy_project_to_kb_bucket(project_id: int, dry_run: bool = True) -> Dict:
    """Copiar proyecto completo al bucket del KB"""

    # Verificar primero
    check_result = check_files_have_metadata(project_id)

    if not check_result['valid']:
        return {
            'status': 'skipped',
            'reason': check_result['reason'],
            'details': check_result
        }

    if dry_run:
        return {
            'status': 'dry_run',
            'files_to_copy': check_result['total_files'] * 2  # file + metadata
        }

    source_path = f's3://{SOURCE_BUCKET}/organizations/1/projects/{project_id}/'
    dest_path = f's3://{DEST_BUCKET}/organization/1/projects/{project_id}/'

    try:
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

        if result.returncode != 0:
            return {
                'status': 'error',
                'error': result.stderr[:200]
            }

        # Contar archivos copiados
        lines = [l for l in result.stdout.strip().split('\n') if l.startswith('copy:')]

        return {
            'status': 'success',
            'files_copied': len(lines)
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Migrar proyectos Colpensiones al Knowledge Base (metadata + copy)'
    )
    parser.add_argument(
        '--projects',
        type=str,
        required=True,
        help='Project IDs (e.g., "6548-6647" or "1,2,3")'
    )
    parser.add_argument(
        '--tenant-id',
        type=int,
        default=1,
        help='Tenant ID (default: 1)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode'
    )
    parser.add_argument(
        '--skip-metadata-generation',
        action='store_true',
        help='Skip metadata generation (only verify and copy)'
    )

    args = parser.parse_args()

    # Parse project IDs
    if '-' in args.projects:
        start, end = map(int, args.projects.split('-'))
        project_ids = list(range(start, end + 1))
    else:
        project_ids = [int(x.strip()) for x in args.projects.split(',')]

    print(f"\n{'='*70}")
    print(f"Colpensiones Project Migration to Knowledge Base")
    print(f"{'='*70}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"Tenant: {args.tenant_id}")
    print(f"Projects: {len(project_ids)} ({min(project_ids)}-{max(project_ids)})")
    print(f"Source: {SOURCE_BUCKET}/organizations/1/projects/")
    print(f"Dest: {DEST_BUCKET}/organization/1/projects/")
    print(f"{'='*70}\n")

    metadata_results = []
    copy_results = []

    for idx, project_id in enumerate(project_ids, 1):
        print(f"\n[{idx}/{len(project_ids)}] Project {project_id}")

        # PASO 1: Generar metadata
        if not args.skip_metadata_generation:
            print(f"  → Generating metadata...")
            metadata_result = generate_metadata_for_project(
                args.tenant_id,
                project_id,
                args.dry_run
            )
            metadata_results.append({
                'project_id': project_id,
                **metadata_result
            })

            if metadata_result['status'] == 'success':
                print(f"    ✅ {metadata_result['files_processed']} files")
            elif metadata_result['status'] == 'no_files':
                print(f"    ⚠️  No files in S3")
                continue
            else:
                print(f"    ❌ {metadata_result.get('status')}")
                continue

        # PASO 2: Verificar y copiar
        print(f"  → Verifying and copying...")
        copy_result = copy_project_to_kb_bucket(project_id, args.dry_run)
        copy_results.append({
            'project_id': project_id,
            **copy_result
        })

        if copy_result['status'] == 'success':
            print(f"    ✅ Copied {copy_result['files_copied']} files")
        elif copy_result['status'] == 'dry_run':
            print(f"    [DRY RUN] Would copy {copy_result['files_to_copy']} files")
        elif copy_result['status'] == 'skipped':
            print(f"    ⚠️  Skipped: {copy_result['reason']}")
        else:
            print(f"    ❌ {copy_result.get('error', 'Unknown error')[:50]}")

    # Summary
    print(f"\n{'='*70}")
    print(f"📊 Migration Summary")
    print(f"{'='*70}")

    if not args.skip_metadata_generation:
        successful_metadata = [r for r in metadata_results if r.get('status') == 'success']
        print(f"Metadata Generation:")
        print(f"  ✅ Success: {len(successful_metadata)} projects")
        print(f"  📄 Files processed: {sum(r.get('files_processed', 0) for r in successful_metadata)}")

    successful_copies = [r for r in copy_results if r.get('status') == 'success']
    skipped = [r for r in copy_results if r.get('status') == 'skipped']

    print(f"\nCopy to KB Bucket:")
    print(f"  ✅ Copied: {len(successful_copies)} projects")
    print(f"  ⚠️  Skipped: {len(skipped)} projects")

    if not args.dry_run:
        total_copied = sum(r.get('files_copied', 0) for r in successful_copies)
        print(f"  📄 Total files: {total_copied}")

    print(f"{'='*70}\n")

    # Save report
    if not args.dry_run:
        report_file = f'/tmp/migration-full-report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump({
                'metadata_results': metadata_results,
                'copy_results': copy_results,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        print(f"📄 Full report: {report_file}\n")

if __name__ == '__main__':
    main()
