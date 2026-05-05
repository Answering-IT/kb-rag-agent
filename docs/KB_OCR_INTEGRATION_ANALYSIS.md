# Integración Lambda OCR con Knowledge Base Ingestion Failures

## 🎯 Resumen Ejecutivo

### ✅ **SÍ ES POSIBLE** - Solución Reactiva Automática

AWS Bedrock Knowledge Base emite eventos a EventBridge que permiten capturar fallos de ingestion y reaccionar automáticamente.

### 📦 Componentes Requeridos

1. **Lambda: Ingestion Failure Handler** (NUEVO) - Captura eventos de KB y dispara OCR
2. **EventBridge Rule** (NUEVO) - Escucha eventos "Ingestion Job State Change"
3. **Lambda OCR: Actualización de metadata** (MODIFICAR) - Genera metadata en formato de migración

### 🔄 Cambio Crítico: Metadata Format

La Lambda OCR debe generar metadata **idéntica** al proceso de migración S3:

```json
{
  "metadataAttributes": {
    "tenant_id": "1",
    "project_id": "949",
    "task_id": "5",
    "partition_key": "t1_p949_t5",
    "project_path": "organizations/1/projects/949/tasks/5"
  }
}
```

**NO incluir:** `partition_type` (removido según requerimientos)

---

## 📋 Análisis de Factibilidad

### ✅ **SÍ ES POSIBLE** integrar la Lambda OCR con el proceso de sync del KB

AWS Bedrock Knowledge Base emite eventos a EventBridge que permiten capturar fallos de ingestion y reaccionar automáticamente.

---

## 🏗️ Arquitectura Propuesta

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FLUJO ACTUAL (sin manejo de errores)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  S3 Upload → KB Ingestion Job → ❌ FAIL (imagen sin texto)             │
│                                   └─> Error no manejado                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ FLUJO PROPUESTO (con auto-recuperación OCR)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. S3 Upload (imagen/PDF)                                             │
│      ↓                                                                  │
│  2. KB Ingestion Job                                                    │
│      ↓                                                                  │
│  3. ❌ FAIL (no text extractable)                                       │
│      ↓                                                                  │
│  4. EventBridge captura evento "Ingestion Job State Change"            │
│      ↓                                                                  │
│  5. Lambda "Ingestion Failure Handler"                                 │
│      ├─> Obtiene GetIngestionJob response                              │
│      ├─> Parsea failureReasons[]                                       │
│      ├─> Identifica archivos con error de extracción                   │
│      └─> Invoca Lambda OCR Processor                                   │
│           ↓                                                             │
│  6. Lambda OCR Processor                                                │
│      ├─> Ejecuta Textract                                              │
│      ├─> Guarda texto extraído (.txt)                                  │
│      └─> Guarda metadata (.metadata.json)                              │
│           ↓                                                             │
│  7. Trigger nuevo ingestion job (automático o manual)                  │
│      ↓                                                                  │
│  8. ✅ SUCCESS (documento indexado)                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Referencias de Documentación AWS

### 1. **Bedrock Knowledge Base Ingestion Events**

**Documentación:**
- https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ingest.html
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_StartIngestionJob.html

**Event Pattern:**
```json
{
  "source": ["aws.bedrock"],
  "detail-type": ["Bedrock Knowledge Base Ingestion Job State Change"],
  "detail": {
    "knowledgeBaseId": ["BLJTRDGQI0"],
    "status": ["COMPLETE", "FAILED"]
  }
}
```

**Evento emitido:**
```json
{
  "version": "0",
  "id": "uuid",
  "detail-type": "Bedrock Knowledge Base Ingestion Job State Change",
  "source": "aws.bedrock",
  "account": "708819485463",
  "time": "2026-05-05T20:00:00Z",
  "region": "us-east-1",
  "resources": [
    "arn:aws:bedrock:us-east-1:708819485463:knowledge-base/BLJTRDGQI0"
  ],
  "detail": {
    "knowledgeBaseId": "BLJTRDGQI0",
    "dataSourceId": "B1OGNN9EMU",
    "ingestionJobId": "XXXXXXXXXXXX",
    "status": "COMPLETE",
    "statistics": {
      "numberOfDocumentsScanned": 100,
      "numberOfDocumentsIndexed": 90,
      "numberOfDocumentsFailed": 10
    }
  }
}
```

### 2. **GetIngestionJob API - Failure Details**

**Documentación:**
- https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_GetIngestionJob.html

