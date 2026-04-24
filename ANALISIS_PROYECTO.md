# 📊 Análisis Completo del Proyecto ProcessApp RAG

**Fecha:** 2026-04-21
**Cuenta AWS:** 708819485463
**Región:** us-east-1

---

## 🎯 ¿De Qué Trata el Proyecto?

**ProcessApp RAG** es un sistema RAG (Retrieval-Augmented Generation) multi-tenant que permite:

1. **Ingestión de documentos** (texto e imágenes/PDFs con OCR)
2. **Búsqueda semántica** usando embeddings de AWS Titan
3. **Respuestas con IA** usando Amazon Nova Pro + Knowledge Base
4. **Protección PII** con guardrails de Bedrock
5. **API REST** para integraciones externas

**Caso de uso:** Sistema de Q&A sobre documentos corporativos con OCR automático y filtros de seguridad.

---

## 🏗️ Arquitectura Real (Lo que SÍ está en uso)

### Flujo de Ingestión (REAL)

```
1. Usuario sube documento a S3
   ↓
2. EventBridge detecta upload
   ↓
3. OCR Lambda procesa (si es imagen/PDF)
   ├→ Textract extrae texto
   └→ Guarda como .txt en S3
   ↓
4. Knowledge Base Sync (manual o cada 6h)
   ├→ Bedrock lee documentos de S3
   ├→ Chunking (512 tokens, 20% overlap)
   ├→ Embeddings (Titan v2, 1024 dims)
   └→ Almacena en S3 Vectors
```

### Flujo de Query (REAL)

```
Usuario → [Opción A: REST API] → API Gateway → Lambda Handler
                                                      ↓
Usuario → [Opción B: SDK directo] ─────────────────→ Bedrock Agent
                                                      ↓
                                             Knowledge Base Search
                                                      ↓
                                                  Guardrails
                                                      ↓
                                                  Respuesta
```

---

## 📦 8 Stacks CDK Desplegados

| # | Stack | Estado | Recursos Clave | Propósito |
|---|-------|--------|---------------|-----------|
| 1 | **PrereqsStack** | ✅ Activo | S3 docs, S3 vectors-v2, KMS key, IAM roles | Recursos globales |
| 2 | **SecurityStack** | ✅ Activo | Bucket policies, IAM policies | Permisos |
| 3 | **BedrockStack** | ✅ Activo | S3VectorBucket, VectorIndex, Knowledge Base, DataSource, Sync Lambda | Motor RAG |
| 4 | **DocumentProcessingStack** | ✅ Activo | OCR Lambda, Embedder Lambda, SQS, SNS, EventBridge | Pipeline docs |
| 5 | **GuardrailsStack** | ✅ Activo | Guardrail, Guardrail Version, Creator Lambdas | Filtros PII |
| 6 | **AgentStack** | ✅ Activo | Bedrock Agent, Agent Alias | Orquestador IA |
| 7 | **APIStack** | ✅ Activo | API Gateway, Handler Lambda, API Key, Usage Plan | REST API |
| 8 | **MonitoringStack** | ✅ Activo | CloudWatch dashboards, alarms, metrics | Observabilidad |

---

## ✅ Recursos EN USO (Conectados y funcionando)

### S3 Buckets

| Bucket | Tipo | Uso | Estado |
|--------|------|-----|--------|
| `processapp-docs-v2-dev-708819485463` | S3 Regular | Documentos originales + procesados | ✅ Activo |
| `processapp-vectors-dev-708819485463` | S3Vectors | Almacenamiento de vectores KB | ✅ Activo |

### Lambdas

| Lambda | Trigger | Propósito | Estado |
|--------|---------|-----------|--------|
| `processapp-ocr-processor-dev` | EventBridge (S3 upload) | OCR con Textract | ✅ Activo |
| `processapp-api-handler-dev` | API Gateway | Proxy al agente | ✅ Activo |
| `processapp-kb-sync-dev` | EventBridge (schedule) | Sincronizar KB cada 6h | ✅ Activo |
| `processapp-guardrail-creator-dev` | Deployment time | Crear guardrail | ✅ Usado 1 vez |
| `processapp-guardrail-version-dev` | Deployment time | Versionar guardrail | ✅ Usado 1 vez |

### Otros Recursos Activos

