# ✅ Test Case Final - Juan Daniel Pérez (Project 6636)

## 🎉 Datos Listos para Pruebas

### 📦 Archivo en S3

```
s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/
├── juan-daniel-perez-datos.txt (235 bytes)
└── juan-daniel-perez-datos.txt.metadata.json
```

### 📄 Contenido del Documento

```
Juan Daniel Pérez es un ingeniero civil nacido el 12 de diciembre de 1994. 
Tiene 31 años.

Le gustan las actividades de mar: surf, buceo, navegación y pesca deportiva.

Ha viajado 5 veces a Bogotá y 3 veces a Medellín por trabajo.
```

### 🏷️ Metadata

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636"
  }
}
```

---

## ✅ Sincronización Completada

**Status:** ✅ COMPLETE  
**Ingestion Job ID:** SXEPZY6LLV  
**Documentos indexados:** 1 nuevo  
**Documentos fallidos:** 0  
**Tiempo:** 4 segundos

```json
{
  "status": "COMPLETE",
  "statistics": {
    "numberOfDocumentsScanned": 14,
    "numberOfMetadataDocumentsScanned": 14,
    "numberOfNewDocumentsIndexed": 1,
    "numberOfDocumentsFailed": 0
  }
}
```

---

## 🧪 Pruebas a Realizar

### ✅ Test 1: Con Filtro Correcto (DEBE RESPONDER)

**Navegación:**
```
http://localhost:4200/requirements/6636
```

**Metadata esperada:**
```json
{
  "tenant_id": "1001",
  "project_id": "6636"
}
```

**Preguntas de prueba:**

**1. Pregunta básica:**
```
Usuario: "¿Quién es Juan Daniel Pérez?"
Agente esperado: "Juan Daniel Pérez es un ingeniero civil nacido el 12 de diciembre de 1994."
```

**2. Edad:**
```
Usuario: "¿Cuántos años tiene Juan Daniel?"
Agente esperado: "Juan Daniel tiene 31 años."
```

**3. Pasatiempos:**
```
Usuario: "¿Qué le gusta hacer a Juan Daniel?"
Agente esperado: "Le gustan las actividades de mar: surf, buceo, navegación y pesca deportiva."
```

**4. Viajes a Bogotá:**
```
Usuario: "¿Cuántas veces ha ido Juan Daniel a Bogotá?"
Agente esperado: "Ha viajado 5 veces a Bogotá por trabajo."
```

**5. Viajes a Medellín:**
```
Usuario: "¿Cuántas veces ha estado en Medellín?"
Agente esperado: "Ha estado 3 veces en Medellín por trabajo."
```

**6. Fecha de nacimiento:**
```
Usuario: "¿Cuándo nació Juan Daniel Pérez?"
Agente esperado: "Nació el 12 de diciembre de 1994."
```

---

### ❌ Test 2: Con Filtro Incorrecto (NO DEBE RESPONDER)

**Navegación:**
```
http://localhost:4200/requirements/5001
```

**Metadata esperada:**
```json
{
  "tenant_id": "1001",
  "project_id": "5001"  ← Proyecto diferente
}
```

**Preguntas de prueba:**

```
Usuario: "¿Quién es Juan Daniel Pérez?"
Agente esperado: "Lo siento, no tengo información disponible sobre eso."
```

**Verificación CRÍTICA:**
- ❌ NO debe mencionar "filtros", "metadata", "project_id"
- ❌ NO debe decir "no cumple con los criterios"
- ✅ DEBE decir simplemente "no tengo información disponible"

---

### 🔍 Test 3: Con wscat (Manual)

**Test con filtro correcto:**
```bash
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# Enviar:
{"action":"sendMessage","data":{"inputText":"¿Quién es Juan Daniel Pérez?","sessionId":"test-juan","tenant_id":"1001","project_id":"6636"}}
```

**Test con filtro incorrecto:**
```bash
# Cambiar project_id a 5001
{"action":"sendMessage","data":{"inputText":"¿Quién es Juan Daniel Pérez?","sessionId":"test-juan","tenant_id":"1001","project_id":"5001"}}

# Debe responder: "Lo siento, no tengo información disponible"
```

---

## 📊 Logs Esperados

### Logs del Servidor (CloudWatch)

```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --follow \
  --profile ans-super
