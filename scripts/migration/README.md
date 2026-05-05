# Migration Scripts

Scripts for data migration and transformation.

---

## ⚠️ Caution

These scripts **modify production data**. Review carefully before running.

---

## Scripts

### migrate-colpensiones-attachments.py

Migrates Colpensiones attachments to KB bucket with proper metadata structure.

### migrate-and-copy-projects.py

Migrates project documents with metadata transformation and validation.

### copy-to-kb-bucket.py

Copies documents to KB bucket maintaining proper S3 structure.

### copy-to-kb-via-download.py

Downloads from source and uploads to KB with metadata preservation.

---

## Best Practices

1. **Backup first** - Ensure data backed up before migration
2. **Test in dev** - Run against dev environment first
3. **Verify metadata** - Check metadata structure after migration
4. **Monitor logs** - Watch CloudWatch during migration
5. **Trigger sync** - Run KB sync after migration

---

## After Migration

```bash
# Verify documents uploaded
aws s3 ls s3://processapp-docs-v2-dev-708819485463/organizations/ --profile ans-super --recursive

# Check metadata
aws s3 cp s3://bucket/path/file.txt.metadata.json - --profile ans-super | jq .

# Trigger KB sync
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id BLJTRDGQI0 \
  --data-source-id B1OGNN9EMU \
  --profile ans-super
```

---

**For production migrations, create detailed runbook first.**