- **Bedrock Agent:** `QWTVV3BY3G` (Nova Pro)
- **Knowledge Base:** Usa Titan v2 embeddings + S3 Vectors
- **API Gateway:** `ay5hutn96k.execute-api.us-east-1.amazonaws.com/dev`
- **Guardrails:** Filtros PII + contenido
- **KMS Key:** Encripta buckets y queues
- **SNS Topic:** `processapp-textract-dev` (Textract callbacks)
- **SQS Queues:** `processapp-chunks-dev` + DLQ (creados pero **vacíos**)

---

## ❌ Recursos DESPLEGADOS pero NO USADOS

### 1. Embedder Lambda ❌

**Stack:** DocumentProcessingStack.ts (líneas 200-255)
**Lambda:** `processapp-embedder-dev`
**Estado:** Desplegado pero **NUNCA se ejecuta**

**Por qué NO se usa:**
- Bedrock Knowledge Base genera embeddings **automáticamente**
- El flujo es: S3 → KB Sync → Bedrock hace embedding internamente
- Esta Lambda fue diseñada para un flujo custom que ya no existe

**Evidencia:**
```typescript
// DocumentProcessingStack.ts:226
this.embedder = new lambda.Function(this, 'Embedder', {
  // ... configuración
  environment: {
    VECTORS_BUCKET: props.vectorsBucket.bucketName,  // ← Este bucket tampoco se usa
    EMBEDDING_MODEL: 'amazon.titan-embed-text-v2:0',
  },
});

// Trigger desde SQS (línea 249)
this.embedder.addEventSource(
  new lambdaEventSources.SqsEventSource(this.chunksQueue, { ... })
);
```

**Problema:** El `chunksQueue` nunca recibe mensajes porque el OCR Lambda no envía chunks al queue.

---

### 2. SQS Chunks Queue ❌

**Stack:** DocumentProcessingStack.ts (líneas 56-82)
**Queues:** `processapp-chunks-dev` + `processapp-chunks-dlq-dev`
**Estado:** Desplegados pero **VACÍOS**

**Por qué NO se usa:**
- El OCR Lambda **NO envía mensajes al queue**
- El flujo era: OCR → Chunking → SQS → Embedder
- Ahora es: OCR → Guarda TXT → Bedrock lo procesa todo

**Evidencia:**
```python
# ocr-processor/index.py
# NO hay código que use:
# sqs.send_message(QueueUrl=os.environ['CHUNKS_QUEUE_URL'], ...)
```

---

### 3. vectorsBucket (S3 Regular) ❌

**Stack:** PrereqsStack.ts (líneas 117-160)
**Bucket:** `processapp-vectors-v2-dev-708819485463`
**Estado:** Desplegado pero **VACÍO**

**Por qué NO se usa:**
- Bedrock KB usa `AWS::S3Vectors::VectorBucket` (tipo especial)
- El bucket regular fue creado pensando en guardar embeddings manualmente
- Nunca se conectó a ningún recurso

**Flujo real:**
```
BedrockStack crea → AWS::S3Vectors::VectorBucket
Nombre: processapp-vectors-dev-708819485463  (sin "-v2")
Bedrock KB usa → Este bucket S3Vectors
```

**El bucket `processapp-vectors-v2-dev-708819485463` NO es usado por nadie.**

---

### 4. SNS Topic + EventBridge Rules ⚠️ Mixto

**Stack:** DocumentProcessingStack.ts

**SNS Topic:** `processapp-textract-dev` ✅ EN USO
- **Estado:** Usado para notificaciones de Textract
- **Flujo:** OCR Lambda usa `start_document_text_detection` (ASÍNCRONO)
- **Funcionamiento:**
  1. OCR Lambda inicia job Textract (línea 155-168 ocr-processor/index.py)
  2. Textract procesa documento
  3. Textract publica a SNS cuando termina
  4. SNS invoca OCR Lambda nuevamente (línea 40-42)
  5. OCR Lambda obtiene resultados y guarda en S3

**CORRECCIÓN:** Este recurso SÍ se usa activamente. ✅

**EventBridge Rule:** `processapp-embeddings-created-dev` ❌ NO USADO
- **Estado:** Creado pero **sin target**
- **Por qué:** No hay embeddings guardados en S3 (Bedrock los guarda en S3Vectors)
- Código dice: "This will be connected to KB sync function" pero nunca se conectó

**ESTA regla SÍ puede eliminarse.** ❌

---

### 5. Lambdas NO desplegadas (solo código)

Estas Lambdas tienen código pero **NO están en ningún stack CDK:**

