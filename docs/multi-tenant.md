# APEX-OS Business Platform — Multi-Tenant Architecture

> **Version:** 1.0.0  
> **Last Updated:** 2026-10-01  
> **Status:** Design Specification  
> **Platform:** APEX-OS Business Platform (AWS · Azure · GCP · Kubernetes)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Tenant Isolation](#2-tenant-isolation)
3. [Tenant Provisioning](#3-tenant-provisioning)
4. [Tenant Billing](#4-tenant-billing)
5. [Tenant Monitoring](#5-tenant-monitoring)
6. [Tenant Security](#6-tenant-security)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Deployment Topology](#8-deployment-topology)
9. [Operational Runbooks](#9-operational-runbooks)

---

## 1. Architecture Overview

### 1.1 Design Goals

| Goal | Target |
|------|--------|
| **Isolation** | Zero cross-tenant data leakage; defense-in-depth at every layer |
| **Scalability** | Support 10,000+ tenants without architectural changes |
| **Operational Efficiency** | Shared infrastructure with tenant-aware controls |
| **Compliance** | SOC 2 Type II, GDPR, HIPAA-ready controls |
| **Cost Efficiency** | Resource pooling with per-tenant metering |

### 1.2 Isolation Model Selection

APEX-OS uses a **hybrid isolation model** — the default is **shared database with row-level security (RLS)**, with the option to upgrade individual tenants to **schema-per-tenant** or **database-per-tenant** tiers.

```
┌─────────────────────────────────────────────────────────────────┐
│                    APEX-OS Business Platform                     │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Tenant A │  │ Tenant B │  │ Tenant C │  │ Tenant D │  ...   │
│  │  (Free)  │  │ (Pro)    │  │(Enterprise)│ │(Dedicated)│      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │              │              │              │              │
│  ┌────▼──────────────▼──────────────▼────┐  ┌─────▼─────┐       │
│  │     Shared PostgreSQL (RLS)           │  │ Dedicated  │       │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │  │ Database  │       │
│  │  │tenant_a │ │tenant_b │ │tenant_c │ │  │  (tenant_d)│      │
│  │  │ schema  │ │ schema  │ │ schema  │ │  └───────────┘       │
│  │  └─────────┘ └─────────┘ └─────────┘ │                        │
│  └───────────────────────────────────────┘                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Kubernetes (EKS / AKS / GKE)             │       │
│  │  Namespace-per-tenant OR shared with NetworkPolicies  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Object Storage (S3 / Azure Blob / GCS)   │       │
│  │              Bucket-per-tenant with IAM policies      │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Tenant Tiers

| Tier | Isolation Level | Target Use Case | Monthly Cost |
|------|----------------|-----------------|--------------|
| **Free** | Shared DB (RLS), shared namespace | Trial, small teams | $0 |
| **Pro** | Shared DB (RLS), dedicated namespace | SMB, startups | $49–$199 |
| **Enterprise** | Schema-per-tenant, dedicated namespace | Mid-market, regulated | $499–$1,999 |
| **Dedicated** | Database-per-tenant, dedicated cluster | Large enterprise, gov | $5,000+ |

---

## 2. Tenant Isolation

### 2.1 Database Isolation

#### 2.1.1 Shared Database with Row-Level Security (Default)

The default isolation mechanism uses PostgreSQL Row-Level Security (RLS) policies enforced at the database engine level.

**Schema Design:**

```sql
-- Core tenant table
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(63) UNIQUE NOT NULL,
    tier            VARCHAR(32) NOT NULL DEFAULT 'free',
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    isolation_mode  VARCHAR(32) NOT NULL DEFAULT 'rls',  -- rls | schema | database
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}',
    billing_email   VARCHAR(255),
    encryption_key_id VARCHAR(255)  -- KMS key reference
);

-- Every tenant-scoped table includes tenant_id
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- RLS policy: tenants can only see their own rows
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON projects
    USING (tenant_id = current_setting('app.current_tenant')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant')::UUID);
```

**Connection Pooling with Tenant Context:**

```python
# Connection pooler (PgBouncer) with tenant-aware routing
# Each connection sets the tenant context before serving requests

class TenantAwareConnection:
    """Wraps a database connection with tenant context."""
    
    def __init__(self, pool, tenant_id: str):
        self._pool = pool
        self._tenant_id = tenant_id
        self._conn = None
    
    async def __aenter__(self):
        self._conn = await self._pool.acquire()
        # Set tenant context for RLS policies
        await self._conn.execute(
            "SELECT set_config('app.current_tenant', $1, false)",
            self._tenant_id
        )
        # Set application name for monitoring
        await self._conn.execute(
            "SELECT set_config('application_name', $1, false)",
            f"tenant:{self._tenant_id}"
        )
        return self._conn
    
    async def __aexit__(self, *args):
        # Reset tenant context before returning to pool
        if self._conn:
            await self._conn.execute(
                "SELECT set_config('app.current_tenant', '', false)"
            )
            await self._pool.release(self._conn)
```

#### 2.1.2 Schema-Per-Tenant (Enterprise Tier)

Each tenant gets a dedicated PostgreSQL schema within the shared database instance.

```sql
-- Create isolated schema for tenant
CREATE SCHEMA tenant_acme_corp;

-- Clone base tables into tenant schema
CREATE TABLE tenant_acme_corp.projects (LIKE public.projects INCLUDING ALL);
CREATE TABLE tenant_acme_corp.users (LIKE public.users INCLUDING ALL);
CREATE TABLE tenant_acme_corp.audit_log (LIKE public.audit_log INCLUDING ALL);

-- Tenant-specific migrations
CREATE OR REPLACE FUNCTION tenant_acme_corp.migrate() RETURNS void AS $$
BEGIN
    -- Tenant-specific schema changes
    ALTER TABLE tenant_acme_corp.projects ADD COLUMN custom_field_1 TEXT;
END;
$$ LANGUAGE plpgsql;
```

**Schema Routing:**

```python
class SchemaTenantRouter:
    """Routes queries to the correct tenant schema."""
    
    SCHEMA_MAP = {
        "acme-corp": "tenant_acme_corp",
        "globex": "tenant_globex",
        "initech": "tenant_initech",
    }
    
    def get_schema(self, tenant_slug: str) -> str:
        return self.SCHEMA_MAP.get(tenant_slug, f"tenant_{tenant_slug}")
    
    def get_connection(self, tenant_slug: str):
        schema = self.get_schema(tenant_slug)
        conn = self._pool.get_connection()
        conn.execute(f"SET search_path TO {schema}, public")
        return conn
```

#### 2.1.3 Database-Per-Tenant (Dedicated Tier)

Each tenant gets a dedicated RDS instance or database within a shared cluster.

```hcl
# Terraform: Dedicated RDS instance for a tenant
resource "aws_db_instance" "tenant_dedicated" {
  identifier           = "apex-os-tenant-${var.tenant_id}"
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = var.tier == "dedicated" ? "db.r6g.xlarge" : "db.t3.medium"
  allocated_storage    = var.tier == "dedicated" ? 500 : 100
  
  # Dedicated VPC for the tenant
  db_subnet_group_name = aws_db_subnet_group.tenant_dedicated.name
  vpc_security_group_ids = [aws_security_group.tenant_dedicated.id]
  
  # Encryption
  storage_encrypted    = true
  kms_key_id          = var.tenant_kms_key_id
  
  # Backup
  backup_retention_period = 35
  deletion_protection     = true
  
  tags = {
    TenantId   = var.tenant_id
    Tier       = "dedicated"
    ManagedBy  = "terraform"
  }
}
```

### 2.2 Application-Layer Isolation

#### 2.2.1 Tenant Context Propagation

```python
from contextvars import ContextVar
from fastapi import Request, HTTPException

# Tenant context stored in request-scoped context variable
tenant_context: ContextVar[str] = ContextVar("tenant_id", default=None)

class TenantMiddleware:
    """Extracts and validates tenant from incoming requests."""
    
    async def __call__(self, request: Request, call_next):
        # Priority: custom header > subdomain > JWT claim > path param
        tenant_id = (
            request.headers.get("X-Tenant-ID")
            or self._extract_from_subdomain(request)
            or self._extract_from_jwt(request)
            or request.path_params.get("tenant_id")
        )
        
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant identifier required")
        
        # Validate tenant exists and is active
        tenant = await self.tenant_service.get(tenant_id)
        if not tenant or tenant.status != "active":
            raise HTTPException(status_code=403, detail="Invalid or inactive tenant")
        
        # Set context for downstream use
        token = tenant_context.set(tenant_id)
        try:
            response = await call_next(request)
            # Add tenant ID to response headers for debugging
            response.headers["X-Tenant-ID"] = tenant_id
            return response
        finally:
            tenant_context.reset(token)
    
    def _extract_from_subdomain(self, request: Request) -> str | None:
        host = request.headers.get("host", "")
        # tenant-a.example.com -> tenant-a
        parts = host.split(".")
        if len(parts) >= 3:
            return parts[0]
        return None
```

#### 2.2.2 Tenant-Aware ORM (SQLAlchemy)

```python
from sqlalchemy import event
from sqlalchemy.orm import Session

class TenantAwareQuery:
    """Automatically filters queries by current tenant."""
    
    @staticmethod
    def apply_tenant_filter(query, model_class):
        tenant_id = tenant_context.get()
        if tenant_id and hasattr(model_class, "tenant_id"):
            return query.filter(model_class.tenant_id == tenant_id)
        return query

# SQLAlchemy event listener to auto-apply tenant filter
@event.listens_for(Session, "do_orm_execute")
def _add_tenant_filter(execute_state):
    if execute_state.is_select:
        tenant_id = tenant_context.get()
        if tenant_id:
            for desc in execute_state.statement.column_descriptions:
                entity = desc.get("entity")
                if entity and hasattr(entity, "tenant_id"):
                    execute_state.statement = execute_state.statement.where(
                        entity.tenant_id == tenant_id
                    )
```

### 2.3 Kubernetes Isolation

#### 2.3.1 Namespace-Per-Tenant (Enterprise+)

```yaml
# Namespace with resource quotas and network policies
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-acme-corp
  labels:
    tenant-id: "acme-corp-uuid"
    tier: "enterprise"
    apex-os.io/managed-by: "tenant-controller"
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: tenant-acme-quota
  namespace: tenant-acme-corp
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
    services: "10"
    persistentvolumeclaims: "10"
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: tenant-acme-isolation
  namespace: tenant-acme-corp
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: apex-os-ingress
        - podSelector:
            matchLabels:
              apex-os.io/tenant-acme-corp: "true"
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: apex-os-core
    - to:
        - namespaceSelector:
            matchLabels:
              name: tenant-acme-corp
```

#### 2.3.2 Shared Namespace with Pod-Level Isolation (Free/Pro)

```yaml
# Shared namespace with tenant-labeled pods
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: apex-os-workloads
spec:
  template:
    metadata:
      labels:
        app: api-server
        apex-os.io/tenant: "acme-corp"  # Tenant label for filtering
    spec:
      serviceAccountName: tenant-acme-corp-sa  # Dedicated SA per tenant
      containers:
        - name: api
          image: apex-os/api:latest
          env:
            - name: TENANT_ID
              value: "acme-corp-uuid"
            - name: TENANT_TIER
              value: "pro"
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

### 2.4 Storage Isolation

#### 2.4.1 Object Storage (S3 / Azure Blob / GCS)

```hcl
# S3 bucket per tenant with IAM policies
resource "aws_s3_bucket" "tenant_data" {
  bucket = "apex-os-tenant-${var.tenant_id}-data"
  
  tags = {
    TenantId  = var.tenant_id
    Tier      = var.tier
  }
}

resource "aws_s3_bucket_policy" "tenant_isolation" {
  bucket = aws_s3_bucket.tenant_data.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "TenantOnlyAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/tenant-${var.tenant_id}-role"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.tenant_data.arn,
          "${aws_s3_bucket.tenant_data.arn}/*"
        ]
      },
      {
        Sid    = "DenyUnencryptedUploads"
        Effect = "Deny"
        Principal = "*"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.tenant_data.arn}/*"
        Condition = {
          StringNotEquals = {
            "s3:x-amz-server-side-encryption" = "aws:kms"
          }
        }
      }
    ]
  })
}

# Bucket-level encryption with tenant-specific KMS key
resource "aws_s3_bucket_server_side_encryption_configuration" "tenant_encryption" {
  bucket = aws_s3_bucket.tenant_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.tenant_kms_key_id
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}
```

#### 2.4.2 Storage Path Convention

```
s3://apex-os-tenant-{tenant_id}-data/
├── uploads/          # User uploads
├── exports/          # Data exports
├── backups/          # Automated backups
├── logs/             # Application logs
└── temp/             # Temporary files (auto-expired)
```

### 2.5 Cache Isolation

```python
import redis.asyncio as redis

class TenantAwareCache:
    """Redis cache with tenant-prefixed keys."""
    
    KEY_PREFIX = "tenant:{}"
    
    def __init__(self, redis_client: redis.Redis):
        self._redis = redis_client
    
    def _key(self, tenant_id: str, key: str) -> str:
        return f"{self.KEY_PREFIX.format(tenant_id)}:{key}"
    
    async def get(self, tenant_id: str, key: str):
        return await self._redis.get(self._key(tenant_id, key))
    
    async def set(self, tenant_id: str, key: str, value: str, ttl: int = 3600):
        return await self._redis.setex(
            self._key(tenant_id, key), ttl, value
        )
    
    async def delete_tenant_cache(self, tenant_id: str):
        """Invalidate all cache keys for a tenant."""
        pattern = self.KEY_PREFIX.format(tenant_id) + ":*"
        keys = await self._redis.keys(pattern)
        if keys:
            await self._redis.delete(*keys)
```

---

## 3. Tenant Provisioning

### 3.1 Provisioning Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Tenant Provisioning Pipeline                 │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Signup   │───▶│ Validate │───▶│ Provision│              │
│  │ Request  │    │ & Approve│    │ Resources│              │
│  └──────────┘    └──────────┘    └────┬─────┘              │
│                                       │                     │
│                    ┌──────────────────┼──────────────┐      │
│                    │                  │              │      │
│              ┌─────▼─────┐    ┌──────▼─────┐  ┌────▼────┐ │
│              │ Database  │    │ Kubernetes │  │ Storage │ │
│              │  Setup    │    │  Namespace │  │ Bucket  │ │
│              └───────────┘    └────────────┘  └─────────┘ │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Seed    │───▶│  Configure│───▶│  Notify  │              │
│  │  Data    │    │  Billing  │    │  Tenant  │              │
│  └──────────┘    └──────────┘    └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Provisioning API

```python
from pydantic import BaseModel, EmailStr
from enum import Enum
from typing import Optional

class TenantTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    DEDICATED = "dedicated"

class TenantCreateRequest(BaseModel):
    name: str
    slug: str
    tier: TenantTier = TenantTier.FREE
    billing_email: EmailStr
    admin_email: EmailStr
    admin_name: str
    region: str = "us-east-1"
    compliance_requirements: list[str] = []  # ["soc2", "gdpr", "hipaa"]

class TenantProvisioner:
    """Orchestrates tenant provisioning across all services."""
    
    def __init__(self):
        self.db = DatabaseService()
        self.k8s = KubernetesService()
        self.storage = StorageService()
        self.billing = BillingService()
        self.monitoring = MonitoringService()
        self.secrets = SecretsService()
    
    async def provision(self, request: TenantCreateRequest) -> dict:
        """Provision a new tenant end-to-end."""
        
        # 1. Create tenant record
        tenant = await self._create_tenant_record(request)
        
        try:
            # 2. Provision database resources
            db_config = await self._provision_database(tenant)
            
            # 3. Provision Kubernetes resources
            k8s_config = await self._provision_kubernetes(tenant)
            
            # 4. Provision storage
            storage_config = await self._provision_storage(tenant)
            
            # 5. Generate secrets and credentials
            credentials = await self._generate_credentials(tenant)
            
            # 6. Seed initial data
            await self._seed_tenant_data(tenant, db_config)
            
            # 7. Configure billing
            await self._setup_billing(tenant)
            
            # 8. Setup monitoring
            await self._setup_monitoring(tenant)
            
            # 9. Send welcome notification
            await self._send_welcome_email(tenant, credentials)
            
            return {
                "tenant_id": tenant.id,
                "status": "active",
                "api_endpoint": f"https://{tenant.slug}.apex-os.io",
                "admin_credentials": credentials,  # Sent securely
            }
            
        except Exception as e:
            # Rollback on failure
            await self._rollback_provisioning(tenant)
            raise ProvisioningError(f"Failed to provision tenant: {e}")
    
    async def _create_tenant_record(self, request: TenantCreateRequest):
        tenant = await self.db.tenants.create({
            "name": request.name,
            "slug": request.slug,
            "tier": request.tier.value,
            "status": "provisioning",
            "isolation_mode": self._get_isolation_mode(request.tier),
            "billing_email": request.billing_email,
            "region": request.region,
            "compliance_requirements": request.compliance_requirements,
        })
        return tenant
    
    async def _provision_database(self, tenant):
        """Provision database based on tenant tier."""
        
        if tenant.isolation_mode == "database":
            # Dedicated RDS instance
            instance = await self.db.create_dedicated_instance(tenant)
            return {"host": instance.endpoint, "port": 5432}
        
        elif tenant.isolation_mode == "schema":
            # Create schema in shared database
            schema_name = f"tenant_{tenant.slug.replace('-', '_')}"
            await self.db.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
            return {"schema": schema_name}
        
        else:  # rls mode
            # Just ensure RLS policies exist
            await self.db.ensure_rls_policies(tenant.id)
            return {"mode": "rls", "tenant_id": tenant.id}
    
    async def _provision_kubernetes(self, tenant):
        """Provision Kubernetes resources."""
        
        if tenant.tier in ("enterprise", "dedicated"):
            # Dedicated namespace
            namespace = await self.k8s.create_namespace(
                name=f"tenant-{tenant.slug}",
                labels={
                    "tenant-id": tenant.id,
                    "tier": tenant.tier,
                },
                resource_quota=self._get_resource_quota(tenant.tier),
            )
            
            # Create service account
            await self.k8s.create_service_account(
                namespace=namespace,
                name=f"tenant-{tenant.slug}-sa",
            )
            
            # Apply network policies
            await self.k8s.apply_network_policy(
                namespace=namespace,
                policy=self._get_network_policy(tenant),
            )
            
            return {"namespace": namespace}
        
        else:
            # Shared namespace, just create service account
            await self.k8s.create_service_account(
                namespace="apex-os-workloads",
                name=f"tenant-{tenant.slug}-sa",
            )
            return {"namespace": "apex-os-workloads"}
    
    async def _provision_storage(self, tenant):
        """Provision object storage."""
        
        bucket_name = f"apex-os-tenant-{tenant.id}-data"
        
        # Create bucket with encryption
        await self.storage.create_bucket(
            name=bucket_name,
            region=tenant.region,
            encryption_key_id=tenant.encryption_key_id,
        )
        
        # Set lifecycle policies
        await self.storage.set_lifecycle_policy(
            bucket=bucket_name,
            rules=[
                {"id": "temp-expiration", "prefix": "temp/", "expiration_days": 7},
                {"id": "log-expiration", "prefix": "logs/", "expiration_days": 90},
                {"id": "backup-retention", "prefix": "backups/", "expiration_days": 365},
            ],
        )
        
        return {"bucket": bucket_name}
    
    async def _generate_credentials(self, tenant):
        """Generate API keys and credentials."""
        
        api_key = self.secrets.generate_api_key(tenant.id)
        db_password = self.secrets.generate_password(length=32)
        
        # Store in secrets manager
        await self.secrets.store(
            name=f"tenant-{tenant.id}-credentials",
            value={
                "api_key": api_key,
                "db_password": db_password,
            },
        )
        
        return {"api_key": api_key, "db_password": db_password}
    
    async def _seed_tenant_data(self, tenant, db_config):
        """Seed initial data for the tenant."""
        
        # Create admin user
        await self.db.execute(
            "INSERT INTO users (tenant_id, email, name, role) VALUES ($1, $2, $3, $4)",
            tenant.id, tenant.admin_email, tenant.admin_name, "admin"
        )
        
        # Create default project
        await self.db.execute(
            "INSERT INTO projects (tenant_id, name) VALUES ($1, $2)",
            tenant.id, "Default Project"
        )
        
        # Create default settings
        await self.db.execute(
            "INSERT INTO tenant_settings (tenant_id, settings) VALUES ($1, $2)",
            tenant.id, '{"theme": "default", "language": "en"}'
        )
    
    async def _setup_billing(self, tenant):
        """Configure billing for the tenant."""
        
        await self.billing.create_customer(
            tenant_id=tenant.id,
            email=tenant.billing_email,
            plan=tenant.tier,
        )
    
    async def _setup_monitoring(self, tenant):
        """Setup monitoring dashboards and alerts."""
        
        # Create tenant-specific dashboard
        await self.monitoring.create_dashboard(
            tenant_id=tenant.id,
            dashboard_type="tenant_overview",
        )
        
        # Create tenant-specific alert rules
        await self.monitoring.create_alert_rules(
            tenant_id=tenant.id,
            rules=self._get_default_alert_rules(tenant.tier),
        )
    
    def _get_isolation_mode(self, tier: TenantTier) -> str:
        mapping = {
            TenantTier.FREE: "rls",
            TenantTier.PRO: "rls",
            TenantTier.ENTERPRISE: "schema",
            TenantTier.DEDICATED: "database",
        }
        return mapping[tier]
    
    def _get_resource_quota(self, tier: TenantTier) -> dict:
        quotas = {
            "enterprise": {
                "requests.cpu": "10",
                "requests.memory": "20Gi",
                "limits.cpu": "20",
                "limits.memory": "40Gi",
                "pods": "50",
            },
            "dedicated": {
                "requests.cpu": "50",
                "requests.memory": "100Gi",
                "limits.cpu": "100",
                "limits.memory": "200Gi",
                "pods": "200",
            },
        }
        return quotas.get(tier, {})
    
    def _get_default_alert_rules(self, tier: TenantTier) -> list:
        base_rules = [
            {"name": "high_cpu", "threshold": 80, "duration": "5m"},
            {"name": "high_memory", "threshold": 85, "duration": "5m"},
            {"name": "error_rate", "threshold": 5, "duration": "5m"},
        ]
        if tier in ("enterprise", "dedicated"):
            base_rules.extend([
                {"name": "disk_usage", "threshold": 80, "duration": "10m"},
                {"name": "connection_pool", "threshold": 90, "duration": "5m"},
            ])
        return base_rules
```

### 3.3 Tenant Lifecycle Management

```python
class TenantLifecycleManager:
    """Manages tenant state transitions."""
    
    VALID_TRANSITIONS = {
        "provisioning": ["active", "failed"],
        "active": ["suspended", "upgrading", "downgrading"],
        "suspended": ["active", "terminated"],
        "upgrading": ["active", "failed"],
        "downgrading": ["active", "failed"],
        "failed": ["provisioning", "terminated"],
        "terminated": [],  # Terminal state
    }
    
    async def transition(self, tenant_id: str, new_status: str, reason: str = ""):
        tenant = await self.db.tenants.get(tenant_id)
        
        if new_status not in self.VALID_TRANSITIONS.get(tenant.status, []):
            raise InvalidTransitionError(
                f"Cannot transition from {tenant.status} to {new_status}"
            )
        
        old_status = tenant.status
        await self.db.tenants.update(tenant_id, {"status": new_status})
        
        # Execute transition actions
        await self._execute_transition_actions(tenant, old_status, new_status)
        
        # Audit log
        await self.audit.log({
            "event": "tenant_status_change",
            "tenant_id": tenant_id,
            "from": old_status,
            "to": new_status,
            "reason": reason,
        })
    
    async def _execute_transition_actions(self, tenant, old_status, new_status):
        if new_status == "suspended":
            # Revoke API keys
            await self.secrets.revoke_api_keys(tenant.id)
            # Scale down deployments
            await self.k8s.scale_deployments(tenant.id, replicas=0)
            # Notify tenant
            await self.notifications.send(tenant.billing_email, "account_suspended")
        
        elif new_status == "active" and old_status == "suspended":
            # Restore API keys
            await self.secrets.restore_api_keys(tenant.id)
            # Scale up deployments
            await self.k8s.scale_deployments(tenant.id, replicas=2)
        
        elif new_status == "terminated":
            # Export tenant data
            export_url = await self.storage.export_tenant_data(tenant.id)
            # Schedule data deletion (30-day grace period)
            await self.scheduler.schedule(
                task="delete_tenant_data",
                tenant_id=tenant.id,
                run_at=datetime.now() + timedelta(days=30),
            )
            # Final notification
            await self.notifications.send(
                tenant.billing_email,
                "account_terminated",
                {"export_url": export_url},
            )
```

### 3.4 Terraform Module for Tenant Provisioning

```hcl
# modules/tenant/main.tf

variable "tenant_name" {
  description = "Tenant display name"
  type        = string
}

variable "tenant_slug" {
  description = "Tenant URL slug"
  type        = string
}

variable "tenant_tier" {
  description = "Tenant tier (free, pro, enterprise, dedicated)"
  type        = string
  default     = "free"
}

variable "tenant_region" {
  description = "Primary region for tenant resources"
  type        = string
  default     = "us-east-1"
}

variable "admin_email" {
  description = "Tenant admin email"
  type        = string
}

# KMS key for tenant encryption
resource "aws_kms_key" "tenant" {
  description             = "Encryption key for tenant ${var.tenant_name}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  tags = {
    TenantSlug = var.tenant_slug
    Tier       = var.tenant_tier
  }
}

# S3 bucket for tenant data
resource "aws_s3_bucket" "tenant_data" {
  bucket = "apex-os-tenant-${var.tenant_slug}-data"
  
  tags = {
    TenantSlug = var.tenant_slug
    Tier       = var.tenant_tier
  }
}

# IAM role for tenant access
resource "aws_iam_role" "tenant" {
  name = "apex-os-tenant-${var.tenant_slug}-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

# Outputs
output "tenant_kms_key_id" {
  value = aws_kms_key.tenant.id
}

output "tenant_bucket_name" {
  value = aws_s3_bucket.tenant_data.id
}

output "tenant_role_arn" {
  value = aws_iam_role.tenant.arn
}
```

---

## 4. Tenant Billing

### 4.1 Billing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Billing Pipeline                          │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Usage   │───▶│  Meter   │───▶│  Rate    │              │
│  │  Events  │    │  & Store │    │  Card    │              │
│  └──────────┘    └──────────┘    └────┬─────┘              │
│                                       │                     │
│  ┌──────────┐    ┌──────────┐    ┌────▼─────┐              │
│  │  Invoice │◀───│  Generate│◀───│  Calculate│             │
│  │  & Send  │    │  Invoice │    │  Charges  │             │
│  └──────────┘    └──────────┘    └──────────┘              │
│                                                              │
│  ┌──────────┐    ┌──────────┐                               │
│  │  Payment │───▶│  Stripe  │                               │
│  │  Method  │    │  /Braintree                              │
│  └──────────┘    └──────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Usage Metering

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

@dataclass
class UsageEvent:
    tenant_id: str
    metric_name: str  # api_calls, storage_gb, compute_hours, etc.
    value: float
    unit: str
    timestamp: datetime
    metadata: dict = None

class UsageMeter:
    """Collects and stores usage metrics per tenant."""
    
    METRICS = {
        "api_calls": {"unit": "requests", "description": "API requests"},
        "storage_gb": {"unit": "GB", "description": "Storage used"},
        "compute_hours": {"unit": "hours", "description": "Compute time"},
        "bandwidth_gb": {"unit": "GB", "description": "Data transfer"},
        "active_users": {"unit": "users", "description": "Monthly active users"},
        "database_queries": {"unit": "queries", "description": "Database queries"},
        "emails_sent": {"unit": "emails", "description": "Emails sent"},
    }
    
    def __init__(self, event_store, metrics_store):
        self._event_store = event_store  # Kafka / Kinesis
        self._metrics_store = metrics_store  # Prometheus / TimescaleDB
    
    async def record(self, event: UsageEvent):
        """Record a usage event."""
        
        # Validate metric
        if event.metric_name not in self.METRICS:
            raise ValueError(f"Unknown metric: {event.metric_name}")
        
        # Store raw event
        await self._event_store.publish(
            topic="usage-events",
            key=event.tenant_id,
            value=json.dumps({
                "tenant_id": event.tenant_id,
                "metric": event.metric_name,
                "value": event.value,
                "unit": event.unit,
                "timestamp": event.timestamp.isoformat(),
                "metadata": event.metadata or {},
            }),
        )
        
        # Update real-time metrics
        await self._metrics_store.increment(
            metric=f"tenant_usage_{event.metric_name}",
            labels={"tenant_id": event.tenant_id},
            value=event.value,
        )
    
    async def get_usage(
        self,
        tenant_id: str,
        start: datetime,
        end: datetime,
        granularity: str = "hour",  # hour, day, month
    ) -> dict:
        """Get aggregated usage for a tenant."""
        
        query = """
            SELECT 
                metric_name,
                SUM(value) as total_value,
                unit
            FROM usage_events
            WHERE tenant_id = $1
              AND timestamp >= $2
              AND timestamp < $3
            GROUP BY metric_name, unit
        """
        
        results = await self._metrics_store.query(query, tenant_id, start, end)
        
        return {
            row["metric_name"]: {
                "value": row["total_value"],
                "unit": row["unit"],
            }
            for row in results
        }
```

### 4.3 Pricing Engine

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PricingTier:
    name: str
    base_price: float
    included_quota: dict  # metric_name -> included amount
    overage_rates: dict   # metric_name -> price per unit

class PricingEngine:
    """Calculates charges based on usage and pricing tier."""
    
    PRICING_TIERS = {
        "free": PricingTier(
            name="free",
            base_price=0,
            included_quota={
                "api_calls": 10_000,
                "storage_gb": 5,
                "compute_hours": 100,
                "active_users": 5,
            },
            overage_rates={},  # No overage allowed
        ),
        "pro": PricingTier(
            name="pro",
            base_price=49,
            included_quota={
                "api_calls": 100_000,
                "storage_gb": 50,
                "compute_hours": 500,
                "active_users": 50,
                "bandwidth_gb": 100,
            },
            overage_rates={
                "api_calls": 0.001,      # $0.001 per request
                "storage_gb": 0.10,       # $0.10 per GB
                "compute_hours": 0.05,    # $0.05 per hour
                "bandwidth_gb": 0.05,     # $0.05 per GB
            },
        ),
        "enterprise": PricingTier(
            name="enterprise",
            base_price=499,
            included_quota={
                "api_calls": 1_000_000,
                "storage_gb": 500,
                "compute_hours": 5000,
                "active_users": 500,
                "bandwidth_gb": 1000,
                "emails_sent": 10_000,
            },
            overage_rates={
                "api_calls": 0.0005,
                "storage_gb": 0.08,
                "compute_hours": 0.03,
                "bandwidth_gb": 0.03,
                "emails_sent": 0.001,
            },
        ),
        "dedicated": PricingTier(
            name="dedicated",
            base_price=5000,
            included_quota={
                "api_calls": 10_000_000,
                "storage_gb": 5000,
                "compute_hours": 50000,
                "active_users": 5000,
                "bandwidth_gb": 10000,
                "emails_sent": 100_000,
            },
            overage_rates={
                "api_calls": 0.0001,
                "storage_gb": 0.05,
                "compute_hours": 0.02,
                "bandwidth_gb": 0.02,
                "emails_sent": 0.0005,
            },
        ),
    }
    
    def calculate_invoice(
        self,
        tenant_id: str,
        tier_name: str,
        usage: dict,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """Calculate invoice for a tenant."""
        
        tier = self.PRICING_TIERS[tier_name]
        line_items = []
        total = tier.base_price
        
        # Base subscription
        line_items.append({
            "description": f"{tier.name.title()} Plan",
            "quantity": 1,
            "unit_price": tier.base_price,
            "amount": tier.base_price,
        })
        
        # Overage charges
        for metric, used in usage.items():
            included = tier.included_quota.get(metric, 0)
            overage = max(0, used - included)
            
            if overage > 0 and metric in tier.overage_rates:
                rate = tier.overage_rates[metric]
                charge = round(overage * rate, 2)
                total += charge
                
                line_items.append({
                    "description": f"{metric} overage",
                    "quantity": round(overage, 2),
                    "unit_price": rate,
                    "amount": charge,
                    "included": included,
                    "used": used,
                })
        
        return {
            "tenant_id": tenant_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "tier": tier_name,
            "line_items": line_items,
            "subtotal": round(total, 2),
            "tax": 0,  # Calculated based on jurisdiction
            "total": round(total, 2),
            "currency": "USD",
        }
```

### 4.4 Billing Database Schema

```sql
-- Billing customers (mirrors Stripe customer)
CREATE TABLE billing_customers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_customer_id VARCHAR(255) UNIQUE,
    email           VARCHAR(255) NOT NULL,
    name            VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE billing_subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id     UUID NOT NULL REFERENCES billing_customers(id),
    plan_id         VARCHAR(63) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end   TIMESTAMPTZ NOT NULL,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Invoices
CREATE TABLE billing_invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id     UUID NOT NULL REFERENCES billing_customers(id),
    subscription_id UUID REFERENCES billing_subscriptions(id),
    stripe_invoice_id VARCHAR(255) UNIQUE,
    status          VARCHAR(32) NOT NULL DEFAULT 'draft',
    amount_due      NUMERIC(12,2) NOT NULL DEFAULT 0,
    amount_paid     NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    due_date        TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Invoice line items
CREATE TABLE billing_invoice_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id      UUID NOT NULL REFERENCES billing_invoices(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    quantity        NUMERIC(12,4) NOT NULL,
    unit_price      NUMERIC(12,4) NOT NULL,
    amount          NUMERIC(12,2) NOT NULL,
    metric_name     VARCHAR(63),
    metadata        JSONB
);

-- Usage events (TimescaleDB hypertable)
CREATE TABLE billing_usage_events (
    time            TIMESTAMPTZ NOT NULL,
    tenant_id       UUID NOT NULL,
    metric_name     VARCHAR(63) NOT NULL,
    value           NUMERIC(12,4) NOT NULL,
    unit            VARCHAR(32) NOT NULL,
    metadata        JSONB
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('billing_usage_events', 'time', chunk_time_interval => INTERVAL '1 day');

-- Indexes for common queries
CREATE INDEX idx_usage_tenant_time ON billing_usage_events (tenant_id, time DESC);
CREATE INDEX idx_invoices_tenant ON billing_invoices (tenant_id, created_at DESC);
```

### 4.5 Stripe Integration

```python
import stripe
from typing import Optional

class StripeBillingService:
    """Stripe integration for payment processing."""
    
    def __init__(self, api_key: str):
        stripe.api_key = api_key
    
    async def create_customer(self, tenant) -> str:
        """Create a Stripe customer for a tenant."""
        
        customer = stripe.Customer.create(
            email=tenant.billing_email,
            name=tenant.name,
            metadata={
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
            },
        )
        
        # Store mapping
        await self.db.billing_customers.create({
            "tenant_id": tenant.id,
            "stripe_customer_id": customer.id,
            "email": tenant.billing_email,
            "name": tenant.name,
        })
        
        return customer.id
    
    async def create_subscription(self, tenant_id: str, plan_id: str) -> dict:
        """Create a Stripe subscription."""
        
        customer = await self.db.billing_customers.get_by_tenant(tenant_id)
        
        subscription = stripe.Subscription.create(
            customer=customer.stripe_customer_id,
            items=[{"price": self._get_stripe_price_id(plan_id)}],
            metadata={"tenant_id": tenant_id},
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        
        await self.db.billing_subscriptions.create({
            "tenant_id": tenant_id,
            "customer_id": customer.id,
            "plan_id": plan_id,
            "status": subscription.status,
            "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
            "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
        })
        
        return subscription
    
    async def handle_webhook(self, event: dict):
        """Process Stripe webhook events."""
        
        event_type = event["type"]
        data = event["data"]["object"]
        
        handlers = {
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_payment_failed,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
        }
        
        handler = handlers.get(event_type)
        if handler:
            await handler(data)
    
    async def _handle_invoice_paid(self, invoice: dict):
        tenant_id = invoice["metadata"]["tenant_id"]
        
        await self.db.billing_invoices.update(
            {"stripe_invoice_id": invoice["id"]},
            {
                "status": "paid",
                "amount_paid": invoice["amount_paid"] / 100,
                "paid_at": datetime.now(),
            },
        )
        
        # Notify tenant
        await self.notifications.send_invoice(tenant_id, invoice["id"])
    
    async def _handle_payment_failed(self, invoice: dict):
        tenant_id = invoice["metadata"]["tenant_id"]
        
        await self.db.billing_invoices.update(
            {"stripe_invoice_id": invoice["id"]},
            {"status": "open"},
        )
        
        # Retry logic and dunning
        await self.dunning.process_failed_payment(tenant_id, invoice)
    
    def _get_stripe_price_id(self, plan_id: str) -> str:
        mapping = {
            "free": "price_free",
            "pro": "price_pro_monthly",
            "enterprise": "price_enterprise_monthly",
            "dedicated": "price_dedicated_monthly",
        }
        return mapping[plan_id]
```

---

## 5. Tenant Monitoring

### 5.1 Monitoring Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Multi-Tenant Monitoring Stack               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Prometheus (Metrics)                  │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│  │  │ Tenant  │  │ Tenant  │  │ Tenant  │  ...         │   │
│  │  │ Scrape  │  │ Scrape  │  │ Scrape  │              │   │
│  │  │ Config  │  │ Config  │  │ Config  │              │   │
│  │  └─────────┘  └─────────┘  └─────────┘              │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│  ┌───────────────────────▼──────────────────────────────┐   │
│  │                  Grafana (Dashboards)                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│  │  │ Tenant      │  │ Platform    │  │ Billing     │  │   │
│  │  │ Overview    │  │ Health      │  │ Dashboard   │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Loki (Logs)                          │   │
│  │  tenant="acme-corp"  tenant="globex"  ...            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Tempo (Traces)                       │   │
│  │  traces tagged with tenant_id                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Alertmanager (Alerts)                │   │
│  │  Route by tenant_id → different notification channels│   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Prometheus Configuration

```yaml
# prometheus.yml - Multi-tenant scrape configuration
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# Tenant-specific scrape configs
scrape_configs:
  # Platform-level metrics
  - job_name: 'apex-os-platform'
    static_configs:
      - targets: ['localhost:9090']
    relabel_configs:
      - target_label: tenant_id
        replacement: '_platform_'
  
  # Per-tenant API metrics
  - job_name: 'tenant-api'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - apex-os-workloads
    relabel_configs:
      # Only scrape pods with tenant label
      - source_labels: [__meta_kubernetes_pod_label_apex_os_io_tenant]
        action: keep
        regex: .+
      # Add tenant_id label
      - source_labels: [__meta_kubernetes_pod_label_apex_os_io_tenant]
        target_label: tenant_id
      # Add tenant tier label
      - source_labels: [__meta_kubernetes_pod_label_apex_os_io_tier]
        target_label: tenant_tier
  
  # Per-tenant database metrics
  - job_name: 'tenant-postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    relabel_configs:
      - target_label: tenant_id
        replacement: '_shared_'
  
  # Per-tenant Redis metrics
  - job_name: 'tenant-redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    relabel_configs:
      - target_label: tenant_id
        replacement: '_shared_'

# Alert rules with tenant labels
rule_files:
  - /etc/prometheus/rules/tenant-alerts.yml
  - /etc/prometheus/rules/platform-alerts.yml

# Alert routing
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

### 5.3 Tenant Alert Rules

```yaml
# tenant-alerts.yml
groups:
  - name: tenant_alerts
    rules:
      # High error rate for a tenant
      - alert: TenantHighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status=~"5.."}[5m])) by (tenant_id)
            /
            sum(rate(http_requests_total[5m])) by (tenant_id)
          ) > 0.05
        for: 5m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High error rate for tenant {{ $labels.tenant_id }}"
          description: "Error rate is {{ $value | humanizePercentage }} for tenant {{ $labels.tenant_id }}"
          runbook: "https://wiki.apex-os.io/runbooks/high-error-rate"
      
      # Tenant approaching API limit
      - alert: TenantApproachingApiLimit
        expr: |
          (
            sum(rate(api_calls_total[1h])) by (tenant_id) * 24
          ) / on(tenant_id) group_left tenant_api_limit > 0.8
        for: 15m
        labels:
          severity: info
          team: billing
        annotations:
          summary: "Tenant {{ $labels.tenant_id }} approaching API limit"
          description: "Tenant is using {{ $value | humanizePercentage }} of daily API limit"
      
      # Tenant storage usage high
      - alert: TenantHighStorageUsage
        expr: |
          tenant_storage_used_bytes / tenant_storage_quota_bytes > 0.85
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "High storage usage for tenant {{ $labels.tenant_id }}"
          description: "Storage usage is {{ $value | humanizePercentage }} of quota"
      
      # Tenant database connections high
      - alert: TenantHighDbConnections
        expr: |
          tenant_db_connections_active / tenant_db_connections_max > 0.8
        for: 5m
        labels:
          severity: warning
          team: database
        annotations:
          summary: "High DB connections for tenant {{ $labels.tenant_id }}"
          description: "{{ $value | humanizePercentage }} of connection pool in use"
      
      # Tenant pod restart loop
      - alert: TenantPodCrashLooping
        expr: |
          rate(kube_pod_container_status_restarts_total[15m]) by (namespace, pod) > 0
        for: 5m
        labels:
          severity: critical
          team: platform
        annotations:
          summary: "Pod crash looping in tenant namespace {{ $labels.namespace }}"
          description: "Pod {{ $labels.pod }} is restarting frequently"
      
      # Tenant latency SLO breach
      - alert: TenantLatencySLOBreach
        expr: |
          histogram_quantile(0.95, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, tenant_id)
          ) > 1.0
        for: 10m
        labels:
          severity: warning
          team: platform
        annotations:
          summary: "Latency SLO breach for tenant {{ $labels.tenant_id }}"
          description: "P95 latency is {{ $value }}s (threshold: 1s)"
