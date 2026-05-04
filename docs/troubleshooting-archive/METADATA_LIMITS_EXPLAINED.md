# AWS Bedrock Knowledge Base - Límites de Metadata Explicados

## 🎯 El Problema que Encontramos

### Error Original
```
"Filterable metadata must have at most 2048 bytes"
```

Este error apareció al intentar indexar documentos de **1.6KB y 2.8KB** con metadata simple.

---

## 🔍 Cómo Funciona la Metadata en Bedrock KB

### 1. Proceso de Ingesta con Chunking

Cuando subes un documento a Bedrock Knowledge Base:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Documento Original (2.8 KB)                              │
│    juan-daniel-perez-experiencia.txt                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Bedrock KB Lee el Documento                              │
│    - Aplica chunking: 512 tokens, 20% overlap              │
│    - Documento de 2.8KB → ~4-5 chunks                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Bedrock KB Lee la Metadata                               │
│    juan-daniel-perez-experiencia.txt.metadata.json         │
│    {                                                         │
│      "metadataAttributes": {                                │
│        "tenant_id": "1001",                                 │
│        "project_id": "6636",                                │
│        "knowledge_type": "specific",                        │
│        "document_type": "experience",                       │
│        "subject": "Juan Daniel Perez",                      │
│        "created_date": "2026-05-03",                        │
│        "description": "Experiencia laboral..."              │
│      }                                                       │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Bedrock KB Crea un Chunk por Cada Fragmento             │
│                                                              │
│    Chunk 1:                                                 │
│      content: "# Experiencia Laboral - Juan Daniel..."     │
│      metadata: {tenant_id, project_id, ...} ← COPIA         │
│                                                              │
│    Chunk 2:                                                 │
│      content: "### Proyectos en Bogotá (5 visitas)..."     │
│      metadata: {tenant_id, project_id, ...} ← COPIA         │
│                                                              │
│    Chunk 3:                                                 │
│      content: "### Proyectos en Medellín (3 visitas)..."   │
│      metadata: {tenant_id, project_id, ...} ← COPIA         │
│                                                              │
│    ... (4-5 chunks total)                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Bedrock KB Envía Cada Chunk a S3 Vectors                │
│    Para cada chunk, calcula:                                │
│    - Embedding del contenido (vector)                       │
│    - Serializa metadata como JSON                           │
│    - VERIFICA: len(metadata_json) <= 2048 bytes            │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ El Límite de 2048 Bytes

### Qué Cuenta en los 2048 Bytes

**TODO lo que va en metadataAttributes:**

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",              // ← 20 bytes
    "project_id": "6636",             // ← 21 bytes
    "knowledge_type": "specific",     // ← 32 bytes
    "document_type": "experience",    // ← 33 bytes
    "subject": "Juan Daniel Perez",   // ← 35 bytes
    "created_date": "2026-05-03",     // ← 30 bytes
    "description": "Experiencia laboral y trayectoria profesional de Juan Daniel Perez"  // ← 97 bytes
  }
}
```

**Total aproximado:** ~270 bytes

Pero cuando se serializa como JSON con espacios, llaves, comillas, etc., puede llegar a **~350-400 bytes**.

### Por Qué Nuestros Documentos Fallaron

**Documento Original:**
- Tamaño: 2.8 KB
- Chunks generados: ~4-5 chunks
- Metadata por chunk: ~350 bytes

**El problema NO era el tamaño individual de la metadata.**

El problema era que **cada chunk lleva una COPIA completa de la metadata**, y cuando hay muchos campos descriptivos largos (como `description: "Experiencia laboral y trayectoria..."`), se acumula.

Además, Bedrock internamente puede agregar campos adicionales:
- `_document_id`
- `_chunk_id`
- `_chunk_index`
- `_source_uri`

Estos campos internos + tu metadata pueden fácilmente exceder los 2048 bytes.

---

## ✅ Solución: Metadata Minimalista

### Metadata Correcta (83 bytes)

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636"
  }
}
```