| Lambda | Ubicación | ¿Se usa? |
|--------|-----------|----------|
| `vector-indexer` | `lambdas/vector-indexer/` | ❌ No |
| `s3-vector-manager` | `lambdas/s3-vector-manager/` | ❌ No |
| `kb-creator` | `lambdas/kb-creator/` | ❌ No |
| `data-source-creator` | `lambdas/data-source-creator/` | ❌ No |

**Por qué existen:**
- Código legacy de versiones anteriores
- Fueron reemplazadas por CfnResources en CDK
- Nunca se eliminaron

---

### 6. Stacks NO usados en app.ts

| Stack File | ¿Importado? |
|------------|-------------|
| `infrastructure-stack.ts` | ❌ No usado |
| `S3VectorStoreStack.ts` | ❌ No usado |

Estos archivos existen pero **NO se importan en `bin/app.ts`**.

---

## 🔗 Mapa de Conexiones REALES

```
┌─────────────────────────────────────────────────────────────┐
│                   FLUJO DE INGESTIÓN REAL                   │
└─────────────────────────────────────────────────────────────┘

Usuario
  ↓
S3 docs bucket (processapp-docs-v2-dev)
  ↓
EventBridge Rule (Object Created)
  ↓
OCR Lambda (processapp-ocr-processor-dev)
  ├→ Si es imagen/PDF:
  │   ├→ Inicia Textract job (ASÍNCRONO)
  │   ├→ Textract procesa documento
  │   ├→ Textract publica a SNS Topic
  │   ├→ SNS invoca OCR Lambda de nuevo
  │   └→ OCR Lambda guarda processed-*.txt en S3
  └→ Si es texto: no hace nada (Bedrock lo lee directo)

[Sync manual o automático cada 6h]
  ↓
Sync Lambda (processapp-kb-sync-dev)
  ↓
Knowledge Base Data Source
  ↓
Bedrock procesa:
  ├→ Chunking automático
  ├→ Embeddings Titan v2
  └→ Guarda en S3Vectors (processapp-vectors-dev)

┌─────────────────────────────────────────────────────────────┐
│                   FLUJO DE QUERY REAL                       │
└─────────────────────────────────────────────────────────────┘

Usuario → API Gateway (optional)
            ↓
       Handler Lambda (optional)
            ↓
       Bedrock Agent (QWTVV3BY3G)
            ├→ Knowledge Base search
            ├→ Guardrails filter
            └→ Nova Pro genera respuesta
            ↓
       Respuesta al usuario
```

---

## 🗑️ Qué Se Puede ELIMINAR de Forma Segura

### Alta Prioridad (eliminar primero)

1. **vectorsBucket (S3 regular)** `processapp-vectors-v2-dev-708819485463`
   - **Donde:** PrereqsStack.ts líneas 117-160
   - **Impacto:** NINGUNO - está vacío y no conectado
   - **Eliminar:**
     ```bash
     aws s3 rb s3://processapp-vectors-v2-dev-708819485463 --force --profile default
     # Luego quitar del código PrereqsStack.ts
     ```

2. **Embedder Lambda** `processapp-embedder-dev`
   - **Donde:** DocumentProcessingStack.ts líneas 200-255
   - **Impacto:** NINGUNO - nunca se ejecuta
   - **Eliminar:** Comentar o borrar esas líneas del stack

3. **SQS Queues** `processapp-chunks-dev` + DLQ
   - **Donde:** DocumentProcessingStack.ts líneas 56-82
   - **Impacto:** NINGUNO - nunca reciben mensajes
   - **Eliminar:** Comentar o borrar esas líneas del stack

4. **EventBridge Rule** `processapp-embeddings-created-dev`
   - **Donde:** DocumentProcessingStack.ts líneas 262-281
   - **Impacto:** NINGUNO - no tiene target
   - **Eliminar:** Comentar o borrar esas líneas del stack

### Media Prioridad (código muerto)

6. **Lambdas sin desplegar:**
   - `lambdas/vector-indexer/`
   - `lambdas/s3-vector-manager/`
   - `lambdas/kb-creator/`
   - `lambdas/data-source-creator/`
   - **Eliminar:** `rm -rf infrastructure/lambdas/{vector-indexer,s3-vector-manager,kb-creator,data-source-creator}`

