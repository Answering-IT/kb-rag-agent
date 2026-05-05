# Hierarchical Fallback - Visual Guide

Quick visual reference for the hierarchical search fallback feature.

---

## 🎯 The Problem

**Before fallback:**
```
User in Project 1: "¿Qué equipos están en semifinales de la Champions?"
           ↓
    Search with filter: partition_key = "t100001_p1"
           ↓
    Only finds: luis_diaz_biografia.txt (about Luis Díaz, not Champions)
           ↓
    Response: ❌ "No tengo información sobre las semifinales"
```

**Issue:** General organizational info (Champions League) stored at tenant-level, but project-level search doesn't see it.

---

## ✅ The Solution

**With hierarchical fallback:**
```
User in Project 1: "¿Qué equipos están en semifinales de la Champions?"
           ↓
    [1] Search with filter: partition_key = "t100001_p1"
           ↓
    Results: 0 (Luis Díaz doc doesn't mention Champions semifinals)
           ↓
    [2] Threshold check: 0 < MIN_RESULTS_THRESHOLD (2)
           ↓
    [3] FALLBACK to tenant-level: partition_key = "t100001"
           ↓
    Results: 3 (champions.txt has the answer!)
           ↓
    [4] Combine results (tenant results returned)
           ↓
    Response: ✅ "PSG, Bayern Múnich, Atlético Madrid, Arsenal"
```

---

## 📊 Fallback Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  User Query: "¿Qué equipos están en semifinales?"              │
│  Context: tenant_id=100001, project_id=1                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [1] Build filter             │
          │ partition_key = "t100001_p1" │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [2] Search KB                │
          │ with project-level filter    │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [3] Count results            │
          │ result_count = 0             │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [4] Check threshold          │
          │ 0 < 2 ? YES → FALLBACK       │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [5] Extract tenant from key  │
          │ "t100001_p1" → "t100001"     │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [6] Build tenant filter      │
          │ partition_key = "t100001"    │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [7] Search KB again          │
          │ with tenant-level filter     │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [8] Combine results          │
          │ 0 project + 3 tenant = 3     │
          └──────────────┬───────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ [9] Return to agent          │
          │ champions.txt content        │
          └──────────────────────────────┘
```

---

## 🔐 Isolation Boundaries

### ✅ Valid Fallback Paths (Hierarchical - Upward Only)

```
Task Level (most specific)
    ↓ fallback
Project Level
    ↓ fallback
Tenant Level (most general)
```

**Examples:**
```
t100001_p1_t5_s3  →  t100001_p1_t5  →  t100001_p1  →  t100001  ✅
t100001_p2        →  t100001                                    ✅
t100001_p1_t3     →  t100001_p1     →  t100001                 ✅
```

### ❌ Invalid Fallback Paths (Cross-Project - Forbidden)

```
Project 1  ↛  Project 2  ❌
   ↓              ↓
Tenant ← ← ← ← ← ←  (only valid path)
```

**Examples:**
```
t100001_p1  →  t100001_p2         ❌ CROSS-PROJECT BREACH
t100001_p1  →  t100001  →  done   ✅ CORRECT
```

---

## 📋 Test Scenarios Summary

| # | Scenario | Filter Applied | Expected Result | Fallback? |
|---|----------|----------------|-----------------|-----------|
| 1 | Tenant-only searches for Luis Díaz | `t100001` | ❌ Not found (in project) | No |
| 2 | Project 1 searches for Luis Díaz | `t100001_p1` | ✅ Found | No |
| 3 | Project 1 searches for Champions | `t100001_p1` → `t100001` | ✅ Found (tenant-level) | Yes |
| 4 | Project 1 searches for Neuer | `t100001_p1` → `t100001` | ❌ Not found (in project 2) | Yes |
| 5 | Project 2 searches for Bayern | `t100001_p2` → `t100001` | ✅ Both found (mixed) | Yes |
| 6 | Tenant-only searches for PSG score | `t100001` | ✅ Found | No |

**Key Insight:** Fallback is automatic and transparent. User doesn't need to know where documents live.

---

## 🎚️ Tuning Parameters

### MIN_RESULTS_THRESHOLD

**Location:** `agents/core/tools/retrieve.py:26`

```python
MIN_RESULTS_THRESHOLD = 2  # Default
```

**Effect:**
- **Lower (1):** Only fallback if no results found (conservative)
- **Current (2):** Fallback if 0-1 results found (balanced)
- **Higher (3):** Fallback if 0-2 results found (aggressive)

**When to adjust:**
- More documents in KB → increase threshold (e.g., 5)
- Fewer documents in KB → decrease threshold (e.g., 1)
- Users complaining "no results" → increase threshold
- Too much irrelevant context → decrease threshold

---

## 🔍 Log Output Examples

### Successful fallback

```
[RetrieveWrapper] ✅ Injected filter into retrieve call
[RetrieveWrapper] Filter: {'andAll': [{'equals': {'key': 'partition_key', 'value': 't100001_p1'}}]}
[RetrieveWrapper] ✅ Retrieve call succeeded (0 results)
[Fallback] Only 0 results found, attempting tenant-level fallback
[Fallback] Building tenant filter: t100001_p1 → t100001
[Fallback] ✅ Tenant-level search succeeded (3 results)
[Fallback] ✅ Combined results: 0 project + 3 tenant
```

### No fallback needed

```
[RetrieveWrapper] ✅ Injected filter into retrieve call
[RetrieveWrapper] Filter: {'andAll': [{'equals': {'key': 'partition_key', 'value': 't100001_p1'}}]}
[RetrieveWrapper] ✅ Retrieve call succeeded (4 results)
```

### Cross-project isolation maintained

```
[RetrieveWrapper] ✅ Retrieve call succeeded (0 results)
[Fallback] Only 0 results found, attempting tenant-level fallback
[Fallback] Building tenant filter: t100001_p1 → t100001
[Fallback] ✅ Tenant-level search succeeded (0 results)
# Document exists in t100001_p2 but not accessible from t100001_p1
```

---

## 💡 User Experience

### Before (without fallback)

```
User: "¿Qué equipos están en semifinales de la Champions?"
Agent: "Lo siento, no tengo información sobre las semifinales de la Champions League."
User: 😡 (Information exists in KB but not found)
```

### After (with fallback)

```
User: "¿Qué equipos están en semifinales de la Champions?"
Agent: "Los equipos en semifinales son Paris Saint-Germain, Bayern Múnich, 
        Atlético de Madrid y Arsenal. PSG venció 5-4 al Bayern en la ida."
User: 😃 (Information found automatically)
```

**Key benefit:** User doesn't need to know organizational structure. Agent intelligently searches across levels.

---

## 🚀 Next Steps

1. **Local testing:** Run `python3 scripts/test-hierarchical-fallback.py`
2. **Deploy:** `npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super`
3. **Monitor:** `aws logs tail /aws/bedrock/agentcore/runtime/processapp_agent_runtime_v2_dev --follow --profile ans-super | grep Fallback`
4. **Tune:** Adjust `MIN_RESULTS_THRESHOLD` based on user feedback

---

**Last Updated:** 2026-05-05  
**Feature Status:** Ready for local testing  
**Implementation:** `agents/core/tools/retrieve.py`
