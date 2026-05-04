# Test Case - Juan Daniel Pérez (Project 6636)

## 📋 Datos de Prueba Creados

### Ubicación en S3

```
s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/
├── juan-daniel-perez-perfil.txt
├── juan-daniel-perez-perfil.txt.metadata.json
├── juan-daniel-perez-experiencia.txt
└── juan-daniel-perez-experiencia.txt.metadata.json
```

### Metadata

```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "6636",
    "knowledge_type": "specific",
    "document_type": "profile/experience",
    "subject": "Juan Daniel Perez",
    "created_date": "2026-05-03"
  }
}
```

---

## 👤 Información de Juan Daniel Pérez

### Datos Personales
- **Nombre:** Juan Daniel Pérez
- **Profesión:** Ingeniero Civil
- **Fecha de Nacimiento:** 12 de diciembre de 1994
- **Edad:** 31 años

### Pasión Principal
- **Actividades de mar:** Surf, buceo, navegación, pesca deportiva

### Historial de Viajes
- **Bogotá:** 5 visitas (proyectos profesionales)
- **Medellín:** 3 visitas (proyectos de infraestructura)

### Especialización
- Diseño estructural
- Supervisión de obras
- Ingeniería hidráulica
- Infraestructura portuaria

---

## 🧪 Pruebas a Realizar

### Estado de Sincronización

Verificar que el Knowledge Base haya completado la ingesta:

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --max-results 1 \
  --profile ans-super
```

**Esperar hasta ver:** `"status": "COMPLETE"`

---

## ✅ Test 1: Pregunta con Filtro Correcto (DEBE RESPONDER)

### Setup
**Ruta Angular:** `/requirements/6636`  
**Metadata extraída:** `{tenant_id: "1001", project_id: "6636"}`

### Preguntas de Prueba

**Pregunta 1: Nombre y profesión**
```
Usuario: "¿Quién es Juan Daniel Pérez?"
Agente esperado: "Juan Daniel Pérez es un ingeniero civil nacido el 12 de diciembre de 1994..."
```

**Pregunta 2: Fecha de nacimiento**
```
Usuario: "¿Cuándo nació Juan Daniel Pérez?"
Agente esperado: "Juan Daniel Pérez nació el 12 de diciembre de 1994."
```

**Pregunta 3: Pasión/hobbies**
```
Usuario: "¿Qué le gusta hacer a Juan Daniel?"
Agente esperado: "A Juan Daniel le gustan las actividades de mar, como surf, buceo, navegación y pesca deportiva."
```

**Pregunta 4: Viajes a Bogotá**
```
Usuario: "¿Cuántas veces ha ido Juan Daniel a Bogotá?"
Agente esperado: "Juan Daniel ha visitado Bogotá 5 veces para reuniones con clientes y supervisión de proyectos."
```

**Pregunta 5: Viajes a Medellín**
```
Usuario: "¿Cuántas veces ha estado en Medellín?"
Agente esperado: "Juan Daniel ha estado en Medellín 3 veces para proyectos de infraestructura urbana."
```

**Pregunta 6: Resumen completo**
```
Usuario: "Dame un resumen de Juan Daniel Pérez"
Agente esperado: [Resumen con nombre, profesión, fecha de nacimiento, pasión por el mar, viajes a Bogotá (5) y Medellín (3)]
```

---

## ❌ Test 2: Pregunta con Filtro Incorrecto (NO DEBE RESPONDER)

### Setup
**Ruta Angular:** `/requirements/5001` (proyecto diferente)  
**Metadata extraída:** `{tenant_id: "1001", project_id: "5001"}`

### Preguntas de Prueba

**Pregunta 1:**
```
Usuario: "¿Quién es Juan Daniel Pérez?"
Agente esperado: "Lo siento, no tengo información disponible sobre eso."
```

**Pregunta 2:**
```
Usuario: "Háblame de Juan Daniel"
Agente esperado: "Lo siento, no tengo información disponible sobre Juan Daniel."
```

**Verificación Crítica:**
- ❌ NO debe mencionar "filtros", "metadata", "project_id=5001"
- ❌ NO debe decir "no cumple con los criterios de búsqueda"
- ✅ DEBE decir simplemente "no tengo información disponible"

---

## 🔍 Test 3: Sin Filtro (Dashboard)

### Setup
**Ruta Angular:** `/dashboard`  
**Metadata extraída:** `{}` (vacío)

### Comportamiento Esperado

**Pregunta:**
```
Usuario: "¿Quién es Juan Daniel Pérez?"
Agente esperado: [Puede o no responder, depende de la configuración sin filtros]
```

**Si no hay filtros activos:**
- El agente debería poder acceder a todos los documentos
- Debería encontrar información de Juan Daniel

---

## 📊 Verificación de Logs

### Logs del Servidor (CloudWatch)

```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --follow \
  --profile ans-super
