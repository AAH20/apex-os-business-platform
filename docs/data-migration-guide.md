# Data Migration Guide

## 1. Migration Strategy

### Principles

- **Incremental, not big-bang**: Break migrations into small, reversible steps.
- **Backward-compatible schema changes**: Add columns/tables first, migrate data, then remove old structures in a later release.
- **Idempotent scripts**: Every migration can run multiple times without side effects.
- **Version-controlled**: All migrations live in `migrations/` and are tracked in git.
- **Environment parity**: Migrations run identically in dev, staging, and production.

### Process

1. **Pre-migration audit** — Profile data volume, identify hot tables, estimate downtime.
2. **Write migration** — Create up/down scripts with clear naming: `YYYYMMDDHHMMSS_description.up.sql` / `.down.sql`.
3. **Dry-run in staging** — Execute against a production-sized snapshot.
4. **Schedule** — Run during low-traffic windows; use blue-green deployment for zero-downtime.
5. **Execute** — Apply migrations via the migration runner (`npm run migrate` or equivalent).
6. **Verify** — Run post-migration validation checks (see Section 3).
7. **Monitor** — Watch error rates and query performance for 24h post-migration.

### Naming Convention

```
migrations/
  20251001000000_add_user_status.up.sql
  20251001000000_add_user_status.down.sql
  20251002000000_create_audit_log.up.sql
  20251002000000_create_audit_log.down.sql
```

---

## 2. Schema Migration

### Adding a Column

```sql
-- up
ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active';
CREATE INDEX idx_users_status ON users(status);

-- down
DROP INDEX idx_users_status;
ALTER TABLE users DROP COLUMN status;
```

### Adding a Table

```sql
-- up
CREATE TABLE audit_log (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id),
  action      VARCHAR(50) NOT NULL,
  payload     JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- down
DROP TABLE audit_log;
```

### Renaming a Column

```sql
-- up
ALTER TABLE users RENAME COLUMN full_name TO display_name;

-- down
ALTER TABLE users RENAME COLUMN display_name TO full_name;
```

### Data Backfill Pattern

```sql
-- Step 1: Add nullable column
ALTER TABLE orders ADD COLUMN total_cents INTEGER;

-- Step 2: Backfill in batches (avoid long locks)
UPDATE orders SET total_cents = amount * 100 WHERE total_cents IS NULL;

-- Step 3: Add constraint after backfill
ALTER TABLE orders ALTER COLUMN total_cents SET NOT NULL;
```

### Zero-Downtime Pattern (Expand-Contract)

1. **Expand**: Add new column/table alongside old.
2. **Dual-write**: Application writes to both old and new.
3. **Backfill**: Copy existing data to new structure.
4. **Switch reads**: Application reads from new structure.
5. **Contract**: Remove old column/table in a subsequent release.

---

## 3. Data Validation

### Pre-Migration Checks

- **Row counts**: Record table row counts before migration.
- **Schema snapshot**: Dump schema (`pg_dump --schema-only`) for diff comparison.
- **Constraint inventory**: List all FK, unique, and check constraints.

### Post-Migration Checks

```sql
-- Row count comparison (should match pre-migration)
SELECT COUNT(*) FROM users;

-- Null check on new NOT NULL columns
SELECT COUNT(*) FROM users WHERE status IS NULL;

-- Referential integrity
SELECT COUNT(*) FROM orders o
LEFT JOIN users u ON o.user_id = u.id
WHERE u.id IS NULL;

-- Business rule validation
SELECT COUNT(*) FROM orders WHERE total_cents < 0;
```

### Automated Validation Script

```bash
#!/bin/bash
# validate-migration.sh
set -euo pipefail

echo "Running post-migration validation..."

psql "$DATABASE_URL" -f migrations/validate/$1.sql

echo "Validation passed."
```

### Data Quality Gates

| Check | Threshold | Action on Failure |
|-------|-----------|-------------------|
| Row count drift | < 0.1% | Alert, investigate |
| Null violations | 0 | Block deployment |
| FK violations | 0 | Block deployment |
| Duplicate unique keys | 0 | Block deployment |
| Query p95 latency | < 2× baseline | Rollback |

---

## 4. Rollback Procedures

### When to Rollback

- Data validation failures that cannot be fixed in-place.
- Application error rate exceeds 5% post-migration.
- Query performance degrades beyond acceptable thresholds.
- Migration script fails midway.

### Rollback Steps

1. **Stop the application** — Prevent further writes to the new schema.
2. **Run down migration** — Execute the `.down.sql` script.
3. **Verify schema** — Confirm old schema is restored.
4. **Restart application** — Resume normal operations.
5. **Investigate** — Diagnose root cause before re-attempting.

### Rollback Script

```bash
#!/bin/bash
# rollback.sh <migration_timestamp>
set -euo pipefail

MIGRATION=$1

echo "Rolling back migration: $MIGRATION"

psql "$DATABASE_URL" -f "migrations/${MIGRATION}.down.sql"

echo "Rollback complete. Verify application health."
```

### Partial Rollback Safety

- **Never drop data** in a down migration if it can be avoided.
- Use `IF EXISTS` / `IF NOT EXISTS` to make down migrations idempotent.
- For destructive changes, rename instead of drop: `ALTER TABLE foo RENAME TO foo_deprecated_20251001`.

### Backup Strategy

- **Pre-migration snapshot**: Full database backup before any production migration.
- **Point-in-time recovery**: Ensure WAL archiving is enabled.
- **Retention**: Keep pre-migration backups for 7 days minimum.

---

## 5. Testing Strategy

### Unit Tests

- Test migration SQL against a fresh database.
- Verify up/down/up cycles produce identical schema.
- Use a test harness that spins up a disposable database per test.

```python
def test_migration_add_user_status():
    db = create_test_db()
    run_migration(db, "20251001000000_add_user_status.up.sql")
    assert column_exists(db, "users", "status")
    assert get_column_default(db, "users", "status") == "active"

    run_migration(db, "20251001000000_add_user_status.down.sql")
    assert not column_exists(db, "users", "status")
```

### Integration Tests

- Run migrations against a copy of production data (anonymized).
- Verify application works end-to-end post-migration.
- Test rollback path: migrate up, run app, migrate down, run app.

### Staging Validation

1. Restore production snapshot to staging.
2. Run full migration suite.
3. Execute smoke tests (critical user journeys).
4. Run performance benchmarks.
5. Compare query plans before/after.

### CI Pipeline

```yaml
# .github/workflows/migration-test.yml
migration-test:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
  steps:
    - uses: actions/checkout@v4
    - name: Run migrations up
      run: npm run migrate
    - name: Run migrations down
      run: npm run migrate:rollback
    - name: Run migrations up again
      run: npm run migrate
    - name: Run validation suite
      run: npm run test:migration
```

### Load Testing

- Replay production traffic against migrated schema.
- Monitor for lock contention, deadlocks, and slow queries.
- Validate connection pool behavior under load.

---

## Quick Reference

| Task | Command |
|------|---------|
| Run all pending migrations | `npm run migrate` |
| Rollback last migration | `npm run migrate:rollback` |
| Check migration status | `npm run migrate:status` |
| Create new migration | `npm run migrate:create <description>` |
| Validate current schema | `npm run migrate:validate` |
