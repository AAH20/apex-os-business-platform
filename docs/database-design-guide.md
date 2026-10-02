# Database Design Guide

## 1. Database Design Principles

### 1.1 Normalization
- **Target 3NF** as the default; denormalize only when read performance demands it.
- Eliminate repeating groups (1NF), partial dependencies (2NF), transitive dependencies (3NF).
- Every table must have a primary key; prefer surrogate keys (UUID/bigint) over natural keys.

### 1.2 Data Integrity
- Enforce constraints at the database level: `NOT NULL`, `UNIQUE`, `CHECK`, `FOREIGN KEY`.
- Use `ON DELETE`/`ON UPDATE` actions deliberately (`CASCADE`, `RESTRICT`, `SET NULL`).
- Prefer database-enforced integrity over application-level checks.

### 1.3 Consistency & Transactions
- Keep transactions short; avoid long-running transactions that hold locks.
- Use appropriate isolation levels (`READ COMMITTED` default; `SERIALIZABLE` only when necessary).
- Design for idempotency: use unique constraints and upserts to make retries safe.

### 1.4 Naming Conventions
- Tables: plural snake_case (`users`, `order_items`).
- Columns: snake_case (`created_at`, `is_active`).
- Indexes: `idx_<table>_<columns>` (`idx_orders_user_id_created_at`).
- Foreign keys: `fk_<table>_<referenced_table>`.

### 1.5 Audit & Soft Delete
- Include `created_at`, `updated_at` (timestamptz, default `now()`) on every table.
- Use `deleted_at` (nullable timestamptz) for soft deletes; add partial indexes excluding soft-deleted rows.
- Log sensitive changes in an audit table (`audit_log`) with actor, action, timestamp, and diff.

---

## 2. Schema Design Patterns

### 2.1 Core Entity Tables
```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMPTZ
);
```

### 2.2 One-to-Many
- Foreign key on the "many" side referencing the "one" side.
- Index the foreign key column.

### 2.3 Many-to-Many
- Use a junction/association table with composite primary key.
```sql
CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);
```

### 2.4 Polymorphic Associations (Avoid When Possible)
- Prefer separate foreign keys with `CHECK` constraints over a single `type`/`id` pair.
- If unavoidable, add a composite index on `(target_type, target_id)`.

### 2.5 JSONB for Semi-Structured Data
- Use `JSONB` (not `JSON`) for flexible payloads; add GIN indexes for containment queries.
- Extract frequently queried fields into generated columns or separate columns.

### 2.6 Enum Types
- Use PostgreSQL `ENUM` types for closed sets; use `CHECK` constraints for open sets that change often.
- Store enum values as text in application code; map at the ORM layer.

### 2.7 Temporal / Versioned Data
- Use `tstzrange` with exclusion constraints for validity periods.
- Store current state in a hot table; archive to a history table via trigger or application logic.

---

## 3. Indexing Strategies

### 3.1 When to Index
- Index columns used in `WHERE`, `JOIN`, `ORDER BY`, and `GROUP BY`.
- Index foreign keys (PostgreSQL does not auto-index FK columns).
- Index columns with high selectivity; skip low-cardinality columns unless combined.

### 3.2 Index Types
| Type | Use Case |
|------|----------|
| B-tree (default) | Equality and range queries |
| GIN | JSONB, array, full-text search |
| GiST | Geospatial, range types |
| BRIN | Very large, naturally ordered tables (time-series) |
| Hash | Equality-only (rarely needed) |

### 3.3 Composite Indexes
- Order columns by selectivity: equality columns first, then range columns.
- A composite index on `(a, b)` serves queries on `a` alone but not `b` alone.
- Avoid redundant indexes: `(a, b)` makes `(a)` redundant.

### 3.4 Partial Indexes
```sql
CREATE INDEX idx_orders_pending ON orders (created_at)
WHERE status = 'pending';
```
- Use when queries consistently filter on a predicate.

### 3.5 Covering Indexes
- Use `INCLUDE` to add non-key columns and enable index-only scans.
```sql
CREATE INDEX idx_users_email ON users (email) INCLUDE (name, created_at);
```

