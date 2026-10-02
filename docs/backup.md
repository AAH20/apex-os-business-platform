# APEX-OS Backup Architecture

## 1. Backup Architecture

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TB
    subgraph Sources
        DB[(PostgreSQL)]
        FS[File Storage]
        CFG[Config Files]
        RED[(Redis Cache)]
    end

    subgraph Backup Engine
        SCHED[Scheduler]
        ENC[AES-256 Encryption]
        COMP[Gzip Compression]
        CHK[Checksum Verification]
    end

    subgraph Storage Tiers
        HOT[Hot Storage - Local SSD]
        WARM[Warm Storage - S3 Standard]
        COLD[Cold Storage - S3 Glacier]
    end

    subgraph Monitoring
        ALERT[Alerting]
        AUDIT[Audit Logs]
    end

    DB --> SCHED
    FS --> SCHED
    CFG --> SCHED
    RED --> SCHED
    SCHED --> ENC --> COMP --> CHK
    CHK --> HOT
    CHK --> WARM
    CHK --> COLD
    HOT --> ALERT
    WARM --> ALERT
    COLD --> ALERT
    ALERT --> AUDIT
```

## 2. Full Backup

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant S as Scheduler
    participant B as Backup Engine
    participant D as Database
    participant F as File Storage
    participant T as Target Storage

    S->>B: Trigger Full Backup
    B->>D: pg_dump --format=custom
    B->>F: rsync -a --delete
    B->>B: Compress + Encrypt
    B->>T: Upload snapshot
    T-->>B: Verify checksum
    B-->>S: Backup complete
```

**Schedule:** Weekly (Sunday 02:00 UTC)
**Retention:** 4 weeks
**Scope:** All databases, all files, all configs

## 3. Incremental Backup

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant S as Scheduler
    participant B as Backup Engine
    participant D as Database
    participant F as File Storage
    participant T as Target Storage

    S->>B: Trigger Incremental
    B->>D: WAL archive since last LSN
    B->>F: rsync --link-dest=last_backup
    B->>B: Compress + Encrypt
    B->>T: Upload delta
    T-->>B: Verify checksum
    B-->>S: Incremental complete
```

**Schedule:** Every 6 hours
**Retention:** 7 days
**Scope:** Changes since last backup (any type)

## 4. Differential Backup

```mermaid
%%{init: {'theme': 'dark'}}%%
sequenceDiagram
    participant S as Scheduler
    participant B as Backup Engine
    participant D as Database
    participant F as File Storage
    participant T as Target Storage

    S->>B: Trigger Differential
    B->>D: pg_dump --format=custom --data-only
    B->>F: rsync --compare-dest=last_full
    B->>B: Compress + Encrypt
    B->>T: Upload delta
    T-->>B: Verify checksum
    B-->>S: Differential complete
```

**Schedule:** Daily (02:00 UTC)
**Retention:** 14 days
**Scope:** Changes since last full backup

## 5. Restoration

```mermaid
%%{init: {'theme': 'dark'}}%%
flowchart LR
    subgraph Restore Process
        A[Identify Backup Point] --> B{Backup Type?}
        B -->|Full| C[Restore Full Snapshot]
        B -->|Incremental| D[Restore Full + Apply WAL]
        B -->|Differential| E[Restore Full + Apply Diff]
        C --> F[Verify Integrity]
        D --> F
        E --> F
        F --> G{Tests Pass?}
        G -->|Yes| H[Switch Traffic]
        G -->|No| I[Rollback & Alert]
    end
```

### Restore Procedures

**Full Restore:**
```bash
# Stop services
apexctl stop --all

# Restore database
pg_restore --clean --if-exists --dbname=apex_os /backups/full/latest.dump

# Restore files
rsync -a --delete /backups/full/latest/files/ /var/lib/apex-os/

# Restore configs
cp /backups/full/latest/configs/* /etc/apex-os/

# Start services
apexctl start --all
```

**Point-in-Time Restore:**
```bash
# Restore base full backup
pg_restore --clean --if-exists --dbname=apex_os /backups/full/latest.dump

# Apply WAL archives up to target time
pg_waldump --timeline=1 --start=0/1000000 --end=0/2000000 | psql apex_os
```

### RTO / RPO Targets

| Metric | Target |
|--------|--------|
| RPO (Data Loss) | ≤ 15 minutes |
| RTO (Downtime) | ≤ 1 hour |
| Full Restore | ≤ 30 minutes |
| PIT Restore | ≤ 45 minutes |