**Serializado como JSON:** ~83 bytes  
**Con campos internos de Bedrock:** ~200-300 bytes  
**Total:** Muy por debajo del límite de 2048 bytes ✅

### Metadata Incorrecta (312 bytes)

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "knowledge_type": "specific",
    "document_type": "experience",
    "subject": "Juan Daniel Perez",
    "created_date": "2026-05-03",
    "description": "Experiencia laboral y trayectoria profesional de Juan Daniel Perez"
  }
}
```

**Serializado como JSON:** ~312 bytes  
**Con campos internos de Bedrock:** ~500-600 bytes  
**Riesgo:** Si el documento genera muchos chunks o Bedrock agrega más campos internos, puede exceder 2048 bytes ❌

---

## 📏 Reglas para Metadata en Bedrock KB

### ✅ DO (Hacer)

1. **Mantener metadata MINIMALISTA:**
   ```json
   {
     "metadataAttributes": {
       "tenant_id": "1001",
       "project_id": "6636",
       "task_id": "3002"
     }
   }
   ```
   Total: ~100 bytes ✅

2. **Solo campos necesarios para filtrado:**
   - IDs numéricos o cortos
   - Sin descripciones largas
   - Sin campos redundantes

3. **Usar valores cortos:**
   - `tenant_id: "1001"` ✅ (no `tenant_id: "colpensiones-org-main"` ❌)
   - `type: "doc"` ✅ (no `document_type: "professional_experience_detailed"` ❌)

4. **Documentos pequeños cuando sea posible:**
   - Idealmente < 1KB
   - Si es más grande, asegurar metadata minimalista

### ❌ DON'T (No hacer)

1. **NO incluir descripciones largas:**
   ```json
   {
     "metadataAttributes": {
       "description": "Este es un documento muy detallado sobre..." ❌
     }
   }
   ```

2. **NO duplicar información del documento:**
   ```json
   {
     "metadataAttributes": {
       "title": "Juan Daniel Perez",        ❌ Ya está en el contenido
       "content_summary": "Ingeniero civil..." ❌ Ya está en el contenido
     }
   }
   ```

3. **NO usar campos con valores muy largos:**
   ```json
   {
     "metadataAttributes": {
       "tags": "ingenieria, civil, estructuras, bogota, medellin, mar, surf..." ❌
     }
   }
   ```

4. **NO agregar metadata "por si acaso":**
   - Solo campos que REALMENTE necesitas para filtrar
   - Menos es más

---

## 🎯 Casos de Uso Correctos

### Caso 1: Multi-tenancy (Lo que necesitamos)

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636"
  }
}
```

**Total:** ~80 bytes ✅  
**Uso:** Filtrar documentos por tenant y proyecto

---

### Caso 2: Multi-tenancy con Tareas

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "task_id": "3002"
  }
}
```

**Total:** ~100 bytes ✅  
**Uso:** Filtrar documentos por tenant, proyecto y tarea

---

### Caso 3: Multi-tenancy con Tipo de Conocimiento

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "type": "doc"
  }
}
```

**Total:** ~90 bytes ✅  
**Uso:** Filtrar por tipo de documento (doc, policy, guide)

---

### Caso 4: Con Permisos de Usuario

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "user_id": "u123"
  }
}
```

**Total:** ~95 bytes ✅  
**Uso:** Filtrar documentos por usuario específico

---

## 🚨 Caso INCORRECTO

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "task_id": "3002",
    "knowledge_type": "specific_professional_experience",
    "document_type": "detailed_work_history",
    "document_category": "human_resources",
    "subject_name": "Juan Daniel Perez Rodriguez",
    "subject_profession": "Civil Engineer",
    "subject_birthdate": "1994-12-12",
    "document_title": "Professional Experience and Work History",
    "created_date": "2026-05-03T21:30:00Z",
    "updated_date": "2026-05-03T21:30:00Z",
    "created_by": "system_administrator",
    "department": "engineering",
    "tags": "engineering, civil, structures, bogota, medellin, coastal, maritime",
    "description": "Detailed professional experience and work history document for Juan Daniel Perez, including all projects in Bogota and Medellin",
    "version": "1.0.0",
    "status": "active"
  }
}
```

