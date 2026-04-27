#!/usr/bin/env python3
"""
Test script for multi-tenant metadata filtering
Creates test documents with metadata and validates filtering works
"""

import boto3
import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any

# Configuration
AWS_PROFILE = 'ans-super'
REGION = 'us-east-1'
BUCKET_NAME = 'processapp-docs-v2-dev-708819485463'
KB_ID = None  # Will be fetched
DS_ID = None  # Will be fetched
API_URL = 'https://ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev/query'
API_KEY = 'x5ots6txyN5Zz0bychGjraWWpY7ialv13BalOXUV'

# Initialize clients
session = boto3.Session(profile_name=AWS_PROFILE, region_name=REGION)
s3 = session.client('s3')
bedrock_agent = session.client('bedrock-agent')

print("=" * 80)
print("MULTI-TENANT METADATA FILTERING TEST")
print("=" * 80)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"AWS Profile: {AWS_PROFILE}")
print(f"Region: {REGION}")
print(f"Bucket: {BUCKET_NAME}")
print("=" * 80)

# Step 1: Get Knowledge Base and Data Source IDs
print("\n[1/6] Fetching Knowledge Base information...")
try:
    kb_list = bedrock_agent.list_knowledge_bases()
    kb = next((k for k in kb_list['knowledgeBaseSummaries'] if 'processapp' in k['name']), None)
    if kb:
        KB_ID = kb['knowledgeBaseId']
        print(f"✅ Knowledge Base ID: {KB_ID}")

        # Get data source
        ds_list = bedrock_agent.list_data_sources(knowledgeBaseId=KB_ID)
        if ds_list['dataSourceSummaries']:
            DS_ID = ds_list['dataSourceSummaries'][0]['dataSourceId']
            print(f"✅ Data Source ID: {DS_ID}")
    else:
        print("❌ Knowledge Base not found")
        exit(1)
except Exception as e:
    print(f"❌ Error fetching KB info: {e}")
    exit(1)

# Step 2: Create test documents
print("\n[2/6] Creating test documents...")

test_documents = [
    {
        'tenant_id': '1',
        'roles': 'viewer,editor',
        'project_id': '100',
        'users': '*',
        'filename': 'tenant1_general_info.txt',
        'content': '''COLPENSIONES - INFORMACIÓN GENERAL DEL TENANT 1

Este documento contiene información general sobre Colpensiones para el tenant 1.

Colpensiones es una entidad pública encargada de administrar el régimen de prima media
del Sistema General de Pensiones en Colombia.

SERVICIOS PRINCIPALES:
- Reconocimiento de pensiones
- Pago de mesadas pensionales
- Gestión de aportes
- Atención al usuario

MISIÓN:
Garantizar el pago oportuno de las pensiones y gestionar los recursos del régimen
de prima media con eficiencia y transparencia.

VALORES:
- Transparencia
- Eficiencia
- Servicio al ciudadano
- Sostenibilidad financiera

Esta información es accesible para todos los usuarios del tenant 1 con rol viewer o editor.
'''
    },
    {
        'tenant_id': '1',
        'roles': 'supervisor',
        'project_id': '100',
        'users': '*',
        'filename': 'tenant1_project100_confidential.txt',
        'content': '''PROYECTO 100 - INFORMACIÓN CONFIDENCIAL (SOLO SUPERVISORES)

Este documento contiene información confidencial del proyecto 100 del tenant 1.
Solo accesible para usuarios con rol 'supervisor'.

PRESUPUESTO DEL PROYECTO:
- Total asignado: $500,000,000 COP
- Ejecutado a la fecha: $320,000,000 COP
- Disponible: $180,000,000 COP

EQUIPO ASIGNADO:
- Director: Juan Pérez
- Supervisor: María García
- Desarrolladores: 5 personas
- QA: 2 personas

HITOS COMPLETADOS:
1. Análisis de requerimientos - Completado
2. Diseño técnico - Completado
3. Desarrollo fase 1 - En progreso (80%)
4. Pruebas - Pendiente

RIESGOS IDENTIFICADOS:
- Retraso en integración con sistema legacy
- Falta de recursos en Q3
- Dependencia de proveedor externo

Esta información es CONFIDENCIAL y solo debe ser accesible para supervisores.
'''
    },
    {
        'tenant_id': '1',
        'roles': 'supervisor,asesor',
        'project_id': '100',
        'users': 'user123,user456',
        'filename': 'tenant1_project100_user_specific.txt',
        'content': '''PROYECTO 100 - COMUNICACIÓN ESPECÍFICA PARA USUARIOS

Este documento es específico para user123 y user456 del proyecto 100.
Roles permitidos: supervisor y asesor.

REUNIÓN DE SEGUIMIENTO - 2026-04-20

PARTICIPANTES:
- user123 (Supervisor)
- user456 (Asesor)

TEMAS DISCUTIDOS:
1. Avance del sprint actual (Sprint 5)
2. Bloqueos identificados
3. Próximos pasos

ACUERDOS:
- Reunión diaria a las 10:00 AM
- Code review en parejas
- Demo al cliente el 2026-05-01

TAREAS ASIGNADAS:
user123:
- Revisar arquitectura de microservicios
- Aprobar PRs pendientes
- Coordinar con DevOps

user456:
- Preparar documentación técnica
- Validar requisitos con cliente
- Capacitar al equipo junior

PRÓXIMA REUNIÓN: 2026-04-27 a las 15:00

Este documento solo debe ser visible para user123 y user456.
'''
    },
    {
        'tenant_id': '2',
        'roles': 'viewer',
        'project_id': '200',
        'users': '*',
        'filename': 'tenant2_general_info.txt',
        'content': '''ORGANIZACIÓN AC - INFORMACIÓN GENERAL DEL TENANT 2

Este documento pertenece al tenant 2 (Organización AC).

DESCRIPCIÓN:
Organización AC es un cliente corporativo que utiliza la plataforma ProcessApp
para gestión de procesos pensionales.

SERVICIOS CONTRATADOS:
- Módulo de consultas
- Reportes personalizados
- API de integración
- Soporte 24/7

USUARIOS ACTIVOS: 150
DOCUMENTOS PROCESADOS: 12,500
UPTIME: 99.95%

CONTACTO:
Email: soporte@organizacionac.com
Teléfono: +57 1 234 5678

Esta información es del tenant 2 y NO debe ser visible para usuarios del tenant 1.
'''
    }
]

