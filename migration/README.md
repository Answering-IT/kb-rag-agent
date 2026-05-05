# Migration Scripts - Legacy Bucket to KB Bucket

Scripts para migrar archivos del bucket legado (`dev-files-colpensiones`) al bucket del Knowledge Base (`processapp-docs-v2-dev-708819485463`) con metadata correcta.

---

## 📋 Descripción General

Este sistema de migración:

1. **Lista proyectos recientes** - Selecciona los últimos 200 proyectos por fecha de modificación
2. **Consulta metadata del API** - Obtiene información de attachments desde el endpoint de migración
3. **Copia archivos con metadata** - Copia archivos al bucket destino con metadata completa
4. **Valida migración** - Verifica que todos los archivos tengan metadata válida

### Características

- ✅ Metadata completa desde API (attachment_id, file_name, attachment_type, project_path)
- ✅ Fallback automático para archivos sin metadata en API
- ✅ Soporte para jerarquía: Tenant → Project → Task → Subtask
- ✅ Ignora archivos ZIP (no requieren metadata)
- ✅ Rate limiting para API y S3
- ✅ Cache de respuestas del API
- ✅ Logs detallados de migración
- ✅ Modo dry-run para pruebas
- ✅ Replicable en otras regiones

---

## 🏗️ Estructura

```
migration/
├── config.py                  # Configuración centralizada
├── utils.py                   # Funciones comunes
├── run_migration.py           # Script master (ejecuta todos los pasos)
├── step1_list_projects.py     # Paso 1: Lista proyectos
├── step2_fetch_api_metadata.py # Paso 2: Fetch API metadata
├── step3_copy_with_metadata.py # Paso 3: Copia archivos
├── step4_validate.py          # Paso 4: Validación
├── cache/                     # Cache de respuestas del API
│   ├── PROJECT-949.json
│   ├── TASK-5.json
│   └── ...
├── logs/                      # Logs de migración
│   ├── migration_log.json
│   └── validation_report.json
└── output/                    # Outputs intermedios
    └── project_list.json
```

---

## 🚀 Uso Rápido

### Opción A: Script Master (Recomendado)

Ejecuta todos los pasos en secuencia:

```bash
cd migration

# Dry run (prueba sin modificar)
python3 run_migration.py --dry-run

# Producción
python3 run_migration.py
```

### Opción B: Paso a Paso

```bash
# Paso 1: Listar proyectos recientes
python3 step1_list_projects.py

# Paso 2: Fetch metadata del API
python3 step2_fetch_api_metadata.py

# Paso 3: Copiar archivos (dry-run primero)
python3 step3_copy_with_metadata.py --dry-run
python3 step3_copy_with_metadata.py

# Paso 4: Validar
python3 step4_validate.py
```

---

## 📝 Configuración

Edita `config.py` para ajustar:

```python
# AWS Configuration
AWS_PROFILE = "ans-super"
AWS_REGION = "us-east-1"

# S3 Buckets
SOURCE_BUCKET = "dev-files-colpensiones"
DESTINATION_BUCKET = "processapp-docs-v2-dev-708819485463"

# API Configuration
API_BASE_URL = "https://dev.app.colpensiones.procesapp.com"
TENANT_ID = "1"

# Migration Settings
MAX_PROJECTS = 200  # Últimos 200 proyectos
```

---

## 🔍 Detalles de Cada Paso

### Step 1: List Recent Projects

**Script:** `step1_list_projects.py`

Lista todos los proyectos en `organizations/1/projects/` del bucket legado, los ordena por fecha de modificación (más recientes primero) y guarda los últimos 200.

**Output:**
```json
// migration/output/project_list.json
[
  {
    "project_id": "949",
    "last_modified": "2025-01-22T18:14:16.634655"
  },
  ...
]
```

### Step 2: Fetch API Metadata

**Script:** `step2_fetch_api_metadata.py`

Para cada proyecto/task/subtask, consulta el API:

```
GET /organization/1/attachments/PROJECT-949/migration
GET /organization/1/attachments/TASK-5/migration
GET /organization/1/attachments/SUBTASK-10/migration
```

**Output:**
```json
// migration/cache/PROJECT-949.json
[
  {
    "attachmentId": 670,
    "partitionId": "PROJECT-949",
    "name": "documento.pdf",
    "path": "organizations/1/projects/949",
    "type": "NORMAL",
    "partitionType": "PROJECT",
    ...
  }
]
```

**Características:**
- Cache local (evita llamadas repetidas)
- Rate limiting (0.5s entre llamadas)
- Manejo de errores (continúa con otros partitions si uno falla)

### Step 3: Copy Files with Metadata

**Script:** `step3_copy_with_metadata.py`

Para cada archivo:

1. **Busca metadata en cache del API** (por nombre de archivo)
2. Si existe: usa metadata completa
3. Si NO existe: genera metadata con fallback (solo tenant_id, project_id, partition_key)
4. **Copia archivo al bucket destino**
5. **Crea archivo `.metadata.json`** con formato Bedrock KB
6. **Ignora archivos ZIP** (no requieren metadata)

**Metadata Completa (con API):**
```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "project_id": "949",
    "partition_key": "t1_p949",
    "partition_type": "PROJECT",
    "attachment_id": "670",
    "file_name": "documento.pdf",
    "attachment_type": "NORMAL",
    "project_path": "organizations/1/projects/949"
  }
}
```