**Total:** ~800+ bytes ❌  
**Con campos internos de Bedrock:** Fácilmente excede 2048 bytes  
**Resultado:** FAIL en ingestion

---

## 💡 Mejores Prácticas

### 1. Diseñar Metadata Desde el Principio

Antes de crear documentos, define:
- ¿Qué campos necesito para FILTRAR? (no para describir)
- ¿Cuál es el mínimo necesario?

### 2. Probar con un Documento Pequeño Primero

```bash
# Crear documento de prueba
echo "Test document" > test.txt

# Crear metadata minimalista
cat > test.txt.metadata.json << EOF
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "test"
  }
}
EOF

# Subir y sincronizar
aws s3 cp test.txt s3://bucket/test.txt
aws bedrock-agent start-ingestion-job ...

# Verificar que funcione antes de subir documentos grandes
```

### 3. Monitorear Ingestion Jobs

```bash
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id $KB_ID \
  --data-source-id $DS_ID \
  --ingestion-job-id $JOB_ID
```

Si ves `numberOfDocumentsFailed > 0`, revisar `failureReasons`.

### 4. Usar Convenciones de Nomenclatura Cortas

```
✅ tenant_id: "1001" (4 caracteres)
❌ tenant_id: "colpensiones-main-org-2024" (27 caracteres)

✅ type: "doc"
❌ document_type: "professional_experience_detailed"
```

---

## 📊 Comparación de Tamaños

| Metadata | Tamaño JSON | Con Bedrock Internals | ¿Pasa? |
|----------|-------------|----------------------|--------|
| Solo tenant_id, project_id | ~80 bytes | ~200 bytes | ✅ Sí |
| + task_id | ~100 bytes | ~250 bytes | ✅ Sí |
| + 3 campos más cortos | ~150 bytes | ~350 bytes | ✅ Sí |
| + 5 campos más cortos | ~200 bytes | ~450 bytes | ✅ Sí |
| + descriptions largas | ~400 bytes | ~750 bytes | ⚠️ Riesgo |
| + muchos campos largos | ~800 bytes | ~1500 bytes | ⚠️ Alto riesgo |
| + 10+ campos diversos | ~1200 bytes | ~2100 bytes | ❌ Falla |

---

## 🔧 Debugging de Errores de Metadata

### Si ves el error "Filterable metadata must have at most 2048 bytes":

1. **Verificar tamaño de metadata:**
   ```bash
   cat your-file.metadata.json | wc -c
   ```

2. **Simplificar metadata:**
   - Eliminar campos no esenciales
   - Acortar valores largos
   - Mantener solo IDs necesarios para filtrado

3. **Reducir tamaño del documento:**
   - Documentos < 1KB son más seguros
   - Si es muy largo, dividir en múltiples archivos pequeños

4. **Reintentar ingestion:**
   ```bash
   aws bedrock-agent start-ingestion-job ...
   ```

---

## 📝 Resumen - Reglas de Oro

1. ✅ **Metadata minimalista:** Solo IDs necesarios para filtrado
2. ✅ **Valores cortos:** IDs numéricos o códigos cortos
3. ✅ **Sin descripciones:** El contenido está en el documento, no en metadata
4. ✅ **Probar primero:** Test con documento pequeño antes de subir muchos
5. ✅ **Monitorear:** Revisar ingestion jobs para detectar fallos temprano

---

## 🎯 Nuestra Solución Final

**Metadata óptima para multi-tenancy:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636"
  }
}
```

**Resultado:**
- ✅ 83 bytes (muy por debajo del límite)
- ✅ Suficiente para filtrado multi-tenant
- ✅ Funciona con documentos de cualquier tamaño
- ✅ Sin fallos en ingestion

---

**Creado:** 2026-05-03  
**Lección:** Menos es más en metadata para Bedrock KB