print(f"📄 Created {len(test_documents)} test documents")
for doc in test_documents:
    print(f"  - {doc['filename']}: tenant={doc['tenant_id']}, roles={doc['roles']}, project={doc['project_id']}, users={doc['users']}")

# Step 3: Upload documents to S3 with metadata
print("\n[3/6] Uploading documents to S3 with metadata...")

for doc in test_documents:
    key = f"documents/{doc['filename']}"

    # Prepare metadata
    metadata = {
        'tenantid': doc['tenant_id'],
        'roles': doc['roles'],
        'projectid': doc['project_id'],
        'users': doc['users'],
        'filename': doc['filename'],
        'uploaddate': datetime.now().isoformat()
    }

    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=key,
            Body=doc['content'].encode('utf-8'),
            ContentType='text/plain',
            Metadata=metadata
        )
        print(f"✅ Uploaded: {doc['filename']}")
        print(f"   Metadata: {metadata}")
    except Exception as e:
        print(f"❌ Error uploading {doc['filename']}: {e}")

# Step 4: Start ingestion job
print("\n[4/6] Starting Knowledge Base ingestion job...")
try:
    ingestion_response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DS_ID,
        description=f'Metadata filtering test - {datetime.now().isoformat()}'
    )
    ingestion_job_id = ingestion_response['ingestionJob']['ingestionJobId']
    print(f"✅ Ingestion job started: {ingestion_job_id}")
    print("   Waiting for ingestion to complete (this may take 2-5 minutes)...")

    # Wait for ingestion to complete
    max_wait = 300  # 5 minutes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        job_status = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=KB_ID,
            dataSourceId=DS_ID,
            ingestionJobId=ingestion_job_id
        )
        status = job_status['ingestionJob']['status']

        if status == 'COMPLETE':
            print(f"✅ Ingestion completed successfully!")
            stats = job_status['ingestionJob'].get('statistics', {})
            print(f"   Documents processed: {stats.get('numberOfDocumentsScanned', 0)}")
            print(f"   Documents indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
            break
        elif status == 'FAILED':
            print(f"❌ Ingestion failed!")
            failure_reasons = job_status['ingestionJob'].get('failureReasons', [])
            print(f"   Reasons: {failure_reasons}")
            exit(1)
        else:
            print(f"   Status: {status}... waiting...")
            time.sleep(15)
    else:
        print("⚠️  Ingestion timeout - may still be in progress")

except Exception as e:
    print(f"❌ Error starting ingestion: {e}")
    exit(1)

# Step 5: Test filtering with API calls
print("\n[5/6] Testing metadata filtering via API...")

import requests

test_cases = [
    {
        'name': 'Tenant 1 - Viewer role - General info',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'testuser1',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is the mission of Colpensiones?',
        'expected': 'Should find general info document'
    },
    {
        'name': 'Tenant 1 - Supervisor role - Confidential project info',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'supervisor1',
            'x-user-roles': '["supervisor"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is the budget for project 100?',
        'expected': 'Should find confidential project document'
    },
    {
        'name': 'Tenant 1 - Viewer role - Try to access supervisor-only doc',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'viewer1',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is the budget for project 100?',
        'expected': 'Should NOT find confidential document (insufficient role)'
    },
    {
        'name': 'Tenant 1 - Specific user (user123)',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '1',
            'x-user-id': 'user123',
            'x-user-roles': '["supervisor"]',
            'Content-Type': 'application/json'
        },
        'question': 'What tasks are assigned to user123?',
        'expected': 'Should find user-specific document'
    },
    {
        'name': 'Tenant 2 - Try to access Tenant 1 data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '2',
            'x-user-id': 'user_tenant2',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'What is the mission of Colpensiones?',
        'expected': 'Should NOT find Tenant 1 documents (tenant isolation)'
    },
    {
        'name': 'Tenant 2 - Access own data',
        'headers': {
            'X-Api-Key': API_KEY,
            'x-tenant-id': '2',
            'x-user-id': 'user_tenant2',
            'x-user-roles': '["viewer"]',
            'Content-Type': 'application/json'
        },
        'question': 'How many users does Organization AC have?',
        'expected': 'Should find Tenant 2 documents'
    }
]