**API Response con failureReasons:**
```json
{
  "ingestionJob": {
    "ingestionJobId": "XXXX",
    "status": "COMPLETE",
    "statistics": {
      "numberOfDocumentsFailed": 10
    },
    "failureReasons": [
      "s3://bucket/organizations/1/projects/949/image.pdf: Failed to extract text from document"
    ]
  }
}
```

### 3. **EventBridge Rules**

**Documentación:**
- https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-rules.html
- https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-event-patterns.html

---

## 🔧 Implementación en CDK

### Componentes Necesarios

#### 1. **Lambda: Ingestion Failure Handler** (NUEVO)

**Propósito:** Captura eventos de ingestion, identifica documentos fallidos, e invoca OCR

**Handler:** `infrastructure/lambdas/ingestion-failure-handler/index.py`

```python
"""
Ingestion Failure Handler Lambda

Captura eventos de Bedrock KB ingestion jobs y procesa documentos fallidos con OCR.
"""

import json
import boto3
import re
from typing import List, Dict

bedrock_agent = boto3.client('bedrock-agent')
lambda_client = boto3.client('lambda')
s3 = boto3.client('s3')

KB_ID = os.environ['KNOWLEDGE_BASE_ID']
DATA_SOURCE_ID = os.environ['DATA_SOURCE_ID']
OCR_LAMBDA_ARN = os.environ['OCR_LAMBDA_ARN']
DOCS_BUCKET = os.environ['DOCS_BUCKET']


def handler(event, context):
    """
    Handle Bedrock KB ingestion job completion event.
    
    Event structure:
    {
      "detail": {
        "knowledgeBaseId": "BLJTRDGQI0",
        "dataSourceId": "B1OGNN9EMU",
        "ingestionJobId": "XXXX",
        "status": "COMPLETE",
        "statistics": {
          "numberOfDocumentsFailed": 10
        }
      }
    }
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract ingestion job details
    detail = event.get('detail', {})
    job_id = detail.get('ingestionJobId')
    status = detail.get('status')
    stats = detail.get('statistics', {})
    failed_count = stats.get('numberOfDocumentsFailed', 0)
    
    print(f"Ingestion job {job_id} status: {status}")
    print(f"Failed documents: {failed_count}")
    
    if failed_count == 0:
        print("No failed documents to process")
        return {'statusCode': 200, 'message': 'No failures'}
    
    # Get detailed failure reasons
    response = bedrock_agent.get_ingestion_job(
        knowledgeBaseId=KB_ID,
        dataSourceId=DATA_SOURCE_ID,
        ingestionJobId=job_id
    )
    
    failure_reasons = response.get('ingestionJob', {}).get('failureReasons', [])
    print(f"Failure reasons: {failure_reasons}")
    
    # Parse failure reasons to extract S3 paths
    failed_documents = parse_failure_reasons(failure_reasons)
    print(f"Parsed {len(failed_documents)} failed documents")
    
    # Process each failed document with OCR
    processed = 0
    for doc_info in failed_documents:
        s3_uri = doc_info['s3_uri']
        reason = doc_info['reason']
        
        # Check if failure is due to text extraction
        if is_ocr_recoverable(reason):
            print(f"Processing OCR for: {s3_uri}")
            
            # Invoke OCR Lambda
            invoke_ocr_lambda(s3_uri)
            processed += 1
        else:
            print(f"Skipping non-OCR failure: {s3_uri} - {reason}")
    
    return {
        'statusCode': 200,
        'processed': processed,
        'total_failures': failed_count
    }


def parse_failure_reasons(failure_reasons: List[str]) -> List[Dict]:
    """
    Parse failure reasons to extract S3 URIs and error details.
    
    Example input:
    [
      "s3://bucket/path/file.pdf: Failed to extract text from document",
      "s3://bucket/path/image.png: Document format not supported"
    ]
    """
    failed_docs = []
    
    for reason in failure_reasons:
        # Extract S3 URI (pattern: s3://bucket/path/file.ext)
        match = re.match(r'(s3://[^:]+):\s*(.+)', reason)
        if match:
            s3_uri = match.group(1)
            error_msg = match.group(2)
            
            failed_docs.append({
                's3_uri': s3_uri,
                'reason': error_msg
            })
    
    return failed_docs


def is_ocr_recoverable(error_message: str) -> bool:
    """
    Check if failure is recoverable with OCR.
    
    OCR-recoverable errors:
    - "Failed to extract text from document"
    - "No text content found"
    - "Document contains only images"
    """
    ocr_keywords = [
        'extract text',
        'no text',
        'text content',
        'only images',
        'scanned document'
    ]
    
    error_lower = error_message.lower()
    return any(keyword in error_lower for keyword in ocr_keywords)


def invoke_ocr_lambda(s3_uri: str):
    """
    Invoke OCR Lambda to process failed document.
    
    Payload:
    {
      "source": "ingestion-failure-handler",
      "s3_uri": "s3://bucket/path/file.pdf"
    }
    """
    # Parse S3 URI
    parts = s3_uri.replace('s3://', '').split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ''
    
    # Invoke OCR Lambda asynchronously
    payload = {
        'source': 'ingestion-failure-handler',
        'detail': {
            'bucket': {'name': bucket},
            'object': {'key': key}
        }
    }
    
    lambda_client.invoke(
        FunctionName=OCR_LAMBDA_ARN,
        InvocationType='Event',  # Asynchronous
        Payload=json.dumps(payload)
    )
    
    print(f"Invoked OCR Lambda for: {s3_uri}")
```