```

**Buscar:**
```
[Agent] 📨 Incoming request
[Agent] 📝 Input: ¿Quién es Juan Daniel Pérez?
[Agent] 🎯 Metadata extracted: {'tenant_id': '1001', 'project_id': '6636'}
[Agent] 🔍 KB Filter active: {"andAll": [{"equals": {"key": "tenant_id", "value": "1001"}}, {"equals": {"key": "project_id", "value": "6636"}}]}
```

### Logs del Widget (Browser Console)

```
[Widget] 📨 Received INIT message from parent
[Widget] 🎯 Metadata received: {tenant_id: "1001", project_id: "6636"}
[Widget] 📤 Sending WebSocket message
[Widget] 📦 Payload: {"action":"sendMessage","data":{"inputText":"¿Quién es Juan Daniel Pérez?","sessionId":"...","tenant_id":"1001","project_id":"6636"}}
```

---

## 🎯 Criterios de Éxito

### ✅ Test EXITOSO si:

1. **Con filtro correcto (project_id=6636):**
   - ✅ Agente responde con información de Juan Daniel Pérez
   - ✅ Incluye datos correctos: nombre, profesión, fecha nacimiento, pasión por el mar
   - ✅ Menciona 5 viajes a Bogotá y 3 a Medellín
   - ✅ NO expone filtros internos ni metadata

2. **Con filtro incorrecto (project_id=5001):**
   - ✅ Agente dice "No tengo información disponible"
   - ✅ NO menciona filtros, metadata, tenant_id, project_id
   - ✅ Respuesta natural y profesional

3. **Logs del servidor:**
   - ✅ Muestran metadata extraída correctamente
   - ✅ Muestran filtro KB activo con valores correctos
   - ✅ Sin errores en CloudWatch

4. **Logs del widget:**
   - ✅ Muestran metadata recibida del Angular app
   - ✅ Muestran metadata incluida en WebSocket messages
   - ✅ Sin errores en browser console

---

## 🚨 Señales de Problema

### ❌ Test FALLIDO si:

1. **Agente expone detalles técnicos:**
   - "Estoy aplicando los filtros..."
   - "Con tenant_id=1001 y project_id=6636..."
   - "No se encontraron resultados que cumplan con esos criterios..."

2. **Filtros no funcionan:**
   - Con project_id=5001 puede acceder a datos de project_id=6636
   - Sin filtros no puede acceder a ningún documento
   - Metadata no se propaga correctamente

3. **Errores en logs:**
   - CloudWatch muestra errores de metadata extraction
   - Browser console muestra errores de WebSocket
   - Filtros KB no se aplican

---

## 🔧 Comandos Útiles

### Verificar archivos en S3
```bash
aws s3 ls s3://processapp-docs-v2-dev-708819485463/tenant/1001/project/6636/ --profile ans-super
```

### Ver estado de ingestion job
```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --max-results 1 \
  --profile ans-super
```

### Forzar nueva sincronización
```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id R80HXGRLHO \
  --data-source-id 6H96SSTEHT \
  --profile ans-super
```

### Ver logs del agente
```bash
aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev \
  --follow \
  --profile ans-super
```

### Test con wscat
```bash
wscat -c wss://mm40zmgsjd.execute-api.us-east-1.amazonaws.com/dev

# Enviar con metadata correcta
{"action":"sendMessage","data":{"inputText":"¿Quién es Juan Daniel Pérez?","sessionId":"test-juan","tenant_id":"1001","project_id":"6636"}}

# Enviar con metadata incorrecta (debe fallar)
{"action":"sendMessage","data":{"inputText":"¿Quién es Juan Daniel Pérez?","sessionId":"test-juan","tenant_id":"1001","project_id":"5001"}}
```

---

## 📝 Checklist de Pruebas

### Antes de Probar
- [ ] Knowledge Base completó sincronización (status: COMPLETE)
- [ ] Angular app corriendo (ng serve)
- [ ] Widget Next.js corriendo (npm run dev)
- [ ] CloudWatch logs abiertos en otra ventana

### Durante las Pruebas
- [ ] Navegar a `/requirements/6636`
- [ ] Verificar metadata en logs del widget
- [ ] Hacer preguntas sobre Juan Daniel
- [ ] Verificar respuestas del agente (correctas y sin exponer filtros)
- [ ] Navegar a `/requirements/5001` (proyecto diferente)
- [ ] Verificar que NO puede acceder a datos de Juan Daniel
- [ ] Verificar logs del servidor (metadata y filtros)

### Después de las Pruebas
- [ ] Documentar resultados
- [ ] Capturar screenshots si hay problemas
- [ ] Reportar comportamientos inesperados

---

## 🎉 Resultados Esperados

Si todo funciona correctamente:

1. ✅ El agente responde preguntas sobre Juan Daniel cuando `project_id=6636`
2. ✅ El agente NO puede acceder a datos de Juan Daniel cuando `project_id=5001`
3. ✅ Las respuestas son naturales sin exponer filtros internos
4. ✅ La metadata se propaga correctamente desde el frontend hasta el agente
5. ✅ Los logs muestran el filtrado funcionando correctamente

---

**Datos creados:** 2026-05-03  
**Ingestion Job ID:** DHTLOAFF59  
**Knowledge Base ID:** R80HXGRLHO  
**Data Source ID:** 6H96SSTEHT

**Tiempo estimado de prueba completa:** 10-15 minutos  
**Prerequisito:** Esperar que KB sync complete (~3-5 minutos)
