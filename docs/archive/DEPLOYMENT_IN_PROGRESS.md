# Deployment In Progress - Agent V2

## 🚀 Despliegue Iniciado

**Fecha:** 2026-05-03  
**Stack:** `dev-us-east-1-agent-v2`  
**Perfil AWS:** `ans-super`  
**Cuenta:** 708819485463  
**Región:** us-east-1

---

## 📦 Cambios Incluidos en Este Despliegue

### 1. System Prompt Actualizado (`agents/main.py`)

**Cambios principales:**

✅ **Restricciones más estrictas:**
- SOLO responde con información del Knowledge Base
- NO expone detalles técnicos (filtros, metadata, tenant_id, project_id)
- NO usa conocimiento general del modelo
- Respuestas naturales sin mencionar funcionamiento interno

✅ **Respuestas mejoradas:**
- Sin mencionar "filtros", "retrieveFilter", "metadata"
- Conversacional y profesional
- Rechaza preguntas fuera del dominio empresarial

✅ **Logs del servidor agregados:**
- `[Agent] 📨 Incoming request`
- `[Agent] 🎯 Metadata extracted`
- `[Agent] 🔍 KB Filter active`

### 2. Logs en Widget Next.js (`fe/`)

✅ **Logs de recepción INIT:**
- `[Widget] 📨 Received INIT message from parent`
- `[Widget] 🎯 Metadata received`

✅ **Logs de envío WebSocket:**
- `[Widget] 📤 Sending WebSocket message`
- `[Widget] 📦 Payload`
- `[Widget] 🎯 Metadata included`

### 3. Frontend Angular Limpieza (`REP_FE_COLPENSIONES`)

✅ **Metadata extraction mejorada:**
- Extrae `orgId`, `project_id`, `task_id` de rutas
- Patrones: `/requirements/:project_id` y `/requirements/:project_id/:task_id`

✅ **Logs eliminados:**
- Todos los logs detallados del Angular app (más limpio)
- Logs solo en el widget Next.js (servidor)

### 4. Fix WebSocket Error

✅ **Error TypeScript corregido:**
- `ws.onerror` ahora usa `(event: Event)` correctamente
- Build pasa sin errores

---

## 📋 Componentes Desplegándose

### Docker Image (Agent Container)
```
agents/
├── main.py               ← System prompt actualizado + logs
├── metadata_handler.py   ← Sin cambios
├── requirements.txt      ← Sin cambios
└── Dockerfile            ← Sin cambios
```

**Proceso:**
1. CDK construye imagen Docker
2. Sube a ECR (Elastic Container Registry)
3. Actualiza Task Definition de ECS
4. Crea nueva revisión del servicio
5. ECS despliega nuevos contenedores
6. Health checks verifican que esté funcionando
7. Termina contenedores viejos

**Tiempo estimado:** 5-10 minutos

### Lambda WebSocket Handler
- Sin cambios en este despliegue
- Ya soporta metadata extraction

### Bedrock Agent Core Runtime
- Actualización de variables de entorno
- Nueva imagen Docker del agente

---

## 🔍 Monitoreo del Despliegue

### Verificar Progreso

```bash
# Ver output del despliegue (en background)
tail -f /private/tmp/claude-501/-Users-qohatpretel-Answering-kb-rag-agent-fe/8589f3ff-ef5d-435d-88b6-a3735f07b5a6/tasks/b7oxul1ub.output

# Ver estado del stack
aws cloudformation describe-stacks \
  --stack-name dev-us-east-1-agent-v2 \
  --query 'Stacks[0].StackStatus' \
  --profile ans-super

# Ver eventos del stack
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-agent-v2 \
  --max-items 10 \
  --profile ans-super
```

### Verificar ECS Service

```bash
# Ver tareas en ejecución
aws ecs list-tasks \
  --cluster processapp-agent-cluster-v2-dev \
  --service-name processapp-agent-service-v2-dev \
  --profile ans-super

# Ver logs del contenedor
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --follow \
  --profile ans-super
```

---

## ✅ Verificación Post-Despliegue

### 1. Health Check
```bash
# Verificar que el agente responda
curl -X POST https://<runtime-url>/ping
# Debe devolver: {"status": "healthy", ...}
```

### 2. Test WebSocket
```bash
# Usar wscat para probar
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# Enviar mensaje
{"action":"sendMessage","data":{"inputText":"Hola","sessionId":"test-deploy"}}
```

