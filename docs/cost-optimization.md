# APEX-OS Business Platform — Cost Optimization Playbook

> **Version:** 1.0.0  
> **Last Updated:** 2026-10-01  
> **Scope:** AWS (EKS, RDS, S3), Azure (AKS, Storage), GCP (GKE, Storage), Kubernetes workloads, Monitoring stack

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Right-Sizing](#2-right-sizing)
3. [Spot Instances](#3-spot-instances)
4. [Reserved Instances & Savings Plans](#4-reserved-instances--savings-plans)
5. [Auto-Scaling](#5-auto-scaling)
6. [Cost Monitoring & Governance](#6-cost-monitoring--governance)
7. [Implementation Roadmap](#7-implementation-roadmap)
8. [Quick-Win Checklist](#8-quick-win-checklist)

---

## 1. Executive Summary

APEX-OS Business Platform runs a multi-cloud Kubernetes workload across AWS, Azure, and GCP with a full observability stack (Prometheus, Grafana, Loki, Tempo) and managed databases. This playbook provides actionable strategies to reduce cloud spend by **30–60%** without compromising reliability or performance.

| Strategy | Estimated Savings | Effort | Risk |
|----------|------------------|--------|------|
| Right-sizing | 15–25% | Low | Low |
| Spot instances | 20–40% (compute) | Medium | Medium |
| Reserved instances / Savings Plans | 30–50% (baseline) | Low | Low |
| Auto-scaling | 10–20% | Medium | Low |
| Cost monitoring | 5–10% (waste elimination) | Low | Low |

---

## 2. Right-Sizing

### 2.1 Current State Analysis

| Resource | Current Size | Cloud | Utilization Target |
|----------|-------------|-------|-------------------|
| EKS nodes | `t3.large` (2 vCPU, 8 GiB) | AWS | 60–80% CPU, 60–80% memory |
| RDS PostgreSQL | `db.t3.medium` (2 vCPU, 4 GiB) | AWS | 50–70% CPU |
| AKS nodes | `Standard_D2s_v3` (2 vCPU, 8 GiB) | Azure | 60–80% CPU |
| GKE nodes | `e2-medium` (2 vCPU, 4 GiB) | GCP | 60–80% CPU |
| S3 buckets | Standard tier | AWS | Lifecycle-managed |

### 2.2 Methodology

1. **Collect metrics** for 2–4 weeks using existing Prometheus + Grafana stack
2. **Identify underutilized resources** (CPU < 30%, memory < 40% sustained)
3. **Identify oversized resources** (CPU > 80% sustained → need larger, not smaller)
4. **Apply changes** in staging first, then production

### 2.3 AWS Right-Sizing

#### EKS Worker Nodes

```hcl
# terraform/variables.tf — right-sized defaults
variable "aws_eks_node_instance_types" {
  description = "Instance types for EKS managed node groups"
  type        = list(string)
  default     = ["t3.large"]  # Keep t3.large for prod; use t3.medium for dev/staging
}

# Recommended by environment:
#   dev/staging: t3.medium (2 vCPU, 4 GiB) — 50% cost reduction
#   prod:        t3.large (2 vCPU, 8 GiB) — if memory-bound
#   prod alt:    t3.xlarge (4 vCPU, 16 GiB) — if CPU-bound, fewer nodes needed
```

**Actions:**
- Enable **AWS Compute Optimizer** (free) for automated recommendations
- Use **Karpenter** or **Cluster Autoscaler** with multiple instance type options
- Set resource requests/limits on all pods (see Kubernetes section)

#### RDS PostgreSQL

```hcl
# Current: db.t3.medium (2 vCPU, 4 GiB)
# Recommendations:
#   dev/staging: db.t3.small (2 vCPU, 2 GiB) — 50% cost reduction
#   prod:        db.t3.large (2 vCPU, 8 GiB) — if memory-bound
#   prod alt:    db.m6g.large (2 vCPU, 8 GiB, Graviton) — 20% cheaper + better perf
```

**Actions:**
- Enable **RDS Performance Insights** (free tier: 7 days retention)
- Use **Graviton-based instances** (m6g, t4g) for 20–30% better price/performance
- Right-size storage: enable storage autoscaling with `max_allocated_storage`
- Use **Multi-AZ only in prod**; disable for dev/staging

#### S3 Storage

```hcl
# Enable lifecycle policies for all buckets
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }
  }
}
```

### 2.4 Azure Right-Sizing

| Resource | Current | Recommended (dev/staging) | Recommended (prod) |
|----------|---------|---------------------------|---------------------|
| AKS nodes | `Standard_D2s_v3` | `Standard_B2s` (burstable) | `Standard_D2s_v3` or `Standard_D4s_v3` |
| Storage | Standard_LRS | Standard_LRS | Standard_ZRS (prod HA) |

**Actions:**
- Use **Azure Advisor** (free) for right-sizing recommendations
- Consider **B-series burstable VMs** for dev/test workloads
- Use **Spot VMs** for AKS node pools (see Spot section)

### 2.5 GCP Right-Sizing

| Resource | Current | Recommended (dev/staging) | Recommended (prod) |
|----------|---------|---------------------------|---------------------|
| GKE nodes | `e2-medium` | `e2-small` | `e2-medium` or `e2-standard-2` |
| Storage | Standard | Nearline (backups) | Standard |

**Actions:**
- Use **GCP Recommender** (free) for right-sizing
- Use **committed use discounts** for baseline workloads
- Consider **Spot VMs** for GKE node pools

### 2.6 Kubernetes Resource Right-Sizing

```yaml
# Example: Set resource requests and limits on all deployments
# helm/values.yaml or per-service values

resources:
  requests:
    cpu: "100m"      # Guaranteed minimum
    memory: "128Mi"
  limits:
    cpu: "500m"      # Burst ceiling
    memory: "512Mi"
```

**Actions:**
- Install **Goldilocks** (Fairwinds) or **Kubecost** for automated resource recommendations
- Use **Vertical Pod Autoscaler (VPA)** in recommendation mode first
- Set `requests` = `limits` for Guaranteed QoS on critical services
- Set `requests` < `limits` for Burstable QoS on non-critical services

---

## 3. Spot Instances

### 3.1 Overview

Spot instances provide **60–90% discount** on compute in exchange for potential interruption (2-minute warning). Ideal for stateless, fault-tolerant workloads.

### 3.2 AWS Spot Strategy

#### EKS Spot Node Groups

```hcl
# terraform/modules/aws/eks — add spot node group
resource "aws_eks_node_group" "spot" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-spot"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.private_subnet_ids

  # Mix of instance types for spot capacity optimization
  instance_types = ["t3.large", "t3a.large", "m5.large", "m5a.large"]

  scaling_config {
    desired_size = var.spot_desired_size
    min_size     = var.spot_min_size
    max_size     = var.spot_max_size
  }

  # Spot capacity type
  capacity_type = "SPOT"

  # Taint to prevent non-spot-tolerant workloads
  taint {
    key    = "spot"
    value  = "true"
    effect = "NO_SCHEDULE"
  }

  tags = merge(var.tags, {
    "k8s.io/cluster-autoscaler/enabled"             = "true"
    "k8s.io/cluster-autoscaler/${var.cluster_name}" = "owned"
  })
}
```

#### Spot-Tolerant Workloads

| Workload | Spot-Tolerant | Notes |
|----------|--------------|-------|
| API Gateway | Yes | Stateless, auto-scaling |
| Web Frontend | Yes | CDN-backed |
| Background Jobs | Yes | Retry logic required |
| PostgreSQL | No | Use on-demand or reserved |
| Redis/ElastiCache | No | Data loss risk |
| Prometheus | No | Data loss risk |
| Grafana | Yes | Stateless UI |
| Loki | No | Data loss risk |
| Tempo | No | Data loss risk |

#### Spot Interruption Handling

```yaml
# Pod Disruption Budget for spot-tolerant workloads
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-gateway-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: api-gateway
```

```yaml
# Deployment with spot toleration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
spec:
  template:
    spec:
      tolerations:
        - key: "spot"
          operator: "Equal"
          value: "true"
          effect: "NO_SCHEDULE"
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: "capacity-type"
                    operator: In
                    values: ["SPOT"]
```

### 3.3 Azure Spot Strategy

```hcl
# terraform/modules/azure/aks — spot node pool
resource "azurerm_kubernetes_cluster_node_pool" "spot" {
  name                  = "spot"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size               = "Standard_D2s_v3"
  node_count            = 1

  # Spot configuration
  priority        = "Spot"
  eviction_policy = "Delete"
  spot_max_price  = 0.05  # Max price per hour (USD)

  node_taints = ["spot=true:NoSchedule"]
  node_labels = {
    "capacity-type" = "spot"
  }

  tags = var.tags
}
```

### 3.4 GCP Spot Strategy

```hcl
# terraform/modules/gcp/gke — spot node pool
resource "google_container_node_pool" "spot" {
  name       = "spot-pool"
  cluster    = google_container_cluster.main.id
  node_count = 1

  node_config {
    machine_type = "e2-medium"

    # Spot VMs
    spot = true

    taint {
      key    = "spot"
      value  = "true"
      effect = "NO_SCHEDULE"
    }

    labels = {
      "capacity-type" = "spot"
    }
  }

  autoscaling {
    min_node_count = 0
    max_node_count = 5
  }
}
```

### 3.5 Spot Best Practices

1. **Diversify instance types** — use multiple families to reduce interruption risk
2. **Set appropriate max price** — use on-demand price as max for critical workloads
3. **Implement graceful shutdown** — handle SIGTERM, drain connections
4. **Use Pod Disruption Budgets** — ensure minimum availability
5. **Monitor interruption rates** — track via CloudWatch/Azure Monitor/Cloud Monitoring
6. **Fallback to on-demand** — Cluster Autoscaler/Karpenter handles this automatically

---

## 4. Reserved Instances & Savings Plans

### 4.1 Overview

Commit to 1-year or 3-year terms for baseline capacity in exchange for **30–60% discount** vs on-demand.

### 4.2 AWS Reserved Instances & Savings Plans

#### Compute Savings Plans (Recommended)

| Commitment | Discount | Flexibility |
|-----------|----------|-------------|
| 1-year, no upfront | ~20–30% | High (instance family, region, OS) |
| 1-year, partial upfront | ~30–40% | High |
| 1-year, all upfront | ~40–50% | High |
| 3-year, no upfront | ~40–50% | High |
| 3-year, all upfront | ~60–70% | High |

**Recommendation:** Start with **1-year Compute Savings Plans, no upfront** for baseline capacity.

#### Reserved Instances (EC2)

```hcl
# Purchase via AWS Console or CLI — not Terraform-managed
# Recommended for:
#   - EKS baseline nodes (1–2 nodes always running)
#   - RDS instances (1-year, no upfront for dev/staging)
#   - ElastiCache (if used)
```

#### RDS Reserved Instances

| Environment | Recommendation |
|-------------|---------------|
| dev/staging | 1-year, no upfront (or skip — use start/stop scheduling) |
| prod | 1-year, partial upfront (or 3-year for stable workloads) |

### 4.3 Azure Reserved VM Instances

| Commitment | Discount |
|-----------|----------|
| 1-year | ~20–30% |
| 3-year | ~40–60% |

**Actions:**
- Purchase reservations for AKS baseline nodes
- Use **Azure Hybrid Benefit** if you have existing Windows/SQL licenses
- Consider **Azure Reservations** for storage (1-year or 3-year)

### 4.4 GCP Committed Use Discounts

| Commitment | Discount |
|-----------|----------|
| 1-year | ~30% |
| 3-year | ~50% |

**Actions:**
- Purchase CUDs for GKE baseline nodes
- Use **GCP CUD Analysis** to track utilization
- Consider **Committed Use Discounts** for Cloud SQL (if used)

### 4.5 Reserved Capacity Strategy by Environment

| Environment | Strategy | Estimated Savings |
|-------------|----------|-------------------|
| dev | Start/stop scheduling (nights/weekends) | 60–70% |
| staging | 1-year Savings Plan, no upfront | 20–30% |
| prod | 1-year or 3-year Savings Plan | 30–50% |

### 4.6 Start/Stop Scheduling (Dev/Staging)

```hcl
# AWS: Use Instance Scheduler or Lambda-based solution
# Azure: Use Azure Automation or DevTest Labs
# GCP: Use Cloud Scheduler + Cloud Functions

# Example: AWS Instance Scheduler (CloudFormation)
# Stops: 7 PM – 7 AM weekdays, all day weekends
# Saves: ~65% on dev/staging compute
```

---

## 5. Auto-Scaling

### 5.1 Kubernetes Auto-Scaling

#### Horizontal Pod Autoscaler (HPA)

```yaml
# Enable HPA for all stateless services
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-gateway-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 min cooldown
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

#### Vertical Pod Autoscaler (VPA)

```yaml
# VPA in recommendation mode (no auto-apply)
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: api-gateway-vpa
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-gateway
  updatePolicy:
    updateMode: "Off"  # Recommendation only — review before applying
```

#### Cluster Autoscaler / Karpenter

```hcl
# AWS: Karpenter (recommended over Cluster Autoscaler)
resource "helm_release" "karpenter" {
  name       = "karpenter"
  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = "0.34.0"

  set {
    name  = "settings.clusterName"
    value = module.aws_eks.cluster_name
  }
}
```

```yaml
# Karpenter NodePool — mixed on-demand + spot
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: default
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["spot", "on-demand"]
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["t3.large", "t3a.large", "m5.large"]
      nodeClassRef:
        name: default
  limits:
    cpu: 100
    memory: 400Gi
  disruption:
    consolidationPolicy: WhenUnderutilized
    expireAfter: 720h  # 30 days
```

### 5.2 Cloud Provider Auto-Scaling

#### AWS EKS Auto-Scaling

```hcl
# terraform/variables.tf — auto-scaling configuration
variable "aws_eks_node_desired_size" {
  default = 3  # Start with 3, auto-scaler adjusts
}

variable "aws_eks_node_min_size" {
  default = 2  # Minimum for HA
}

variable "aws_eks_node_max_size" {
  default = 6  # Maximum for cost control
}
```

#### Azure AKS Auto-Scaling

```hcl
resource "azurerm_kubernetes_cluster_node_pool" "default" {
  name                = "default"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size             = "Standard_D2s_v3"

  enable_auto_scaling = true
  min_count           = 2
  max_count           = 6
}
```

#### GCP GKE Auto-Scaling

```hcl
resource "google_container_node_pool" "default" {
  name       = "default"
  cluster    = google_container_cluster.main.id

  autoscaling {
    min_node_count = 2
    max_node_count = 6
  }
}
```

### 5.3 Database Auto-Scaling

#### RDS Storage Autoscaling

```hcl
variable "aws_rds_allocated_storage" {
  default = 100  # Initial storage
}

variable "aws_rds_max_allocated_storage" {
  default = 500  # Max storage (prevents runaway costs)
}
```

#### RDS Read Replicas (Prod)

```hcl
# Add read replicas for read-heavy workloads
resource "aws_db_instance" "replica" {
  count               = var.environment == "prod" ? 1 : 0
  replicate_source_db = aws_db_instance.main.arn
  instance_class      = "db.t3.medium"
}
```

### 5.4 Auto-Scaling Best Practices

1. **Set appropriate min/max bounds** — prevent runaway scaling
2. **Use scale-down cooldowns** — avoid flapping (300s recommended)
3. **Scale on custom metrics** — queue depth, request latency, not just CPU
4. **Use predictive scaling** — AWS Auto Scaling predictive scaling for known patterns
5. **Test scaling behavior** — load test to verify scaling works correctly

---

## 6. Cost Monitoring & Governance

### 6.1 Tagging Strategy

```hcl
# terraform/variables.tf — cost allocation tags
variable "common_tags" {
  type = map(string)
  default = {
    Project     = "apex-os-business-platform"
    ManagedBy   = "terraform"
    Environment = "dev"
    CostCenter  = "engineering"
    Owner       = "platform-team"
  }
}
```

**Required Tags for Cost Allocation:**
- `Environment` — dev, staging, prod
- `Project` — apex-os-business-platform
- `CostCenter` — engineering, product, etc.
- `Owner` — team or individual
- `Service` — api-gateway, database, monitoring, etc.

### 6.2 AWS Cost Monitoring

#### AWS Cost Explorer + Budgets

```hcl
# Monthly budget with alerts
resource "aws_budgets_budget" "monthly" {
  name              = "apex-os-monthly-budget"
  budget_type       = "COST"
  limit_amount      = "5000"  # Adjust to your budget
  limit_unit        = "USD"
  time_period_start = "2026-10-01_00:00"
  time_unit         = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = ["alerts@apex-os.io"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = ["alerts@apex-os.io"]
  }

  cost_filter {
    name = "TagKeyValue"
    values = [
      "user:Project$apex-os-business-platform",
    ]
  }
}
```

#### AWS Cost Anomaly Detection

```hcl
resource "aws_ce_anomaly_monitor" "service_monitor" {
  name              = "apex-os-service-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_ce_anomaly_subscription" "subscription" {
  name      = "apex-os-anomaly-subscription"
  threshold = 100  # $100 minimum anomaly
  frequency = "DAILY"

  monitor_arn_list = [aws_ce_anomaly_monitor.service_monitor.arn]

  subscriber {
    type    = "EMAIL"
    address = "alerts@apex-os.io"
  }
}
```

### 6.3 Azure Cost Management

- Enable **Azure Cost Management** (free)
- Create **budgets** with action groups for alerts
- Use **Azure Advisor** cost recommendations
- Tag all resources for cost allocation

### 6.4 GCP Cost Monitoring

- Enable **Cloud Billing** export to BigQuery
- Create **budgets** with alert thresholds
- Use **GCP Recommender** for cost optimization
- Tag all resources for cost allocation

### 6.5 Kubernetes Cost Monitoring (Kubecost)

```yaml
# Install Kubecost via Helm
helm repo add kubecost https://kubecost.github.io/cost-analyzer/
helm install kubecost kubecost/cost-analyzer \
  --namespace kubecost \
  --create-namespace \
  --set kubecostToken="your-token-here"
```

**Kubecost provides:**
- Cost allocation by namespace, deployment, service
- Right-sizing recommendations
- Spot instance recommendations
- Savings opportunities dashboard

### 6.6 Grafana Cost Dashboard

```yaml
# Add cost dashboard to existing Grafana
# Use cloud provider APIs or Kubecost API to feed data

# Example: AWS Cost Explorer API → Grafana
# Use datasource: https://github.com/kaykaym/aws-cost-exporter
```

### 6.7 Cost Monitoring Best Practices

1. **Daily cost alerts** — anomaly detection for unexpected spikes
2. **Weekly cost reviews** — team review of cost trends
3. **Monthly cost reports** — leadership reporting with cost per service
4. **Tag compliance enforcement** — AWS Config rules or Azure Policy
5. **Rightsizing alerts** — automated notifications for underutilized resources
6. **Budget enforcement** — auto-shutdown or scaling limits when budget exceeded

---

## 7. Implementation Roadmap

### Phase 1: Quick Wins (Week 1–2)

- [ ] Enable AWS Compute Optimizer, Azure Advisor, GCP Recommender
- [ ] Tag all resources with cost allocation tags
- [ ] Set up billing alerts and budgets
- [ ] Right-size dev/staging environments (t3.medium, B2s, e2-small)
- [ ] Enable S3 lifecycle policies
- [ ] Disable Multi-AZ for dev/staging RDS

### Phase 2: Auto-Scaling (Week 3–4)

- [ ] Deploy Karpenter (AWS) or configure Cluster Autoscaler
- [ ] Enable HPA for all stateless services
- [ ] Configure VPA in recommendation mode
- [ ] Set up start/stop scheduling for dev/staging
- [ ] Configure RDS storage autoscaling

### Phase 3: Spot Instances (Week 5–6)

- [ ] Deploy spot node groups (EKS, AKS, GKE)
- [ ] Add spot tolerations to stateless workloads
- [ ] Configure Pod Disruption Budgets
- [ ] Test spot interruption handling
- [ ] Monitor spot interruption rates

### Phase 4: Reserved Capacity (Week 7–8)

- [ ] Analyze baseline capacity requirements
- [ ] Purchase 1-year Savings Plans (AWS), Reservations (Azure), CUDs (GCP)
- [ ] Purchase RDS Reserved Instances (prod)
- [ ] Set up CUD/reservation utilization tracking

### Phase 5: Cost Monitoring (Week 9–10)

- [ ] Deploy Kubecost for Kubernetes cost visibility
- [ ] Create Grafana cost dashboards
- [ ] Set up cost anomaly detection
- [ ] Implement weekly cost review process
- [ ] Document cost per service/team

---

## 8. Quick-Win Checklist

| Action | Savings | Time to Implement |
|--------|---------|-------------------|
| Right-size dev/staging instances | 20–30% | 1 hour |
| Enable S3 lifecycle policies | 10–20% (storage) | 30 minutes |
| Set up billing alerts | Prevents surprises | 15 minutes |
| Tag all resources | Enables cost allocation | 1 hour |
| Enable auto-scaling (HPA) | 10–20% | 2 hours |
| Deploy spot node groups | 20–40% (compute) | 4 hours |
| Purchase Savings Plans (baseline) | 30–50% | 2 hours |
| Start/stop scheduling (dev) | 60–70% (dev) | 1 hour |
| Deploy Kubecost | Visibility | 1 hour |
| Enable RDS storage autoscaling | Prevents over-provisioning | 30 minutes |

---

## Appendix A: Terraform Variables for Cost Optimization

```hcl
# Add to terraform/variables.tf

variable "cost_optimization_enabled" {
  description = "Enable cost optimization features"
  type        = bool
  default     = true
}

variable "spot_enabled" {
  description = "Enable spot instance node groups"
  type        = bool
  default     = true
}

variable "spot_desired_size" {
  description = "Desired number of spot nodes"
  type        = number
  default     = 1
}

variable "spot_min_size" {
  description = "Minimum number of spot nodes"
  type        = number
  default     = 0
}

variable "spot_max_size" {
  description = "Maximum number of spot nodes"
  type        = number
  default     = 4
}

variable "dev_start_stop_schedule" {
  description = "Enable start/stop scheduling for dev environment"
  type        = bool
  default     = true
}

variable "rds_max_allocated_storage" {
  description = "Maximum RDS storage in GB"
  type        = number
  default     = 500
}
```

## Appendix B: Useful Commands

```bash
# AWS Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2026-09-01,End=2026-10-01 \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UnblendedCost" \
  --group-by Type=DIMENSION,Key=SERVICE

# Azure Cost Management
az consumption usage list --billing-period-name 20261001

# GCP Billing
gcloud billing accounts list
gcloud beta billing accounts get-ia --billing-account=XXXXXX

# Kubernetes resource usage
kubectl top nodes
kubectl top pods --all-namespaces
kubectl describe node <node-name>
```

---

*This playbook should be reviewed and updated quarterly as cloud pricing and platform requirements evolve.*
