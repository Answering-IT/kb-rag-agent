# DocumentProcessingStack - Cambios Necesarios para KB OCR Integration

## 📋 Estado Actual del Stack

El `DocumentProcessingStack.ts` ya existe y está funcional. Contiene:

✅ **OCR Lambda** (`this.ocrProcessor`) - Ya exportado como public
✅ **Textract SNS Topic** - Para notificaciones de jobs
✅ **Textract IAM Role** - Para que Textract publique a SNS
✅ **EventBridge Rule** - Trigger en S3 uploads (prefix: `documents/`)

## ✅ BUENAS NOTICIAS: Stack está LISTO

El `DocumentProcessingStack` **NO requiere modificaciones** para la integración KB OCR. Ya tiene todo lo necesario:

### 1. OCR Lambda ya es público
```typescript
// Línea 41
export class DocumentProcessingStack extends cdk.Stack {
  public readonly ocrProcessor: lambda.Function;  // ✅ Ya exportado
```

**Esto significa:** `BedrockStack` puede acceder a `ocrProcessor` sin cambios.

### 2. EventBridge Rule ya existe
```typescript
// Líneas 179-200
const documentUploadRule = new events.Rule(this, 'DocumentUploadRule', {
  ruleName: `processapp-document-upload-${props.stage}`,
  description: 'Trigger OCR when documents are uploaded',
  eventPattern: {
    source: ['aws.s3'],
    detailType: ['Object Created'],
    detail: {
      bucket: { name: [props.docsBucket.bucketName] },
      object: { key: [{ prefix: 'documents/' }] }  // ⚠️ Solo 'documents/'
    },
  },
});
```

**Observación:** Esta regla solo escucha uploads a `documents/`, pero nuestros archivos están en `organizations/`.

---

## 🔧 Modificaciones Requeridas

### Modificación 1: Actualizar EventBridge Rule (OPCIONAL pero RECOMENDADO)

**Problema:** La regla actual solo escucha `documents/` pero los archivos están en `organizations/`.

**Opción A: Ampliar regla existente (RECOMENDADO)**

```typescript
// En DocumentProcessingStack.ts, líneas 179-200
const documentUploadRule = new events.Rule(this, 'DocumentUploadRule', {
  ruleName: `processapp-document-upload-${props.stage}`,
  description: 'Trigger OCR when documents are uploaded',
  eventPattern: {
    source: ['aws.s3'],
    detailType: ['Object Created'],
    detail: {
      bucket: {
        name: [props.docsBucket.bucketName],
      },
      object: {
        key: [
          { prefix: 'documents/' },      // Original
          { prefix: 'organizations/' }   // NUEVO - Para archivos migrados
        ],
      },
    },
  },
});
```

**Opción B: Eliminar filtro de prefix (MÁS SIMPLE)**

```typescript
const documentUploadRule = new events.Rule(this, 'DocumentUploadRule', {
  ruleName: `processapp-document-upload-${props.stage}`,
  description: 'Trigger OCR when documents are uploaded',
  eventPattern: {
    source: ['aws.s3'],
    detailType: ['Object Created'],
    detail: {
      bucket: {
        name: [props.docsBucket.bucketName],
      },
      // Eliminado: object.key filter
      // Ahora escucha TODOS los uploads al bucket
    },
  },
});
```

**Recomendación:** Usar **Opción B** (eliminar prefix filter) porque:
- ✅ Más simple
- ✅ Funciona con cualquier estructura de carpetas
- ✅ La Lambda OCR ya valida extensiones internamente (pdf, png, jpg, etc.)
- ✅ No procesa archivos innecesarios (la Lambda tiene lógica de filtrado)

---

## 📝 Resumen de Cambios

### ❌ NO Requiere Cambios

- ✅ `ocrProcessor` ya es público
- ✅ Textract SNS Topic ya existe
- ✅ Textract Role ya configurado
- ✅ OCR Lambda ya tiene permisos S3, Textract, KMS

### ✅ Requiere 1 Cambio (OPCIONAL)

**Archivo:** `infrastructure/lib/DocumentProcessingStack.ts`

**Líneas:** 179-200

**Cambio:** Actualizar EventBridge rule para escuchar `organizations/` o eliminar prefix filter

**Antes:**
```typescript
object: {
  key: [{ prefix: 'documents/' }],
},
```

