# 🧹 Plan de Limpieza Segura - ProcessApp RAG

Plan gradual para eliminar código y recursos no usados **sin afectar la infraestructura funcionando**.

---

## 🎯 Estrategia

1. **Fase 1:** Limpiar código muerto (no desplegado) ✅ **SEGURO**
2. **Fase 2:** Eliminar buckets vacíos ✅ **SEGURO**
3. **Fase 3:** Actualizar stacks CDK (quitar recursos no usados) ⚠️ **Requiere redeploy**
4. **Fase 4:** Limpiar recursos AWS desplegados ⚠️ **Requiere cuidado**

**Principio:** Cada fase puede revertirse. Git commit entre fases.

---

## ✅ FASE 1: Código Muerto (100% Seguro)

**Qué eliminar:** Código que NO está desplegado ni importado.

**Riesgo:** CERO - este código no está en uso.

### Paso 1.1: Eliminar carpetas de Lambdas no desplegadas

```bash
# Estas lambdas NO están en ningún stack CDK
cd infrastructure/lambdas
rm -rf vector-indexer/
rm -rf s3-vector-manager/
rm -rf kb-creator/
rm -rf data-source-creator/
rm -rf guardrail-creator/  # Ya se usó en deployment, no se necesita más

# Verificar que solo quedan las usadas
ls -la
# Debe quedar solo:
# - ocr-processor/     ✅
# - api-handler/       ✅
# - embedder/          ⚠️  (lo quitaremos en Fase 3)
```

### Paso 1.2: Eliminar stack files no importados

```bash
cd infrastructure/lib
rm infrastructure-stack.ts infrastructure-stack.d.ts
rm S3VectorStoreStack.ts S3VectorStoreStack.d.ts

# Verificar que app.ts no los importa
grep -r "infrastructure-stack" ../bin/app.ts
grep -r "S3VectorStoreStack" ../bin/app.ts
# Debe devolver: nada
```

### Paso 1.3: Commit

```bash
git add -A
git commit -m "chore: remove unused lambda code and stack files

- Remove lambdas not deployed: vector-indexer, s3-vector-manager, kb-creator, data-source-creator, guardrail-creator
- Remove unused stack files: infrastructure-stack.ts, S3VectorStoreStack.ts
- No infrastructure impact - these were never deployed"
```

**✅ Checkpoint:** Si algo falla, `git reset --hard HEAD~1`

---

## ✅ FASE 2: Buckets Vacíos (100% Seguro)

**Qué eliminar:** Bucket S3 regular `processapp-vectors-v2-dev-708819485463` que está vacío.

**Riesgo:** CERO - no contiene datos y no está conectado a nada.

### Paso 2.1: Verificar que está vacío

```bash
# Verificar que está vacío
aws s3 ls s3://processapp-vectors-v2-dev-708819485463 --profile default
# Debe devolver: nada

# Verificar tamaño
aws s3api head-bucket --bucket processapp-vectors-v2-dev-708819485463 --profile default
```

### Paso 2.2: Eliminar bucket de AWS

```bash
# Eliminar bucket (está vacío, no necesita --force)
aws s3 rb s3://processapp-vectors-v2-dev-708819485463 --profile default

# Verificar que se eliminó
aws s3 ls --profile default | grep vectors
# Debe mostrar solo: processapp-vectors-dev-708819485463 (sin -v2)
```

### Paso 2.3: Eliminar del código CDK

**Editar:** `infrastructure/lib/PrereqsStack.ts`

**Buscar líneas 117-160** (la sección `this.vectorsBucket = new s3.Bucket`)

**Comentar o eliminar completamente esa sección.**

También buscar en:
- `infrastructure/bin/app.ts` donde se pasa `vectorsBucket` a otros stacks
- Cualquier referencia a `props.vectorsBucket`

### Paso 2.4: Compilar y verificar

```bash
cd infrastructure
npm run build

# Si hay errores, arreglar referencias
# Buscar todos los usos:
grep -r "vectorsBucket" lib/ bin/
```

### Paso 2.5: Commit

```bash
git add -A
git commit -m "chore: remove unused vectors bucket (regular S3)

- Remove processapp-vectors-v2-dev-708819485463 bucket
- This bucket was empty and not connected to any resource
- Bedrock KB uses AWS::S3Vectors (processapp-vectors-dev) instead
- Bucket already deleted from AWS"
```

