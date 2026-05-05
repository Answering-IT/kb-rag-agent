# Testing Quickstart - Hierarchical Fallback

Quick guide to test hierarchical fallback locally with Docker before deploying to AWS.

---

## 🚀 Quick Start (5 minutes)

### 1. Build agent container

```bash
cd agents
docker build -t processapp-agent:test .
```

### 2. Run agent locally

```bash
docker run -d \
  -p 8080:8080 \
  -e AWS_PROFILE=ans-super \
  -e AWS_REGION=us-east-1 \
  -e KB_ID=BLJTRDGQI0 \
  -e MODEL_ID=amazon.nova-pro-v1:0 \
  -v ~/.aws:/root/.aws:ro \
  --name agent-test \
  processapp-agent:test
```

### 3. Verify agent is running

```bash
# Check health
curl http://localhost:8080/health

# Should return: {"status": "healthy", ...}
```

### 4. Install test dependencies (if needed)

```bash
pip3 install requests
```

### 5. Run tests

```bash
cd /Users/qohatpretel/Answering/kb-rag-agent
python3 scripts/test-hierarchical-fallback.py
```

### 6. Cleanup

```bash
docker stop agent-test && docker rm agent-test
```

---

## 📊 What the tests verify

1. ✅ **Tenant isolation** - Tenant-only cannot see project documents
2. ✅ **Project access** - Project can see its own documents  
3. 🔥 **Fallback to tenant** - Project searches fallback to tenant-level when needed
4. ✅ **Cross-project isolation** - Project 1 cannot see Project 2 documents
5. 🔥 **Mixed results** - Combines project + tenant results when both relevant
6. ✅ **Tenant access** - Tenant-level can access general documents

---

## 🧪 Manual test (without script)

```bash
# Test fallback from project to tenant
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: 100001" \
  -H "x-project-id: 1" \
  -d '{
    "inputText": "¿Qué equipos están en semifinales de la Champions?",
    "sessionId": "test-123",
    "knowledgeBases": [{
      "knowledgeBaseId": "BLJTRDGQI0",
      "retrievalConfiguration": {
        "vectorSearchConfiguration": {"numberOfResults": 5}
      }
    }]
  }'
```

**Expected:** Response mentions PSG, Bayern, Atlético, Arsenal (from tenant-level `champions.txt`)

---

## 🔍 Check logs for fallback behavior

```bash
docker logs agent-test | grep -E "Fallback|Filter|results\)"
```

**Look for:**
```
[RetrieveWrapper] ✅ Retrieve call succeeded (0 results)
[Fallback] Only 0 results found, attempting tenant-level fallback
[Fallback] Building tenant filter: t100001_p1 → t100001
[Fallback] ✅ Tenant-level search succeeded (3 results)
[Fallback] ✅ Combined results: 0 project + 3 tenant
```

---

## 🚢 Deploy after tests pass

```bash
cd infrastructure
npm run build
npx cdk deploy dev-us-east-1-agent-v2 --profile ans-super --require-approval never
```

---

## 📖 Full documentation

See `docs/HIERARCHICAL_FALLBACK_TESTING.md` for:
- Detailed test scenarios
- Implementation details
- Troubleshooting guide
- Tuning parameters

---

**Last Updated:** 2026-05-05  
**Feature:** Hierarchical search fallback (project → tenant)  
**Files modified:** `agents/core/tools/retrieve.py`