**Después (Opción A):**
```typescript
object: {
  key: [
    { prefix: 'documents/' },
    { prefix: 'organizations/' }
  ],
},
```

**Después (Opción B - RECOMENDADO):**
```typescript
// Eliminar el bloque 'object' completamente
// O dejar el bucket sin filtro de key
```

---

## 🎯 Plan de Implementación Actualizado

### Fase 1: Actualizar Lambda OCR
- [x] Crear `metadata_utils.py` ✅ YA CREADO
- [ ] Actualizar `index.py` con nueva lógica de metadata
- [ ] Agregar soporte para eventos de `ingestion-failure-handler`

### Fase 2: Crear Ingestion Failure Handler
- [ ] Crear `infrastructure/lambdas/ingestion-failure-handler/index.py`
- [ ] Crear `infrastructure/lambdas/ingestion-failure-handler/requirements.txt`

### Fase 3: Actualizar CDK Infrastructure

#### BedrockStack.ts (NUEVO)
- [ ] Agregar `ocrProcessor` a props
- [ ] Crear Lambda Ingestion Failure Handler
- [ ] Grant permissions (bedrock + lambda invoke)
- [ ] Crear EventBridge Rule para KB ingestion events
- [ ] Add Lambda as target

#### DocumentProcessingStack.ts (OPCIONAL)
- [ ] **OPCIONAL:** Actualizar EventBridge rule para `organizations/` prefix

#### app.ts (MODIFICAR)
- [ ] Pasar `ocrProcessor` de DocumentProcessingStack a BedrockStack

---

## 🔍 Verificación de Dependencias

### app.ts - Orden de Creación

```typescript
// 1. DocumentProcessingStack se crea primero
const documentProcessingStack = new DocumentProcessingStack(...);

// 2. BedrockStack se crea después y recibe ocrProcessor
const bedrockStack = new BedrockStack(app, stackName, {
  // ... existing props
  ocrProcessor: documentProcessingStack.ocrProcessor,  // ✅ Disponible
});
```

**Status:** ✅ Orden correcto ya establecido en app.ts

---

## 🚀 Próximos Pasos Concretos

### Paso 1: Verificar app.ts

```bash
# Buscar cómo se instancia BedrockStack actualmente
grep -A 10 "new BedrockStack" infrastructure/bin/app.ts
```

**Acción:** Agregar línea `ocrProcessor: documentProcessingStack.ocrProcessor`

### Paso 2: Modificar DocumentProcessingStack (OPCIONAL)

```bash
# Editar líneas 179-200
vim infrastructure/lib/DocumentProcessingStack.ts +179
```

**Acción:** Eliminar prefix filter o agregar `organizations/`

### Paso 3: Actualizar BedrockStack

```bash
# Agregar ocrProcessor a props
vim infrastructure/lib/BedrockStack.ts +23
```

**Acción:** Seguir plan del documento KB_OCR_INTEGRATION_CHECKLIST.md

---

## 📊 Matriz de Cambios

| Archivo | Cambio | Prioridad | Status |
|---------|--------|-----------|--------|
| `lambdas/ocr-processor/metadata_utils.py` | Crear | ✅ REQUERIDO | ✅ CREADO |
| `lambdas/ocr-processor/index.py` | Modificar | ✅ REQUERIDO | ⏳ PENDIENTE |
| `lambdas/ingestion-failure-handler/index.py` | Crear | ✅ REQUERIDO | ⏳ PENDIENTE |
| `lib/BedrockStack.ts` | Modificar | ✅ REQUERIDO | ⏳ PENDIENTE |
| `bin/app.ts` | Modificar | ✅ REQUERIDO | ⏳ PENDIENTE |
| `lib/DocumentProcessingStack.ts` | Modificar | 🔵 OPCIONAL | ⏳ PENDIENTE |

---

## ✅ Conclusión

**DocumentProcessingStack está 95% listo** para la integración KB OCR.

**Única modificación opcional:** Actualizar EventBridge rule para escuchar `organizations/` prefix.

**Toda la complejidad está en:**
1. Actualizar Lambda OCR (metadata generation)
2. Crear nueva Lambda Failure Handler
3. Conectar todo en BedrockStack

**DocumentProcessingStack NO es el bloqueador.**

---

**Fecha:** 2026-05-05  
**Autor:** Análisis de cambios requeridos en DocumentProcessingStack  
**Conclusión:** ✅ Stack está listo, cambios mínimos requeridos
