# Summary of Changes - 2026-05-03

## 🎯 Objetivos Completados

1. ✅ Pasar `orgId` del frontend Angular al widget
2. ✅ Extraer `project_id` y `task_id` de rutas `/requirements/$project_id` y `/requirements/$project_id/$task_id`
3. ✅ Eliminar logs excesivos del frontend Angular (Colpensiones)
4. ✅ Agregar logs en el widget Next.js (para ver propagación en el servidor)
5. ✅ Restringir el agente para que SOLO responda preguntas del Knowledge Base (no alucinar ni responder temas generales)

---

## 📝 Cambios Realizados

### 1. Frontend Angular - Colpensiones (`REP_FE_COLPENSIONES`)

#### `src/app/shared/components/fury-chat-widget/fury-chat-widget.component.ts`

**Cambios:**
- ✅ Agregado `@Input() orgId?: string` para recibir organization ID
- ✅ Eliminados todos los logs detallados (console.log con emojis)
- ✅ Actualizado `updateContextFromRoute()` para extraer:
  - `project_id` de `/requirements/:project_id`
  - `task_id` de `/requirements/:project_id/:task_id` (si existe)
  - Usar `orgId` como `tenant_id` (fallback a '1001')
- ✅ Limpieza automática de `task_id` cuando no está en la ruta

**Extracción de metadata:**
```typescript
// Ruta: /requirements/5001
{ tenant_id: orgId || '1001', project_id: '5001' }

// Ruta: /requirements/5001/3002
{ tenant_id: orgId || '1001', project_id: '5001', task_id: '3002' }

// Ruta: /dashboard
{} (vacío)
```

#### `src/app/app.component.ts`

**Cambios:**
- ✅ Eliminados logs del método `toggleAIChatWidget()`
- ✅ Mantenido `orgId` como propiedad pública (extraído de route params)

#### `src/app/app.component.html`

**Cambios:**
- ✅ Agregado `[orgId]="orgId"` al componente `fury-chat-widget`

---

### 2. Widget Next.js (`kb-rag-agent/fe`)

#### `hooks/useWebSocketChat.ts`

**Cambios:**
- ✅ Agregados logs detallados en `sendMessage()`:
  ```typescript
  console.log('[Widget] 📤 Sending WebSocket message');
  console.log('[Widget] 📦 Payload:', JSON.stringify(payload, null, 2));
  console.log('[Widget] 🎯 Metadata included:', {
    tenant_id: metadata?.tenant_id,
    project_id: metadata?.project_id,
    task_id: metadata?.task_id,
    user_id: metadata?.user_id
  });
  ```

**Logs visibles:**
- Cada vez que el usuario envía un mensaje
- Payload completo con estructura
- Metadata específica (tenant_id, project_id, task_id)

#### `app/widget/page.tsx`

**Cambios:**
- ✅ Agregados logs al recibir mensaje INIT:
  ```typescript
  console.log('[Widget] 📨 Received INIT message from parent');
  console.log('[Widget] 📦 Full INIT data:', JSON.stringify(event.data.data, null, 2));
  console.log('[Widget] 🎯 Metadata received:', {
    tenant_id: initData.metadata?.tenant_id,
    project_id: initData.metadata?.project_id,
    task_id: initData.metadata?.task_id,
    user_id: initData.metadata?.user_id,
    user_roles: initData.metadata?.user_roles
  });
  ```

**Logs visibles:**
- Cuando el widget recibe configuración inicial del Angular app
- Metadata completa recibida
- Campos específicos para validación

---

### 3. Agent Backend (`kb-rag-agent/agents`)

#### `agents/main.py`

**Cambios principales:**

**1. System Prompt Restringido (CRÍTICO):**
```python
system_prompt="""Eres un asistente especializado en responder ÚNICAMENTE preguntas basadas en la base de conocimiento empresarial.

**RESTRICCIÓN CRÍTICA:**
- SOLO puedes responder preguntas cuya información esté disponible en la base de conocimiento (Knowledge Base)
- NO puedes responder preguntas sobre temas generales (clima, noticias, deportes, entretenimiento, etc.)
- NO puedes inventar o "alucinar" información que no esté en los documentos
- Si la pregunta NO puede ser respondida con la información del Knowledge Base, debes responder: "Lo siento, no tengo información sobre eso en la base de conocimiento."

**Proceso obligatorio:**
1. El usuario hace una pregunta
2. Usas `retrieve` para buscar en el Knowledge Base
3. Si hay resultados: Respondes basándose ÚNICAMENTE en esos documentos
4. Si NO hay resultados: Respondes "No tengo información sobre eso en la base de conocimiento"
5. NUNCA uses tu conocimiento general del modelo

**Ejemplos de respuestas correctas:**
- Usuario: "¿Qué políticas de vacaciones tenemos?" → Usas `retrieve` y respondes con la información encontrada
- Usuario: "¿Cómo está el clima?" → "Lo siento, no tengo información sobre eso en la base de conocimiento."
- Usuario: "¿Quién ganó el partido?" → "Lo siento, no tengo información sobre eso en la base de conocimiento."
"""
```

