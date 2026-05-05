# KB OCR Integration - Implementation Checklist

## 📋 Plan de Implementación

### Fase 1: Preparación de Lambda OCR (REQUERIDO)

#### ✅ Tarea 1.1: Crear metadata_utils.py

**Archivo:** `infrastructure/lambdas/ocr-processor/metadata_utils.py`

**Contenido:** Funciones para parsear S3 paths y generar metadata

- [ ] `parse_s3_path()` - Extrae tenant_id, project_id, task_id, subtask_id
- [ ] `generate_partition_key()` - Formato: `t{tenant}_p{project}_t{task}_s{subtask}`
- [ ] `generate_project_path()` - Formato: `organizations/{tenant}/projects/{project}/tasks/{task}/subtasks/{subtask}`
- [ ] `generate_metadata_json()` - Genera metadata en formato Bedrock KB

**Status:** ✅ CREADO - `/infrastructure/lambdas/ocr-processor/metadata_utils.py`

#### ✅ Tarea 1.2: Actualizar index.py - handler()

**Archivo:** `infrastructure/lambdas/ocr-processor/index.py`

**Cambios:**
```python
# Agregar import
from metadata_utils import parse_s3_path, generate_metadata_json

# Modificar handler() para aceptar eventos de failure handler
def handler(event, context):
    # Agregar case para 'ingestion-failure-handler'
    if event.get('source') == 'ingestion-failure-handler':
        return handle_s3_upload(event, context)
```

**Checklist:**
- [ ] Import `metadata_utils`
- [ ] Agregar case para `event.get('source') == 'ingestion-failure-handler'`
- [ ] Mantener compatibilidad con eventos S3 y SNS existentes

#### ✅ Tarea 1.3: Actualizar save_processed_text_to_s3()

**Archivo:** `infrastructure/lambdas/ocr-processor/index.py`

**Cambios:**
```python
def save_processed_text_to_s3(original_key: str, text: str) -> str:
    # 1. Parse S3 path
    parsed = parse_s3_path(original_key)
    tenant_id = parsed.get("tenant_id")
    project_id = parsed.get("project_id")
    task_id = parsed.get("task_id")
    subtask_id = parsed.get("subtask_id")
    
    # 2. Generate output key (same path, .txt extension)
    output_key = original_key.rsplit('.', 1)[0] + '.txt'
    
    # 3. Save text file
    s3.put_object(...)
    
    # 4. Generate metadata using metadata_utils
    if tenant_id:
        metadata_json = generate_metadata_json(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            subtask_id=subtask_id
        )
        
        # 5. Save metadata.json
        metadata_key = f'{output_key}.metadata.json'
        s3.put_object(
            Body=json.dumps(metadata_json, indent=2),
            ...
        )
```

**Checklist:**
- [ ] Usar `parse_s3_path()` para extraer IDs
- [ ] Usar `generate_metadata_json()` para crear metadata
- [ ] Guardar `.txt` en mismo directorio que original (no en `processed/`)
- [ ] Guardar `.metadata.json` junto al `.txt`
- [ ] NO incluir `partition_type` en metadata
- [ ] Incluir `project_path` con jerarquía correcta

---

### Fase 2: Crear Ingestion Failure Handler (NUEVO)

#### ✅ Tarea 2.1: Crear Lambda Handler

**Archivo:** `infrastructure/lambdas/ingestion-failure-handler/index.py`

**Funcionalidad:**
1. Recibe evento de EventBridge (ingestion job completion)
2. Llama `bedrock_agent.get_ingestion_job()` para obtener `failureReasons`
3. Parsea failure reasons para extraer S3 URIs
4. Filtra solo errores recuperables con OCR
5. Invoca Lambda OCR para cada archivo fallido

**Checklist:**
- [ ] Crear directorio `infrastructure/lambdas/ingestion-failure-handler/`
- [ ] Crear `index.py` con handler
- [ ] Implementar `parse_failure_reasons()`
- [ ] Implementar `is_ocr_recoverable()`
- [ ] Implementar `invoke_ocr_lambda()`
- [ ] Agregar logging detallado
- [ ] Agregar error handling

#### ✅ Tarea 2.2: Crear requirements.txt

**Archivo:** `infrastructure/lambdas/ingestion-failure-handler/requirements.txt`

```
boto3>=1.26.0
```

**Checklist:**
- [ ] Crear archivo requirements.txt

---

### Fase 3: Actualizar CDK Infrastructure

#### ✅ Tarea 3.1: Actualizar BedrockStack.ts

