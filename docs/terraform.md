# Terraform — Infrastructure as Code

## 1. Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TB
    subgraph Local["Developer Workstation"]
        TF_CONFIG["*.tf files"]
        TF_VARS["*.tfvars"]
        TF_STATE_LOCAL["local state (dev only)"]
    end

    subgraph CI["CI Pipeline"]
        TF_PLAN["terraform plan"]
        TF_APPLY["terraform apply"]
    end

    subgraph Remote["Remote State Backend"]
        S3["S3 Bucket\nterraform-state"]
        DYNAMO["DynamoDB Table\nlock table"]
    end

    subgraph Cloud["AWS Cloud"]
        VPC["VPC / Subnets / IGW"]
        EKS["EKS Cluster"]
        RDS["RDS PostgreSQL"]
        ELASTICACHE["ElastiCache Redis"]
        ALB["Application Load Balancer"]
        IAM["IAM Roles / Policies"]
        CW["CloudWatch Logs & Metrics"]
    end

    TF_CONFIG --> TF_PLAN
    TF_VARS --> TF_PLAN
    TF_PLAN --> TF_APPLY
    TF_APPLY -->|"state lock"| DYNAMO
    TF_APPLY -->|"read/write state"| S3
    TF_APPLY --> VPC
    TF_APPLY --> EKS
    TF_APPLY --> RDS
    TF_APPLY --> ELASTICACHE
    TF_APPLY --> ALB
    TF_APPLY --> IAM
    TF_APPLY --> CW
```

## 2. Module Structure

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    ROOT["main.tf\n(root module)"]

    ROOT --> NET["modules/networking"]
    ROOT --> COMP["modules/compute"]
    ROOT --> DATA["modules/data"]
    ROOT --> SEC["modules/security"]
    ROOT --> OBS["modules/observability"]

    NET --> NET_VPC["vpc"]
    NET --> NET_SG["security-groups"]
    NET --> NET_RT["route-tables"]

    COMP --> COMP_EKS["eks"]
    COMP --> COMP_NODE["node-groups"]
    COMP --> COMP_ALB["alb"]

    DATA --> DATA_RDS["rds"]
    DATA --> DATA_REDIS["elasticache"]
    DATA --> DATA_S3["s3"]

    SEC --> SEC_IAM["iam"]
    SEC --> SEC_KMS["kms"]
    SEC --> SEC_SM["secrets-manager"]

    OBS --> OBS_CW["cloudwatch"]
    OBS --> OBS_GF["grafana"]
```

### Module Layout

```
modules/
├── networking/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
├── compute/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
├── data/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
├── security/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
└── observability/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── versions.tf
```

## 3. State Management

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Locking["State Locking"]
        DDB["DynamoDB\nLockID item"]
        S3["S3\nstate file JSON"]
    end

    subgraph Environments["Environment Isolation"]
        DEV["dev/\nterraform.tfstate"]
        STAGING["staging/\nterraform.tfstate"]
        PROD["prod/\nterraform.tfstate"]
    end

    subgraph Backend["Backend Configuration"]
        BT["terraform {\n  backend \"s3\" {\n    bucket = \"...\"\n    key    = \"...\"\n    region = \"...\"\n    dynamodb_table = \"...\"\n  }\n}"]
    end

    BT --> S3
    BT --> DDB
    S3 --> DEV
    S3 --> STAGING
    S3 --> PROD
```

### Backend Configuration

```hcl
terraform {
  backend "s3" {
    bucket         = "apex-os-tf-state"
    key            = "env:/${var.environment}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

### State Commands

| Command | Purpose |
|---------|---------|
| `terraform state list` | List resources in state |
| `terraform state show <resource>` | Inspect a single resource |
| `terraform state rm <resource>` | Remove resource from state |
| `terraform state mv <old> <new>` | Rename/move resource |
| `terraform import <resource> <id>` | Import existing infrastructure |
| `terraform force-unlock <LOCKID>` | Break stale lock (use with caution) |

## 4. Deployment

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    INIT["terraform init"] --> FMT["terraform fmt -check"]
    FMT --> VALID["terraform validate"]
    VALID --> PLAN["terraform plan -out=tfplan"]
    PLAN --> REVIEW{"Manual Review"}
    REJECTED["Reject & Revise"] --> FMT
    REVIEW -->|Approved| APPLY["terraform apply tfplan"]
    APPLY --> VERIFY["Smoke Tests / Health Checks"]
    VERIFY -->|Failed| ROLLBACK["terraform apply -replace / rollback"]
    VERIFY -->|Passed| DONE["Deployment Complete"]
    ROLLBACK --> APPLY
```

### Environment Promotion

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    DEV["Dev\n(auto-apply on PR merge)"] --> STG["Staging\n(auto-apply on tag)"]
    STG --> PRD["Production\n(manual approval gate)"]
```

### Deployment Commands

```bash
# Initialize with backend
terraform init -backend-config="environments/dev/backend.hcl"

# Plan with variable files
terraform plan -var-file="environments/dev/terraform.tfvars" -out=tfplan

# Apply saved plan
terraform apply tfplan

# Destroy (dev only)
terraform destroy -var-file="environments/dev/terraform.tfvars"
```

### CI/CD Integration

```yaml
# .github/workflows/terraform.yml (excerpt)
- name: Terraform Plan
  run: terraform plan -no-color -out=tfplan
- name: Terraform Apply
  if: github.ref == 'refs/heads/main'
  run: terraform apply -auto-approve tfplan
```

## 5. Monitoring

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TB
    subgraph Infra["Infrastructure Metrics"]
        CW_CPU["CPU Utilization"]
        CW_MEM["Memory Utilization"]
        CW_NET["Network I/O"]
        CW_DISK["Disk I/O"]
    end

    subgraph App["Application Metrics"]
        REQ["Request Rate"]
        LAT["Latency (p50/p95/p99)"]
        ERR["Error Rate"]
        SAT["Saturation"]
    end

    subgraph Alerts["Alerting"]
        ALERT_CPU["CPU > 80% for 5m"]
        ALERT_MEM["Memory > 85% for 5m"]
        ALERT_ERR["5xx rate > 1%"]
        ALERT_LAT["p99 latency > 500ms"]
    end

    subgraph Dashboards["Dashboards"]
        GRAFANA["Grafana\nService Overview"]
        CW_DASH["CloudWatch\nInfra Overview"]
    end

    CW_CPU --> ALERT_CPU
    CW_MEM --> ALERT_MEM
    REQ --> GRAFANA
    LAT --> ALERT_LAT
    ERR --> ALERT_ERR
    LAT --> GRAFANA
    ERR --> GRAFANA
    CW_CPU --> CW_DASH
    CW_MEM --> CW_DASH
```

### Key Metrics

| Metric | Source | Threshold | Action |
|--------|--------|-----------|--------|
| Node CPU | CloudWatch | > 80% | Scale node group |
| Node Memory | CloudWatch | > 85% | Scale node group |
| RDS Connections | CloudWatch | > 80% max | Increase max_connections |
| ALB 5xx | ALB Access Log | > 1% | Page on-call |
| Request Latency | Grafana / Prometheus | p99 > 500ms | Investigate |
| Pod Restart | Kubernetes | > 3 in 10m | Alert + auto-rollback |

### Observability Stack

- **Metrics**: Prometheus + Grafana (app), CloudWatch (infra)
- **Logs**: CloudWatch Logs → Fluent Bit → OpenSearch
- **Tracing**: AWS X-Ray / OpenTelemetry
- **Alerting**: PagerDuty via Grafana / CloudWatch Alarms