**2. Logs de Servidor (para debugging):**
```python
print(f'[Agent] 📨 Incoming request')
print(f'[Agent] 📝 Input: {input_text[:80]}...')
print(f'[Agent] 🔑 Session: {session_id}')

print(f'[Agent] 🎯 Metadata extracted:', {
    'tenant_id': metadata.get('tenant_id'),
    'project_id': metadata.get('project_id'),
    'task_id': metadata.get('task_id'),
    'user_id': metadata.get('user_id'),
    'user_roles': metadata.get('user_roles')
})

if kb_filter:
    print(f'[Agent] 🔍 KB Filter active:', json.dumps(kb_filter, indent=2))
else:
    print(f'[Agent] ℹ️ No KB filter (accessing all documents)')
```

**Logs visibles en CloudWatch:**
- Cada request que llega al agente
- Metadata extraída (tenant_id, project_id, task_id)
- Filtro KB activo (si aplica)

---

## 🔄 Flujo Completo de Metadata

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Usuario navega: /requirements/5001/3002                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. fury-chat-widget.component.ts → updateContextFromRoute() │
│    Extrae: { tenant_id: orgId, project_id: '5001',          │
│              task_id: '3002' }                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Usuario abre chat → sendInitMessage()                    │
│    Envía metadata via postMessage al iframe                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Widget Next.js recibe INIT                               │
│    LOG: [Widget] 📨 Received INIT message from parent       │
│    LOG: [Widget] 🎯 Metadata received: {...}                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Usuario escribe mensaje en el chat                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. useWebSocketChat.sendMessage()                           │
│    LOG: [Widget] 📤 Sending WebSocket message               │
│    LOG: [Widget] 🎯 Metadata included: {...}                │
│    Envía via WebSocket: {action, data: {inputText, ...}}    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Lambda websocket-handler-v2 recibe mensaje               │
│    Extrae metadata y la pasa al Agent Runtime               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. agents/main.py → /invocations                            │
│    LOG: [Agent] 📨 Incoming request                         │
│    LOG: [Agent] 🎯 Metadata extracted: {...}                │
│    LOG: [Agent] 🔍 KB Filter active: {...}                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. Agent usa retrieve tool con retrieveFilter               │
│    Bedrock KB filtra por tenant_id, project_id, task_id     │
│    SOLO devuelve documentos que coincidan                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. Agent responde SOLO con información del KB              │
│     Si no hay resultados: "No tengo información sobre eso"  │
│     NO usa conocimiento general del modelo                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Cómo Probar

### 1. Iniciar Servicios

```bash
# Angular app (Colpensiones)
cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
ng serve

# Widget Next.js
cd /Users/qohatpretel/Answering/kb-rag-agent/fe
npm run dev
```

### 2. Navegación de Prueba

**Test 1: Con project_id solamente**
```
URL: http://localhost:4200/requirements/5001
Metadata esperada: { tenant_id: orgId, project_id: '5001' }
```

**Test 2: Con project_id y task_id**
```
URL: http://localhost:4200/requirements/5001/3002
Metadata esperada: { tenant_id: orgId, project_id: '5001', task_id: '3002' }
```

**Test 3: Sin contexto**
```
URL: http://localhost:4200/dashboard
Metadata esperada: {} (vacío)
```

### 3. Verificar Logs

**A. Frontend (Browser DevTools Console):**
```
[Widget] 📨 Received INIT message from parent
[Widget] 🎯 Metadata received: {tenant_id: "1001", project_id: "5001", task_id: "3002"}
[Widget] 📤 Sending WebSocket message
[Widget] 📦 Payload: {...}
```

**B. Backend (Terminal del servidor Next.js o CloudWatch):**
```
[Agent] 📨 Incoming request
[Agent] 🎯 Metadata extracted: {'tenant_id': '1001', 'project_id': '5001', 'task_id': '3002'}
[Agent] 🔍 KB Filter active: {"andAll": [...]}
```