#### 2. **EventBridge Rule** (CDK)

**Archivo:** `infrastructure/lib/BedrockStack.ts`

```typescript
// ========================================
// INGESTION FAILURE HANDLER
// ========================================

// Lambda function to handle ingestion failures
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
    OCR_LAMBDA_ARN: props.ocrProcessor.functionArn,  // From DocumentProcessingStack
    DOCS_BUCKET: props.docsBucket.bucketName,
  },
  timeout: cdk.Duration.minutes(5),
  memorySize: 256,
});

// Grant permissions
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

// Grant permission to invoke OCR Lambda
props.ocrProcessor.grantInvoke(ingestionFailureHandler);

// EventBridge rule to capture ingestion job completions
const ingestionEventRule = new events.Rule(this, 'IngestionEventRule', {
  ruleName: `processapp-kb-ingestion-${props.stage}`,
  description: 'Capture Bedrock KB ingestion job completions and trigger OCR for failures',
  eventPattern: {
    source: ['aws.bedrock'],
    detailType: ['Bedrock Knowledge Base Ingestion Job State Change'],
    detail: {
      knowledgeBaseId: [this.knowledgeBaseId],
      status: ['COMPLETE', 'FAILED'],
    },
  },
});

// Add Lambda as target
ingestionEventRule.addTarget(
  new targets.LambdaFunction(ingestionFailureHandler)
);
```

#### 3. **Modificar OCR Lambda** (REQUERIDO)

**Archivo:** `infrastructure/lambdas/ocr-processor/index.py`

**Cambios necesarios:**

##### A) Agregar soporte para invocaciones desde Failure Handler

```python
def handler(event, context):
    """
    Main handler for OCR processing

    Handles three types of events:
    1. S3 EventBridge notification (document uploaded)
    2. SNS notification from Textract (job completed)
    3. Ingestion Failure Handler invocation (NEW)
    """
    print(f'Received event: {json.dumps(event)}')

    # Check event source
    if event.get('source') == 'ingestion-failure-handler':
        # Invoked by failure handler
        return handle_s3_upload(event, context)
    
    elif 'source' in event and event['source'] == 'aws.s3':
        # S3 upload event
        return handle_s3_upload(event, context)

    elif 'Records' in event and event['Records'][0].get('EventSource') == 'aws:sns':
        # SNS notification from Textract
        return handle_textract_completion(event, context)

    else:
        print(f'Unknown event type: {event}')
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Unknown event type'})
        }
```

##### B) Actualizar `save_processed_text_to_s3` con nueva lógica de metadata

**IMPORTANTE:** La metadata debe generarse igual que en el proceso de migración S3.

