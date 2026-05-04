# Test Case - Luis Fernández (Project 165, Task 174)

**Created:** 2026-05-03  
**Tenant:** 1001  
**Project:** 165  
**Task:** 174

---

## 📦 Test Data Structure

```
s3://processapp-docs-v2-dev-708819485463/
└── tenant/1001/
    └── project/165/
        ├── luis-fernandez-datos.txt
        ├── luis-fernandez-datos.txt.metadata.json
        └── tasks/174/
            ├── luis-fernandez-hazanas.txt
            └── luis-fernandez-hazanas.txt.metadata.json
```

---

## 📄 Document Contents

### Project Level: `luis-fernandez-datos.txt`

**Content:**
```
Luis Fernández nació en 1968 en Santa Marta, Colombia.

Es un atleta excepcional conocido por sus increíbles hazañas de resistencia física.

Actualmente tiene 58 años y reside en la costa caribeña colombiana.
```

**Metadata:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165"
  }
}
```

**Size:** 216 bytes (✅ well below metadata limit)

---

### Task Level: `luis-fernandez-hazanas.txt`

**Content:**
```
Hazañas extraordinarias de Luis Fernández:

1. Trotó 40 kilómetros completamente descalzo, sin zapatos, por la playa de Santa Marta.

2. Caminó 12 kilómetros parado de manos en un evento benéfico, estableciendo un récord local.

Estas hazañas demuestran su extraordinaria capacidad física y determinación.
```

**Metadata:**
```json
{
  "metadataAttributes": {
    "tenant_id": "1001",
    "project_id": "165",
    "task_id": "174"
  }
}
```

**Size:** 317 bytes (✅ well below metadata limit)

---

## ✅ Ingestion Status

**Job ID:** XQVWGVOMFP  
**Status:** ✅ COMPLETE  
**Started:** 2026-05-04 02:57:36  
**Completed:** 2026-05-04 02:57:42 (6 seconds)

**Statistics:**
- Documents scanned: 16
- Metadata scanned: 16
- New indexed: 2 ✅ (Luis's documents)
- Modified: 0
- Deleted: 0
- Failed: 0 ✅

---

## 🧪 Test Scenarios

### Scenario 1: Access with Project Filter Only

**Route:** `http://localhost:4200/requirements/165`

**Expected Metadata:**
```json
{
  "tenant_id": "1001",
  "project_id": "165"
}
```

**Test Questions:**

1. **"¿Quién es Luis Fernández?"**
   - ✅ Should respond: "Luis Fernández nació en 1968 en Santa Marta..."
   - ✅ Should access: Project-level document

2. **"¿Dónde nació Luis?"**
   - ✅ Should respond: "Nació en Santa Marta, Colombia"
   - ✅ Should access: Project-level document

3. **"¿Cuántos años tiene Luis?"**
   - ✅ Should respond: "Actualmente tiene 58 años"
   - ✅ Should access: Project-level document

4. **"¿Qué hazañas ha realizado Luis?"**
   - ❓ Might respond or might say "no tengo información" (task-specific data)
   - If responds: Should mention 40 km without shoes and 12 km on hands
   - ⚠️ **Note:** Without task_id filter, agent might not access task-level document

---

### Scenario 2: Access with Project + Task Filter

**Route:** `http://localhost:4200/requirements/165/174`

**Expected Metadata:**
```json
{
  "tenant_id": "1001",
  "project_id": "165",
  "task_id": "174"
}
```

**Test Questions:**

1. **"¿Quién es Luis Fernández?"**
   - ✅ Should respond: "Luis Fernández nació en 1968 en Santa Marta..."
   - ✅ Should access: Project-level document

2. **"¿Qué hazañas ha realizado Luis?"**
   - ✅ Should respond: "Trotó 40 kilómetros descalzo... caminó 12 kilómetros parado de manos..."
   - ✅ Should access: Task-level document

3. **"¿Cuántos kilómetros trotó sin zapatos?"**
   - ✅ Should respond: "40 kilómetros"
   - ✅ Should access: Task-level document

4. **"¿Qué hizo parado de manos?"**
   - ✅ Should respond: "Caminó 12 kilómetros parado de manos"
   - ✅ Should access: Task-level document

---

### Scenario 3: Wrong Project (Should Fail)

**Route:** `http://localhost:4200/requirements/6636`

**Expected Metadata:**
```json
{
  "tenant_id": "1001",
  "project_id": "6636"  ← Different project
}
```

**Test Questions:**

1. **"¿Quién es Luis Fernández?"**
   - ❌ Should respond: "Lo siento, no tengo información disponible sobre eso."
   - ❌ Should NOT access Luis's documents (different project)

2. **"¿Qué hazañas realizó Luis?"**
   - ❌ Should respond: "Lo siento, no tengo información disponible sobre eso."

**CRITICAL Verification:**
- ❌ Agent must NOT mention: "filtros", "metadata", "tenant_id", "project_id"
- ❌ Agent must NOT say: "no cumple con los criterios"
- ✅ Agent MUST only say: "no tengo información disponible"

---

### Scenario 4: Wrong Task (Should Partially Fail)

