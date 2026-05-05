# Scripts Index

Quick reference for finding scripts by purpose.

**Last Updated:** 2026-05-05

---

## 🔍 Find Scripts by Purpose

### Testing & Validation

| Script | Location | Purpose |
|--------|----------|---------|
| `run-tests.sh` | `active/` | ⭐ Automated test runner (recommended) |
| `test-hierarchical-fallback.py` | `active/` | Comprehensive fallback tests |
| `quick-ws-test.py` | `active/` | Quick WebSocket verification |

### Metadata Management

| Script | Location | Purpose |
|--------|----------|---------|
| `fix-s3-metadata-wrapper.py` | `active/` | Fix metadata wrapper structure |
| `add-partition-keys.py` | `active/` | Add hierarchical partition keys |

### Data Migration

| Script | Location | Purpose |
|--------|----------|---------|
| `migrate-colpensiones-attachments.py` | `migration/` | Migrate Colpensiones data |
| `migrate-and-copy-projects.py` | `migration/` | Migrate project documents |
| `copy-to-kb-bucket.py` | `migration/` | Copy to KB bucket |
| `copy-to-kb-via-download.py` | `migration/` | Download & upload migration |

### Utilities

| Script | Location | Purpose |
|--------|----------|---------|
| `create-ocr-image.py` | `utilities/` | Generate OCR test images |

### Deprecated (Reference Only)

| Script | Location | Reason Deprecated |
|--------|----------|-------------------|
| `test-agent.py` | `deprecated/` | Agent V1 replaced by V2 |
| `test-ocr-agent.py` | `deprecated/` | Archived |
| `test-api.py` | `deprecated/` | Old API replaced |
| `test-tools.py` | `deprecated/` | Replaced by new tests |
| `test-agent-tools.sh` | `deprecated/` | Old shell tests |
| `run-e2e-tests.sh` | `deprecated/` | Old E2E runner |

---

## 🎯 Common Tasks

### Run Tests

```bash
# Automated (all-in-one)
./scripts/active/run-tests.sh

# Manual steps
python3 scripts/active/test-hierarchical-fallback.py
```

### Fix Metadata Issues

```bash
# Add KB wrapper
python3 scripts/active/fix-s3-metadata-wrapper.py

# Add partition keys
python3 scripts/active/add-partition-keys.py
```

### Quick Checks

```bash
# WebSocket connectivity
python3 scripts/active/quick-ws-test.py

# View logs
docker logs agent-test
```

---

## 📚 Documentation

- **Main Guide:** `README.md`
- **Testing Guide:** `README-TESTS.md`
- **Active Scripts:** `active/README.md`
- **Deprecated:** `deprecated/README.md`
- **Migration:** `migration/README.md`
- **Utilities:** `utilities/README.md`

---

## 🔑 Quick Reference

**By Status:**
- ⭐ Active scripts → `active/`
- 📦 Old scripts → `deprecated/`
- 🔄 Migrations → `migration/`
- 🔧 Helpers → `utilities/`
- 📚 Historical → `archive/`, `testing-archive/`

**By Function:**
- Testing → `active/test-*.py`, `active/run-tests.sh`
- Metadata → `active/fix-*.py`, `active/add-*.py`
- Migration → `migration/migrate-*.py`, `migration/copy-*.py`
- Quick checks → `active/quick-*.py`

---

**Total Scripts:** 16 organized + archives  
**Active:** 5 (frequently used)  
**Status:** ✅ Fully documented and organized