**✅ Checkpoint:** Si algo falla, `git reset --hard HEAD~1` y recrea el bucket.

---

## ⚠️ FASE 3: Limpiar Stacks CDK (Requiere Redeploy)

**Qué hacer:** Eliminar recursos del código CDK que están desplegados pero no usados.

**Riesgo:** MEDIO - requiere redeploy, pero los recursos a eliminar no afectan funcionalidad.

**Estrategia:** Hacer cambios incrementales, un recurso a la vez.

### Paso 3.1: Eliminar SQS Queues

**Editar:** `infrastructure/lib/DocumentProcessingStack.ts`

**Comentar líneas 56-82** (chunksQueue y DLQ):

```typescript
// ========================================
// SQS QUEUE FOR TEXT CHUNKS - NOT USED
// ========================================
// Bedrock KB handles chunking internally, no need for SQS
/*
const dlq = new sqs.Queue(this, 'ChunksDLQ', {
  ...
});

this.chunksQueue = new sqs.Queue(this, 'ChunksQueue', {
  ...
});
*/
```

**Actualizar exports** del stack (quitar `chunksQueue`):

```typescript
export class DocumentProcessingStack extends cdk.Stack {
  public readonly ocrProcessor: lambda.Function;
  public readonly embedder: lambda.Function;
  // public readonly chunksQueue: sqs.Queue;  // ← Comentar
```

**Buscar referencias** en otros archivos:

```bash
grep -r "chunksQueue" infrastructure/
```

**Arreglar MonitoringStack** si tiene referencias.

### Paso 3.2: Eliminar Embedder Lambda

**En el mismo archivo**, comentar líneas 200-255:

```typescript
// ========================================
// EMBEDDER LAMBDA - NOT USED
// ========================================
// Bedrock KB generates embeddings automatically
/*
const embedderRole = new iam.Role(this, 'EmbedderRole', {
  ...
});

this.embedder = new lambda.Function(this, 'Embedder', {
  ...
});

this.embedder.addEventSource(
  new lambdaEventSources.SqsEventSource(this.chunksQueue, { ... })
);
*/
```

**Actualizar exports:**

```typescript
export class DocumentProcessingStack extends cdk.Stack {
  public readonly ocrProcessor: lambda.Function;
  // public readonly embedder: lambda.Function;  // ← Comentar
  // public readonly chunksQueue: sqs.Queue;
```

### Paso 3.3: Eliminar EventBridge Rule no usada

**En el mismo archivo**, comentar líneas 262-281:

```typescript
// ========================================
// EVENTBRIDGE RULE: TRIGGER KB SYNC - NOT USED
// ========================================
// This rule was never connected to a target
/*
const embeddingsCreatedRule = new events.Rule(
  this,
  'EmbeddingsCreatedRule',
  {
    ...
  }
);
*/
```

### Paso 3.4: Compilar y verificar

```bash
cd infrastructure
npm run build

# Si hay errores de referencias, arreglar
grep -r "embedder" lib/
grep -r "chunksQueue" lib/
```

### Paso 3.5: CDK Diff (ver cambios antes de aplicar)

```bash
npx cdk diff dev-us-east-1-document-processing --profile default

# Debe mostrar:
# [-] AWS::Lambda::Function embedder
# [-] AWS::SQS::Queue chunks-queue
# [-] AWS::SQS::Queue chunks-dlq
# [-] AWS::Events::Rule embeddings-created
```

### Paso 3.6: Deploy solo este stack

```bash
# Deploy SOLO el stack modificado
npx cdk deploy dev-us-east-1-document-processing --profile default

# Esto eliminará los recursos no usados
```

### Paso 3.7: Verificar que todo sigue funcionando

```bash
# Probar el agente
python3 scripts/test-agent.py

# Ver logs OCR (debe seguir funcionando)
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile default
```

### Paso 3.8: Commit

```bash
git add -A
git commit -m "refactor: remove unused resources from DocumentProcessingStack

- Remove Embedder Lambda (Bedrock KB handles embeddings)
- Remove SQS chunks queue (not used)
- Remove EventBridge embeddings rule (no target)
- OCR Lambda continues working normally
- Tested: agent still responds correctly"
```

**✅ Checkpoint:** Si algo falla:
```bash
git reset --hard HEAD~1
cd infrastructure
npm run build
npx cdk deploy dev-us-east-1-document-processing --profile default
```