**Route:** `http://localhost:4200/requirements/165/999`

**Expected Metadata:**
```json
{
  "tenant_id": "1001",
  "project_id": "165",
  "task_id": "999"  ← Different task
}
```

**Test Questions:**

1. **"¿Quién es Luis Fernández?"**
   - ✅ Should respond: "Luis Fernández nació en 1968 en Santa Marta..."
   - ✅ Project-level doc doesn't have task_id, so should be accessible

2. **"¿Qué hazañas realizó Luis?"**
   - ❌ Should respond: "Lo siento, no tengo información disponible sobre eso."
   - ❌ Task-level doc has task_id=174, so should NOT match task_id=999

---

## 🔍 Metadata Filtering Logic

### How it works:

**Project-level document** (`luis-fernandez-datos.txt`):
```json
{
  "tenant_id": "1001",
  "project_id": "165"
  // No task_id
}
```
- ✅ Matches filter: `{tenant_id: "1001", project_id: "165"}`
- ✅ Matches filter: `{tenant_id: "1001", project_id: "165", task_id: "174"}`
  (because document doesn't have task_id, it's accessible to all tasks in project)

**Task-level document** (`luis-fernandez-hazanas.txt`):
```json
{
  "tenant_id": "1001",
  "project_id": "165",
  "task_id": "174"
}
```
- ✅ Matches filter: `{tenant_id: "1001", project_id: "165", task_id: "174"}`
- ❌ Does NOT match filter: `{tenant_id: "1001", project_id: "165"}` (if strict matching)
- ❌ Does NOT match filter: `{tenant_id: "1001", project_id: "165", task_id: "999"}`

⚠️ **Important:** Bedrock metadata filtering uses `andAll` with `equals`, which means:
- All fields in the filter must match
- If document has extra fields not in filter, it might still match (depends on implementation)

---

## 🚀 How to Run Tests

### 1. Start Services

```bash
# Angular app (Colpensiones)
cd /Users/qohatpretel/Answering/REP_FE_COLPENSIONES
ng serve

# Widget Next.js
cd /Users/qohatpretel/Answering/kb-rag-agent/fe
npm run dev
```

### 2. Test Project-Level Access

1. Navigate to: `http://localhost:4200/requirements/165`
2. Open chat widget
3. Ask: "¿Quién es Luis Fernández?"
4. Ask: "¿Dónde nació Luis?"
5. Ask: "¿Cuántos años tiene?"

**Expected:** All questions answered correctly

### 3. Test Task-Level Access

1. Navigate to: `http://localhost:4200/requirements/165/174`
2. Open chat widget
3. Ask: "¿Qué hazañas ha realizado Luis?"
4. Ask: "¿Cuántos kilómetros trotó sin zapatos?"
5. Ask: "¿Qué hizo parado de manos?"

**Expected:** All questions answered correctly

### 4. Test Wrong Project (Isolation)

1. Navigate to: `http://localhost:4200/requirements/6636`
2. Open chat widget
3. Ask: "¿Quién es Luis Fernández?"

**Expected:** "Lo siento, no tengo información disponible sobre eso."

### 5. Test Wrong Task

1. Navigate to: `http://localhost:4200/requirements/165/999`
2. Open chat widget
3. Ask: "¿Quién es Luis Fernández?" → Should work (project-level)
4. Ask: "¿Qué hazañas realizó Luis?" → Should fail (task-level)

---

## 📊 Expected Results Summary

| Scenario | Route | Question | Expected Result |
|----------|-------|----------|-----------------|
| Project only | `/requirements/165` | ¿Quién es Luis? | ✅ "Nació en 1968..." |
| Project only | `/requirements/165` | ¿Qué hazañas? | ❓ Might work or fail |
| Project + Task | `/requirements/165/174` | ¿Quién es Luis? | ✅ "Nació en 1968..." |
| Project + Task | `/requirements/165/174` | ¿Qué hazañas? | ✅ "40 km descalzo..." |
| Wrong project | `/requirements/6636` | ¿Quién es Luis? | ❌ "No tengo información" |
| Wrong task | `/requirements/165/999` | ¿Quién es Luis? | ✅ "Nació en 1968..." |
| Wrong task | `/requirements/165/999` | ¿Qué hazañas? | ❌ "No tengo información" |

---

## 🔒 Security Verification

During all tests, verify agent NEVER mentions:
- ❌ "filtros"
- ❌ "metadata"
- ❌ "tenant_id"
- ❌ "project_id"
- ❌ "task_id"
- ❌ "retrieveFilter"
- ❌ "no cumple con los criterios"

Agent should ONLY say:
- ✅ "Lo siento, no tengo información disponible sobre eso."

---

## 📝 Notes

- Documents are intentionally small (< 400 bytes) to avoid metadata size issues
- Metadata is minimal (only IDs, no descriptions)
- Task-level document lives in `tasks/174/` subfolder
- Project-level document is at project root
- Both documents share same tenant_id and project_id
- Only task document has task_id

---

**Test Status:** ⏳ Ready for manual testing  
**KB Status:** ✅ Documents indexed successfully  
**Ingestion Job:** XQVWGVOMFP (COMPLETE)