```

### 5.4 Grafana Dashboard Provisioning

```yaml
# grafana/dashboards/tenant-overview.json
{
  "dashboard": {
    "title": "Tenant Overview",
    "tags": ["tenant", "multi-tenant"],
    "timezone": "utc",
    "schemaVersion": 36,
    "refresh": "30s",
    "templating": {
      "list": [
        {
          "name": "tenant_id",
          "type": "query",
          "query": "label_values(tenant_id)",
          "label": "Tenant",
          "multi": true,
          "includeAll": true
        },
        {
          "name": "tier",
          "type": "query",
          "query": "label_values(tenant_tier)",
          "label": "Tier",
          "multi": true,
          "includeAll": true
        }
      ]
    },
    "panels": [
      {
        "title": "Request Rate by Tenant",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{tenant_id=~\"$tenant_id\"}[5m])) by (tenant_id)",
            "legendFormat": "{{tenant_id}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "title": "Error Rate by Tenant",
        "type": "timeseries",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{tenant_id=~\"$tenant_id\",status=~\"5..\"}[5m])) by (tenant_id) / sum(rate(http_requests_total{tenant_id=~\"$tenant_id\"}[5m])) by (tenant_id)",
            "legendFormat": "{{tenant_id}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "title": "P95 Latency by Tenant",
        "type": "timeseries",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{tenant_id=~\"$tenant_id\"}[5m])) by (le, tenant_id))",
            "legendFormat": "{{tenant_id}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "title": "Active Users by Tenant",
        "type": "stat",
        "targets": [
          {
            "expr": "count(count by (tenant_id, user_id) (user_activity{tenant_id=~\"$tenant_id\"})) by (tenant_id)",
            "legendFormat": "{{tenant_id}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "title": "Storage Usage by Tenant",
        "type": "bargauge",
        "targets": [
          {
            "expr": "tenant_storage_used_bytes{tenant_id=~\"$tenant_id\"} / tenant_storage_quota_bytes{tenant_id=~\"$tenant_id\"}",
            "legendFormat": "{{tenant_id}}"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 16}
      },
      {
        "title": "API Calls by Tier",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum(rate(api_calls_total[1h])) by (tenant_tier)",
            "legendFormat": "{{tenant_tier}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
      },
      {
        "title": "Cost by Tenant",
        "type": "table",
        "targets": [
          {
            "expr": "tenant_estimated_cost{tenant_id=~\"$tenant_id\"}",
            "format": "table",
            "instant": true
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
      }
    ]
  }
}
```

### 5.5 Log Aggregation with Tenant Context

```yaml
# loki/promtail-config.yaml
server:
  http_listen_port: 3100

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: tenant-logs
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - apex-os-workloads
    pipeline_stages:
      # Parse JSON logs
      - json:
          expressions:
            level: level
            message: message
            tenant_id: tenant_id
            trace_id: trace_id
      
      # Extract tenant_id from log if not present
      - template:
          source: tenant_id
          template: '{{ if .tenant_id }}{{ .tenant_id }}{{ else }}{{ .kubernetes.pod_labels.apex_os_io_tenant }}{{ end }}'
      
      # Add tenant_id as label
      - labels:
          tenant_id:
          level:
      
      # Drop logs without tenant_id (except platform logs)
      - match:
          selector: '{tenant_id=""}'
          action: drop
      
      # Add tenant tier as label
      - labels:
          tenant_tier:
    
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_apex_os_io_tenant]
        target_label: tenant_id
      - source_labels: [__meta_kubernetes_pod_label_apex_os_io_tier]
        target_label: tenant_tier
```

### 5.6 Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

class TenantAwareTracer:
    """OpenTelemetry tracer with tenant context propagation."""
    
    def __init__(self):
        provider = TracerProvider()
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint="tempo:4317"))
        )
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer("apex-os")
    
    def start_span(self, name: str, tenant_id: str = None):
        """Start a new span with tenant context."""
        
        tenant_id = tenant_id or tenant_context.get()
        
        with self._tracer.start_as_current_span(name) as span:
            if tenant_id:
                span.set_attribute("tenant.id", tenant_id)
                span.set_attribute("tenant.tier", self._get_tier(tenant_id))
            
            # Add trace context to tenant context
            span.set_attribute("trace.id", format(span.get_span_context().trace_id, "032x"))
            
            return span
    
    def _get_tier(self, tenant_id: str) -> str:
        # Cache tier lookup
        return self._tier_cache.get(tenant_id, "unknown")
```

---

## 6. Tenant Security

### 6.1 Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Defense-in-Depth Security                   │
│                                                              │
│  Layer 1: Network Security                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  WAF → Security Groups → Network Policies → mTLS    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 2: Identity & Access Management                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  OAuth2/OIDC → RBAC → ABAC → Service Accounts       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 3: Application Security                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Input Validation → RLS → Encryption → Audit Logging │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 4: Data Security                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Encryption at Rest → Encryption in Transit → DLP   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Layer 5: Operational Security                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Secrets Management → Vulnerability Scanning → SOC  │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Authentication & Authorization

#### 6.2.1 Multi-Tenant OAuth2/OIDC

```python
from fastapi import Depends, HTTPException
from jose import jwt, JWTError

class MultiTenantAuth:
    """Handles authentication across tenants."""
    
    def __init__(self):
        self._jwks_cache = {}  # tenant_id -> JWKS
    
    async def authenticate(self, token: str) -> dict:
        """Validate JWT and extract tenant context."""
        
        # Decode without verification to get tenant
        unverified = jwt.get_unverified_claims(token)
        tenant_id = unverified.get("tenant_id")
        
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Token missing tenant_id")
        
        # Get tenant-specific JWKS
        jwks = await self._get_tenant_jwks(tenant_id)
        
        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=f"apex-os-{tenant_id}",
                issuer=f"https://auth.apex-os.io/{tenant_id}",
            )
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
        
        return {
            "user_id": payload["sub"],
            "tenant_id": tenant_id,
            "roles": payload.get("roles", []),
            "permissions": payload.get("permissions", []),
        }
    
    async def authorize(
        self,
        user: dict,
        required_permission: str,
        resource_tenant_id: str = None,
    ):
        """Check if user has permission for the resource."""
        
        # Cross-tenant access check
        if resource_tenant_id and resource_tenant_id != user["tenant_id"]:
            # Only platform admins can access cross-tenant
            if "platform:admin" not in user["permissions"]:
                raise HTTPException(
                    status_code=403,
                    detail="Cross-tenant access denied"
                )
        
        # Permission check
        if required_permission not in user["permissions"]:
            raise HTTPException(
                status_code=403,
                detail=f"Missing permission: {required_permission}"
            )
```

#### 6.2.2 Role-Based Access Control (RBAC)

```yaml
# RBAC policy definitions
roles:
  # Platform roles (cross-tenant)
  platform_admin:
    description: "Full platform access"
    permissions:
      - "platform:*"
      - "tenant:read"
      - "tenant:write"
      - "tenant:delete"
      - "billing:read"
      - "billing:write"
  
  platform_support:
    description: "Support access to all tenants"
    permissions:
      - "platform:read"
      - "tenant:read"
      - "tenant:impersonate"
      - "logs:read"
  
  # Tenant roles (scoped to tenant)
  tenant_admin:
    description: "Full access within tenant"
    permissions:
      - "tenant:read"
      - "tenant:write"
      - "users:manage"
      - "projects:manage"
      - "billing:read"
      - "settings:manage"
  
  tenant_member:
    description: "Standard member"
    permissions:
      - "tenant:read"
      - "projects:read"
      - "projects:write"
  
  tenant_viewer:
    description: "Read-only access"
    permissions:
      - "tenant:read"
      - "projects:read"
```

### 6.3 Encryption

#### 6.3.1 Encryption at Rest

```hcl
# Terraform: Encryption configuration for all tenant data

# RDS encryption
resource "aws_db_instance" "tenant" {
  storage_encrypted = true
  kms_key_id       = aws_kms_key.tenant.arn
}

# S3 encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "tenant" {
  bucket = aws_s3_bucket.tenant_data.id
  
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.tenant.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# EKS secrets encryption
resource "aws_kms_key" "eks_secrets" {
  description             = "EKS secret encryption key for tenant ${var.tenant_id}"
  deletion_window_in_days = 30
  enable_key_rotation     = true
}

# EBS encryption
resource "aws_ebs_encryption_by_default" "tenant" {
  enabled = true
}
```

#### 6.3.2 Encryption in Transit

```yaml
# Istio mTLS configuration for service-to-service traffic
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: tenant-mtls
  namespace: apex-os-workloads
spec:
  mtls:
    mode: STRICT
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: tenant-tls
  namespace: apex-os-workloads
spec:
  host: "*.apex-os-workloads.svc.cluster.local"
  trafficPolicy:
    tls:
      mode: ISTIO_MUTUAL
```

#### 6.3.3 Application-Level Encryption

```python
from cryptography.fernet import Fernet
from aws_encryption_sdk import EncryptionSDKClient

class TenantDataEncryption:
    """Encrypt sensitive tenant data before storage."""
    
    def __init__(self, kms_key_id: str):
        self._client = EncryptionSDKClient()
        self._kms_key_id = kms_key_id
    
    async def encrypt(self, tenant_id: str, plaintext: str, context: dict = None) -> bytes:
        """Encrypt data with tenant-specific encryption context."""
        
        encryption_context = {
            "tenant_id": tenant_id,
            "purpose": context.get("purpose", "data") if context else "data",
        }
        
        encrypted, _ = self._client.encrypt(
            source=plaintext.encode(),
            key_provider=self._kms_key_id,
            encryption_context=encryption_context,
        )
        
        return encrypted
    
    async def decrypt(self, tenant_id: str, ciphertext: bytes, context: dict = None) -> str:
        """Decrypt data with tenant verification."""
        
        encryption_context = {
            "tenant_id": tenant_id,
            "purpose": context.get("purpose", "data") if context else "data",
        }
        
        plaintext, actual_context = self._client.decrypt(
            source=ciphertext,
            key_provider=self._kms_key_id,
        )
        
        # Verify tenant context
        if actual_context.get("tenant_id") != tenant_id:
            raise SecurityError("Encryption context tenant mismatch")
        
        return plaintext.decode()
```

### 6.4 Audit Logging

```python
from datetime import datetime
from typing import Optional
import json

class TenantAuditLogger:
    """Comprehensive audit logging for all tenant operations."""
    
    AUDIT_EVENTS = {
        # Authentication events
        "auth.login": {"severity": "info", "retention_days": 365},
        "auth.login_failed": {"severity": "warning", "retention_days": 365},
        "auth.logout": {"severity": "info", "retention_days": 365},
        "auth.token_refreshed": {"severity": "info", "retention_days": 365},
        "auth.mfa_enabled": {"severity": "info", "retention_days": 365},
        "auth.mfa_disabled": {"severity": "warning", "retention_days": 365},
        
        # Data access events
        "data.read": {"severity": "info", "retention_days": 90},
        "data.write": {"severity": "info", "retention_days": 90},
        "data.delete": {"severity": "warning", "retention_days": 365},
        "data.export": {"severity": "warning", "retention_days": 365},
        
        # Admin events
        "admin.user_created": {"severity": "info", "retention_days": 365},
        "admin.user_deleted": {"severity": "warning", "retention_days": 365},
        "admin.role_changed": {"severity": "warning", "retention_days": 365},
        "admin.settings_changed": {"severity": "info", "retention_days": 365},
        
        # Security events
        "security.suspicious_activity": {"severity": "critical", "retention_days": 730},
        "security.permission_denied": {"severity": "warning", "retention_days": 365},
        "security.api_key_created": {"severity": "info", "retention_days": 365},
        "security.api_key_revoked": {"severity": "warning", "retention_days": 365},
        
        # Billing events
        "billing.subscription_created": {"severity": "info", "retention_days": 730},
        "billing.subscription_cancelled": {"severity": "warning", "retention_days": 730},
        "billing.payment_failed": {"severity": "warning", "retention_days": 730},
        "billing.invoice_generated": {"severity": "info", "retention_days": 730},
    }
    
    async def log(
        self,
        event_type: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log an audit event."""
        
        event_config = self.AUDIT_EVENTS.get(event_type, {
            "severity": "info",
            "retention_days": 90,
        })
        
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "severity": event_config["severity"],
            "tenant_id": tenant_id,
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "retention_days": event_config["retention_days"],
        }
        
        # Store in audit log (append-only)
        await self._store_audit_log(audit_entry)
        
        # Real-time alerting for critical events
        if event_config["severity"] == "critical":
            await self._alert_security_team(audit_entry)
    
    async def _store_audit_log(self, entry: dict):
        """Store audit entry in tamper-proof storage."""
        
        # Write to append-only audit table
        await self._db.execute(
            """
            INSERT INTO audit_log (
                timestamp, event_type, severity, tenant_id, user_id,
                resource_type, resource_id, details, ip_address, user_agent
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            entry["timestamp"],
            entry["event_type"],
            entry["severity"],
            entry["tenant_id"],
            entry["user_id"],
            entry["resource_type"],
            entry["resource_id"],
            json.dumps(entry["details"]),
            entry["ip_address"],
            entry["user_agent"],
        )
        
        # Also write to immutable storage (S3 with object lock)
        await self._storage.write(
            bucket="apex-os-audit-logs",
            key=f"audit/{entry['tenant_id']}/{entry['timestamp'][:10]}/{entry['timestamp']}.json",
            data=json.dumps(entry),
            metadata={"retention-days": str(entry["retention_days"])},
        )
```

### 6.5 Network Security

#### 6.5.1 VPC Isolation

```hcl
# Network isolation for dedicated tier tenants
resource "aws_vpc" "tenant" {
  cidr_block           = var.tenant_vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name      = "apex-os-tenant-${var.tenant_id}"
    TenantId = var.tenant_id
    Tier      = "dedicated"
  }
}

# Private subnets only for dedicated tenants
resource "aws_subnet" "tenant_private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.tenant.id
  cidr_block        = cidrsubnet(var.tenant_vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]
  
  tags = {
    Name      = "apex-os-tenant-${var.tenant_id}-private-${count.index}"
    TenantId = var.tenant_id
    Type      = "private"
  }
}

# VPC peering to shared services
resource "aws_vpc_peering_connection" "tenant_to_shared" {
  vpc_id        = aws_vpc.tenant.id
  peer_vpc_id   = var.shared_vpc_id
  auto_accept   = true
  
  tags = {
    Name      = "apex-os-tenant-${var.tenant_id}-to-shared"
    TenantId = var.tenant_id
  }
}
```

#### 6.5.2 WAF Rules

```hcl
# AWS WAF rules for tenant protection
resource "aws_wafv2_web_acl" "tenant_protection" {
  name        = "apex-os-tenant-protection"
  description = "WAF rules for multi-tenant protection"
  scope       = "REGIONAL"
  
  # Rate limiting per tenant
  rule {
    name     = "tenant-rate-limit"
    priority = 1
    
    action {
      block {}
    }
    
    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "CUSTOM"
        
        custom_key {
          header {
            name = "x-tenant-id"
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "tenant-rate-limit"
      sampled_requests_enabled   = true
    }
  }
  
  # SQL injection protection
  rule {
    name     = "sqli-protection"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "sqli-protection"
      sampled_requests_enabled   = true
    }
  }
  
  # Cross-tenant access prevention
  rule {
    name     = "cross-tenant-access-prevention"
    priority = 3
    
    action {
      block {}
    }
    
    statement {
      and_statement {
        statement {
          byte_match_statement {
            search_string         = "/api/v1/tenants/"
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "URL_DECODE"
            }
            positional_constraint = "CONTAINS"
          }
        }
        statement {
          not_statement {
            statement {
              byte_match_statement {
                search_string         = "x-tenant-id"
                field_to_match {
                  single_header {
                    name = "x-tenant-id"
                  }
                }
                text_transformation {
                  priority = 0
                  type     = "NONE"
                }
                positional_constraint = "EXACTLY"
              }
            }
          }
        }
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "cross-tenant-access-attempts"
      sampled_requests_enabled   = true
    }
  }
}
```

### 6.6 Secrets Management

```hcl
# HashiCorp Vault configuration for tenant secrets
resource "vault_mount" "tenant" {
  path        = "tenants/${var.tenant_id}"
  type        = "kv-v2"
  description = "Secrets for tenant ${var.tenant_name}"
}

resource "vault_kv_secret_v2" "tenant_api_key" {
  mount = vault_mount.tenant.path
  name  = "api-key"
  
  data_json = jsonencode({
    key = var.tenant_api_key
  })
}

resource "vault_kv_secret_v2" "tenant_db_credentials" {
  mount = vault_mount.tenant.path
  name  = "database"
  
  data_json = jsonencode({
    username = "tenant_${var.tenant_id}"
    password = random_password.tenant_db.result
    host     = var.db_host
    port     = 5432
  })
}

# Policy: tenant can only access its own secrets
resource "vault_policy" "tenant_isolation" {
  name = "tenant-${var.tenant_id}-isolation"
  
  policy = <<EOT
# Tenant can read/write its own secrets
path "tenants/${var.tenant_id}/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Tenant cannot access other tenants' secrets
path "tenants/+/+" {
  capabilities = ["deny"]
}

# Platform admin override (separate policy)
path "tenants/*" {
  capabilities = ["read", "list"]
}
EOT
}
```

### 6.7 Data Loss Prevention (DLP)

```python
import re
from typing import List, Tuple

class TenantDLP:
    """Data loss prevention for tenant data."""
    
    # Patterns that indicate sensitive data
    SENSITIVE_PATTERNS = {
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
        "api_key": re.compile(r"\b[A-Za-z0-9]{32,64}\b"),
    }
    
    def scan_text(self, text: str) -> List[Tuple[str, str]]:
        """Scan text for sensitive data patterns."""
        findings = []
        
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            matches = pattern.findall(text)
            for match in matches:
                findings.append((pattern_name, match))
        
        return findings
    
    def sanitize_for_logs(self, text: str) -> str:
        """Remove sensitive data before logging."""
        sanitized = text
        
        for pattern in self.SENSITIVE_PATTERNS.values():
            sanitized = pattern.sub("[REDACTED]", sanitized)
        
        return sanitized
    
    def validate_export(self, tenant_id: str, data: dict) -> bool:
        """Validate data export for compliance."""
        
        # Check for unencrypted sensitive fields
        for key, value in data.items():
            if isinstance(value, str):
                findings = self.scan_text(value)
                if findings:
                    raise DLPViolation(
                        f"Sensitive data found in export field '{key}': "
                        f"{[f[0] for f in findings]}"
                    )
        
        return True
```

---

## 7. Cross-Cutting Concerns

### 7.1 Tenant-Aware Feature Flags

```python
class TenantFeatureFlags:
    """Feature flags with tenant-level granularity."""
    
    DEFAULT_FLAGS = {
        "new_dashboard": False,
        "api_v2": False,
        "advanced_analytics": False,
        "custom_integrations": False,
        "sso": False,
        "audit_log": False,
    }
    
    TIER_DEFAULTS = {
        "free": {
            "new_dashboard": True,
            "api_v2": False,
            "advanced_analytics": False,
            "custom_integrations": False,
            "sso": False,
            "audit_log": False,
        },
        "pro": {
            "new_dashboard": True,
            "api_v2": True,
            "advanced_analytics": True,
            "custom_integrations": False,
            "sso": False,
            "audit_log": True,
        },
        "enterprise": {
            "new_dashboard": True,
            "api_v2": True,
            "advanced_analytics": True,
            "custom_integrations": True,
            "sso": True,
            "audit_log": True,
        },
        "dedicated": {
            "new_dashboard": True,
            "api_v2": True,
            "advanced_analytics": True,
            "custom_integrations": True,
            "sso": True,
            "audit_log": True,
        },
    }
    
    def is_enabled(self, tenant_id: str, feature: str) -> bool:
        """Check if a feature is enabled for a tenant."""
        
        # Check tenant-specific override
        override = self._get_tenant_override(tenant_id, feature)
        if override is not None:
            return override
        
        # Fall back to tier default
        tier = self._get_tenant_tier(tenant_id)
        return self.TIER_DEFAULTS.get(tier, self.DEFAULT_FLAGS).get(feature, False)
```

### 7.2 Tenant Data Residency

```python
class TenantDataResidency:
    """Enforce data residency requirements per tenant."""
    
    REGION_MAPPINGS = {
        "us-east-1": {"provider": "aws", "country": "US"},
        "us-west-2": {"provider": "aws", "country": "US"},
        "eu-west-1": {"provider": "aws", "country": "IE"},
        "eu-central-1": {"provider": "aws", "country": "DE"},
        "ap-southeast-1": {"provider": "aws", "country": "SG"},
        "eastus": {"provider": "azure", "country": "US"},
        "westeurope": {"provider": "azure", "country": "NL"},
        "us-central1": {"provider": "gcp", "country": "US"},
        "europe-west1": {"provider": "gcp", "country": "BE"},
    }
    
    COMPLIANCE_REQUIREMENTS = {
        "gdpr": {"allowed_regions": ["eu-west-1", "eu-central-1", "westeurope", "europe-west1"]},
        "hipaa": {"allowed_regions": ["us-east-1", "us-west-2", "eastus", "us-central1"]},
        "soc2": {"allowed_regions": list(REGION_MAPPINGS.keys())},
    }
    
    def validate_region(self, tenant_id: str, region: str) -> bool:
        """Check if region meets tenant's compliance requirements."""
        
        tenant = self._get_tenant(tenant_id)
        requirements = tenant.compliance_requirements
        
        for req in requirements:
            allowed = self.COMPLIANCE_REQUIREMENTS.get(req, {}).get("allowed_regions", [])
            if region not in allowed:
                return False
        
        return True
    
    def get_allowed_regions(self, tenant_id: str) -> list:
        """Get list of allowed regions for a tenant."""
        
        tenant = self._get_tenant(tenant_id)
        requirements = tenant.compliance_requirements
        
        if not requirements:
            return list(self.REGION_MAPPINGS.keys())
        
        # Intersect all allowed regions
        allowed = None
        for req in requirements:
            regions = set(self.COMPLIANCE_REQUIREMENTS.get(req, {}).get("allowed_regions", []))
            if allowed is None:
                allowed = regions
            else:
                allowed &= regions
        
        return list(allowed) if allowed else []
```

### 7.3 Disaster Recovery

```yaml
# DR strategy per tier
disaster_recovery:
  free:
    rpo: "24h"
    rto: "4h"
    backup_frequency: "daily"
    cross_region_replication: false
    
  pro:
    rpo: "4h"
    rto: "2h"
    backup_frequency: "hourly"
    cross_region_replication: true
    
  enterprise:
    rpo: "1h"
    rto: "30m"
    backup_frequency: "15min"
    cross_region_replication: true
    
  dedicated:
    rpo: "5min"
    rto: "5min"
    backup_frequency: "continuous"
    cross_region_replication: true
    dedicated_dr_region: true
```

---

## 8. Deployment Topology

### 8.1 Multi-Region Active-Active

```
┌─────────────────────────────────────────────────────────────────┐
│                     Global Traffic Manager                       │
│                    (Route 53 / Cloudflare)                       │
└────────────┬────────────────┬────────────────┬──────────────────┘
             │                │                │
    ┌────────▼───────┐ ┌──────▼────────┐ ┌────▼──────────┐
    │  US-East-1     │ │  EU-West-1    │ │  APAC-1       │
    │  (Primary)     │ │  (Secondary)  │ │  (Secondary)  │
    │                │ │               │ │               │
    │  ┌──────────┐  │ │  ┌──────────┐ │ │  ┌──────────┐ │
    │  │ EKS      │  │ │  │ EKS      │ │ │  │ EKS      │ │
    │  │ Cluster  │  │ │  │ Cluster  │ │ │  │ Cluster  │ │
    │  └──────────┘  │ │  └──────────┘ │ │  └──────────┘ │
    │  ┌──────────┐  │ │  ┌──────────┐ │ │  ┌──────────┐ │
    │  │ RDS      │  │ │  │ RDS      │ │ │  │ RDS      │ │
    │  │ Primary  │──┼─┼──▶ Replica  │ │ │  │ Replica  │ │
    │  └──────────┘  │ │  └──────────┘ │ │  └──────────┘ │
    │  ┌──────────┐  │ │  ┌──────────┐ │ │  ┌──────────┐ │
    │  │ S3       │  │ │  │ S3       │ │ │  │ S3       │ │
    │  │ Primary  │──┼─┼──▶ Replica  │ │ │  │ Replica  │ │
    │  └──────────┘  │ │  └──────────┘ │ │  └──────────┘ │
    └────────────────┘ └───────────────┘ └───────────────┘
```

### 8.2 Kubernetes Multi-Tenant Deployment

```yaml
# Namespace structure for multi-tenant EKS
apiVersion: v1
kind: Namespace
metadata:
  name: apex-os-system
  labels:
    apex-os.io/managed-by: "platform"
    apex-os.io/tier: "system"
---
apiVersion: v1
kind: Namespace
metadata:
  name: apex-os-workloads
  labels:
    apex-os.io/managed-by: "platform"
    apex-os.io/tier: "shared"
---
apiVersion: v1
kind: Namespace
metadata:
  name: apex-os-ingress
  labels:
    apex-os.io/managed-by: "platform"
    apex-os.io/tier: "system"
---
apiVersion: v1
kind: Namespace
metadata:
  name: apex-os-monitoring
  labels:
    apex-os.io/managed-by: "platform"
    apex-os.io/tier: "system"
---
# Tenant namespaces are created dynamically
# apiVersion: v1
# kind: Namespace
# metadata:
#   name: tenant-acme-corp
#   labels:
#     apex-os.io/managed-by: "tenant-controller"
#     apex-os.io/tenant-id: "acme-corp-uuid"
#     apex-os.io/tier: "enterprise"
```

---

## 9. Operational Runbooks

### 9.1 Tenant Onboarding Runbook

```markdown
# Runbook: Tenant Onboarding

## Prerequisites
- [ ] Tenant request approved
- [ ] Billing information collected
- [ ] Compliance requirements documented

## Steps

### 1. Create Tenant Record
```bash
curl -X POST https://api.apex-os.io/v1/admin/tenants \
  -H "Authorization: Bearer $PLATFORM_ADMIN_TOKEN" \
  -d '{
    "name": "Acme Corp",
    "slug": "acme-corp",
    "tier": "enterprise",
    "billing_email": "billing@acme.com",
    "admin_email": "admin@acme.com",
    "region": "us-east-1"
  }'
```

### 2. Verify Provisioning
```bash
# Check tenant status
kubectl get namespace tenant-acme-corp
kubectl get pods -n tenant-acme-corp

# Verify database
psql $DATABASE_URL -c "SELECT * FROM tenants WHERE slug = 'acme-corp';"

# Verify storage
aws s3 ls s3://apex-os-tenant-acme-corp-data/
```

### 3. Validate Security
```bash
# Check RLS policies
psql $DATABASE_URL -c "\dp projects"

# Verify network policies
kubectl get networkpolicy -n tenant-acme-corp

# Check encryption
aws kms describe-key --key-id alias/apex-os-tenant-acme-corp
```

### 4. Send Welcome Email
```bash
curl -X POST https://api.apex-os.io/v1/admin/tenants/acme-corp/welcome \
  -H "Authorization: Bearer $PLATFORM_ADMIN_TOKEN"
```

## Rollback
```bash
curl -X DELETE https://api.apex-os.io/v1/admin/tenants/acme-corp \
  -H "Authorization: Bearer $PLATFORM_ADMIN_TOKEN"
```
```

### 9.2 Tenant Incident Response

```markdown
# Runbook: Tenant Incident Response

## Severity Levels

### SEV1: Complete tenant outage
- Tenant cannot access any resources
- All API requests failing
- **Response Time:** 5 minutes
- **Escalation:** Platform on-call + engineering manager

### SEV2: Partial tenant outage
- Some features unavailable
- Elevated error rates
- **Response Time:** 15 minutes
- **Escalation:** Platform on-call

### SEV3: Performance degradation
- Increased latency
- Resource constraints
- **Response Time:** 1 hour
- **Escalation:** Next business day

## Diagnostic Steps

### 1. Identify affected tenant
```bash
# Check tenant status
curl https://api.apex-os.io/v1/admin/tenants/{tenant_id}/status

# Check recent deployments
kubectl rollout history deployment/api -n tenant-{tenant_slug}

# Check resource usage
kubectl top pods -n tenant-{tenant_slug}
```

### 2. Check logs
```bash
# Application logs
kubectl logs -n tenant-{tenant_slug} -l app=api --tail=100

# Platform logs
kubectl logs -n apex-os-system -l app=platform --tail=100
```

### 3. Check metrics
```bash
# Grafana dashboard
open https://grafana.apex-os.io/d/tenant-overview?var-tenant_id={tenant_id}

# Prometheus queries
curl 'http://prometheus:9090/api/v1/query?query=tenant_error_rate{tenant_id="{tenant_id}"}'
```

## Common Issues

### Issue: Tenant pod crash looping
```bash
# Check pod status
kubectl describe pod -n tenant-{tenant_slug} -l app=api

# Check resource limits
kubectl get resourcequota -n tenant-{tenant_slug}

# Scale down and up
kubectl scale deployment api -n tenant-{tenant_slug} --replicas=0
kubectl scale deployment api -n tenant-{tenant_slug} --replicas=2
```

### Issue: Database connection exhaustion
```bash
# Check active connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE application_name LIKE 'tenant:{tenant_id}%';"

# Kill idle connections
psql $DATABASE_URL -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE application_name LIKE 'tenant:{tenant_id}%';"
```

### Issue: Storage quota exceeded
```bash
# Check usage
aws s3 ls s3://apex-os-tenant-{tenant_id}-data/ --recursive --human-readable --summarize

# Notify tenant
curl -X POST https://api.apex-os.io/v1/admin/tenants/{tenant_id}/notify \
  -d '{"type": "storage_quota_warning"}'
```
```

### 9.3 Tenant Migration Runbook

```markdown
# Runbook: Tenant Tier Migration

## Upgrade: Free → Pro

### 1. Pre-migration checks
```bash
# Verify billing setup
curl https://api.apex-os.io/v1/admin/tenants/{tenant_id}/billing

# Check current usage
curl https://api.apex-os.io/v1/admin/tenants/{tenant_id}/usage
```

### 2. Execute migration
```bash
# Update tenant tier
curl -X PATCH https://api.apex-os.io/v1/admin/tenants/{tenant_id} \
  -d '{"tier": "pro"}'

# Update resource quotas
kubectl patch resourcequota tenant-quota -n tenant-{tenant_slug} \
  -p '{"spec":{"hard":{"requests.cpu":"5","requests.memory":"10Gi"}}}'
```

### 3. Verify
```bash
# Check new limits
kubectl describe resourcequota -n tenant-{tenant_slug}

# Verify billing
curl https://api.apex-os.io/v1/admin/tenants/{tenant_id}/billing/subscription
```

## Upgrade: Pro → Enterprise (Schema-per-tenant)

### 1. Create dedicated schema
```bash
psql $DATABASE_URL -c "CREATE SCHEMA tenant_{tenant_slug};"
psql $DATABASE_URL -c "CREATE TABLE tenant_{tenant_slug}.projects (LIKE public.projects INCLUDING ALL);"
```

### 2. Migrate data
```bash
psql $DATABASE_URL -c "
  INSERT INTO tenant_{tenant_slug}.projects
  SELECT * FROM public.projects WHERE tenant_id = '{tenant_id}';
"
```

### 3. Update connection routing
```bash
# Update tenant config
curl -X PATCH https://api.apex-os.io/v1/admin/tenants/{tenant_id} \
  -d '{"isolation_mode": "schema"}'
```

### 4. Verify and cleanup
```bash
# Verify data integrity
psql $DATABASE_URL -c "SELECT count(*) FROM tenant_{tenant_slug}.projects;"

# Remove old data (after verification period)
psql $DATABASE_URL -c "DELETE FROM public.projects WHERE tenant_id = '{tenant_id}';"
```

## Downgrade: Enterprise → Pro

### 1. Pre-downgrade checks
```bash
# Verify no enterprise-specific features in use
curl https://api.apex-os.io/v1/admin/tenants/{tenant_id}/features
```

### 2. Migrate data back to shared schema
```bash
psql $DATABASE_URL -c "
  INSERT INTO public.projects (tenant_id, name, description)
  SELECT '{tenant_id}', name, description FROM tenant_{tenant_slug}.projects
  ON CONFLICT DO NOTHING;
"
```

### 3. Update tenant config
```bash
curl -X PATCH https://api.apex-os.io/v1/admin/tenants/{tenant_id} \
  -d '{"tier": "pro", "isolation_mode": "rls"}'
```

### 4. Cleanup schema (after grace period)
```bash
psql $DATABASE_URL -c "DROP SCHEMA tenant_{tenant_slug} CASCADE;"
```
```

---

## Appendix A: Tenant Resource Limits

| Resource | Free | Pro | Enterprise | Dedicated |
|----------|------|-----|------------|-----------|
| API calls/month | 10,000 | 100,000 | 1,000,000 | 10,000,000 |
| Storage | 5 GB | 50 GB | 500 GB | 5 TB |
| Compute hours/month | 100 | 500 | 5,000 | 50,000 |
| Active users | 5 | 50 | 500 | 5,000 |
| Projects | 3 | 25 | Unlimited | Unlimited |
| Custom domains | 0 | 1 | 10 | Unlimited |
| SSO/SAML | No | No | Yes | Yes |
| Audit log retention | 7 days | 90 days | 365 days | 730 days |
| Support | Community | Email | Priority | Dedicated CSM |

## Appendix B: Compliance Matrix

| Control | Free | Pro | Enterprise | Dedicated |
|---------|------|-----|------------|-----------|
| Data encryption at rest | AES-256 | AES-256 | AES-256 + KMS | AES-256 + KMS + HSM |
| Data encryption in transit | TLS 1.2 | TLS 1.2 | TLS 1.3 | TLS 1.3 + mTLS |
| SOC 2 Type II | No | No | Yes | Yes |
| GDPR | No | Yes | Yes | Yes |
| HIPAA | No | No | Yes | Yes |
| Data residency | No | No | Yes | Yes |
| Audit logging | Basic | Standard | Full | Full + Immutable |
| Backup retention | 7 days | 30 days | 90 days | 365 days |
| RPO | 24h | 4h | 1h | 5min |
| RTO | 4h | 2h | 30min | 5min |

---

*End of document.*