results = []

for i, test in enumerate(test_cases, 1):
    print(f"\n--- Test Case {i}/{len(test_cases)}: {test['name']} ---")
    print(f"Question: {test['question']}")
    print(f"Expected: {test['expected']}")

    try:
        response = requests.post(
            API_URL,
            headers=test['headers'],
            json={'question': test['question']},
            timeout=30
        )

        result = response.json()

        if response.status_code == 200 and result.get('status') == 'success':
            answer = result.get('answer', '')
            print(f"✅ Response received:")
            print(f"   Answer: {answer[:200]}{'...' if len(answer) > 200 else ''}")
            results.append({
                'test': test['name'],
                'status': 'SUCCESS',
                'answer': answer
            })
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            results.append({
                'test': test['name'],
                'status': 'ERROR',
                'error': result.get('error')
            })

    except Exception as e:
        print(f"❌ Exception: {e}")
        results.append({
            'test': test['name'],
            'status': 'EXCEPTION',
            'error': str(e)
        })

# Step 6: Generate test report
print("\n" + "=" * 80)
print("[6/6] TEST REPORT")
print("=" * 80)

report_filename = f'test-report-metadata-filtering-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
report_path = f'/Users/qohatpretel/Answering/kb-rag-agent/scripts/{report_filename}'

report = {
    'test_date': datetime.now().isoformat(),
    'configuration': {
        'bucket': BUCKET_NAME,
        'kb_id': KB_ID,
        'ds_id': DS_ID,
        'api_url': API_URL,
        'region': REGION
    },
    'documents_uploaded': len(test_documents),
    'test_cases': len(test_cases),
    'results': results
}

# Save report
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f"\n✅ Test report saved to: {report_path}")

# Print summary
success_count = sum(1 for r in results if r['status'] == 'SUCCESS')
error_count = sum(1 for r in results if r['status'] != 'SUCCESS')

print(f"\nSUMMARY:")
print(f"  Total tests: {len(test_cases)}")
print(f"  ✅ Successful: {success_count}")
print(f"  ❌ Failed: {error_count}")

if success_count == len(test_cases):
    print("\n🎉 ALL TESTS PASSED! Metadata filtering is working correctly.")
else:
    print(f"\n⚠️  {error_count} test(s) failed. Review the report for details.")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