### 3.6 Index Maintenance
- Monitor index usage: `pg_stat_user_indexes.idx_scan`.
- Remove unused indexes; they slow writes and consume space.
- Use `CREATE INDEX CONCURRENTLY` to avoid locking in production.
- Reindex periodically on tables with heavy write churn.

---

## 4. Partitioning Strategies

### 4.1 When to Partition
- Tables exceeding ~100M rows or growing beyond manageable backup/restore windows.
- Time-series data (events, logs, metrics) with natural time-based access patterns.
- Multi-tenant systems where tenant_id provides clean data isolation.

### 4.2 Partition Types
| Type | Best For |
|------|----------|
| RANGE | Time-series, sequential IDs |
| LIST | Discrete categories (region, tenant) |
| HASH | Even distribution when no natural range exists |

### 4.3 Time-Based Partitioning (Example)
```sql
CREATE TABLE events (
    id          BIGSERIAL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload     JSONB
) PARTITION BY RANGE (occurred_at);

CREATE TABLE events_2026_q4 PARTITION OF events
    FOR VALUES FROM ('2026-10-01') TO ('2027-01-01');
```
- Create future partitions ahead of time (cron or application logic).
- Drop or archive old partitions instead of `DELETE` for performance.

### 4.4 Partition Key Selection
- Choose a column that appears in most `WHERE` clauses.
- The partition key must be part of the primary key.
- Avoid columns that change frequently (requires row movement).

### 4.5 Multi-Tenant Partitioning
- Partition by `tenant_id` (LIST or HASH) for hard isolation.
- Combine with sub-partitioning by time for large tenants.
- Use `ROW LEVEL SECURITY` as an alternative for smaller scale.

### 4.6 Partition Pruning
- Ensure queries include the partition key to enable pruning.
- Verify with `EXPLAIN` that only relevant partitions are scanned.
- Avoid functions on the partition key in `WHERE` clauses (prevents pruning).

---

## 5. Migration Strategies

### 5.1 Tooling
- Use a migration tool (Alembic, Flyway, golang-migrate, or Django migrations).
- Store migrations in version control alongside application code.
- Each migration file must be immutable once merged; never edit applied migrations.

### 5.2 Migration Best Practices
- **Expand-Contract pattern**: add new schema first, migrate data, then remove old schema in a later release.
- Make migrations idempotent where possible (`IF NOT EXISTS`, `IF EXISTS`).
- Keep migrations small and focused; one logical change per migration.
- Test migrations against a production-sized dataset in staging.

### 5.3 Zero-Downtime Migrations
1. Add new column (nullable or with default) — backward compatible.
2. Deploy code that writes to both old and new columns.
3. Backfill data in batches (avoid long transactions).
4. Add constraints/indexes `CONCURRENTLY`.
5. Deploy code that reads from new column.
6. Remove old column in a subsequent release.

### 5.4 Backfilling Data
```sql
-- Batch backfill example
UPDATE orders SET new_col = old_col
WHERE id BETWEEN 1 AND 10000 AND new_col IS NULL;
```
- Process in chunks (1k–10k rows) to avoid lock contention and replication lag.
- Use `pg_sleep()` or application-level throttling between batches.
- Track progress in a control table for resumability.

### 5.5 Rollback Plan
- Every migration should have a corresponding down migration.
- Test down migrations in staging.
- For destructive changes (drop column, drop table), ensure a backup exists and a rollback path is documented.

### 5.6 Schema Versioning
- Track applied migrations in a schema history table (`schema_migrations`).
- Use a single source of truth for schema: migrations, not manual DDL.
- Generate schema diffs in CI to catch drift between migrations and desired state.

### 5.7 Monitoring & Validation
- Run `EXPLAIN ANALYZE` on critical queries before and after migrations.
- Monitor replication lag during large backfills.
- Validate row counts and checksums after data migrations.
- Set statement and lock timeouts on migration sessions.

---

## Quick Reference Checklist

- [ ] Every table has a primary key
- [ ] `created_at` / `updated_at` on all tables
- [ ] Foreign keys indexed
- [ ] Constraints enforce data integrity
- [ ] No N+1 query patterns in ORM config
- [ ] Composite indexes ordered correctly
- [ ] Partial indexes for common filters
- [ ] Partitions created ahead of time
- [ ] Migrations are idempotent and reversible
- [ ] Backfills run in batches
- [ ] Schema drift checked in CI