---

## ⚠️ FASE 4: Limpiar Código Embedder (Seguro después de Fase 3)

**Qué hacer:** Eliminar carpeta `embedder/` después de que la Lambda fue eliminada de AWS.

**Riesgo:** BAJO - la Lambda ya no existe en AWS.

### Paso 4.1: Verificar que la Lambda fue eliminada

```bash
aws lambda list-functions --query 'Functions[?contains(FunctionName, `embedder`)]' --profile default
# Debe devolver: []
```

### Paso 4.2: Eliminar carpeta

```bash
rm -rf infrastructure/lambdas/embedder/
```

### Paso 4.3: Commit

```bash
git add -A
git commit -m "chore: remove embedder lambda code

- Lambda already deleted from AWS in previous deployment
- Code no longer needed"
```

---

## 📋 Checklist de Ejecución

### Pre-requisitos

- [ ] Hacer backup completo del repo: `git branch backup-before-cleanup`
- [ ] Verificar que todo funciona: `python3 scripts/test-agent.py`
- [ ] Tener acceso a AWS CLI con perfil `default`

### Fase 1: Código Muerto ✅ SEGURO

- [ ] Eliminar lambdas no desplegadas (5 carpetas)
- [ ] Eliminar stack files no importados (2 archivos)
- [ ] Commit cambios
- [ ] Verificar: `npm run build` pasa sin errores

### Fase 2: Buckets Vacíos ✅ SEGURO

- [ ] Verificar bucket está vacío
- [ ] Eliminar bucket de AWS
- [ ] Eliminar del código CDK
- [ ] Compilar: `npm run build`
- [ ] Commit cambios

### Fase 3: Stacks CDK ⚠️ REQUIERE DEPLOY

- [ ] Comentar SQS queues en DocumentProcessingStack
- [ ] Comentar Embedder Lambda
- [ ] Comentar EventBridge rule
- [ ] Compilar: `npm run build`
- [ ] CDK diff: verificar cambios
- [ ] Deploy: `npx cdk deploy dev-us-east-1-document-processing`
- [ ] Probar agente: `python3 scripts/test-agent.py`
- [ ] Commit cambios

### Fase 4: Limpiar Código ✅ SEGURO

- [ ] Verificar Lambda eliminada de AWS
- [ ] Eliminar carpeta embedder/
- [ ] Commit cambios

---

## 🔄 Plan de Rollback

Si algo sale mal en **Fase 3**:

```bash
# 1. Revertir cambios de código
git reset --hard HEAD~1

# 2. Recompilar
cd infrastructure
npm run build

# 3. Redesplegar stack anterior
npx cdk deploy dev-us-east-1-document-processing --profile default

# 4. Verificar funcionamiento
python3 scripts/test-agent.py
```

Si todo falla:

```bash
# Volver al backup
git checkout backup-before-cleanup
cd infrastructure
npm run build
npx cdk deploy --all --profile default
```

---

## ✅ Resultado Final

Después de todas las fases:

**Eliminado:**
- ❌ 5 carpetas de lambdas no usadas
- ❌ 2 stack files no importados
- ❌ 1 bucket S3 vacío
- ❌ 2 SQS queues vacías
- ❌ 1 Lambda embedder
- ❌ 1 EventBridge rule sin target

**Mantenido:**
- ✅ OCR Lambda (funcionando)
- ✅ API Gateway + Handler
- ✅ Bedrock Agent + KB
- ✅ Guardrails
- ✅ SNS Topic Textract
- ✅ Todos los recursos críticos

**Ahorro:**
- ~30% menos código CDK
- ~5 recursos AWS menos
- ~38% menos carpetas de lambdas
- Arquitectura más clara y mantenible

---

## 🎯 Orden de Ejecución Recomendado

**Hoy (30 min):**
1. Fase 1: Eliminar código muerto
2. Commit

**Mañana (30 min):**
3. Fase 2: Eliminar bucket vacío
4. Commit

**Próxima semana (1 hora):**
5. Fase 3: Limpiar stacks CDK
6. Deploy y probar
7. Commit

**Cuando quieras (5 min):**
8. Fase 4: Eliminar código embedder
9. Commit final

---

**Última actualización:** 2026-04-21
**Tiempo total estimado:** 2 horas
**Riesgo total:** BAJO con este plan gradual