**Archivo:** `infrastructure/lib/BedrockStack.ts`

**Cambios:**

1. **Agregar props.ocrProcessor:**
```typescript
export interface BedrockStackProps extends cdk.StackProps {
  // ... existing props
  ocrProcessor: lambda.IFunction;  // NEW: From DocumentProcessingStack
}
```

2. **Crear Lambda Ingestion Failure Handler:**
```typescript
const ingestionFailureHandler = new lambda.Function(this, 'IngestionFailureHandler', {
  functionName: `processapp-kb-ingestion-failure-${props.stage}`,
  runtime: lambda.Runtime.PYTHON_3_11,
  handler: 'index.handler',
  code: lambda.Code.fromAsset(
    path.join(__dirname as any, '../lambdas/ingestion-failure-handler')
  ),
  environment: {
    KNOWLEDGE_BASE_ID: this.knowledgeBaseId,
    DATA_SOURCE_ID: this.dataSourceId,
    OCR_LAMBDA_ARN: props.ocrProcessor.functionArn,
    DOCS_BUCKET: props.docsBucket.bucketName,
  },
  timeout: cdk.Duration.minutes(5),
  memorySize: 256,
});
```

3. **Grant permissions:**
```typescript
// Permission to get ingestion job details
ingestionFailureHandler.addToRolePolicy(
  new iam.PolicyStatement({
    actions: [
      'bedrock:GetIngestionJob',
      'bedrock:ListIngestionJobs',
    ],
    resources: [
      `arn:aws:bedrock:${region}:${props.accountId}:knowledge-base/${this.knowledgeBaseId}`,
    ],
  })
);

// Permission to invoke OCR Lambda
props.ocrProcessor.grantInvoke(ingestionFailureHandler);
```

4. **Create EventBridge Rule:**
```typescript
const ingestionEventRule = new events.Rule(this, 'IngestionEventRule', {
  ruleName: `processapp-kb-ingestion-${props.stage}`,
  description: 'Capture Bedrock KB ingestion job completions',
  eventPattern: {
    source: ['aws.bedrock'],
    detailType: ['Bedrock Knowledge Base Ingestion Job State Change'],
    detail: {
      knowledgeBaseId: [this.knowledgeBaseId],
      status: ['COMPLETE', 'FAILED'],
    },
  },
});

ingestionEventRule.addTarget(
  new targets.LambdaFunction(ingestionFailureHandler)
);
```

**Checklist:**
- [ ] Agregar `ocrProcessor` a `BedrockStackProps`
- [ ] Crear Lambda Ingestion Failure Handler
- [ ] Grant permissions (bedrock + lambda:InvokeFunction)
- [ ] Crear EventBridge Rule
- [ ] Add Lambda as target

#### ✅ Tarea 3.2: Actualizar app.ts

**Archivo:** `infrastructure/bin/app.ts`

**Cambios:**
```typescript
// Pass ocrProcessor from DocumentProcessingStack to BedrockStack
const bedrockStack = new BedrockStack(app, stackName, {
  // ... existing props
  ocrProcessor: documentProcessingStack.ocrProcessor,  // NEW
});
```

**Checklist:**
- [ ] Pasar `ocrProcessor` de `documentProcessingStack` a `bedrockStack`
- [ ] Verificar dependencias (DocumentProcessingStack debe crearse antes)

---

### Fase 4: Testing

#### ✅ Tarea 4.1: Test Local - Metadata Generation

**Script:** Test metadata_utils.py

```bash
cd infrastructure/lambdas/ocr-processor
python3 << 'EOF'
from metadata_utils import parse_s3_path, generate_metadata_json
import json

# Test project-level
print("Project-level:")
parsed = parse_s3_path("organizations/1/projects/949/doc.pdf")
print(f"  Parsed: {parsed}")
metadata = generate_metadata_json(**parsed)
print(f"  Metadata: {json.dumps(metadata, indent=2)}")

# Test task-level
print("\nTask-level:")
parsed = parse_s3_path("organizations/1/projects/949/tasks/5/doc.pdf")
metadata = generate_metadata_json(**parsed)
print(f"  Metadata: {json.dumps(metadata, indent=2)}")

# Test subtask-level
print("\nSubtask-level:")
parsed = parse_s3_path("organizations/1/projects/949/tasks/5/subtasks/10/doc.pdf")
metadata = generate_metadata_json(**parsed)
print(f"  Metadata: {json.dumps(metadata, indent=2)}")
EOF
```

**Expected Output:**
- ✅ partition_key correcto (`t1_p949`, `t1_p949_t5`, `t1_p949_t5_s10`)
- ✅ project_path correcto con jerarquía
- ✅ NO incluye partition_type

