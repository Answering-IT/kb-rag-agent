# Production Ready - Multi-tenant RAG Agent

## ✅ Estado: Listo para Producción

**Última actualización:** 2026-05-03  
**Versión:** 2.0  
**Stack:** Agent V2 (Agent Core Runtime + Strand SDK)

---

## 🎯 Características Implementadas

### 1. Multi-tenancy con Metadata Filtering
- ✅ Filtrado por `tenant_id` y `project_id`
- ✅ Soporte para `task_id` opcional
- ✅ Aislamiento de datos por tenant
- ✅ Metadata minimalista (< 100 bytes)

### 2. Restricciones de Seguridad
- ✅ Agente SOLO responde del Knowledge Base
- ✅ NO expone detalles técnicos internos
- ✅ NO menciona filtros, metadata, tenant_id
- ✅ Rechaza preguntas fuera del dominio empresarial

### 3. Frontend Integration
- ✅ Extracción automática de metadata desde rutas Angular
- ✅ Widget Next.js embebible vía iframe
- ✅ WebSocket streaming para respuestas en tiempo real
- ✅ Propagación de contexto (orgId, project_id, task_id)

---

## 📁 Estructura del Proyecto

```
kb-rag-agent/
├── agents/                          # Agent Backend (Python)
│   ├── main.py                      # Agent con Strand SDK
│   ├── metadata_handler.py          # Multi-tenant filtering
│   └── requirements.txt
├── infrastructure/                   # CDK (TypeScript)
│   ├── lib/
│   │   ├── AgentStackV2.ts          # Agent Core Runtime stack
│   │   ├── BedrockStack.ts          # Knowledge Base + S3 Vectors
│   │   └── WebSocketStackV2.ts      # WebSocket API
│   └── config/environments.ts       # Configuración
├── fe/                              # Widget Next.js
│   ├── app/widget/page.tsx          # Widget embebible
│   ├── hooks/useWebSocketChat.ts    # WebSocket client
│   └── components/chat.tsx          # UI del chat
└── docs/                            # Documentación
    ├── DEPLOYMENT_GUIDE.md
    ├── METADATA_FILTERING_SUCCESS.md
    └── WEBSOCKET_STREAMING_GUIDE.md
```

---

## 🚀 Quick Start

### Prerequisitos
- AWS CLI configurado con perfil `ans-super`
- Node.js 18+
- Python 3.11+
- Docker

### Deploy Infrastructure

```bash
cd infrastructure
npm install
npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

### Run Widget Locally

```bash
cd fe
npm install
npm run dev  # http://localhost:3000
```

---

## 📊 Arquitectura

### Flujo de Datos

```
Angular App (Colpensiones)
    ↓ [postMessage]
Widget Next.js (iframe)
    ↓ [WebSocket]
API Gateway WebSocket
    ↓ [Lambda]
Agent Core Runtime (ECS)
    ↓ [retrieve tool]
Bedrock Knowledge Base
    ↓ [metadata filter]
S3 Vectors (filtered results)
```

### Metadata Filtering

```
Route: /requirements/6636
    ↓
Extract: {tenant_id: "1001", project_id: "6636"}
    ↓
Filter KB: {"andAll": [
    {"equals": {"key": "tenant_id", "value": "1001"}},
    {"equals": {"key": "project_id", "value": "6636"}}
]}
    ↓
Return: ONLY documents matching filter
```

---

## 🔧 Configuración

### Metadata en S3

**Estructura de archivos:**
```
s3://bucket/tenant/1001/project/6636/
├── documento.txt
└── documento.txt.metadata.json
```

**Metadata minimalista (recomendada):**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636"
  }
}
```

**Límite:** Máximo 2048 bytes (incluye campos internos de Bedrock)

### Variables de Entorno

**Agent (agents/main.py):**
- `MODEL_ID`: amazon.nova-pro-v1:0
- `KB_ID`: ID del Knowledge Base
- `AWS_REGION`: us-east-1
- `DEBUG`: false (producción)

**Widget (fe/.env.local):**
- `NEXT_PUBLIC_WS_URL`: WebSocket endpoint
- `NEXT_PUBLIC_LANGUAGE`: es (default)

---

## 🧪 Testing

### Test Manual con wscat

```bash
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# Enviar mensaje con metadata
{"action":"sendMessage","data":{"inputText":"Hola","sessionId":"test-123","tenant_id":"1001","project_id":"6636"}}
```

### Test con Frontend

1. **Navegar a:** `http://localhost:4200/requirements/6636`
2. **Abrir chat** y preguntar sobre documentos del proyecto
3. **Verificar** que solo devuelve documentos del proyecto 6636
4. **Cambiar a:** `/requirements/5001`
5. **Verificar** que NO puede acceder a documentos de 6636

### Logs para Debugging

**CloudWatch (solo con DEBUG=true):**
```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --follow \
  --profile ans-super
```

---

## 📝 Best Practices

### 1. Metadata

✅ **DO:**
- Mantener metadata minimalista (solo IDs necesarios)
- Usar valores cortos (`tenant_id: "1001"`, no `tenant_id: "colpensiones-main-2024"`)
- Documentos pequeños (< 1KB idealmente)