```python
def parse_s3_path(s3_key: str) -> Dict[str, Optional[str]]:
    """
    Parse S3 path to extract tenant, project, task, subtask IDs.
    
    Examples:
        organizations/1/projects/949/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: None, subtask_id: None}
        
        organizations/1/projects/949/tasks/5/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: "5", subtask_id: None}
        
        organizations/1/projects/949/tasks/5/subtasks/10/file.pdf
        -> {tenant_id: "1", project_id: "949", task_id: "5", subtask_id: "10"}
    """
    parts = s3_key.split('/')
    
    result = {
        "tenant_id": None,
        "project_id": None,
        "task_id": None,
        "subtask_id": None
    }
    
    try:
        # Find organizations index
        if "organizations" in parts:
            org_idx = parts.index("organizations")
            if len(parts) > org_idx + 1:
                result["tenant_id"] = parts[org_idx + 1]
        
        # Find projects index
        if "projects" in parts:
            projects_idx = parts.index("projects")
            if len(parts) > projects_idx + 1:
                result["project_id"] = parts[projects_idx + 1]
        
        # Find tasks index
        if "tasks" in parts:
            tasks_idx = parts.index("tasks")
            if len(parts) > tasks_idx + 1:
                result["task_id"] = parts[tasks_idx + 1]
        
        # Find subtasks index
        if "subtasks" in parts:
            subtasks_idx = parts.index("subtasks")
            if len(parts) > subtasks_idx + 1:
                result["subtask_id"] = parts[subtasks_idx + 1]
    
    except (ValueError, IndexError):
        pass
    
    return result


def generate_partition_key(
    tenant_id: str,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    subtask_id: Optional[str] = None
) -> str:
    """
    Generate partition_key from IDs.
    
    Format:
    - Tenant: t{tenant_id}
    - Project: t{tenant_id}_p{project_id}
    - Task: t{tenant_id}_p{project_id}_t{task_id}
    - Subtask: t{tenant_id}_p{project_id}_t{task_id}_s{subtask_id}
    """
    if not tenant_id:
        raise ValueError("tenant_id is required")
    
    key = f"t{tenant_id}"
    
    if project_id:
        key += f"_p{project_id}"
    
    if task_id:
        if not project_id:
            raise ValueError("project_id required when task_id is provided")
        key += f"_t{task_id}"
    
    if subtask_id:
        if not task_id:
            raise ValueError("task_id required when subtask_id is provided")
        key += f"_s{subtask_id}"
    
    return key


def generate_project_path(
    tenant_id: str,
    project_id: str,
    task_id: Optional[str] = None,
    subtask_id: Optional[str] = None
) -> str:
    """
    Generate project_path based on hierarchy level.
    
    Returns:
        - Project: "organizations/1/projects/949"
        - Task: "organizations/1/projects/949/tasks/5"
        - Subtask: "organizations/1/projects/949/tasks/5/subtasks/10"
    """
    path = f"organizations/{tenant_id}/projects/{project_id}"
    
    if task_id:
        path += f"/tasks/{task_id}"
    
    if subtask_id:
        path += f"/subtasks/{subtask_id}"
    
    return path


def save_processed_text_to_s3(original_key: str, text: str) -> str:
    """
    Save processed text to S3 for Bedrock KB to read.
    Creates companion metadata.json with proper format.
    
    Metadata format matches migration process:
    {
      "metadataAttributes": {
        "tenant_id": "1",
        "project_id": "949",
        "task_id": "5",           # Optional
        "subtask_id": "10",       # Optional
        "partition_key": "t1_p949_t5_s10",
        "project_path": "organizations/1/projects/949/tasks/5/subtasks/10"
      }
    }
    
    Args:
        original_key: Original S3 key (e.g., "organizations/1/projects/949/test.png")
        text: Extracted text to save
    
    Returns:
        S3 key where text was saved
    """
    # Parse S3 path to extract IDs
    parsed = parse_s3_path(original_key)
    tenant_id = parsed.get("tenant_id")
    project_id = parsed.get("project_id")
    task_id = parsed.get("task_id")
    subtask_id = parsed.get("subtask_id")
    
    print(f'Parsed path: tenant={tenant_id}, project={project_id}, task={task_id}, subtask={subtask_id}')
    
    # Generate output key (replace extension with .txt)
    filename = original_key.split('/')[-1]
    base_name = '.'.join(filename.split('.')[:-1])
    
    # Keep same directory structure, just change extension
    output_key = original_key.rsplit('.', 1)[0] + '.txt'
    
    try:
        # Save processed text
        put_params = {
            'Bucket': DOCS_BUCKET,
            'Key': output_key,
            'Body': text.encode('utf-8'),
            'ContentType': 'text/plain'
        }
        
        # Add KMS encryption if key is available
        if KMS_KEY_ID:
            put_params['ServerSideEncryption'] = 'aws:kms'
            put_params['SSEKMSKeyId'] = KMS_KEY_ID
        
        s3.put_object(**put_params)
        print(f'Saved processed text to: {output_key}')
        
        # Create companion metadata.json file
        if tenant_id:
            metadata_json_key = f'{output_key}.metadata.json'
            
            # Build metadata attributes
            metadata_attributes = {
                "tenant_id": tenant_id,
                "partition_key": generate_partition_key(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    task_id=task_id,
                    subtask_id=subtask_id
                )
            }
            
            # Add optional fields
            if project_id:
                metadata_attributes["project_id"] = project_id
                metadata_attributes["project_path"] = generate_project_path(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    task_id=task_id,
                    subtask_id=subtask_id
                )
            
            if task_id:
                metadata_attributes["task_id"] = task_id
            
            if subtask_id:
                metadata_attributes["subtask_id"] = subtask_id
            
            # Create metadata JSON
            metadata_json = {
                "metadataAttributes": metadata_attributes
            }
            
            metadata_put_params = {
                'Bucket': DOCS_BUCKET,
                'Key': metadata_json_key,
                'Body': json.dumps(metadata_json, indent=2).encode('utf-8'),
                'ContentType': 'application/json'
            }
            
            if KMS_KEY_ID:
                metadata_put_params['ServerSideEncryption'] = 'aws:kms'
                metadata_put_params['SSEKMSKeyId'] = KMS_KEY_ID
            
            s3.put_object(**metadata_put_params)
            print(f'Created metadata.json: {metadata_json_key}')
            print(f'Metadata: {metadata_json}')
        else:
            print(f'Warning: No tenant_id found in path, skipping metadata.json creation')
        
        return output_key
    
    except Exception as e:
        print(f'Error saving processed text to S3: {str(e)}')
        raise
```

