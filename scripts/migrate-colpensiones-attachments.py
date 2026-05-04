#!/usr/bin/env python3
"""
Script de migración de metadata para attachments de Colpensiones.

Este script SOLO crea archivos .metadata.json junto a los archivos existentes en S3.
NO copia archivos - los archivos ya están en dev-files-colpensiones.

Uso:
    python3 migrate-colpensiones-attachments.py --dry-run
    python3 migrate-colpensiones-attachments.py --tenant-id 1 --projects 1-100
"""

import boto3
import requests
import json
import argparse
import subprocess
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
import os

# Configuración
API_BASE = os.getenv('API_BASE', 'https://dev.app.colpensiones.procesapp.com')
BUCKET = os.getenv('BUCKET', 'dev-files-colpensiones')
AWS_PROFILE = 'ans-super'  # Always use ans-super profile

def get_attachments(tenant_id: int, partition_id: str) -> List[Dict]:
    """Obtener lista de attachment IDs desde API"""
    url = f"{API_BASE}/organization/{tenant_id}/attachments/{partition_id}/migration"
    print(f"  📡 GET {url}")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Error fetching attachments: {e}")
        return []

def get_attachment_metadata_detailed(tenant_id: int, attachment_id: int) -> Optional[Dict]:
    """
    Obtener metadata detallada de un attachment específico.
    Si falla (404), retorna None para usar fallback.
    """
    url = f"{API_BASE}/organization/{tenant_id}/attachments/{attachment_id}/metadata"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None  # Not found - usar fallback
        print(f"    ⚠️  HTTP {e.response.status_code} fetching metadata for {attachment_id}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"    ⚠️  Error fetching metadata: {e}")
        return None

def extract_ids_from_attachment(att: Dict, tenant_id: int) -> Dict:
    """
    Extraer IDs de tenant, project, task, subtask desde el attachment.

    partitionId format: PROJECT-123, TASK-456, SUBTASK-789
    path format: organizations/1/projects/123/tasks/456/subtasks/789
    """
    metadata = {
        'tenant_id': tenant_id,
        'attachment_id': att.get('attachmentId'),
        'file_name': att.get('name', ''),
        'attachment_type': att.get('type', ''),
        'project_path': att.get('path', '')
    }

    # Extraer IDs del path: organizations/1/projects/123/tasks/456
    path = att.get('path', '')
    path_parts = path.split('/')

    # Buscar project_id
    if 'projects' in path_parts:
        idx = path_parts.index('projects')
        if idx + 1 < len(path_parts):
            try:
                metadata['project_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    # Buscar task_id
    if 'tasks' in path_parts:
        idx = path_parts.index('tasks')
        if idx + 1 < len(path_parts):
            try:
                metadata['task_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    # Buscar subtask_id
    if 'subtasks' in path_parts:
        idx = path_parts.index('subtasks')
        if idx + 1 < len(path_parts):
            try:
                metadata['subtask_id'] = int(path_parts[idx + 1])
            except ValueError:
                pass

    return metadata

def build_partition_key(metadata: Dict) -> str:
    """
    Construir partition_key según jerarquía.
    Formato: t{tenant}_p{project}[_t{task}][_s{subtask}]
    """
    parts = [f"t{metadata['tenant_id']}"]

    if metadata.get('project_id'):
        parts.append(f"p{metadata['project_id']}")

    if metadata.get('task_id'):
        parts.append(f"t{metadata['task_id']}")

    if metadata.get('subtask_id'):
        parts.append(f"s{metadata['subtask_id']}")

    return "_".join(parts)

def build_project_path(metadata: Dict) -> str:
    """
    Construir ruta jerárquica legible.
    NOTA: Preferiblemente usar project_path del API si viene incluido.
    """
    # Si viene del API, usarlo directamente
    if metadata.get('project_path'):
        return metadata['project_path']

    # Fallback: construir manualmente
    paths = [f"organization/{metadata['tenant_id']}"]

    if metadata.get('project_id'):
        paths.append(f"projects/{metadata['project_id']}")

    if metadata.get('task_id'):
        paths.append(f"tasks/{metadata['task_id']}")

    if metadata.get('subtask_id'):
        paths.append(f"subtasks/{metadata['subtask_id']}")

    return "/".join(paths)

def create_metadata_json(metadata: Dict) -> Dict:
    """
    Crear estructura de metadata para .metadata.json

    Filterable metadata (para queries): tenant_id, project_id, task_id, subtask_id, partition_key
    Non-filterable metadata (contexto): attachment_id, file_name, attachment_type, project_path

    IMPORTANTE: Ignorar campos null/None
    """
    # Filterable metadata (solo campos con valor)
    filterable = {"tenant_id": metadata['tenant_id']}

    if metadata.get('project_id') is not None:
        filterable['project_id'] = metadata['project_id']

    if metadata.get('task_id') is not None:
        filterable['task_id'] = metadata['task_id']

    if metadata.get('subtask_id') is not None:
        filterable['subtask_id'] = metadata['subtask_id']

    filterable['partition_key'] = build_partition_key(metadata)

    # Non-filterable metadata
    non_filterable = {
        'attachment_id': metadata['attachment_id'],
        'file_name': metadata.get('file_name', ''),
        'attachment_type': metadata.get('attachment_type', ''),
        'project_path': build_project_path(metadata)
    }

    # Combinar todo en metadataAttributes
    return {
        "metadataAttributes": {
            **filterable,
            **non_filterable
        }
    }

def create_metadata_file(s3_client, file_key: str, metadata_json: Dict, dry_run: bool = True) -> Optional[str]:
    """Crear archivo .metadata.json junto al archivo existente en S3"""
    metadata_key = f"{file_key}.metadata.json"

    if dry_run:
        print(f"    [DRY RUN] Would create: {metadata_key}")
        return metadata_key

    try:
        # Usar AWS CLI en lugar de boto3 (boto3 put_object tiene issues de permisos)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(metadata_json, tmp, indent=2)
            tmp_path = tmp.name

        s3_uri = f"s3://{BUCKET}/{metadata_key}"
        result = subprocess.run(
            ['/opt/homebrew/bin/aws', 's3', 'cp', tmp_path, s3_uri, '--profile', AWS_PROFILE],
            capture_output=True,
            text=True
        )

        os.unlink(tmp_path)  # Clean up temp file

        if result.returncode != 0:
            print(f"    ❌ S3 CLI error: {result.stderr.strip()}")
            return None

        return metadata_key
    except Exception as e:
        print(f"    ❌ Error creating metadata: {e}")
        return None

def list_files_in_s3_folder(folder_path: str) -> List[str]:
    """Listar archivos reales en un folder de S3 usando AWS CLI"""
    try:
        s3_uri = f"s3://{BUCKET}/{folder_path}/"

        # Use --profile flag instead of environment variable to avoid conflicts
        cmd = ['/opt/homebrew/bin/aws', 's3', 'ls', s3_uri, '--recursive', '--profile', AWS_PROFILE]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"    ❌ S3 ls error (folder: {folder_path}): {result.stderr.strip()}")
            return []

        # Parse AWS CLI output: "2024-01-01 12:00:00    1234 path/to/file.txt"
        files = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 4:
                # Last part is the full S3 key
                key = ' '.join(parts[3:])
                # Excluir folders y archivos .metadata.json existentes
                if not key.endswith('/') and not key.endswith('.metadata.json'):
                    files.append(key)

        return files
    except Exception as e:
        print(f"    ❌ Error listing S3 folder: {e}")
        return []

def migrate_projects(tenant_id: int, project_ids: List[int], dry_run: bool = True) -> tuple:
    """Añadir metadata a archivos existentes en S3"""
    s3_client = None  # Not using boto3 anymore - using AWS CLI
    migrated = []
    failed = []

    print(f"\n{'='*60}")
    print(f"{'DRY RUN - ' if dry_run else ''}Processing {len(project_ids)} projects for tenant {tenant_id}")
    print(f"{'='*60}\n")

    for idx, project_id in enumerate(project_ids, 1):
        partition_id = f"PROJECT-{project_id}"
        print(f"[{idx}/{len(project_ids)}] Project {project_id} (partition: {partition_id})")

        try:
            # Obtener attachments del proyecto para extraer metadata
            attachments = get_attachments(tenant_id, partition_id)

            if not attachments:
                print(f"  ⚠️  No attachments found in API")
                continue

            # Usar el path del primer attachment para determinar el folder en S3
            first_att = attachments[0]
            folder_path = first_att.get('path', '')

            if not folder_path:
                print(f"  ⚠️  No path found for project")
                continue

            # Listar archivos REALES en S3
            s3_files = list_files_in_s3_folder(folder_path)

            if not s3_files:
                print(f"  ⚠️  No files found in S3 at {folder_path}")
                continue

            print(f"  Found {len(attachments)} attachments in API, {len(s3_files)} files in S3")

            # Intentar obtener metadata detallada, con fallback a extracción básica
            attachment_id = first_att.get('attachmentId')
            detailed_metadata = None

            if attachment_id:
                detailed_metadata = get_attachment_metadata_detailed(tenant_id, attachment_id)

            if detailed_metadata:
                # Usar metadata detallada del endpoint
                project_metadata = detailed_metadata
                project_metadata['tenant_id'] = tenant_id  # Asegurar tenant_id
            else:
                # Fallback: extraer IDs del attachment básico
                project_metadata = extract_ids_from_attachment(first_att, tenant_id)

            # Crear metadata.json para cada archivo REAL en S3
            for file_key in s3_files:
                try:
                    # Extraer nombre del archivo desde S3 key
                    file_name = file_key.split('/')[-1]

                    # Usar metadata del proyecto para este archivo
                    file_metadata = project_metadata.copy()
                    file_metadata['file_name'] = file_name

                    # Crear metadata JSON
                    metadata_json = create_metadata_json(file_metadata)

                    # Crear metadata.json en S3
                    metadata_key = create_metadata_file(s3_client, file_key, metadata_json, dry_run)

                    if metadata_key:
                        migrated.append({
                            'attachment_id': file_metadata.get('attachment_id', 'unknown'),
                            'project_id': project_id,
                            'file_key': file_key,
                            'metadata_key': metadata_key,
                            'partition_key': metadata_json['metadataAttributes']['partition_key']
                        })
                        print(f"    ✅ {file_name} → {metadata_key}")
                    else:
                        failed.append({
                            'file_key': file_key,
                            'project_id': project_id,
                            'error': 'Failed to create metadata file'
                        })

                except Exception as e:
                    failed.append({
                        'file_key': file_key,
                        'project_id': project_id,
                        'error': str(e)
                    })
                    print(f"    ❌ Failed: {file_key} - {e}")

        except Exception as e:
            print(f"  ❌ Failed to process project {project_id}: {e}")

    return migrated, failed

def save_migration_report(migrated: List[Dict], failed: List[Dict], output_file: str):
    """Guardar reporte de migración"""
    report = {
        'total_migrated': len(migrated),
        'total_failed': len(failed),
        'migrated': migrated,
        'failed': failed,
        'timestamp': datetime.now().isoformat()
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 Migration Report")
    print(f"{'='*60}")
    print(f"✅ Successfully processed: {len(migrated)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"📄 Report saved to: {output_file}")
    print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(
        description='Migrar metadata de attachments a S3 para Bedrock Knowledge Base'
    )
    parser.add_argument(
        '--tenant-id',
        type=int,
        default=1,
        help='Tenant ID (default: 1)'
    )
    parser.add_argument(
        '--projects',
        type=str,
        default='1-100',
        help='Project IDs range (e.g., "1-100", "1,2,3", "all") (default: 1-100)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - no S3 writes'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Output report file path (default: /tmp/migration-report-tenantX-TIMESTAMP.json)'
    )

    args = parser.parse_args()

    # Parse project IDs
    if args.projects.lower() == 'all':
        # TODO: Implement fetching all projects from API
        print("⚠️  'all' not implemented yet. Please specify a range.")
        return
    elif '-' in args.projects:
        start, end = map(int, args.projects.split('-'))
        project_ids = list(range(start, end + 1))
    else:
        project_ids = [int(x.strip()) for x in args.projects.split(',')]

    print(f"\n{'='*60}")
    print(f"Colpensiones Attachments Metadata Migration")
    print(f"{'='*60}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print(f"Tenant ID: {args.tenant_id}")
    print(f"Projects: {len(project_ids)} ({min(project_ids)}-{max(project_ids)})")
    print(f"API: {API_BASE}")
    print(f"Bucket: {BUCKET}")
    print(f"{'='*60}\n")

    if not args.dry_run and not args.yes:
        confirm = input("⚠️  This will create metadata files in S3. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            return

    # Execute migration
    migrated, failed = migrate_projects(args.tenant_id, project_ids, args.dry_run)

    # Save report
    if args.output:
        report_file = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_file = f"/tmp/migration-report-tenant{args.tenant_id}-{timestamp}.json"

    save_migration_report(migrated, failed, report_file)

if __name__ == "__main__":
    main()