❌ **DON'T:**
- Incluir descripciones largas en metadata
- Usar más de 5-6 campos
- Duplicar información del documento

### 2. System Prompt

✅ **DO:**
- Ser explícito sobre restricciones
- Dar ejemplos de respuestas correctas/incorrectas
- Prohibir mención de aspectos técnicos

❌ **DON'T:**
- Asumir que el modelo "entenderá" implícitamente
- Dejar espacio para interpretación
- Confiar en conocimiento general del modelo

### 3. Logs

✅ **DO:**
- Usar DEBUG=true solo en desarrollo
- Logs esenciales: errores y warnings
- Logs estructurados (JSON cuando sea posible)

❌ **DON'T:**
- Logs excesivos en producción
- Información sensible en logs
- Logs sin contexto

---

## 🔒 Security

### Multi-tenancy
- Filtrado a nivel de vector search (no post-processing)
- Metadata inmutable en S3
- Sin acceso cross-tenant

### Data Protection
- Encriptación en reposo (KMS)
- Encriptación en tránsito (TLS)
- IAM roles con least privilege

### Agent Restrictions
- SOLO responde del Knowledge Base
- NO expone implementación interna
- Rechaza preguntas fuera del dominio

---

## 📊 Monitoring

### Métricas Clave

**Agent Performance:**
- Response time (p50, p95, p99)
- Token usage
- Error rate

**Knowledge Base:**
- Query latency
- Cache hit rate
- Ingestion success rate

**WebSocket:**
- Connection success rate
- Message throughput
- Reconnection rate

### Alertas Recomendadas

- Error rate > 5%
- p95 latency > 3s
- Ingestion failures
- WebSocket disconnections > 10%

---

## 🚨 Troubleshooting

### Problema: Metadata ingestion falla

**Error:** `"Filterable metadata must have at most 2048 bytes"`

**Solución:**
1. Reducir campos de metadata (solo IDs esenciales)
2. Acortar valores de metadata
3. Dividir documentos largos en archivos más pequeños

**Ver:** `METADATA_LIMITS_EXPLAINED.md`

### Problema: Agente responde preguntas generales

**Síntoma:** Responde sobre clima, deportes, etc.

**Solución:**
1. Revisar system prompt
2. Verificar que incluya restricciones explícitas
3. Agregar ejemplos de respuestas correctas

**Ver:** `AGENT_RESPONSE_GUIDE.md`

### Problema: Filtros no funcionan

**Síntoma:** Usuario ve documentos de otros tenants/proyectos

**Solución:**
1. Verificar metadata en archivos S3
2. Verificar logs: metadata extraction y filter building
3. Confirmar que Knowledge Base sync completó

---

## 📚 Documentación Adicional

### Core Documentation
- **README.md** - Overview y getting started
- **CLAUDE.md** - Instrucciones para Claude Code
- **DEPLOYMENT_SUCCESS.md** - Último despliegue exitoso

### Detailed Guides
- **METADATA_LIMITS_EXPLAINED.md** - Límites y best practices
- **AGENT_RESPONSE_GUIDE.md** - Ejemplos de respuestas
- **TEST_JUAN_DANIEL_FINAL.md** - Test case de referencia

### Archives
- **docs/archive/** - Documentación histórica

---

## 🎯 Production Checklist

### Antes de Producción

- [ ] DEBUG=false en todas las variables de entorno
- [ ] Logs reducidos a esenciales (warnings y errors)
- [ ] Metadata validada en todos los documentos
- [ ] Knowledge Base completamente sincronizado
- [ ] Tests E2E pasando
- [ ] Monitoring y alertas configuradas
- [ ] IAM roles revisados (least privilege)
- [ ] Backup strategy definida
- [ ] Incident response plan documentado

### Post-Deployment

- [ ] Smoke tests ejecutados
- [ ] Logs monitoreados (primeras 24h)
- [ ] Métricas baseline establecidas
- [ ] Alertas funcionando
- [ ] Team notificado
- [ ] Documentation actualizada

---

## 🔗 Links Útiles

### AWS Resources
- **Agent Runtime:** processapp_agent_runtime_v2_dev-9b2dszEtqw
- **Knowledge Base:** R80HXGRLHO
- **S3 Bucket:** processapp-docs-v2-dev-708819485463
- **WebSocket URL:** wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

### Repositories
- **Infrastructure:** `/Users/qohatpretel/Answering/kb-rag-agent/infrastructure`
- **Agent:** `/Users/qohatpretel/Answering/kb-rag-agent/agents`
- **Widget:** `/Users/qohatpretel/Answering/kb-rag-agent/fe`
- **Frontend:** `/Users/qohatpretel/Answering/REP_FE_COLPENSIONES`

---

## 📞 Support

### Comandos de Emergencia

```bash
# Ver logs en tiempo real
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super

# Forzar re-sync del KB
aws bedrock-agent start-ingestion-job --knowledge-base-id R80HXGRLHO --data-source-id 6H96SSTEHT --profile ans-super

# Rollback deployment
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --force

# Ver estado del stack
aws cloudformation describe-stacks --stack-name dev-us-east-1-agent-v2 --profile ans-super
```

---

**Status:** ✅ Production Ready  
**Last Tested:** 2026-05-03  
**Maintainer:** Development Team
