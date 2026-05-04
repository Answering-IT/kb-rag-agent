# Progress de Migración de Proyectos Colpensiones

**Fecha inicio:** 2026-05-04  
**Script:** `migrate-and-copy-projects.py`

---

## Sesión 1: Proyectos de prueba (72, 85, 86, 90)

**Fecha:** 2026-05-04 16:00-16:30  
**Proyectos:** 4  
**Archivos copiados:** 76 (38 documentos + 38 metadata)  
**Resultado:** ✅ 37 documentos indexados en KB (1 fallo)

**Detalles:**
- Bucket destino limpiado completamente antes de copiar
- Solo archivos en STANDARD storage class (no archive tier)
- DataSource actualizado para escanear solo `organization/` prefix
- Sync KB completado exitosamente

**Knowledge Base Sync:**
- Job ID: D1UJRPI9NN
- Status: COMPLETE
- Scanned: 38
- Indexed: 37
- Failed: 1

---

## Sesión 2: Prueba de script integrado (6548-6550)

**Fecha:** 2026-05-04 17:08  
**Proyectos:** 3  
**Archivos procesados:** 12 (6 documentos + 6 metadata)  
**Resultado:** ✅ Migración exitosa

**Detalles:**
- Primer uso del script `migrate-and-copy-projects.py`
- Metadata generada automáticamente
- Verificación de integridad pasó
- Archivos copiados al KB bucket

**Reporte:** `/tmp/migration-full-report-20260504-170849.json`

---

## Sesión 3: Migración masiva (6000-6550) - EN PROCESO

**Fecha:** 2026-05-04 17:10 - ???  
**Proyectos:** 551  
**Status:** 🔄 En progreso  
**Proceso PID:** 45961

**Comando ejecutado:**
```bash
python3 scripts/migrate-and-copy-projects.py \
  --projects 6000-6550 \
  --tenant-id 1
```

**Pasos del proceso:**
1. Generar metadata para cada proyecto (llamadas al API)
2. Verificar que cada archivo tenga su metadata
3. Copiar proyectos completos al KB bucket
4. Generar reporte JSON

**Próximos pasos después de completar:**
1. Revisar reporte de migración
2. Contar archivos copiados
3. Sincronizar Knowledge Base
4. Verificar indexación

---

## Estadísticas Acumuladas (Sesión 1 + Sesión 2)

**Total proyectos migrados:** 7  
**Total archivos copiados:** 88  
**Total documentos indexados:** 37 (solo Sesión 1, Sesión 2 pendiente de sync)

**Proyectos migrados:**
- 72, 85, 86, 90 (Sesión 1)
- 6548, 6549, 6550 (Sesión 2)

---

## Configuración Actual

**Knowledge Base:**
- ID: CPERLTG5EU
- Name: processapp-kb-v3-dev
- DataSource ID: BUHHRDRZ90
- Inclusion prefix: `organization/`

**Buckets:**
- Source: `dev-files-colpensiones/organizations/1/projects/`
- Dest: `processapp-docs-v2-dev-708819485463/organization/1/projects/`

**Agent V2:**
- Runtime ID: processapp_agent_runtime_v2_dev-Fhe45j6xK2
- Endpoint: https://processapp_endpoint_v2_dev.bedrock-agentcore.us-east-1.amazonaws.com

**WebSocket V2:**
- URL: wss://hfck2ijkrh.execute-api.us-east-1.amazonaws.com/dev
- API ID: hfck2ijkrh

---

## Issues Conocidos

### 1. Archivos en Archive Tier

**Problema:** Archivos en INTELLIGENT_TIERING archive tier no se pueden copiar directamente.

**Error:** `InvalidObjectState: Operation is not valid for the source object's access tier`

**Archivos afectados:**
- `signed.pdf` (en múltiples proyectos)
- Archivos `*ComOf*.pdf`
- `documentosiri.pdf`
- `*ejemplo_400MB*`

**Solución aplicada:** 
- Sesión 1: Excluir esos archivos específicos
- Sesión 2-3: Script migra solo archivos disponibles (skips automáticamente si fallan)

**Alternativa futura:** Usar `copy-to-kb-via-download.py` para estos archivos

### 2. Proyectos sin archivos

**Comportamiento:** Script salta automáticamente proyectos sin archivos en S3.

**Log:** `⚠️ No files in S3`

**Esperado:** Normal, muchos proyectos fueron creados pero nunca tuvieron uploads.

### 3. API Timeout

**Problema potencial:** API de Colpensiones puede tener timeouts con 551 requests consecutivos.

**Mitigación:** Script tiene timeout de 30s por request, continúa con siguientes proyectos si falla.

---

## Próximas Migraciones Planificadas

**Pendiente:** Proyectos 6551-6647 (últimos ~100 proyectos)

**Estimado:**
- ~50-70 proyectos con archivos
- ~200-500 documentos
- Tiempo: 15-30 minutos

---

## Comandos Útiles

### Ver progreso de migración en curso

```bash
# Check si el proceso sigue corriendo
ps aux | grep migrate-and-copy | grep -v grep

# Ver último reporte generado
ls -lht /tmp/migration-full-report-*.json | head -1

# Ver estadísticas del último reporte
cat /tmp/migration-full-report-*.json | jq '{
  total_projects: .copy_results | length,
  successful: [.copy_results[] | select(.status == "success")] | length,
  skipped: [.copy_results[] | select(.status == "skipped")] | length,
  total_files: [.copy_results[] | select(.status == "success") | .files_copied] | add
}'
```

### Sincronizar Knowledge Base

```bash
KB_ID="CPERLTG5EU"
DS_ID="BUHHRDRZ90"

# Start ingestion
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --profile ans-super

# Monitor (reemplazar JOB_ID)
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id ${KB_ID} \
  --data-source-id ${DS_ID} \
  --ingestion-job-id ${JOB_ID} \
  --profile ans-super \
  --query 'ingestionJob.{Status:status,Scanned:statistics.numberOfDocumentsScanned,Indexed:statistics.numberOfNewDocumentsIndexed,Failed:statistics.numberOfDocumentsFailed}'
```

### Verificar archivos en KB bucket

```bash
# Contar proyectos
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organization/1/projects/ \
  --profile ans-super | grep "PRE" | wc -l

# Contar archivos totales
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organization/1/projects/ \
  --recursive --profile ans-super | wc -l

# Contar solo metadata files
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organization/1/projects/ \
  --recursive --profile ans-super | grep "\.metadata\.json" | wc -l

# Ver proyecto específico
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organization/1/projects/6548/ \
  --recursive --profile ans-super
```

---

**Última actualización:** 2026-05-04 17:15  
**Status:** Migración masiva en progreso (6000-6550)
