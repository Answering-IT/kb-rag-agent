# ProcessApp RAG - Claude Code Guide

Guía rápida para desarrollar con el agente RAG usando AWS Bedrock.

---

## 🎯 Configuración AWS

**SIEMPRE usar:**
- **Perfil:** `default`
- **Cuenta:** `708819485463`
- **Región:** `us-east-1`

```bash
# Verificar configuración
export AWS_PROFILE=default
aws sts get-caller-identity
```

---

## 🚀 Probar el Agente (Método Simple)

Usa el SDK de AWS directamente - **NO necesitas API key**:

```bash
python3 scripts/test-agent.py
```

Este script:
- ✅ Se conecta directamente al agente Bedrock
- ✅ No requiere permisos de API Gateway
- ✅ Usa tus credenciales AWS normales

**IDs del Agente:**
- Agent ID: `QWTVV3BY3G`
- Agent Alias ID: `QZITGFMONE`

---

## 📝 Ejemplo de Código Python

```python
import boto3
import uuid

# Cliente
session = boto3.Session(profile_name='default')
bedrock = session.client('bedrock-agent-runtime', region_name='us-east-1')

# Hacer pregunta
response = bedrock.invoke_agent(
    agentId='QWTVV3BY3G',
    agentAliasId='QZITGFMONE',
    sessionId=str(uuid.uuid4()),
    inputText='What documents do you have?'
)

# Procesar respuesta
answer = ""
for event in response['completion']:
    if 'chunk' in event:
        answer += event['chunk']['bytes'].decode('utf-8')

print(answer)
```

---

## 🏗️ Desplegar Infraestructura

```bash
cd infrastructure

# Compilar
npm install
npm run build

# Desplegar
npx cdk deploy --all --profile default --require-approval never

# Desplegar stack específico
npx cdk deploy dev-us-east-1-bedrock --profile default
```

---

## 📂 Subir Documentos

```bash
# Configuración
BUCKET="processapp-docs-v2-dev-708819485463"
KMS_KEY="e6a714f6-70a7-47bf-a9ee-55d871d33cc6"

# Subir documento
aws s3 cp documento.txt s3://${BUCKET}/documents/ \
  --sse aws:kms \
  --sse-kms-key-id ${KMS_KEY} \
  --profile default

# Sincronizar Knowledge Base
KB_ID=$(aws bedrock-agent list-knowledge-bases \
  --query 'knowledgeBaseSummaries[?contains(name, `processapp`)].knowledgeBaseId' \
  --output text --profile default)

DS_ID=$(aws bedrock-agent list-data-sources \
  --knowledge-base-id ${KB_ID} \
  --query 'dataSourceSummaries[0].dataSourceId' \
  --output text --profile default)

aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --profile default
```

---

## 📊 Ver Logs

```bash
# Logs del agente
aws logs filter-log-events \
  --log-group-name /aws/bedrock/agents/QWTVV3BY3G \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --profile default

# Logs de OCR
aws logs tail /aws/lambda/processapp-ocr-processor-dev --follow --profile default
```

---

## 🔧 Configuración Principal

**Archivo:** `infrastructure/config/environments.ts`

```typescript
// Cuenta
SDLCAccounts: [{ id: '708819485463', stage: 'dev', profile: 'default' }]

// Modelo del agente
AgentConfig.foundationModel: 'amazon.nova-pro-v1:0'

// Chunking
ProcessingConfig.chunking: {
  maxTokens: 512,
  overlapPercentage: 20,
}
```

---

## 📚 Estructura del Proyecto

```
kb-rag-agent/
├── infrastructure/           # CDK stacks (8 stacks)
│   ├── bin/app.ts           # Entry point
│   ├── lib/                 # Stack definitions
│   ├── lambdas/             # Lambda functions
│   └── config/              # Configuration
├── scripts/
│   └── test-agent.py        # Test script (USA ESTE)
└── docs/                    # Documentation
```

---

## 🎯 Recursos Desplegados

1. **PrereqsStack** - S3, KMS, IAM
2. **SecurityStack** - Políticas
3. **BedrockStack** - Knowledge Base
4. **DocumentProcessingStack** - OCR Lambda
5. **GuardrailsStack** - Filtros PII
6. **AgentStack** - Agente Bedrock
7. **APIStack** - API Gateway (opcional)
8. **MonitoringStack** - CloudWatch

---

## ⚡ Comandos Rápidos

```bash
# Probar agente
python3 scripts/test-agent.py

# Desplegar todo
cd infrastructure && npm run build && npx cdk deploy --all --profile default

# Ver estado del Knowledge Base
aws bedrock-agent get-knowledge-base --knowledge-base-id <KB_ID> --profile default

# Sincronizar documentos
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID> \
  --profile default
```

---

## 📖 Documentación Adicional

- **[README.md](README.md)** - Documentación técnica completa
- **[QUICK_START.md](QUICK_START.md)** - Inicio rápido
- **[docs/](docs/)** - Arquitectura y guías detalladas

---

**Última actualización:** 2026-04-21
**Cuenta:** 708819485463
**Perfil:** default
