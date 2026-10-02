# APEX-OS Business Platform — Performance Tuning Guide

> **Version:** 1.0.0  
> **Last Updated:** 2026-10-01  
> **Scope:** Database, API, Cache, Queue, Monitoring

---

## Table of Contents

1. [Overview](#overview)
2. [Database Tuning](#1-database-tuning)
3. [API Tuning](#2-api-tuning)
4. [Cache Tuning](#3-cache-tuning)
5. [Queue Tuning](#4-queue-tuning)
6. [Monitoring & Observability](#5-monitoring--observability)
7. [Quick Reference: Tuning Parameters by Environment](#quick-reference-tuning-parameters-by-environment)

---

## Overview

APEX-OS Business Platform runs on Kubernetes (EKS/AKS/GKE) with a Node.js API layer, PostgreSQL database, Redis cache, background workers, and a full observability stack. This guide provides concrete, production-ready tuning recommendations for each layer.

**Architecture at a glance:**

| Layer | Technology | Default Resources |
|-------|-----------|-------------------|
| API | Node.js (apex-os/api) | 250m–1 CPU, 256Mi–512Mi |
| Web | Nginx (apex-os/web) | 100m–500m CPU, 128Mi–256Mi |
| Worker | Node.js (apex-os/worker) | 200m–1 CPU, 256Mi–512Mi |
| Database | PostgreSQL 15.4 (RDS db.t3.medium) | 250m–1 CPU, 256Mi–512Mi |
| Cache | Redis (single master) | 100m–500m CPU, 128Mi–256Mi |
| Ingress | Nginx Ingress Controller | Rate-limited at 100 RPS |

---

## 1. Database Tuning

### 1.1 PostgreSQL Configuration

#### Connection Pooling

The default PostgreSQL configuration uses direct connections from each API/worker pod. With 2–10 API replicas and 1–5 worker replicas, the database can face connection storms.

**Recommended: PgBouncer as a connection pooler**

```yaml
# Add to Helm values or deploy as a sidecar/standalone service
pgbouncer:
  enabled: true
  image:
    repository: pgbouncer/pgbouncer
    tag: "1.21.0"
  config:
    pgbouncer:
      pool_mode: transaction          # Best for short-lived API queries
      max_client_conn: 1000
      default_pool_size: 20           # Per user/database pair
      reserve_pool_size: 5
      reserve_pool_timeout: 3
      max_db_connections: 100
      server_idle_timeout: 60
      server_lifetime: 3600
      server_connect_timeout: 5
      query_timeout: 0
      query_wait_timeout: 120
      client_idle_timeout: 0
      client_login_timeout: 60
      idle_transaction_timeout: 0
      log_connections: 1
      log_disconnections: 1
      log_pooler_errors: 1
      stats_period: 60
    databases:
      apexos:
        host: apex-os-postgres
        port: 5432
        dbname: apexos
        user: apexos
        password: changeme
```

**Why transaction pooling?** API requests are typically short-lived. Transaction pooling multiplexes client connections across a small set of server connections, reducing PostgreSQL backend process overhead.

#### PostgreSQL Server Parameters

Tune these in the RDS parameter group or via the Helm chart's `postgresql.primary.initdb.scripts`:

| Parameter | Default | Recommended | Rationale |
|-----------|---------|-------------|-----------|
| `shared_buffers` | 128MB | 25% of available RAM (e.g., 128MB for 512Mi limit) | Cache frequently accessed data |
| `effective_cache_size` | 4GB | 75% of total RAM | Planner's assumption of available cache |
| `work_mem` | 4MB | 16–32MB | Per-sort/hash operation memory |
| `maintenance_work_mem` | 64MB | 64–128MB | For VACUUM, CREATE INDEX |
| `max_connections` | 100 | 200 (with PgBouncer) | Accommodate burst traffic |
| `wal_buffers` | -1 (auto) | 16MB | Write-ahead log buffering |
| `checkpoint_completion_target` | 0.5 | 0.9 | Spread checkpoint I/O |
| `random_page_cost` | 4.0 | 1.1 (SSD) | Encourage index scans on SSD |
| `effective_io_concurrency` | 1 | 200 (SSD) | Parallel I/O operations |
| `synchronous_commit` | on | `off` for non-critical, `on` for critical | Balance durability vs. latency |
| `max_worker_processes` | 8 | 8 | Parallel query workers |
| `max_parallel_workers_per_gather` | 2 | 4 | Parallel query execution |
| `max_parallel_workers` | 8 | 8 | Total parallel workers |

#### Indexing Strategy

```sql
-- Run as migration or init script
-- Core lookup indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_tenant_created 
  ON audit_log(tenant_id, created_at DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_business_entities_tenant_status 
  ON business_entities(tenant_id, status) WHERE status = 'active';

-- Partial indexes for soft-deleted records
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_active ON users(id) 
  WHERE deleted_at IS NULL;

-- GIN indexes for JSONB columns
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_config_data_gin ON config_data USING GIN(data);
```

#### Query Performance

```sql
-- Enable pg_stat_statements for query analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Monitor slow queries (run periodically)
SELECT 
  query,
  calls,
  total_exec_time,
  mean_exec_time,
  rows,
  100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Check for missing indexes
SELECT 
  schemaname,
  relname,
  seq_scan,
  idx_scan,
  n_live_tup,
  seq_scan::float / nullif(seq_scan + idx_scan, 0) AS seq_scan_ratio
FROM pg_stat_user_tables
WHERE seq_scan > 0
  AND seq_scan::float / nullif(seq_scan + idx_scan, 0) > 0.1
  AND n_live_tup > 10000
ORDER BY seq_scan DESC;
```

#### Storage & I/O

| Setting | Recommendation |
|---------|---------------|
| Storage type | Provisioned IOPS (io1/io2) for production; GP3 for staging |
| IOPS | 3000+ for production workloads |
| Storage autoscaling | Enable with max 500GB |
| RDS Multi-AZ | Enable for production (already default) |
| Read replicas | Add 1–2 for read-heavy workloads |
| Backup window | Off-peak hours (e.g., 02:00–04:00 UTC) |
| Snapshot retention | 7–35 days based on RPO requirements |

#### Maintenance Schedule

```sql
-- Daily: Analyze tables with high write volume
ANALYZE users;
ANALYZE sessions;
ANALYZE audit_log;

-- Weekly: Vacuum and reindex
VACUUM ANALYZE;
REINDEX INDEX CONCURRENTLY idx_users_email;

-- Monthly: Full vacuum (if autovacuum is insufficient)
VACUUM FULL VERBOSE ANALYZE;
```

---

### 1.2 RDS-Specific Tuning (AWS)

```hcl
# terraform/modules/aws/rds — recommended overrides
resource "aws_db_instance" "apex_os" {
  # ... existing config ...
  
  # Performance Insights
  performance_insights_enabled    = true
  performance_insights_retention_period = 7
  
  # Enhanced Monitoring
  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.rds_monitoring.arn
  
  # Parameter group
  parameter_group_name = aws_db_parameter_group.apex_os.name
  
  # Storage
  storage_type          = "gp3"
  allocated_storage     = 100
  max_allocated_storage = 500
  
  # Backup
  backup_retention_period = 35
  backup_window          = "02:00-04:00"
  
  # Maintenance
  maintenance_window = "Mon:04:00-Mon:06:00"
  
  # Deletion protection for production
  deletion_protection = var.environment == "prod" ? true : false
  
  # IAM authentication
  iam_database_authentication_enabled = true
}
```

```hcl
# Custom parameter group
resource "aws_db_parameter_group" "apex_os" {
  family = "postgres15"
  name   = "${var.name_prefix}-postgres15-params"
  
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/32768}"  # 25% of RAM
  }
  
  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory/4194304}"  # 75% of RAM
  }
  
  parameter {
    name  = "work_mem"
    value = "16384"  # 16MB
  }
  
  parameter {
    name  = "maintenance_work_mem"
    value = "65536"  # 64MB
  }
  
  parameter {
    name  = "random_page_cost"
    value = "1.1"
  }
  
  parameter {
    name  = "effective_io_concurrency"
    value = "200"
  }
  
  parameter {
    name  = "checkpoint_completion_target"
    value = "0.9"
  }
  
  parameter {
    name  = "max_connections"
    value = "200"
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"  # Log queries > 1s
  }
  
  parameter {
    name  = "log_connections"
    value = "1"
  }
  
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  
  parameter {
    name  = "log_lock_waits"
    value = "1"
  }
  
  parameter {
    name  = "deadlock_timeout"
    value = "5s"
  }
}
```

---

## 2. API Tuning

### 2.1 Node.js Runtime Tuning

```yaml
# Helm values — api.env additions
api:
  env:
    # Existing env vars...
    - name: NODE_ENV
      value: production
    - name: LOG_LEVEL
      value: info
    
    # ── Performance tuning ──
    # UV_THREADPOOL_SIZE: Increase libuv thread pool for I/O-heavy workloads
    - name: UV_THREADPOOL_SIZE
      value: "16"
    
    # NODE_OPTIONS: V8 flags for memory and GC tuning
    - name: NODE_OPTIONS
      value: "--max-old-space-size=384 --max-semi-space-size=32"
    
    # Enable HTTP keep-alive
    - name: HTTP_KEEP_ALIVE_TIMEOUT
      value: "65000"
    - name: HTTP_HEADERS_TIMEOUT
      value: "66000"
    
    # Connection pool sizing
    - name: DB_POOL_MIN
      value: "2"
    - name: DB_POOL_MAX
      value: "10"
    - name: DB_POOL_ACQUIRE_TIMEOUT
      value: "30000"
    - name: DB_POOL_IDLE_TIMEOUT
      value: "10000"
    
    # Redis connection pool
    - name: REDIS_POOL_SIZE
      value: "10"
    - name: REDIS_CONNECT_TIMEOUT
      value: "5000"
    
    # Request handling
    - name: REQUEST_TIMEOUT
      value: "30000"
    - name: SHUTDOWN_TIMEOUT
      value: "10000"
    
    # Compression
    - name: COMPRESSION_LEVEL
      value: "6"
    - name: COMPRESSION_THRESHOLD
      value: "1024"
```

### 2.2 Express/Fastify Framework Tuning

```javascript
// api/src/server.js — performance-optimized server setup
const fastify = require('fastify')({
  // Connection handling
  keepAliveTimeout: 65000,
  connectionTimeout: 30000,
  
  // Request body limits
  bodyLimit: 50 * 1024 * 1024, // 50MB (matches ingress proxy-body-size)
  
  // Logging
  logger: {
    level: process.env.LOG_LEVEL || 'info',
    serializers: {
      req(req) {
        return {
          method: req.method,
          url: req.url,
          hostname: req.hostname,
          remoteAddress: req.ip,
          requestId: req.id,
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
          responseTime: res.getResponseTime(),
        };
      },
    },
  },
  
  // Trust proxy for correct client IP behind ingress
  trustProxy: true,
  
  // Disable unnecessary features
  disableRequestLogging: false,
  caseSensitive: false,
});

// Compression
fastify.register(require('@fastify/compress'), {
  level: parseInt(process.env.COMPRESSION_LEVEL || '6'),
  threshold: parseInt(process.env.COMPRESSION_THRESHOLD || '1024'),
  encodings: ['br', 'gzip', 'deflate'],
});

// Rate limiting (defense-in-depth beyond ingress)
fastify.register(require('@fastify/rate-limit'), {
  max: 1000,
  timeWindow: '1 minute',
  keyGenerator: (req) => req.headers['x-api-key'] || req.ip,
  errorResponseBuilder: (req, context) => ({
    statusCode: 429,
    error: 'Too Many Requests',
    message: `Rate limit exceeded. Retry in ${context.after}`,
    retryAfter: context.after,
  }),
});

// Graceful shutdown
fastify.addHook('onClose', async (instance) => {
  await instance.db.pool.end();
  await instance.redis.quit();
  await instance.queue.close();
});

process.on('SIGTERM', () => {
  fastify.close(() => process.exit(0));
  setTimeout(() => process.exit(1), parseInt(process.env.SHUTDOWN_TIMEOUT || '10000'));
});
```

### 2.3 Database Connection Pooling in Application

```javascript
// api/src/db/pool.js
const { Pool } = require('pg');

const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT || '5432'),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  
  // Pool sizing
  min: parseInt(process.env.DB_POOL_MIN || '2'),
  max: parseInt(process.env.DB_POOL_MAX || '10'),
  
  // Timeouts
  acquireTimeoutMillis: parseInt(process.env.DB_POOL_ACQUIRE_TIMEOUT || '30000'),
  idleTimeoutMillis: parseInt(process.env.DB_POOL_IDLE_TIMEOUT || '10000'),
  connectionTimeoutMillis: 5000,
  
  // Keep-alive
  keepAlive: true,
  keepAliveInitialDelayMillis: 10000,
  
  // Statement timeout
  statement_timeout: 30000,
  
  // Application name for monitoring
  application_name: 'apex-os-api',
});

// Pool monitoring
pool.on('connect', () => {
  metrics.increment('db.pool.connections.active');
});

pool.on('remove', () => {
  metrics.decrement('db.pool.connections.active');
});

pool.on('error', (err) => {
  metrics.increment('db.pool.errors');
  logger.error({ err }, 'Unexpected database pool error');
});

module.exports = pool;
```

### 2.4 Kubernetes Resource Tuning

```yaml
# Helm values — api.resources (production)
api:
  resources:
    requests:
      cpu: 500m          # Increased from 250m for stable performance
      memory: 512Mi      # Increased from 256Mi
    limits:
      cpu: "2"           # Increased from 1
      memory: 1Gi        # Increased from 512Mi
  
  autoscaling:
    enabled: true
    minReplicas: 3       # Increased from 2 for HA
    maxReplicas: 15      # Increased from 10 for burst
    targetCPUUtilizationPercentage: 65
    targetMemoryUtilizationPercentage: 75
    behavior:
      scaleUp:
        stabilizationWindowSeconds: 60
        policies:
          - type: Percent
            value: 100
            periodSeconds: 60
      scaleDown:
        stabilizationWindowSeconds: 300
        policies:
          - type: Percent
            value: 10
            periodSeconds: 60
  
  # Pod topology for even distribution
  topologySpreadConstraints:
    - maxSkew: 1
      topologyKey: topology.kubernetes.io/zone
      whenUnsatisfiable: ScheduleAnyway
      labelSelector:
        matchLabels:
          app.kubernetes.io/component: api
  
  affinity:
    podAntiAffinity:
      preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchLabels:
                app.kubernetes.io/component: api
            topologyKey: kubernetes.io/hostname
```

### 2.5 Ingress & Network Tuning

```yaml
# Helm values — ingress annotations
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    
    # ── Performance tuning ──
    # Connection and rate limiting
    nginx.ingress.kubernetes.io/limit-rps: "50"
    nginx.ingress.kubernetes.io/limit-connections: "20"
    nginx.ingress.kubernetes.io/limit-burst: "100"
    
    # Buffering
    nginx.ingress.kubernetes.io/proxy-buffering: "on"
    nginx.ingress.kubernetes.io/proxy-buffer-size: "16k"
    nginx.ingress.kubernetes.io/proxy-buffers-number: "4"
    
    # Keep-alive
    nginx.ingress.kubernetes.io/upstream-keepalive-connections: "100"
    nginx.ingress.kubernetes.io/upstream-keepalive-requests: "1000"
    nginx.ingress.kubernetes.io/upstream-keepalive-timeout: "60"
    
    # CORS preflight caching
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "86400"
    
    # Compression at ingress level
    nginx.ingress.kubernetes.io/server-snippet: |
      gzip on;
      gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
      gzip_min_length 256;
      gzip_comp_level 6;
```

---

## 3. Cache Tuning

### 3.1 Redis Configuration

```yaml
# Helm values — redis
redis:
  enabled: true
  name: apex-os-redis
  auth:
    password: changeme  # Use secrets in production!
  
  master:
    persistence:
      enabled: true
      storageClass: ""
      size: 5Gi
      accessModes:
        - ReadWriteOnce
    
    resources:
      requests:
        cpu: 250m       # Increased from 100m
        memory: 512Mi    # Increased from 128Mi
      limits:
        cpu: "1"         # Increased from 500m
        memory: 1Gi      # Increased from 256Mi
    
    # ── Redis server configuration ──
    # Override redis.conf via command args or ConfigMap
    command: ["redis-server"]
    args:
      - "--maxmemory"
      - "768mb"                          # 75% of 1Gi limit
      - "--maxmemory-policy"
      - "allkeys-lru"                    # Evict least recently used
      - "--maxmemory-samples"
      - "5"                              # Approximate LRU (faster)
      - "--appendonly"
      - "yes"
      - "--appendfsync"
      - "everysec"                       # Balance durability/performance
      - "--save"
      - ""                               # Disable RDB snapshots (use AOF)
      - "--tcp-keepalive"
      - "60"
      - "--timeout"
      - "0"
      - "--tcp-backlog"
      - "511"
      - "--databases"
      - "16"
      - "--activerehashing"
      - "yes"
      - "--lazyfree-lazy-eviction"
      - "yes"
      - "--lazyfree-lazy-expire"
      - "yes"
      - "--lazyfree-lazy-server-del"
      - "yes"
      - "--io-threads"
      - "4"                              # For Redis 6.0+
      - "--io-threads-do-reads"
      - "yes"
  
  replica:
    replicaCount: 1                      # Add a replica for read scaling
    resources:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
  
  # Sentinel for HA (production)
  sentinel:
    enabled: true
    quorum: 2
    downAfterMilliseconds: 5000
    failoverTimeout: 60000
    parallelSyncs: 1
```

### 3.2 Application Cache Strategy

```javascript
// api/src/cache/redis.js
const Redis = require('ioredis');

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  
  // Connection pool
  poolSize: parseInt(process.env.REDIS_POOL_SIZE || '10'),
  
  // Timeouts
  connectTimeout: parseInt(process.env.REDIS_CONNECT_TIMEOUT || '5000'),
  commandTimeout: 5000,
  
  // Retry strategy
  retryStrategy(times) {
    const delay = Math.min(times * 50, 2000);
    return delay;
  },
  
  // Reconnect on error
  reconnectOnError(err) {
    const targetError = 'READONLY';
    return err.message.includes(targetError);
  },
  
  // Keep-alive
  keepAlive: 30000,
  
  // Lazy connect
  lazyConnect: true,
  
  // Key prefix for multi-tenancy
  keyPrefix: 'apexos:',
});

// Cache helpers with TTL and invalidation
const cache = {
  async get(key) {
    const value = await redis.get(key);
    return value ? JSON.parse(value) : null;
  },
  
  async set(key, value, ttlSeconds = 300) {
    return redis.set(key, JSON.stringify(value), 'EX', ttlSeconds);
  },
  
  async getOrSet(key, factory, ttlSeconds = 300) {
    const cached = await this.get(key);
    if (cached !== null) {
      metrics.increment('cache.hit');
      return cached;
    }
    metrics.increment('cache.miss');
    const value = await factory();
    await this.set(key, value, ttlSeconds);
    return value;
  },
  
  async del(key) {
    return redis.del(key);
  },
  
  async delPattern(pattern) {
    const keys = await redis.keys(pattern);
    if (keys.length > 0) {
      return redis.del(...keys);
    }
  },
  
  // Multi-tenant cache key
  tenantKey(tenantId, key) {
    return `t:${tenantId}:${key}`;
  },
};

module.exports = { redis, cache };
```

### 3.3 Cache Invalidation Strategy

```javascript
// api/src/cache/invalidation.js
const { redis } = require('./redis');

const invalidation = {
  // Invalidate user-related caches
  async invalidateUser(userId) {
    await redis.del(`user:${userId}`);
    await redis.del(`user:${userId}:profile`);
    await redis.del(`user:${userId}:permissions`);
    await redis.del(`user:${userId}:sessions`);
  },
  
  // Invalidate tenant-wide caches
  async invalidateTenant(tenantId) {
    const keys = await redis.keys(`t:${tenantId}:*`);
    if (keys.length > 0) {
      const pipeline = redis.pipeline();
      keys.forEach(key => pipeline.del(key));
      await pipeline.exec();
    }
  },
  
  // Invalidate with pub/sub for multi-pod consistency
  async publishInvalidation(channel, message) {
    await redis.publish(`invalidate:${channel}`, JSON.stringify(message));
  },
  
  // Subscribe to invalidation events
  subscribeInvalidations() {
    const subscriber = redis.duplicate();
    subscriber.subscribe('invalidate:users', 'invalidate:tenants', 'invalidate:config');
    subscriber.on('message', (channel, message) => {
      const data = JSON.parse(message);
      // Clear local in-memory caches
      localCache.clear(data.key);
    });
  },
};

module.exports = invalidation;
```

### 3.4 Cache TTL Guidelines

| Data Type | TTL | Invalidation Trigger |
|-----------|-----|---------------------|
| User sessions | 24 hours | Logout, password change |
| User profiles | 5 minutes | Profile update |
| Permissions/RBAC | 10 minutes | Role/permission change |
| Configuration | 1 minute | Config update |
| Business entities | 2 minutes | Entity CRUD operations |
| Audit logs | No cache | Write-only |
| API responses | 30 seconds | Related entity change |
| Static reference data | 1 hour | Manual refresh |
| Rate limit counters | Rolling window | Automatic |

---

## 4. Queue Tuning

### 4.1 Background Worker Configuration

```yaml
# Helm values — worker
worker:
  name: apex-os-worker
  image:
    repository: apex-os/worker
    tag: "1.0.0"
    pullPolicy: IfNotPresent
  
  resources:
    requests:
      cpu: 500m          # Increased from 200m
      memory: 512Mi      # Increased from 256Mi
    limits:
      cpu: "2"           # Increased from 1
      memory: 1Gi        # Increased from 512Mi
  
  autoscaling:
    enabled: true
    minReplicas: 2       # Increased from 1
    maxReplicas: 10      # Increased from 5
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 75
    behavior:
      scaleUp:
        stabilizationWindowSeconds: 30
        policies:
          - type: Percent
            value: 100
            periodSeconds: 30
      scaleDown:
        stabilizationWindowSeconds: 300
        policies:
          - type: Percent
            value: 10
            periodSeconds: 60
  
  env:
    - name: NODE_ENV
      value: production
    - name: DB_HOST
      value: apex-os-postgres
    - name: REDIS_HOST
      value: apex-os-redis
    
    # ── Queue tuning ──
    - name: QUEUE_CONCURRENCY
      value: "10"                    # Parallel job processing per worker
    - name: QUEUE_MAX_ATTEMPTS
      value: "3"                     # Retry failed jobs
    - name: QUEUE_BACKOFF_TYPE
      value: "exponential"           # Exponential backoff for retries
    - name: QUEUE_BACKOFF_DELAY
      value: "5000"                  # Initial delay 5s
    - name: QUEUE_BACKOFF_MAX_DELAY
      value: "300000"                # Max delay 5 minutes
    - name: QUEUE_REMOVE_ON_COMPLETE
      value: "100"                   # Keep last 100 completed jobs
    - name: QUEUE_REMOVE_ON_FAIL
      value: "500"                   # Keep last 500 failed jobs
    - name: QUEUE_STALLED_INTERVAL
      value: "30000"                 # Check for stalled jobs every 30s
    - name: QUEUE_MAX_STALLED_COUNT
      value: "3"                     # Max stalled attempts before fail
    - name: QUEUE_DRAIN_TIMEOUT
      value: "30000"                 # Time to wait for in-flight jobs on shutdown
    - name: QUEUE_PREFETCH
      value: "20"                    # Jobs to prefetch from Redis
```

### 4.2 BullMQ Queue Configuration

```javascript
// worker/src/queues/index.js
const { Queue, QueueEvents, Worker } = require('bullmq');
const IORedis = require('ioredis');

const connection = new IORedis({
  host: process.env.REDIS_HOST,
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  maxRetriesPerRequest: null,
  enableReadyCheck: true,
});

// Queue definitions with tuning
const queues = {
  // High-priority: user-facing operations
  notifications: new Queue('notifications', {
    connection,
    defaultJobOptions: {
      attempts: parseInt(process.env.QUEUE_MAX_ATTEMPTS || '3'),
      backoff: {
        type: process.env.QUEUE_BACKOFF_TYPE || 'exponential',
        delay: parseInt(process.env.QUEUE_BACKOFF_DELAY || '5000'),
      },
      removeOnComplete: parseInt(process.env.QUEUE_REMOVE_ON_COMPLETE || '100'),
      removeOnFail: parseInt(process.env.QUEUE_REMOVE_ON_FAIL || '500'),
    },
  }),
  
  // Medium-priority: business logic
  'business-operations': new Queue('business-operations', {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: 'exponential', delay: 10000 },
      removeOnComplete: 50,
      removeOnFail: 200,
    },
  }),
  
  // Low-priority: batch/reporting jobs
  reports: new Queue('reports', {
    connection,
    defaultJobOptions: {
      attempts: 2,
      backoff: { type: 'fixed', delay: 60000 },
      removeOnComplete: 20,
      removeOnFail: 100,
    },
  }),
  
  // Scheduled jobs
  maintenance: new Queue('maintenance', {
    connection,
    defaultJobOptions: {
      attempts: 1,
      removeOnComplete: 10,
      removeOnFail: 50,
    },
  }),
};

// Worker factory with concurrency control
function createWorker(queueName, processor, options = {}) {
  const worker = new Worker(queueName, processor, {
    connection,
    concurrency: options.concurrency || parseInt(process.env.QUEUE_CONCURRENCY || '10'),
    stalledInterval: parseInt(process.env.QUEUE_STALLED_INTERVAL || '30000'),
    maxStalledCount: parseInt(process.env.QUEUE_MAX_STALLED_COUNT || '3'),
    limiter: options.limiter || undefined,
  });
  
  worker.on('completed', (job) => {
    metrics.increment('queue.job.completed', { queue: queueName });
    logger.info({ jobId: job.id, queue: queueName }, 'Job completed');
  });
  
  worker.on('failed', (job, err) => {
    metrics.increment('queue.job.failed', { queue: queueName });
    logger.error({ jobId: job.id, queue: queueName, err }, 'Job failed');
  });
  
  worker.on('stalled', (jobId) => {
    metrics.increment('queue.job.stalled', { queue: queueName });
    logger.warn({ jobId, queue: queueName }, 'Job stalled');
  });
  
  worker.on('error', (err) => {
    metrics.increment('queue.worker.error', { queue: queueName });
    logger.error({ queue: queueName, err }, 'Worker error');
  });
  
  return worker;
}

// Graceful shutdown
async function shutdownWorkers(workers) {
  const timeout = parseInt(process.env.QUEUE_DRAIN_TIMEOUT || '30000');
  const shutdownPromise = Promise.all(workers.map(w => w.close()));
  const timeoutPromise = new Promise((_, reject) => 
    setTimeout(() => reject(new Error('Worker shutdown timeout')), timeout)
  );
  
  try {
    await Promise.race([shutdownPromise, timeoutPromise]);
    logger.info('All workers shut down gracefully');
  } catch (err) {
    logger.error({ err }, 'Worker shutdown timed out, forcing exit');
    workers.forEach(w => w.forceClose());
  }
}

module.exports = { queues, createWorker, shutdownWorkers, connection };
```

### 4.3 Queue Monitoring & Backpressure

```javascript
// worker/src/queues/monitor.js
const { queues } = require('./index');

const queueMonitor = {
  async getMetrics() {
    const metrics = {};
    
    for (const [name, queue] of Object.entries(queues)) {
      const [waiting, active, completed, failed, delayed, paused] = await Promise.all([
        queue.getWaitingCount(),
        queue.getActiveCount(),
        queue.getCompletedCount(),
        queue.getFailedCount(),
        queue.getDelayedCount(),
        queue.getPausedCount(),
      ]);
      
      metrics[name] = {
        waiting,
        active,
        completed,
        failed,
        delayed,
        paused,
        total: waiting + active + delayed,
      };
      
      // Alert on queue depth
      if (waiting > 1000) {
        metrics.increment('queue.backpressure.warning', { queue: name });
        logger.warn({ queue: name, waiting }, 'Queue backpressure detected');
      }
      
      // Alert on failure rate
      const total = completed + failed;
      if (total > 0 && failed / total > 0.1) {
        metrics.increment('queue.failure_rate.high', { queue: name });
        logger.error({ queue: name, failed, total }, 'High queue failure rate');
      }
    }
    
    return metrics;
  },
  
  // Auto-scale workers based on queue depth
  async evaluateScaling() {
    const metrics = await this.getMetrics();
    
    for (const [name, data] of Object.entries(metrics)) {
      const targetReplicas = Math.min(
        Math.max(2, Math.ceil(data.waiting / 100)), 10
      );
      
      // Patch HPA or deployment replicas
      await k8sAppsV1Api.patchNamespacedDeploymentScale(
        `apex-os-worker-${name}`,
        'apex-os-core',
        { spec: { replicas: targetReplicas } }
      );
    }
  },
};

module.exports = queueMonitor;
```

---

## 5. Monitoring & Observability

### 5.1 Prometheus Configuration

```yaml
# Helm values — monitoring.prometheusRule
monitoring:
  enabled: true
  serviceMonitor:
    enabled: true
    interval: 15s          # Increased from 30s for finer granularity
    scrapeTimeout: 10s
    labels: {}
  
  prometheusRule:
    enabled: true
    labels: {}
    rules:
      # ── API Alerts ──
      - alert: APIHighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API error rate > 5%"
          description: "API error rate is {{ $value | humanizePercentage }} for {{ $labels.service }}"
      
      - alert: APIHighLatency
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API P95 latency > 2s"
          description: "P95 latency for {{ $labels.service }} is {{ $value }}s"
      
      - alert: APIHighLatencyP99
        expr: |
          histogram_quantile(0.99, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service)
          ) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API P99 latency > 5s"
          description: "P99 latency for {{ $labels.service }} is {{ $value }}s"
      
      # ── Database Alerts ──
      - alert: PostgreSQLHighConnections
        expr: |
          pg_stat_activity_count / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connections > 80%"
          description: "PostgreSQL has {{ $value | humanizePercentage }} connections in use"
      
      - alert: PostgreSQLSlowQueries
        expr: |
          rate(pg_stat_statements_total_exec_time[5m]) > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL slow queries detected"
          description: "Multiple queries exceeding 1s execution time"
      
      - alert: PostgreSQLDeadlocks
        expr: |
          rate(pg_stat_database_deadlocks[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL deadlock detected"
          description: "Deadlocks occurring in the database"
      
      - alert: PostgreSQLReplicationLag
        expr: |
          pg_replication_lag > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL replication lag > 30s"
          description: "Replica is {{ $value }}s behind primary"
      
      # ── Redis Alerts ──
      - alert: RedisHighMemory
        expr: |
          redis_memory_used_bytes / redis_memory_max_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage > 85%"
          description: "Redis is using {{ $value | humanizePercentage }} of max memory"
      
      - alert: RedisHighLatency
        expr: |
          redis_commands_duration_seconds_total / redis_commands_total > 0.01
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis command latency > 10ms"
          description: "Average Redis command latency is {{ $value }}s"
      
      - alert: RedisConnectionRefused
        expr: |
          rate(redis_rejected_connections_total[5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis rejecting connections"
          description: "Redis is refusing new connections"
      
      # ── Queue Alerts ──
      - alert: QueueHighBacklog
        expr: |
          bull_queue_waiting > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue backlog > 1000 jobs"
          description: "Queue {{ $labels.queue }} has {{ $value }} waiting jobs"
      
      - alert: QueueHighFailureRate
        expr: |
          rate(bull_queue_failed_total[5m]) / 
          (rate(bull_queue_completed_total[5m]) + rate(bull_queue_failed_total[5m])) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Queue failure rate > 10%"
          description: "Queue {{ $labels.queue }} has {{ $value | humanizePercentage }} failure rate"
      
      - alert: QueueStalledJobs
        expr: |
          bull_queue_stalled > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Stalled jobs detected"
          description: "Queue {{ $labels.queue }} has {{ $value }} stalled jobs"
      
      # ── Kubernetes Alerts --
      - alert: PodHighRestartRate
        expr: |
          rate(kube_pod_container_status_restarts_total[15m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod restarting frequently"
          description: "Pod {{ $labels.pod }} in {{ $labels.namespace }} is restarting"
      
      - alert: PodHighMemoryUsage
        expr: |
          container_memory_working_set_bytes / container_spec_memory_limit_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod memory usage > 85%"
          description: "Pod {{ $labels.pod }} is using {{ $value | humanizePercentage }} of memory limit"
      
      - alert: PodHighCPUUsage
        expr: |
          rate(container_cpu_usage_seconds_total[5m]) / container_spec_cpu_quota > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Pod CPU usage > 80%"
          description: "Pod {{ $labels.pod }} is using {{ $value | humanizePercentage }} of CPU limit"
      
      - alert: HPAAtMax
        expr: |
          kube_horizontalpodautoscaler_status_current_replicas 
          / kube_horizontalpodautoscaler_spec_max_replicas >= 1
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "HPA at maximum replicas"
          description: "HPA {{ $labels.horizontalpodautoscaler }} is at max replicas"
      
      - alert: IngressHighLatency
        expr: |
          histogram_quantile(0.95, 
            sum(rate(nginx_ingress_controller_request_duration_seconds_bucket[5m])) by (le)
          ) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Ingress P95 latency > 5s"
          description: "Ingress P95 latency is {{ $value }}s"
      
      - alert: IngressHighErrorRate
        expr: |
          sum(rate(nginx_ingress_controller_requests{status=~"5.."}[5m])) 
          / sum(rate(nginx_ingress_controller_requests[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Ingress error rate > 5%"
          description: "Ingress error rate is {{ $value | humanizePercentage }}"
```

### 5.2 Grafana Dashboards

```json
{
  "dashboard": {
    "title": "APEX-OS Platform Overview",
    "uid": "apex-os-overview",
    "timezone": "utc",
    "refresh": "30s",
    "panels": [
      {
        "title": "Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(http_requests_total[5m])) by (service)",
          "legendFormat": "{{service }}"
        }],
        "fieldConfig": {
          "defaults": {
            "unit": "reqps",
            "custom": {"drawStyle": "line", "fillOpacity": 10}
          }
        }
      },
      {
        "title": "Response Time (P50/P95/P99)",
        "type": "timeseries",
        "targets": [
          {"expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))", "legendFormat": "P50 {{service}}"},
          {"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))", "legendFormat": "P95 {{service}}"},
          {"expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))", "legendFormat": "P99 {{service}}"}
        ],
        "fieldConfig": {
          "defaults": {"unit": "s", "custom": {"drawStyle": "line"}}
        }
      },
      {
        "title": "Error Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service) / sum(rate(http_requests_total[5m])) by (service)",
          "legendFormat": "{{service}}"
        }],
        "fieldConfig": {
          "defaults": {"unit": "percentunit", "custom": {"drawStyle": "line", "fillOpacity": 20}}
        }
      },
      {
        "title": "Database Connections",
        "type": "timeseries",
        "targets": [
          {"expr": "pg_stat_activity_count", "legendFormat": "Active"},
          {"expr": "pg_settings_max_connections", "legendFormat": "Max"}
        ],
        "fieldConfig": {
          "defaults": {"unit": "short", "custom": {"drawStyle": "line"}}
        }
      },
      {
        "title": "Database Query Performance",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(pg_stat_statements_total_exec_time[5m]) / rate(pg_stat_statements_calls[5m])",
          "legendFormat": "Avg Query Time"
        }],
        "fieldConfig": {
          "defaults": {"unit": "ms", "custom": {"drawStyle": "line"}}
        }
      },
      {
        "title": "Redis Memory Usage",
        "type": "gauge",
        "targets": [{
          "expr": "redis_memory_used_bytes / redis_memory_max_bytes"
        }],
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "steps": [
                {"color": "green", "value": 0},
                {"color": "yellow", "value": 0.7},
                {"color": "red", "value": 0.85}
              ]
            }
          }
        }
      },
      {
        "title": "Redis Operations/sec",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(redis_commands_total[5m])",
          "legendFormat": "{{cmd}}"
        }],
        "fieldConfig": {
          "defaults": {"unit": "ops", "custom": {"drawStyle": "line"}}
        }
      },
      {
        "title": "Queue Depth",
        "type": "timeseries",
        "targets": [
          {"expr": "bull_queue_waiting", "legendFormat": "Waiting {{queue}}"},
          {"expr": "bull_queue_active", "legendFormat": "Active {{queue}}"},
          {"expr": "bull_queue_delayed", "legendFormat": "Delayed {{queue}}"}
        ],
        "fieldConfig": {
          "defaults": {"unit": "short", "custom": {"drawStyle": "line", "fillOpacity": 10}}
        }
      },
      {
        "title": "Pod Resource Usage",
        "type": "timeseries",
        "targets": [
          {"expr": "container_memory_working_set_bytes / 1024 / 1024", "legendFormat": "Memory {{pod}}"},
          {"expr": "rate(container_cpu_usage_seconds_total[5m])", "legendFormat": "CPU {{pod}}"}
        ],
        "fieldConfig": {
          "defaults": {"custom": {"drawStyle": "line", "fillOpacity": 10}}
        }
      },
      {
        "title": "HPA Replicas",
        "type": "timeseries",
        "targets": [
          {"expr": "kube_horizontalpodautoscaler_status_current_replicas", "legendFormat": "Current {{hpa}}"},
          {"expr": "kube_horizontalpodautoscaler_spec_max_replicas", "legendFormat": "Max {{hpa}}"}
        ],
        "fieldConfig": {
          "defaults": {"unit": "short", "custom": {"drawStyle": "line"}}
        }
      }
    ]
  }
}
```

### 5.3 Distributed Tracing with Tempo

```yaml
# Helm values — monitoring.tempo
monitoring:
  enabled: true
  tempo:
    enabled: true
    retention: 168h  # 7 days
    
    # Sampling configuration
    configs:
      trace:
        # Tail-based sampling
        tail_sampling:
          policies:
            # Keep all error traces
            - name: errors
              type: status_code
              status_code: {status_codes: [ERROR]}
            
            # Keep slow traces (> 1s)
            - name: slow-requests
              type: latency
              latency: {threshold_ms: 1000}
            
            # Sample 10% of normal traffic
            - name: probabilistic
              type: probabilistic
              probabilistic: {sampling_percentage: 10}
        
        # Span limits
        max_bytes_per_trace: 1048576  # 1MB
        max_traces_per_user: 10000
    
    # Storage
    storage:
      trace:
        backend: s3
        s3:
          bucket: apex-os-traces
          endpoint: s3.amazonaws.com
          region: us-east-1
```

### 5.4 Log Aggregation with Loki

```yaml
# Helm values — monitoring.loki
monitoring:
  enabled: true
  loki:
    enabled: true
    retention: 720h  # 30 days
    
    # Index and chunk configuration
    config:
      limits_config:
        reject_old_samples: true
        reject_old_samples_max_age: 168h
        max_query_length: 721h
        max_query_series: 500
        per_stream_rate_limit: 3MB
        per_stream_rate_limit_burst: 15MB
      
      schema_config:
        configs:
          - from: 2024-01-01
            store: boltdb-shipper
            object_store: s3
            schema: v12
            index:
              prefix: loki_index_
              period: 24h
      
      compactor:
        working_directory: /var/loki/compactor
        shared_store: s3
        compaction_interval: 10m
        retention_enabled: true
        retention_delete_delay: 2h
        retention_delete_worker_count: 150
    
    # Storage
    storage:
      bucketNames:
        chunks: apex-os-loki-chunks
        ruler: apex-os-loki-ruler
        admin: apex-os-loki-admin
      type: s3
      s3:
        endpoint: s3.amazonaws.com
        region: us-east-1
```

### 5.5 Alertmanager Configuration

```yaml
# Alertmanager config
global:
  smtp_smarthost: smtp.example.com:587
  smtp_from: alerts@apex-os.io
  smtp_auth_username: alerts@apex-os.io
  smtp_auth_password: "${SMTP_PASSWORD}"
  slack_api_url: "${SLACK_WEBHOOK_URL}"
  pagerduty_url: https://events.pagerduty.com/v2/enqueue

route:
  group_by: ['alertname', 'severity', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: default
  
  routes:
    # Critical alerts → PagerDuty + Slack
    - match:
        severity: critical
      receiver: critical
      group_wait: 10s
      repeat_interval: 1h
    
    # Warning alerts → Slack only
    - match:
        severity: warning
      receiver: slack-warnings
      group_wait: 1m
      repeat_interval: 4h
    
    # Database alerts → DBA team
    - match_re:
        alertname: PostgreSQL.*
      receiver: dba-team
      group_wait: 30s
      repeat_interval: 2h

receivers:
  - name: default
    slack_configs:
      - channel: '#apex-os-alerts'
        send_resolved: true
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: critical
    pagerduty_configs:
      - service_key: "${PAGERDUTY_KEY}"
        severity: critical
    slack_configs:
      - channel: '#apex-os-critical'
        send_resolved: true
        title: '🚨 {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: slack-warnings
    slack_configs:
      - channel: '#apex-os-warnings'
        send_resolved: true
        title: '⚠️ {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
  
  - name: dba-team
    email_configs:
      - to: dba@apex-os.io
        send_resolved: true
        subject: 'Database Alert: {{ .GroupLabels.alertname }}'
    slack_configs:
      - channel: '#apex-os-dba'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname', 'service']
```

### 5.6 Custom Metrics (Application-Level)

```javascript
// api/src/metrics/index.js
const promClient = require('prom-client');

// Create a Registry
const register = new promClient.Registry();

// Add default metrics (CPU, memory, etc.)
promClient.collectDefaultMetrics({
  register,
  prefix: 'apex_os_',
  gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5],
});

// Custom metrics
const metrics = {
  // HTTP metrics
  httpRequestDuration: new promClient.Histogram({
    name: 'apex_os_http_request_duration_seconds',
    help: 'Duration of HTTP requests in seconds',
    labelNames: ['method', 'route', 'status_code'],
    buckets: [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    registers: [register],
  }),
  
  httpRequestsTotal: new promClient.Counter({
    name: 'apex_os_http_requests_total',
    help: 'Total number of HTTP requests',
    labelNames: ['method', 'route', 'status_code'],
    registers: [register],
  }),
  
  // Database metrics
  dbQueryDuration: new promClient.Histogram({
    name: 'apex_os_db_query_duration_seconds',
    help: 'Duration of database queries in seconds',
    labelNames: ['operation', 'table'],
    buckets: [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5],
    registers: [register],
  }),
  
  dbPoolActive: new promClient.Gauge({
    name: 'apex_os_db_pool_active_connections',
    help: 'Number of active database pool connections',
    registers: [register],
  }),
  
  dbPoolIdle: new promClient.Gauge({
    name: 'apex_os_db_pool_idle_connections',
    help: 'Number of idle database pool connections',
    registers: [register],
  }),
  
  // Cache metrics
  cacheHits: new promClient.Counter({
    name: 'apex_os_cache_hits_total',
    help: 'Total number of cache hits',
    labelNames: ['cache_type'],
    registers: [register],
  }),
  
  cacheMisses: new promClient.Counter({
    name: 'apex_os_cache_misses_total',
    help: 'Total number of cache misses',
    labelNames: ['cache_type'],
    registers: [register],
  }),
  
  cacheEvictions: new promClient.Counter({
    name: 'apex_os_cache_evictions_total',
    help: 'Total number of cache evictions',
    labelNames: ['cache_type'],
    registers: [register],
  }),
  
  // Queue metrics
  queueJobsWaiting: new promClient.Gauge({
    name: 'apex_os_queue_jobs_waiting',
    help: 'Number of jobs waiting in queue',
    labelNames: ['queue'],
    registers: [register],
  }),
  
  queueJobsActive: new promClient.Gauge({
    name: 'apex_os_queue_jobs_active',
    help: 'Number of jobs being processed',
    labelNames: ['queue'],
    registers: [register],
  }),
  
  queueJobDuration: new promClient.Histogram({
    name: 'apex_os_queue_job_duration_seconds',
    help: 'Duration of job processing in seconds',
    labelNames: ['queue', 'status'],
    buckets: [0.1, 0.5, 1, 5, 10, 30, 60, 300],
    registers: [register],
  }),
  
  // Business metrics
  activeUsers: new promClient.Gauge({
    name: 'apex_os_active_users',
    help: 'Number of active users',
    labelNames: ['tenant'],
    registers: [register],
  }),
  
  apiCallsTotal: new promClient.Counter({
    name: 'apex_os_api_calls_total',
    help: 'Total number of API calls by endpoint',
    labelNames: ['endpoint', 'method', 'status'],
    registers: [register],
  }),
};

// Metrics endpoint for Prometheus scraping
async function metricsHandler(req, res) {
  res.set('Content-Type', register.contentType);
  res.end(await register.metrics());
}

module.exports = { metrics, metricsHandler, register };
```

---

## Quick Reference: Tuning Parameters by Environment

### Development

| Component | Parameter | Value |
|-----------|-----------|-------|
| API | Replicas | 1 |
| API | CPU request/limit | 100m / 500m |
| API | Memory request/limit | 128Mi / 256Mi |
| Worker | Replicas | 1 |
| Worker | CPU request/limit | 100m / 500m |
| Worker | Memory request/limit | 128Mi / 256Mi |
| PostgreSQL | Instance | db.t3.micro |
| PostgreSQL | Storage | 20GB GP2 |
| Redis | Memory | 128Mi |
| Redis | Persistence | Disabled |
| Monitoring | Retention | 7 days |
| Monitoring | Scrape interval | 60s |

### Staging

| Component | Parameter | Value |
|-----------|-----------|-------|
| API | Replicas | 2 |
| API | CPU request/limit | 250m / 1 |
| API | Memory request/limit | 256Mi / 512Mi |
| Worker | Replicas | 1 |
| Worker | CPU request/limit | 200m / 1 |
| Worker | Memory request/limit | 256Mi / 512Mi |
| PostgreSQL | Instance | db.t3.medium |
| PostgreSQL | Storage | 50GB GP3 |
| Redis | Memory | 256Mi |
| Redis | Persistence | Enabled (2Gi) |
| Monitoring | Retention | 14 days |
| Monitoring | Scrape interval | 30s |

### Production

| Component | Parameter | Value |
|-----------|-----------|-------|
| API | Replicas | 3–15 (HPA) |
| API | CPU request/limit | 500m / 2 |
| API | Memory request/limit | 512Mi / 1Gi |
| Worker | Replicas | 2–10 (HPA) |
| Worker | CPU request/limit | 500m / 2 |
| Worker | Memory request/limit | 512Mi / 1Gi |
| PostgreSQL | Instance | db.r6g.large+ |
| PostgreSQL | Storage | 100GB+ GP3 (3000 IOPS) |
| PostgreSQL | Multi-AZ | Enabled |
| PostgreSQL | Read replicas | 1–2 |
| Redis | Memory | 1Gi+ |
| Redis | Replicas | 1+ |
| Redis | Sentinel | Enabled |
| Monitoring | Retention | 30 days |
| Monitoring | Scrape interval | 15s |
| Tracing | Sampling | 10% + errors + slow |
| Logs | Retention | 30 days |

---

## Appendix: Performance Checklist

### Pre-Deployment

- [ ] PgBouncer configured with transaction pooling
- [ ] PostgreSQL parameters tuned for workload
- [ ] Indexes created for common query patterns
- [ ] Redis maxmemory-policy set to `allkeys-lru`
- [ ] Redis persistence configured (AOF everysec)
- [ ] Node.js UV_THREADPOOL_SIZE increased
- [ ] Node.js heap size configured via NODE_OPTIONS
- [ ] HTTP keep-alive enabled
- [ ] Compression enabled (gzip/brotli)
- [ ] Rate limiting configured at ingress and application
- [ ] Graceful shutdown handlers implemented
- [ ] Database connection pool sized correctly
- [ ] Redis connection pool sized correctly
- [ ] Queue concurrency configured
- [ ] Queue retry/backoff policies set
- [ ] HPA configured with appropriate thresholds
- [ ] Pod disruption budgets enabled
- [ ] Topology spread constraints configured
- [ ] Resource requests/limits set appropriately

### Monitoring Setup

- [ ] Prometheus scraping all services
- [ ] Grafana dashboards imported
- [ ] Alert rules configured
- [ ] Alertmanager routes configured
- [ ] PagerDuty/Slack integration tested
- [ ] Distributed tracing enabled (Tempo)
- [ ] Log aggregation configured (Loki)
- [ ] Custom application metrics exposed
- [ ] SLOs defined and tracked
- [ ] Error budgets configured

### Load Testing

- [ ] Baseline performance established
- [ ] Load test with expected traffic (2x expected peak)
- [ ] Stress test to find breaking point
- [ ] Soak test for memory leaks (24h+)
- [ ] Failover testing (DB, Redis, pods)
- [ ] Auto-scaling validation
- [ ] Circuit breaker testing
- [ ] Queue backpressure testing

---

*For questions or contributions, contact the APEX-OS Platform Team.*