---

## 🎯 Ventajas de esta Solución

1. ✅ **Automática:** No requiere intervención manual
2. ✅ **Reactiva:** Solo procesa documentos que realmente fallaron
3. ✅ **Eficiente:** Evita procesar OCR en archivos que ya tienen texto
4. ✅ **Escalable:** Maneja múltiples fallos en paralelo (Lambda concurrency)
5. ✅ **Observable:** EventBridge logs + CloudWatch metrics
6. ✅ **Cost-effective:** OCR solo cuando es necesario

---

## 🚀 Alternativas Consideradas

### Alternativa 1: Pre-procesamiento preventivo (NO RECOMENDADO)

**Flujo:**
```
S3 Upload → Siempre ejecutar OCR → Guardar .txt → KB Ingestion
```

**Desventajas:**
- ❌ Procesa OCR innecesariamente en archivos con texto
- ❌ Mayor costo (Textract)
- ❌ Mayor latencia
- ❌ Más complejo (detectar tipos de archivo)

### Alternativa 2: Retry manual (NO RECOMENDADO)

**Flujo:**
```
KB Ingestion → Fallos → Usuario revisa logs → Usuario ejecuta OCR manualmente
```

**Desventajas:**
- ❌ Requiere intervención manual
- ❌ Documentos quedan sin indexar hasta que alguien lo note
- ❌ No escalable

---

## 📊 Estimación de Costos

**Asumiendo 1000 documentos migrados:**

| Escenario | Costo Textract | Costo Lambda | Total |
|-----------|----------------|--------------|-------|
| Pre-procesamiento (1000 archivos) | ~$1.50/page × 1000 | $0.20 | ~$1500 |
| Reactivo (40 fallos) | ~$1.50/page × 40 | $0.01 | ~$60 |

**Ahorro:** ~$1440 (96%) usando el enfoque reactivo

---

## ✅ Recomendación Final

**Implementar la solución reactiva con EventBridge + Ingestion Failure Handler**

### Pasos de Implementación:

1. ✅ Crear Lambda `ingestion-failure-handler` (código arriba)
2. ✅ Actualizar `BedrockStack.ts` con EventBridge rule
3. ✅ Modificar `ocr-processor` para aceptar invocaciones del handler
4. ✅ Actualizar dependencias en CDK (pasar `ocrProcessor` a BedrockStack)
5. ✅ Deploy: `npx cdk deploy dev-us-east-1-bedrock --profile ans-super`
6. ✅ Test: Subir imagen escaneada y verificar auto-recuperación

### Testing:

```bash
# 1. Subir imagen sin texto
aws s3 cp test-scanned.pdf s3://processapp-docs-v2-dev-708819485463/organizations/1/projects/999/

# 2. Trigger ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id BLJTRDGQI0 \
  --data-source-id B1OGNN9EMU \
  --profile ans-super

# 3. Esperar evento → Verificar logs de failure-handler
aws logs tail /aws/lambda/processapp-kb-ingestion-failure-dev --follow --profile ans-super

# 4. Verificar que OCR se ejecutó
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile ans-super

# 5. Verificar .txt creado en S3
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organizations/1/projects/999/
```

---

**Fecha:** 2026-05-05  
**Autor:** Análisis técnico para integración KB + OCR  
**Estado:** ✅ FACTIBLE - Recomendado para implementación