```

**Logs esperados cuando project_id=6636:**
```
[Agent] 📨 Incoming request
[Agent] 📝 Input: ¿Quién es Juan Daniel Pérez?
[Agent] 🎯 Metadata extracted: {'tenant_id': '1001', 'project_id': '6636'}
[Agent] 🔍 KB Filter active: {"andAll": [{"equals": {"key": "tenant_id", "value": "1001"}}, {"equals": {"key": "project_id", "value": "6636"}}]}
```

**Logs esperados cuando project_id=5001:**
```
[Agent] 📨 Incoming request
[Agent] 📝 Input: ¿Quién es Juan Daniel Pérez?
[Agent] 🎯 Metadata extracted: {'tenant_id': '1001', 'project_id': '5001'}
[Agent] 🔍 KB Filter active: {"andAll": [{"equals": {"key": "tenant_id", "value": "1001"}}, {"equals": {"key": "project_id", "value": "5001"}}]}
```

### Logs del Widget (Browser Console)

```
[Widget] 📨 Received INIT message from parent
[Widget] 🎯 Metadata received: {tenant_id: "1001", project_id: "6636"}
[Widget] 📤 Sending WebSocket message
[Widget] 📦 Payload: {"action":"sendMessage","data":{...,"tenant_id":"1001","project_id":"6636"}}
```

---

## ✅ Criterios de Éxito

### Test EXITOSO si:

1. **Con project_id=6636:**
   - ✅ Agente responde con información de Juan Daniel Pérez
   - ✅ Menciona: ingeniero civil, 12 de diciembre de 1994, 31 años
   - ✅ Menciona: actividades de mar (surf, buceo, navegación, pesca)
   - ✅ Menciona: 5 viajes a Bogotá, 3 viajes a Medellín
   - ✅ NO expone filtros internos

2. **Con project_id=5001:**
   - ✅ Agente dice "No tengo información disponible"
   - ✅ NO menciona filtros, metadata, tenant_id, project_id
   - ✅ Respuesta natural y profesional

3. **Logs:**
   - ✅ Metadata se propaga correctamente
   - ✅ Filtros KB se aplican
   - ✅ Sin errores

---

## 🐛 Solución del Error de Metadata

### Problema Original

Los documentos largos (1.6KB y 2.8KB) causaban error:
```
"Filterable metadata must have at most 2048 bytes"
```

### Causa

Cuando Bedrock chunking divide documentos largos, la metadata se replica en cada chunk. Si el documento es muy largo y genera muchos chunks, la metadata acumulada puede exceder el límite.

### Solución Aplicada

1. ✅ Documentos más pequeños (235 bytes)
2. ✅ Metadata minimalista (solo tenant_id y project_id)
3. ✅ Información concisa pero completa

### Lección Aprendida

Para AWS Bedrock Knowledge Base con S3 Vectors:
- Mantener documentos pequeños (~500 bytes o menos)
- Metadata simple (2-3 campos)
- Si necesitas documentos largos, considera pre-chunking manual

---

## 📝 Comandos Útiles

### Verificar archivo en S3
```bash
aws s3 ls s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/ \
  --profile ans-super
```

### Ver contenido del documento
```bash
aws s3 cp s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/juan-daniel-perez-datos.txt - \
  --profile ans-super
```

### Ver metadata
```bash
aws s3 cp s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/juan-daniel-perez-datos.txt.metadata.json - \
  --profile ans-super
```

### Forzar re-sincronización
```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --profile ans-super
```

---

## 🎯 Resumen

**Datos de Juan Daniel Pérez:**
- ✅ Nombre: Juan Daniel Pérez
- ✅ Profesión: Ingeniero Civil
- ✅ Fecha de nacimiento: 12 de diciembre de 1994
- ✅ Edad: 31 años
- ✅ Pasión: Actividades de mar
- ✅ Viajes: 5 a Bogotá, 3 a Medellín

**Ubicación:**
- ✅ tenant_id: 1001
- ✅ project_id: 6636

**Estado:**
- ✅ Documento subido a S3
- ✅ Metadata configurada
- ✅ Knowledge Base sincronizado
- ✅ Listo para probar

---

**Creado:** 2026-05-03  
**Ingestion Job:** SXEPZY6LLV (COMPLETE)  
**Documentos indexados:** 1  
**Documentos fallidos:** 0  
**Tiempo de sync:** 4 segundos

¡Todo listo para probar! 🚀
