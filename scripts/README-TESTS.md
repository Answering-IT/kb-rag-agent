# Test Scripts

Collection of test scripts for the ProcessApp Agent.

---

## 🚀 Quick Start

### Automated Testing (Recommended)

```bash
# Run complete test suite with automated build and cleanup
./scripts/run-tests.sh
```

**What it does:**
1. Cleans up existing test containers
2. Builds fresh Docker image
3. Starts agent container
4. Verifies health
5. Runs all tests
6. Optionally cleans up

**Output:** Test results + archived log file in `/tmp/test-results-YYYYMMDD-HHMMSS.txt`

---

## Active Tests

### `run-tests.sh` (NEW - Automated Runner)

**Purpose:** Automated build → test → cleanup workflow

**Usage:**
```bash
./scripts/run-tests.sh
```

**Features:**
- ✅ Color-coded output
- ✅ Health checks before testing
- ✅ Test result archiving
- ✅ Optional cleanup
- ✅ Proper error handling

**Exit codes:**
- `0` - All tests passed
- `1` - Some tests failed or build error

**Requirements:**
- Docker installed and running
- AWS credentials configured (`ans-super` profile)
- `jq` installed (for JSON parsing)

---

### `test-hierarchical-fallback.py`

**Purpose:** Test hierarchical search fallback strategy

**What it tests:**
- Tenant isolation (tenant cannot see project docs)
- Project access (project can see its own docs)
- Fallback to tenant-level (when project search yields few results)
- Cross-project isolation (project 1 cannot see project 2 docs)
- Mixed results combination (project + tenant results)

**Prerequisites:**
- Docker running locally
- AWS credentials configured (`ans-super` profile)
- Knowledge Base synced with test data (3 documents)

**Usage:**
```bash
# 1. Build and run agent container
cd agents
docker build -t processapp-agent:test .
docker run -d -p 8080:8080 \
  -e AWS_PROFILE=ans-super \
  -e AWS_REGION=us-east-1 \
  -e KB_ID=BLJTRDGQI0 \
  -v ~/.aws:/root/.aws:ro \
  --name agent-test \
  processapp-agent:test

# 2. Run tests
python3 scripts/test-hierarchical-fallback.py

# 3. Cleanup
docker stop agent-test && docker rm agent-test
```

**Documentation:** See `docs/HIERARCHICAL_FALLBACK_TESTING.md`

---

## Archived Tests

See `scripts/testing-archive/` for deprecated test scripts:
- `test-agent.py` - Agent V1 REST API tests
- `test-ocr-agent.py` - OCR Lambda integration tests
- `test-websocket.sh` - Manual WebSocket testing

---

## Test Data

Current KB structure for tests:

```
organizations/100001/
├── champions.txt (tenant-level)
│   └── partition_key: "t100001"
│   └── Content: Champions League 2025-26, semifinales
│
├── projects/1/luis_diaz_biografia.txt (project 1)
│   └── partition_key: "t100001_p1"
│   └── Content: Luis Díaz, Liverpool FC, Colombia
│
└── projects/2/manuel_neuer_info.txt (project 2)
    └── partition_key: "t100001_p2"
    └── Content: Manuel Neuer, Bayern Múnich, portero
```

To add more test data:
```bash
aws s3 cp document.txt s3://processapp-docs-v2-dev-708819485463/organizations/100001/ \
  --metadata tenant_id=100001,partition_key=t100001 \
  --profile ans-super
```

Then trigger KB sync:
```bash
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id BLJTRDGQI0 \
  --data-source-id B1OGNN9EMU \
  --profile ans-super
```

---

## Quick Reference

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| Tenant isolation | Verify tenant cannot see project docs | ❌ No access |
| Project access | Verify project sees its own docs | ✅ Access granted |
| Fallback to tenant | Search falls back when results < 2 | ✅ Finds tenant docs |
| Cross-project isolation | Project 1 cannot see project 2 | ❌ No access |
| Mixed results | Combines project + tenant results | ✅ Both returned |

---

**Last Updated:** 2026-05-05  
**Active Agent Version:** Agent V2 (Strands SDK)  
**KB ID:** BLJTRDGQI0  
**DataSource ID:** B1OGNN9EMU