**Metadata Fallback (sin API):**
```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "project_id": "949",
    "partition_key": "t1_p949",
    "partition_type": "PROJECT"
  }
}
```

**Formato partition_key:**
- Tenant: `t1`
- Project: `t1_p949`
- Task: `t1_p949_t5`
- Subtask: `t1_p949_t5_s10`

**Output:**
```json
// migration/logs/migration_log.json
[
  {
    "source_key": "organizations/1/projects/949/file.pdf",
    "dest_key": "organizations/1/projects/949/file.pdf",
    "status": "success",
    "metadata_source": "api",
    "partition_key": "t1_p949"
  },
  ...
]
```

### Step 4: Validate Migration

**Script:** `step4_validate.py`

Verifica que todos los archivos en el bucket destino tengan:

- ✅ Archivo `.metadata.json` existente
- ✅ Estructura `metadataAttributes` wrapper
- ✅ Campos requeridos: `tenant_id`, `partition_key`, `partition_type`

**Output:**
```json
// migration/logs/validation_report.json
{
  "summary": {
    "total_files": 1500,
    "valid": 1450,
    "invalid": 20,
    "missing": 30,
    "ignored": 50
  },
  "issues": [
    {
      "file": "organizations/1/projects/949/file.pdf",
      "status": "missing",
      "issues": ["Metadata file not found"]
    },
    ...
  ]
}
```

---

## 🔧 Campos de Metadata

### Filterable (para queries)
- `tenant_id` - ID del tenant (siempre "1")
- `project_id` - ID del proyecto (opcional)
- `task_id` - ID de la tarea (opcional)
- `subtask_id` - ID de la subtarea (opcional)
- `partition_key` - Clave de partición jerárquica (obligatorio)
- `partition_type` - Tipo: TENANT, PROJECT, TASK, SUBTASK

### Non-Filterable (información adicional)
- `attachment_id` - ID del attachment en la DB
- `file_name` - Nombre del archivo
- `attachment_type` - Tipo: NORMAL, COMMUNICATION_RECEIVED, etc.
- `project_path` - Path del proyecto en S3

---

## 📊 Logs y Reportes

### Migration Log
**Ubicación:** `migration/logs/migration_log.json`

Contiene el resultado de cada archivo procesado:
- source_key / dest_key
- status: success / error / ignored
- metadata_source: api / fallback
- partition_key

### Validation Report
**Ubicación:** `migration/logs/validation_report.json`

Contiene:
- Summary con totales
- Lista de issues (archivos sin metadata o con metadata inválida)

---

## 🌎 Replicación en Otras Regiones (us-east-2)

Para migrar en **us-east-2** (producción):

1. **Clonar carpeta migration:**
   ```bash
   cp -r migration migration-us-east-2
   cd migration-us-east-2
   ```

2. **Editar config.py:**
   ```python
   AWS_REGION = "us-east-2"
   SOURCE_BUCKET = "prod-files-colpensiones"
   DESTINATION_BUCKET = "processapp-docs-v2-prod-XXXXX"
   API_BASE_URL = "https://app.colpensiones.procesapp.com"
   ```

3. **Ejecutar migración:**
   ```bash
   python3 run_migration.py --dry-run  # Prueba
   python3 run_migration.py            # Producción
   ```

4. **Revisar logs:**
   Los logs en `migration-us-east-2/logs/` contendrán el registro completo de archivos migrados.

---

## ⚠️ Consideraciones Importantes

### Archivos ZIP
Los archivos `.zip` son **ignorados automáticamente** (no se copia ni se crea metadata). El Knowledge Base no los procesará.

### Rate Limiting
- **API:** 0.5 segundos entre llamadas (configurable en `config.py`)
- **S3:** 0.1 segundos entre operaciones

### Fallback Metadata
Si el API no tiene información de un archivo, se genera metadata con:
- tenant_id, project_id, task_id, partition_key (campos requeridos)
- SIN: attachment_id, file_name, attachment_type, project_path

Estos archivos igual se indexarán correctamente en el KB, pero con menos metadata.

### Cache del API
Las respuestas del API se cachean en `migration/cache/`. Para forzar re-fetch, borra la carpeta cache.

### Dry Run
Usa `--dry-run` para probar sin modificar S3:
```bash
python3 step3_copy_with_metadata.py --dry-run
```

---

## 🐛 Troubleshooting

### Error: "Project list not found"
```bash
# Ejecuta Step 1 primero
python3 step1_list_projects.py
```

### Error: API timeout
```bash
# Aumenta el timeout en step2_fetch_api_metadata.py
response = requests.get(url, timeout=60)  # De 30 a 60 segundos
```

### Validation muestra "missing metadata"
```bash
# Re-ejecuta Step 3 para los archivos faltantes
python3 step3_copy_with_metadata.py
```

### Archivos duplicados
El script NO sobreescribe archivos existentes. Si necesitas re-migrar, borra primero los archivos en el bucket destino.

---

## 📞 Soporte

Para problemas o preguntas sobre la migración, contactar al equipo de desarrollo.

---

**Última actualización:** 2026-05-05  
**Región:** us-east-1 (dev)  
**Tenant:** 1 (Colpensiones)