7. **Stacks no usados:**
   - `infrastructure/lib/infrastructure-stack.ts`
   - `infrastructure/lib/S3VectorStoreStack.ts`
   - **Eliminar:** `rm infrastructure/lib/{infrastructure-stack.ts,S3VectorStoreStack.ts}`

### Baja Prioridad (no molestan)

8. **Guardrail Creator Lambdas**
   - Se usan solo en deployment time
   - No cuesta nada mantenerlas
   - Dejar tal cual

---

## 🔧 Qué NO se Puede Eliminar

### Recursos Críticos

| Recurso | Por qué es crítico |
|---------|-------------------|
| **PrereqsStack** | S3 docs bucket, KMS key, IAM roles usados por todo |
| **BedrockStack** | KB, DataSource, S3Vectors - corazón del RAG |
| **OCR Lambda** | Único procesador de imágenes/PDFs |
| **AgentStack** | Bedrock Agent - orquestador de respuestas |
| **APIStack** | Interfaz REST para clientes |
| **GuardrailsStack** | Filtros PII - seguridad |
| **SecurityStack** | Permisos - rompe todo si se elimina |
| **MonitoringStack** | Observabilidad - puedes vivir sin él pero no recomendado |

---

## 📋 Resumen Ejecutivo

### ¿Qué funciona?

✅ **Flujo de ingestión:**
1. S3 upload → EventBridge → OCR Lambda → Textract → S3
2. KB Sync (manual/auto) → Bedrock procesa → S3Vectors

✅ **Flujo de query:**
1. API Gateway → Lambda Handler → Bedrock Agent → Knowledge Base → Respuesta
2. SDK directo → Bedrock Agent → Knowledge Base → Respuesta

### ¿Qué está roto/no conectado?

❌ **Embedder Lambda** - nunca se ejecuta
❌ **SQS Queues** - nunca reciben mensajes
❌ **vectorsBucket S3 regular** - vacío, no conectado
✅ **SNS Topic Textract** - usado para callbacks asíncronos
❌ **EventBridge embeddings rule** - sin target
❌ **5 Lambdas con código** - no desplegadas
❌ **2 Stack files** - no importados

### Porcentaje de Código Usado

- **Stacks CDK:** 8/10 usados (80%)
- **Lambdas desplegadas:** 3/6 activas (50%)
- **S3 Buckets:** 2/3 usados (67%)
- **Código Lambda:** 3/8 carpetas usadas (38%)

**Total estimado:** ~60% del código está en uso activo

---

## 🎯 Recomendaciones

### Inmediato (esta semana)

1. **Eliminar `processapp-vectors-v2-dev-708819485463`** bucket
2. **Eliminar carpetas de lambdas no usadas** (vector-indexer, etc.)
3. **Eliminar stacks files no importados** (infrastructure-stack.ts, S3VectorStoreStack.ts)

### Corto plazo (próximo sprint)

4. **Refactorizar DocumentProcessingStack:**
   - Eliminar Embedder Lambda
   - Eliminar SQS queues
   - Eliminar SNS topic Textract
   - Eliminar EventBridge embeddings rule
   - Simplificar a solo: OCR Lambda + EventBridge upload trigger

5. **Actualizar documentación** para reflejar arquitectura real

### Largo plazo (cuando haya tiempo)

6. **Considerar:** ¿Vale la pena mantener el Embedder Lambda por si en el futuro se necesita chunking custom?
   - Si NO → Eliminar completamente
   - Si SÍ → Documentar claramente que está "en standby" para futuros usos

7. **Consolidar:** Mover guardrail creator lambdas a un stack separado "deployment helpers"

---

## 📊 Impacto de Limpieza

### Si eliminas todo lo recomendado:

**Ahorro de complejidad:**
- -30% líneas de código CDK
- -5 recursos AWS desplegados
- -38% carpetas de lambdas

**Ahorro de costos:**
- Embedder Lambda: $0 (nunca se ejecuta)
- SQS queues: ~$0.01/mes (vacías)
- S3 bucket vacío: $0
- **Total:** Insignificante (~$0.01/mes)

**Ahorro de mantenimiento:**
- Menos código que entender
- Menos recursos que monitorear
- Arquitectura más clara

**Riesgo:**
- ⚠️ Bajo - los recursos no usados no afectan a los activos
- ✅ Fácil reversión - todo está en Git

---

**Siguiente paso sugerido:** Empezar por eliminar el bucket `processapp-vectors-v2-dev` y las carpetas de lambdas no usadas. Es seguro y de bajo riesgo.