**Checklist:**
- [ ] Test project-level path parsing
- [ ] Test task-level path parsing
- [ ] Test subtask-level path parsing
- [ ] Verify partition_key format
- [ ] Verify project_path format
- [ ] Verify NO partition_type in output

#### ✅ Tarea 4.2: Deploy Infrastructure

```bash
cd infrastructure
npm run build  # Must pass with 0 errors

# Deploy stacks in order
npx cdk deploy dev-us-east-1-document-processing --profile ans-super
npx cdk deploy dev-us-east-1-bedrock --profile ans-super
```

**Checklist:**
- [ ] `npm run build` passes
- [ ] Deploy DocumentProcessingStack (contains OCR Lambda)
- [ ] Deploy BedrockStack (contains Failure Handler + EventBridge)
- [ ] Verify CloudFormation stacks created successfully

#### ✅ Tarea 4.3: Test End-to-End

**Scenario 1: Upload scanned image**

```bash
# 1. Upload scanned PDF (no text)
aws s3 cp test-scanned.pdf \
  s3://processapp-docs-v2-dev-708819485463/organizations/1/projects/999/ \
  --sse aws:kms \
  --sse-kms-key-id e6a714f6-70a7-47bf-a9ee-55d871d33cc6 \
  --profile ans-super

# 2. Trigger ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id BLJTRDGQI0 \
  --data-source-id B1OGNN9EMU \
  --profile ans-super

# 3. Monitor failure handler logs
aws logs tail /aws/lambda/processapp-kb-ingestion-failure-dev --follow --profile ans-super

# 4. Monitor OCR logs
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile ans-super

# 5. Verify .txt and .metadata.json created
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organizations/1/projects/999/

# 6. Verify metadata content
aws s3 cp s3://processapp-docs-v2-dev-708819485463/organizations/1/projects/999/test-scanned.txt.metadata.json - --profile ans-super | python3 -m json.tool
```

**Expected Results:**
- ✅ Ingestion job fails with "Failed to extract text"
- ✅ EventBridge triggers failure handler
- ✅ Failure handler invokes OCR Lambda
- ✅ OCR creates `.txt` file with extracted text
- ✅ OCR creates `.metadata.json` with correct format
- ✅ Next ingestion job succeeds

**Checklist:**
- [ ] Upload scanned document
- [ ] Trigger ingestion job
- [ ] Verify job fails (expected)
- [ ] Verify EventBridge event captured
- [ ] Verify failure handler executed
- [ ] Verify OCR Lambda invoked
- [ ] Verify `.txt` file created
- [ ] Verify `.metadata.json` created with correct format
- [ ] Verify metadata includes: tenant_id, partition_key, project_path
- [ ] Verify metadata EXCLUDES: partition_type
- [ ] Trigger second ingestion job
- [ ] Verify second job succeeds

---

## 📊 Success Criteria

### ✅ Metadata Format Validation

```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "project_id": "999",
    "partition_key": "t1_p999",
    "project_path": "organizations/1/projects/999"
  }
}
```

**Must have:**
- ✅ `tenant_id`
- ✅ `partition_key` (formato correcto)
- ✅ `project_id` (si existe en path)
- ✅ `project_path` (jerarquía correcta)
- ✅ `task_id` (si existe en path)
- ✅ `subtask_id` (si existe en path)

**Must NOT have:**
- ❌ `partition_type` (removido)

### ✅ Functional Validation

- [ ] OCR procesa solo archivos que fallaron (no todos)
- [ ] Metadata generada es idéntica al proceso de migración
- [ ] EventBridge captura eventos correctamente
- [ ] Failure handler identifica errores OCR-recuperables
- [ ] OCR Lambda se invoca automáticamente
- [ ] Archivos `.txt` y `.metadata.json` se crean correctamente
- [ ] Segundo ingestion job indexa documentos exitosamente

---

## 🚀 Deployment Order

1. ✅ Fase 1: Actualizar Lambda OCR (metadata_utils + index.py)
2. ✅ Fase 2: Crear Ingestion Failure Handler Lambda
3. ✅ Fase 3: Actualizar CDK (BedrockStack + app.ts)
4. ✅ Fase 4: Deploy infrastructure
5. ✅ Fase 5: Testing end-to-end

---

**Fecha creación:** 2026-05-05  
**Estado:** ✅ READY FOR IMPLEMENTATION  
**Próximo paso:** Ejecutar Fase 1 - Actualizar Lambda OCR
