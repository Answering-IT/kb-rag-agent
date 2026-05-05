# Active Scripts

Currently used scripts for testing and maintenance.

---

## 🚀 run-tests.sh

**Automated test runner**

```bash
./run-tests.sh
```

Performs complete test cycle: build → start → test → cleanup

---

## 🧪 test-hierarchical-fallback.py

**Hierarchical fallback test suite**

```bash
python3 test-hierarchical-fallback.py
```

Requires agent on localhost:8080. Tests all fallback scenarios.

**Results:** 5/6 tests passing (83%)

---

## 🔌 quick-ws-test.py

**WebSocket quick test**

```bash
python3 quick-ws-test.py
```

Verifies WebSocket connectivity and basic responses.

---

## 🔧 fix-s3-metadata-wrapper.py

**Metadata wrapper fixer**

```bash
python3 fix-s3-metadata-wrapper.py
```

Adds `metadataAttributes` wrapper to S3 metadata files. Idempotent.

---

## 🔑 add-partition-keys.py

**Partition key migration**

```bash
python3 add-partition-keys.py
```

Adds hierarchical partition_key to existing documents.

---

**See parent README.md for detailed documentation.**