### 3. Verificar Logs del Servidor

**Buscar estos logs nuevos:**
```
[Agent] 📨 Incoming request
[Agent] 📝 Input: Hola...
[Agent] 🔑 Session: test-deploy
[Agent] 🎯 Metadata extracted: {...}
[Agent] 🔍 KB Filter active: {...}
```

### 4. Probar Restricciones del Agente

**Test A: Pregunta del KB (debe responder)**
```
Usuario: "¿Qué información tienes?"
Agente: [Responde con información del KB o dice "No tengo información disponible"]
```

**Test B: Pregunta general (debe rechazar)**
```
Usuario: "¿Cómo está el clima?"
Agente: "Lo siento, solo puedo ayudarte con información de nuestra base de conocimiento empresarial."
```

**Test C: Verificar que NO exponga filtros**
```
Usuario: "¿Por qué no encuentras nada?"
Agente: "Lo siento, no tengo información disponible sobre eso."
[NO DEBE MENCIONAR: filtros, metadata, tenant_id, project_id, retrieveFilter]
```

---

## 🚨 Errores Comunes y Soluciones

### Error 1: ECS Task No Inicia

**Síntoma:** Task se queda en PROVISIONING o falla
```bash
aws ecs describe-tasks \
  --cluster processapp-agent-cluster-v2-dev \
  --tasks <task-arn> \
  --profile ans-super
```

**Solución:**
- Revisar logs de CloudWatch
- Verificar que la imagen Docker se construyó correctamente
- Confirmar permisos de IAM

### Error 2: Health Check Falla

**Síntoma:** Service no pasa healthy
```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --profile ans-super
```

**Solución:**
- Revisar si el agente está iniciando correctamente
- Verificar variables de entorno (KB_ID, MODEL_ID)
- Confirmar que el puerto 8080 está disponible

### Error 3: Rollback Automático

**Síntoma:** CloudFormation hace rollback
```bash
aws cloudformation describe-stack-events \
  --stack-name dev-us-east-1-agent-v2 \
  --profile ans-super \
  | grep "ROLLBACK"
```

**Solución:**
- Revisar eventos del stack para ver qué falló
- Verificar que el código compile sin errores
- Confirmar permisos y recursos disponibles

---

## 📊 Estado Esperado

### Durante el Despliegue (5-10 minutos)

```
✓ Compilación TypeScript
✓ Síntesis CloudFormation
✓ Construcción imagen Docker
✓ Push a ECR
↻ UPDATE_IN_PROGRESS - AgentServiceV2
↻ UPDATE_IN_PROGRESS - TaskDefinitionV2
↻ WAIT - ECS Health Checks (puede tardar 3-5 min)
✓ UPDATE_COMPLETE
```

### Después del Despliegue (Success)

```
Stack Status: UPDATE_COMPLETE
Service Status: ACTIVE
Tasks Running: 1 (RUNNING)
Health Status: HEALTHY
```

---

## 🎯 Siguiente Paso Después del Despliegue

1. **Esperar confirmación** (recibirás notificación cuando termine)
2. **Verificar logs** del nuevo contenedor
3. **Probar con wscat** o desde el frontend
4. **Validar restricciones** del agente (no exponer filtros)
5. **Monitorear respuestas** naturales sin mencionar metadata

---

## 📝 Cambios Resumidos

| Componente | Cambio | Impacto |
|------------|--------|---------|
| `agents/main.py` | System prompt actualizado + logs | ✅ Crítico - Restricciones y naturalidad |
| `fe/hooks/useWebSocketChat.ts` | Logs agregados + fix error | ✅ Debugging mejorado |
| `fe/app/widget/page.tsx` | Logs agregados | ✅ Debugging mejorado |
| `REP_FE_COLPENSIONES` | Metadata extraction + cleanup | ✅ Mejor extracción de contexto |

---

## 🔗 Recursos

- **CloudFormation:** https://console.aws.amazon.com/cloudformation
- **ECS Cluster:** https://console.aws.amazon.com/ecs/v2/clusters/processapp-agent-cluster-v2-dev
- **CloudWatch Logs:** https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fbedrock$252Fagentcore$252Fruntime$252Fprocessapp_agent_runtime_v2_dev

---

**Despliegue iniciado:** 2026-05-03  
**Estado actual:** 🔄 IN_PROGRESS  
**Archivo de seguimiento:** Este documento se actualizará cuando el despliegue termine
