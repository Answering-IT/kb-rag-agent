# Guía de Migración de Proyectos Colpensiones al Knowledge Base

**Versión:** 1.0  
**Fecha:** 2026-05-04  
**Autor:** Sistema de migración automatizado

---

## Índice

1. [Resumen](#resumen)
2. [Prerequisitos](#prerequisitos)
3. [Scripts Disponibles](#scripts-disponibles)
4. [Proceso de Migración](#proceso-de-migración)
5. [Estructura de Metadata](#estructura-de-metadata)
6. [Troubleshooting](#troubleshooting)
7. [Casos de Uso](#casos-de-uso)

---

## Resumen

Este sistema migra documentos de Colpensiones desde `dev-files-colpensiones` al Knowledge Base de Bedrock en `processapp-docs-v2-dev`, generando metadata estructurada para queries multi-tenant.

### ¿Qué hace la migración?

1. **Genera metadata** (`.metadata.json`) para cada archivo en el bucket origen
2. **Verifica integridad** (cada archivo debe tener su metadata)
3. **Copia al KB bucket** (`organization/1/projects/`) para indexación
4. **Registra resultados** (reportes JSON con detalles)

### Arquitectura

```
dev-files-colpensiones/                  processapp-docs-v2-dev/
organizations/1/projects/X/              organization/1/projects/X/
├── file.pdf                             ├── file.pdf
└── file.pdf.metadata.json      →        └── file.pdf.metadata.json
```

**Knowledge Base:**
- Escanea solo `organization/` prefix
- Lee metadata de archivos `.metadata.json`
- Indexa con partition_key para aislamiento multi-tenant

---

## Prerequisitos

### 1. Acceso AWS

```bash
export AWS_PROFILE=ans-super
aws sts get-caller-identity  # Verificar account 708819485463
```

### 2. Dependencias Python

```bash
pip install boto3 requests
```

### 3. AWS CLI

```bash
which aws  # Debe estar en /opt/homebrew/bin/aws
```

### 4. API de Colpensiones

- Endpoint: `https://dev.app.colpensiones.procesapp.com`
- No requiere autenticación
- Endpoints usados:
  - `GET /organization/{tenantId}/attachments/{partitionId}/migration`
  - `GET /organization/{tenantId}/attachments/{attachmentId}/metadata`

---

## Scripts Disponibles

### 1. `migrate-and-copy-projects.py` (RECOMENDADO)

**Script integrado** que hace todo el proceso en un solo comando.

**Uso básico:**

```bash
# Dry run (recomendado primero)
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548-6647 \
  --tenant-id 1 \
  --dry-run

# Ejecución real
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548-6647 \
  --tenant-id 1
```

**Parámetros:**

- `--projects`: Rango (`6548-6647`) o lista (`1,2,3`)
- `--tenant-id`: ID del tenant (default: 1)
- `--dry-run`: Modo simulación (no escribe nada)
- `--skip-metadata-generation`: Solo verificar y copiar (metadata ya existe)

**Proceso:**

1. Genera metadata para archivos sin ella
2. Verifica que cada archivo tenga metadata
3. Copia proyectos completos al KB bucket
4. Genera reporte en `/tmp/migration-full-report-*.json`

---

### 2. `migrate-colpensiones-attachments.py`

**Script de solo metadata** - genera archivos `.metadata.json`.

**Uso:**

```bash
# Dry run
python3 scripts/migrate-colpensiones-attachments.py \
  --tenant-id 1 \
  --projects 1-100 \
  --dry-run

# Ejecución real
python3 scripts/migrate-colpensiones-attachments.py \
  --tenant-id 1 \
  --projects 1-100 \
  --yes
```

**Cuándo usar:**
- Solo necesitas generar metadata (sin copiar)
- Re-generar metadata para proyectos existentes

---

### 3. `copy-to-kb-bucket.py`

**Script de solo copia** - asume que metadata ya existe.

**Uso:**

```bash
python3 scripts/copy-to-kb-bucket.py \
  --projects "72,85,86,90"
```

**Cuándo usar:**
- Metadata ya está generada
- Solo necesitas copiar al KB bucket

**⚠️ Limitación:** Archivos en INTELLIGENT_TIERING archive tier fallarán (necesitan restauración).

---

### 4. `copy-to-kb-via-download.py`

**Script de copia con download/upload** - funciona con archived files.

**Uso:**

```bash
python3 scripts/copy-to-kb-via-download.py \
  --projects "1,2,4" \
  --dry-run
```

**Cuándo usar:**
- Archivos en archive tier (INTELLIGENT_TIERING)
- `copy-to-kb-bucket.py` falla con "InvalidObjectState"

**⚠️ Advertencia:** Más lento (download + upload), usar solo si es necesario.

---

## Proceso de Migración

### Migración Completa (Nuevo Rango de Proyectos)

**Caso:** Migrar proyectos 6548-6647 (últimos 100 proyectos)

```bash
# Paso 1: Dry run para verificar
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548-6647 \
  --tenant-id 1 \
  --dry-run

# Revisar output:
# - Cuántos proyectos tienen archivos
# - Cuántos archivos por proyecto
# - Si hay errores de API

# Paso 2: Ejecutar migración
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548-6647 \
  --tenant-id 1

# Paso 3: Verificar reporte
cat /tmp/migration-full-report-*.json | jq '{
  total_projects: .copy_results | length,
  successful: [.copy_results[] | select(.status == "success")] | length,
  total_files: [.copy_results[] | select(.status == "success") | .files_copied] | add
}'

# Paso 4: Sincronizar Knowledge Base
KB_ID="CPERLTG5EU"
DS_ID="BUHHRDRZ90"

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --profile ans-super

# Paso 5: Monitorear sync
JOB_ID="<ingestionJobId del comando anterior>"

aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id ${JOB_ID} \
  --profile ans-super \
  --query 'ingestionJob.{Status:status,Scanned:statistics.numberOfDocumentsScanned,Indexed:statistics.numberOfNewDocumentsIndexed,Failed:statistics.numberOfDocumentsFailed}'
```

---

### Re-migración (Proyectos Ya Migrados)

**Caso:** Actualizar metadata para proyectos existentes

```bash
# Paso 1: Regenerar metadata (sobrescribe existente)
python3 scripts/migrate-colpensiones-attachments.py \
  --tenant-id 1 \
  --projects 72,85,86,90 \
  --yes

# Paso 2: Copiar (solo archivos modificados)
python3 scripts/migrate-and-copy-projects.py \
  --projects 72,85,86,90 \
  --tenant-id 1 \
  --skip-metadata-generation

# Paso 3: Sync KB (opcional si no hay cambios)
```

---

### Migración Selectiva (Proyectos Específicos)

**Caso:** Solo migrar proyectos con archivos recientes

```bash
# Encontrar proyectos con archivos
aws s3 ls s3://dev-files-colpensiones/organizations/1/projects/ \
  --recursive --profile ans-super | \
  awk '{print $4}' | \
  grep -E "projects/[0-9]+/" | \
  sed 's|.*projects/\([0-9]*\)/.*|\1|' | \
  sort -u > /tmp/projects_with_files.txt

# Migrar solo esos proyectos
PROJECT_LIST=$(cat /tmp/projects_with_files.txt | head -100 | tr '\n' ',' | sed 's/,$//')

python3 scripts/migrate-and-copy-projects.py \
  --projects "${PROJECT_LIST}" \
  --tenant-id 1
```

---

## Estructura de Metadata

### Formato del archivo `.metadata.json`

**Ubicación:** Junto al archivo (mismo directorio)

```json
{
  "metadataAttributes": {
    "tenant_id": 1,
    "project_id": 6548,
    "partition_key": "t1_p6548",
    "attachment_id": 12345,
    "file_name": "document.pdf",
    "attachment_type": "NORMAL",
    "project_path": "organizations/1/projects/6548"
  }
}
```

### Campos Filterable (para queries)

| Campo | Tipo | Descripción | Ejemplo |
|-------|------|-------------|---------|
| `tenant_id` | number | ID del tenant | `1` |
| `project_id` | number | ID del proyecto | `6548` |
| `task_id` | number | ID de la tarea (opcional) | `123` |
| `subtask_id` | number | ID de la subtarea (opcional) | `456` |
| `partition_key` | string | Clave jerárquica | `t1_p6548_t123` |

**Formato de `partition_key`:**
- Tenant solo: `t1`
- Tenant + Project: `t1_p6548`
- Tenant + Project + Task: `t1_p6548_t123`
- Tenant + Project + Task + Subtask: `t1_p6548_t123_s456`

### Campos Non-Filterable (solo contexto)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `attachment_id` | number | ID interno del attachment |
| `file_name` | string | Nombre del archivo |
| `attachment_type` | string | Tipo (NORMAL, etc.) |
| `project_path` | string | Ruta legible |

**IMPORTANTE:** Estos campos NO pueden usarse en filtros de query, solo para contexto en resultados.

---

## Troubleshooting

### Error: "InvalidObjectState: Operation is not valid for the source object's access tier"

**Causa:** Archivos en INTELLIGENT_TIERING archive tier.

**Solución:**

1. **Opción 1:** Usar `copy-to-kb-via-download.py` (download/upload)
2. **Opción 2:** Excluir esos archivos específicos (ver ejemplo abajo)
3. **Opción 3:** Restaurar archivos primero (toma horas)

**Ejemplo - Excluir archivos problemáticos:**

```bash
# Editar copy-to-kb-bucket.py, agregar en cmd:
'--exclude', 'signed.pdf',
'--exclude', '*ComOf*.pdf',
'--exclude', '*ejemplo_400MB*'
```

---

### Error: "No attachments found in API"

**Causa:** Proyecto sin attachments o partitionId incorrecto.

**Verificación:**

```bash
curl "https://dev.app.colpensiones.procesapp.com/organization/1/attachments/PROJECT-6548/migration"
```

**Si retorna `[]`:** El proyecto no tiene attachments, es normal. El script lo salta automáticamente.

---

### Error: "Missing path or name in attachment"

**Causa:** API no retornó campos `path` o `name`.

**Solución:** Verificar respuesta del API:

```bash
curl "https://dev.app.colpensiones.procesapp.com/organization/1/attachments/12345/metadata"
```

**Workaround:** El script usa extracción de IDs desde el path si falla.

---

### Archivos copiados pero no indexados en KB

**Verificación:**

1. **Confirmar que metadata existe:**
   ```bash
   aws s3 ls s3://processapp-docs-v2-dev-708819485463/organization/1/projects/6548/ \
     --recursive --profile ans-super | grep metadata.json
   ```

2. **Verificar formato de metadata:**
   ```bash
   aws s3 cp s3://processapp-docs-v2-dev-708819485463/organization/1/projects/6548/file.pdf.metadata.json - \
     --profile ans-super | jq .
   ```

3. **Revisar logs del ingestion job:**
   ```bash
   aws bedrock-agent get-ingestion-job \
     --knowledge-base-id ${KB_ID} \
     --data-source-id ${DS_ID} \
     --ingestion-job-id ${JOB_ID} \
     --profile ans-super
   ```

**Posibles causas:**
- Metadata con formato incorrecto (debe ser JSON válido)
- Archivo sin extensión soportada (.pdf, .docx, .txt)
- Archivo muy grande (>50MB puede fallar)

---

### Dry run muestra 0 archivos pero hay archivos en S3

**Causa:** Archivos sin metadata generada.

**Solución:**

```bash
# Primero genera metadata
python3 scripts/migrate-colpensiones-attachments.py \
  --tenant-id 1 \
  --projects 6548 \
  --yes

# Luego copia
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548 \
  --tenant-id 1 \
  --skip-metadata-generation
```

---

## Casos de Uso

### 1. Migrar últimos 100 proyectos

```bash
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548-6647 \
  --tenant-id 1
```

**Resultado esperado:**
- ~50-70 proyectos con archivos (el resto sin archivos se salta)
- ~200-500 documentos indexados
- Tiempo: 10-20 minutos

---

### 2. Re-sincronizar proyectos existentes

```bash
# Solo trigger sync (sin re-migración)
KB_ID="CPERLTG5EU"
DS_ID="BUHHRDRZ90"

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --profile ans-super
```

**Cuándo usar:**
- Archivos ya copiados al KB bucket
- Solo necesitas re-indexar (ej: cambios en chunking config)

---

### 3. Migrar solo proyectos con archivos grandes

```bash
# Encontrar proyectos con archivos >1MB
aws s3 ls s3://dev-files-colpensiones/organizations/1/projects/ \
  --recursive --profile ans-super | \
  awk '$3 > 1000000 {print $4}' | \
  sed 's|.*projects/\([0-9]*\)/.*|\1|' | \
  sort -u | head -50 > /tmp/large_projects.txt

# Migrar esos proyectos
PROJECT_LIST=$(cat /tmp/large_projects.txt | tr '\n' ',' | sed 's/,$//')

python3 scripts/migrate-and-copy-projects.py \
  --projects "${PROJECT_LIST}" \
  --tenant-id 1
```

---

### 4. Limpiar y re-migrar proyecto específico

```bash
# Paso 1: Eliminar archivos existentes en KB bucket
aws s3 rm s3://processapp-docs-v2-dev-708819485463/organization/1/projects/6548/ \
  --recursive --profile ans-super

# Paso 2: Re-migrar
python3 scripts/migrate-and-copy-projects.py \
  --projects 6548 \
  --tenant-id 1

# Paso 3: Sync KB
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id CPERLTG5EU \
  --data-source-id BUHHRDRZ90 \
  --profile ans-super
```

---

## Configuración Adicional

### Variables de entorno personalizadas

```bash
# Cambiar API endpoint
export API_BASE="https://prod.app.colpensiones.procesapp.com"

# Cambiar bucket destino
export DEST_BUCKET="processapp-docs-v2-prod-708819485463"

# Cambiar perfil AWS
export AWS_PROFILE="production"
```

**Nota:** Los scripts leen estas variables automáticamente.

---

### Limitar rate de llamadas al API

Editar scripts y agregar `time.sleep()`:

```python
# En migrate-and-copy-projects.py, línea ~350
for idx, project_id in enumerate(project_ids, 1):
    print(f"\n[{idx}/{len(project_ids)}] Project {project_id}")
    
    # Rate limiting
    import time
    time.sleep(0.5)  # 0.5 segundos entre proyectos
    
    metadata_result = generate_metadata_for_project(...)
```

---

## Métricas y Reportes

### Ver estadísticas de migración

```bash
# Total de archivos migrados
cat /tmp/migration-full-report-*.json | jq '
  [.copy_results[] | select(.status == "success") | .files_copied] | add
'

# Proyectos por estado
cat /tmp/migration-full-report-*.json | jq '
  .copy_results | group_by(.status) | 
  map({status: .[0].status, count: length})
'

# Proyectos con más archivos
cat /tmp/migration-full-report-*.json | jq '
  .copy_results | 
  sort_by(.files_copied) | 
  reverse | 
  .[0:10] | 
  map({project_id, files_copied})
'
```

---

### Verificar estado del Knowledge Base

```bash
KB_ID="CPERLTG5EU"

# Ver último ingestion job
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --max-results 1 \
  --profile ans-super

# Estadísticas del KB
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id ${KB_ID} \
  --profile ans-super
```

---

## Changelog

### v1.0 - 2026-05-04

**Inicial:**
- Script `migrate-and-copy-projects.py` integrado
- Soporte para generación de metadata + copia en un solo comando
- Verificación de integridad (archivo + metadata)
- Reportes JSON detallados
- Documentación completa

**Scripts legacy:**
- `migrate-colpensiones-attachments.py` - solo metadata
- `copy-to-kb-bucket.py` - solo copia (sync)
- `copy-to-kb-via-download.py` - copia con download/upload

**Infraestructura:**
- Knowledge Base: `CPERLTG5EU` (processapp-kb-v3-dev)
- Data Source: `BUHHRDRZ90` (processapp-kb-v3-dev-datasource-v2)
- Bucket KB: `processapp-docs-v2-dev-708819485463`
- Prefix: `organization/1/projects/`

---

## Soporte

**Logs de scripts:**
```bash
# Ejecutar con output redirigido
python3 scripts/migrate-and-copy-projects.py ... 2>&1 | tee /tmp/migration.log
```

**Issues conocidos:**
1. Archivos en archive tier requieren script especial
2. API puede retornar 404 para attachments eliminados (esperado)
3. Proyectos sin archivos se saltan automáticamente

**Contacto:** Ver `CLAUDE.md` para más información sobre la arquitectura.

---

**Última actualización:** 2026-05-04  
**Versión de Knowledge Base:** v3  
**Región:** us-east-1