### 4. Probar Restricciones del Agente

**Test A: Pregunta del Knowledge Base (DEBE RESPONDER)**
```
Usuario: "¿Qué documentos tenemos en el proyecto?"
Agente: [Usa retrieve, devuelve información del KB]
```

**Test B: Pregunta general fuera del KB (NO DEBE RESPONDER)**
```
Usuario: "¿Cómo está el clima hoy?"
Agente: "Lo siento, no tengo información sobre eso en la base de conocimiento."
```

**Test C: Pregunta sobre deportes (NO DEBE RESPONDER)**
```
Usuario: "¿Quién ganó el partido de ayer?"
Agente: "Lo siento, no tengo información sobre eso en la base de conocimiento."
```

---

## 📊 Resumen de Logs

### Logs Eliminados (Angular)
- ❌ Todos los logs con emojis en `fury-chat-widget.component.ts`
- ❌ Logs de navegación detallados
- ❌ Logs de construcción de metadata
- ❌ Logs en `app.component.ts`

### Logs Agregados (Widget Next.js)
- ✅ `[Widget] 📨 Received INIT message` (app/widget/page.tsx)
- ✅ `[Widget] 🎯 Metadata received` (app/widget/page.tsx)
- ✅ `[Widget] 📤 Sending WebSocket message` (hooks/useWebSocketChat.ts)
- ✅ `[Widget] 📦 Payload` (hooks/useWebSocketChat.ts)
- ✅ `[Widget] 🎯 Metadata included` (hooks/useWebSocketChat.ts)

### Logs Agregados (Agent Backend)
- ✅ `[Agent] 📨 Incoming request` (agents/main.py)
- ✅ `[Agent] 🎯 Metadata extracted` (agents/main.py)
- ✅ `[Agent] 🔍 KB Filter active` (agents/main.py)
- ✅ `[Agent] ℹ️ No KB filter` (agents/main.py)

---

## 🔒 Seguridad - Restricciones del Agente

### Antes (Problema)
- ❌ Agente respondía preguntas generales (clima, deportes, noticias)
- ❌ Usaba conocimiento general del modelo
- ❌ Podía "alucinar" información no presente en documentos

### Después (Solución)
- ✅ Agente SOLO responde con información del Knowledge Base
- ✅ Si `retrieve` no devuelve resultados → responde "No tengo información"
- ✅ NO usa conocimiento general del modelo
- ✅ NO responde preguntas fuera del dominio empresarial

### System Prompt Actualizado

**Restricciones clave:**
1. **SOLO** responder con información del KB
2. **SIEMPRE** usar `retrieve` para buscar
3. **NUNCA** usar conocimiento general del modelo
4. Si NO hay resultados → decir "No tengo información sobre eso"
5. `http_request` SOLO para URLs proporcionadas por el usuario (enriquecimiento, no búsqueda general)

---

## 🚀 Próximos Pasos Sugeridos

1. **Desplegar cambios al ambiente de desarrollo:**
   ```bash
   cd /Users/qohatpretel/Answering/kb-rag-agent/infrastructure
   npm run build
   npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
   ```

2. **Verificar logs en CloudWatch:**
   ```bash
   aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super
   ```

3. **Probar en producción:**
   - Navegar a diferentes proyectos y tareas
   - Verificar que metadata se propaga correctamente
   - Probar restricciones del agente (preguntas fuera del KB)

4. **Monitorear comportamiento:**
   - Revisar logs para confirmar metadata correcta
   - Validar que filtros KB se aplican
   - Confirmar que agente rechaza preguntas generales

---

## 📁 Archivos Modificados

```
REP_FE_COLPENSIONES/
├── src/app/shared/components/fury-chat-widget/
│   └── fury-chat-widget.component.ts  (metadata extraction + cleanup)
├── src/app/
│   ├── app.component.ts               (cleanup)
│   └── app.component.html             (add orgId binding)

kb-rag-agent/
├── fe/
│   ├── hooks/useWebSocketChat.ts      (add logs)
│   └── app/widget/page.tsx            (add logs)
├── agents/
│   └── main.py                        (restrict agent + add logs)
└── CHANGES_SUMMARY.md                 (this file)
```

---

**Última actualización:** 2026-05-03  
**Estado:** ✅ Completado y listo para desplegar  
**Testing:** Pendiente verificación en desarrollo
