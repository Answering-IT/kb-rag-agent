# Scripts Directory

Organized collection of scripts for ProcessApp Agent development, testing, and maintenance.

**Last Updated:** 2026-05-05

---

## 📁 Directory Structure

```
scripts/
├── active/              ⭐ Currently used scripts
├── deprecated/          📦 Old/archived scripts
├── migration/           🔄 Data migration scripts
├── utilities/           🔧 Helper utilities
├── archive/             📚 Historical scripts
├── testing-archive/     🧪 Old test scripts
├── README.md           📖 This file
├── README-TESTS.md     📖 Testing documentation
└── requirements.txt    📦 Python dependencies
```

---

## ⭐ Active Scripts

**Location:** `active/`

These are the primary scripts currently in use.

### `run-tests.sh` 🚀

**Purpose:** Automated test runner for hierarchical fallback tests

**Usage:**
```bash
./scripts/active/run-tests.sh
```

**What it does:**
1. Cleans up existing containers
2. Builds Docker image
3. Starts agent container
4. Verifies health
5. Runs test suite
6. Optionally cleans up

**Output:** Test results + archived log in `/tmp/test-results-*.txt`

**Requirements:** Docker, AWS credentials, `jq`

---

### `test-hierarchical-fallback.py` 🧪

**Purpose:** Comprehensive test suite for hierarchical search fallback

**Usage:**
```bash
# Requires agent running on localhost:8080
python3 scripts/active/test-hierarchical-fallback.py
```

**Tests:**
- Tenant isolation (tenant cannot see project docs)
- Project access (project can see own docs)
- Fallback to tenant (project searches tenant when needed)
- Cross-project isolation (projects cannot see each other)
- Mixed results (combining project + tenant results)
- Tenant-level access (direct tenant queries)

**Documentation:** See `docs/HIERARCHICAL_FALLBACK_TESTING.md`

---

### `quick-ws-test.py` 🔌

**Purpose:** Quick WebSocket API testing

**Usage:**
```bash
python3 scripts/active/quick-ws-test.py
```

**Use case:** Verify WebSocket connectivity and basic agent responses

---

### `fix-s3-metadata-wrapper.py` 🔧

**Purpose:** Fix S3 metadata files to include AWS KB wrapper

**Usage:**
```bash
python3 scripts/active/fix-s3-metadata-wrapper.py
```

**What it fixes:**
- Before: `{"tenant_id": "100001", "partition_key": "t100001"}`
- After: `{"metadataAttributes": {"tenant_id": "100001", "partition_key": "t100001"}}`

**Safety:** Idempotent (safe to run multiple times)

---

### `add-partition-keys.py` 🔑

**Purpose:** Add partition_key field to existing KB documents

**Usage:**
```bash
python3 scripts/active/add-partition-keys.py
```

**Use case:** Migrate documents to use hierarchical partition keys

---

## 📦 Deprecated Scripts

**Location:** `deprecated/`

Old scripts no longer actively used but kept for reference.

- `test-agent.py` - Agent V1 REST API tests (Agent V1 deprecated)
- `test-ocr-agent.py` - OCR Lambda testing (archived)
- `test-api.py` - Old API tests
- `test-tools.py` - Old tool tests
- `test-agent-tools.sh` - Old shell-based tests
- `run-e2e-tests.sh` - Old end-to-end tests

**Note:** These scripts may not work with current infrastructure.

---

## 🔄 Migration Scripts

**Location:** `migration/`

Scripts for migrating data between systems or formats.

### `migrate-colpensiones-attachments.py`

Migrates Colpensiones attachments to KB bucket with proper metadata.

### `migrate-and-copy-projects.py`

Migrates project documents with metadata transformation.

### `copy-to-kb-bucket.py`

Copies documents to KB bucket with proper structure.

### `copy-to-kb-via-download.py`

Downloads and uploads documents with metadata preservation.

**Note:** Run migration scripts carefully - they modify production data.

---

## 🔧 Utilities

**Location:** `utilities/`

Helper scripts for development tasks.

### `create-ocr-image.py`

Creates test images for OCR processing verification.

---

## 📚 Archives

### `archive/`

Historical scripts from early development phases.

### `testing-archive/`

Old test scripts preserved for reference:
- `quick-isolation-test.sh`
- `test-metadata-filtering-complete.py`
- `test-metadata-isolation.py`
- `test-strict-isolation.sh`
- `split-large-files.py`

---

## 🚀 Quick Start

### Run Tests

```bash
# Automated (recommended)
./scripts/active/run-tests.sh

# Manual
cd agents && docker build -t processapp-agent:test .
docker run -d -p 8080:8080 -e AWS_PROFILE=ans-super \
  -v ~/.aws:/root/.aws:ro --name agent-test processapp-agent:test
python3 scripts/active/test-hierarchical-fallback.py
docker stop agent-test && docker rm agent-test
```

### Fix Metadata

```bash
# Fix metadata wrapper
python3 scripts/active/fix-s3-metadata-wrapper.py

# Add partition keys
python3 scripts/active/add-partition-keys.py
```

### Test WebSocket

```bash
python3 scripts/active/quick-ws-test.py
```

---

## 📖 Documentation

- **README-TESTS.md** - Detailed testing documentation
- **docs/HIERARCHICAL_FALLBACK_TESTING.md** - Fallback testing guide
- **docs/HIERARCHICAL_FALLBACK_RESULTS.md** - Test results and metrics
- **TESTING_QUICKSTART.md** - Quick testing guide

---

## 📦 Dependencies

Install Python dependencies:

```bash
pip3 install -r scripts/requirements.txt
```

**Contents:**
- `requests` - HTTP client for API testing
- Other dependencies as needed

---

## 🔑 Environment Requirements

Most scripts require:

- **AWS Profile:** `ans-super` configured
- **AWS Region:** `us-east-1`
- **Knowledge Base ID:** `BLJTRDGQI0`
- **DataSource ID:** `B1OGNN9EMU`
- **Docker:** For container-based testing

---

## 📝 Adding New Scripts

When adding new scripts:

1. **Determine category:**
   - Active: Currently used in development/testing
   - Utilities: Helper tools
   - Migration: Data transformation/migration
   - Deprecated: Old but kept for reference

2. **Place in appropriate directory**

3. **Update this README:**
   - Add description
   - Add usage example
   - Document requirements

4. **Make executable if needed:**
   ```bash
   chmod +x scripts/active/your-script.sh
   ```

5. **Add documentation:**
   - Inline comments
   - Docstrings for Python
   - Usage examples

---

## 🗑️ Deprecating Scripts

When deprecating a script:

1. Move to `deprecated/` directory
2. Update README to note deprecation
3. Add comment at top of script explaining why deprecated
4. Keep for reference (don't delete immediately)

---

## 🔍 Finding Scripts

**By function:**
- Testing → `active/test-*.py` or `active/run-tests.sh`
- Metadata fixes → `active/fix-*.py` or `active/add-*.py`
- Migration → `migration/migrate-*.py`
- Quick checks → `active/quick-*.py`

**By status:**
- Current → `active/`
- Old → `deprecated/` or `archive/`
- Historical → `testing-archive/`

---

## 📞 Support

For issues with scripts:

1. Check script's inline documentation
2. Review related docs in `docs/`
3. Check CloudWatch logs if AWS-related
4. Verify AWS credentials and permissions

---

**Last Updated:** 2026-05-05  
**Total Active Scripts:** 5  
**Total Deprecated Scripts:** 6  
**Total Migration Scripts:** 4  
**Status:** ✅ Organized and documented
