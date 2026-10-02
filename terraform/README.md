# APEX-OS Business Platform - Terraform Infrastructure

This directory contains the Terraform configuration for the APEX-OS Business Platform infrastructure across AWS, Azure, and GCP.

## Architecture Overview

The infrastructure is organized into the following modules:

### Cloud Providers
- **AWS** (`modules/aws/`): VPC, EKS, RDS, S3, IAM
- **Azure** (`modules/azure/`): VNet, AKS, Storage
- **GCP** (`modules/gcp/`): VPC, GKE, Storage

### Platform Services
- **Kubernetes** (`modules/kubernetes/`): Namespaces, RBAC, Network Policies, Resource Quotas
- **Monitoring** (`modules/monitoring/`): Prometheus, Grafana, Alertmanager, Loki, Tempo
- **Security** (`modules/security/`): Security Groups, WAF, GuardDuty, Security Hub, KMS

## Directory Structure

```
terraform/
├── main.tf                 # Root module orchestrating all infrastructure
├── variables.tf            # Global variables
├── outputs.tf              # Global outputs
├── providers.tf            # Provider configurations
├── versions.tf             # Terraform and provider version constraints
├── backend.tf              # Backend configuration
├── modules/
│   ├── aws/
│   │   ├── vpc/            # AWS VPC, subnets, NAT, route tables, flow logs
│   │   ├── eks/            # AWS EKS cluster and managed node groups
│   │   ├── rds/            # AWS RDS PostgreSQL instance
│   │   ├── s3/             # AWS S3 buckets with encryption and lifecycle
│   │   └── iam/            # AWS IAM policies for EKS addons
│   ├── azure/
│   │   ├── vnet/           # Azure VNet, subnets, NSGs
│   │   ├── aks/            # Azure AKS cluster
│   │   └── storage/        # Azure Storage accounts
│   ├── gcp/
│   │   ├── vpc/            # GCP VPC, subnets, Cloud NAT, firewall rules
│   │   ├── gke/            # GCP GKE cluster
│   │   └── storage/        # GCP Cloud Storage buckets
│   ├── kubernetes/
│   │   └── core/           # K8s namespaces, RBAC, network policies, quotas
│   ├── monitoring/         # Prometheus, Grafana, Alertmanager, Loki, Tempo
│   └── security/           # Security groups, WAF, GuardDuty, Security Hub
```

## Prerequisites

- Terraform >= 1.5.0
- AWS CLI configured with appropriate credentials
- Azure CLI logged in
- GCP CLI authenticated with application default credentials

## Usage

### Initialize
```bash
cd terraform
terraform init
```

### Plan
```bash
terraform plan -var-file="environments/dev.tfvars"
```

### Apply
```bash
terraform apply -var-file="environments/dev.tfvars"
```

### Destroy
```bash
terraform destroy -var-file="environments/dev.tfvars"
```

## Environment Configuration

Create environment-specific variable files in the `environments/` directory:

### dev.tfvars
```hcl
environment = "dev"
project_name = "apex-os"

aws_region = "us-east-1"
azure_location = "East US"
gcp_region = "us-central1"

aws_eks_node_desired_size = 2
azure_aks_node_count = 2
gcp_gke_node_count = 2
```

### prod.tfvars
```hcl
environment = "prod"
project_name = "apex-os"

aws_region = "us-east-1"
azure_location = "East US"
gcp_region = "us-central1"

aws_eks_node_desired_size = 5
azure_aks_node_count = 5
gcp_gke_node_count = 5

aws_rds_multi_az = true
security_enable_shield = true
```

## Security

- All storage is encrypted at rest by default
- TLS/SSL encryption in transit is enforced
- Network policies implement default-deny with explicit allow rules
- WAF with AWS Managed Rules protects web applications
- GuardDuty and Security Hub provide threat detection
- KMS keys with automatic rotation for encryption

## Monitoring

- Prometheus for metrics collection with 30-day retention
- Grafana for visualization with pre-configured dashboards
- Alertmanager for alert routing and notification
- Loki for log aggregation
- Tempo for distributed tracing

## Cost Optimization

- Non-production environments use smaller instance types
- S3 lifecycle policies transition data to cheaper storage classes
- GKE and EKS cluster autoscaling configured with appropriate min/max
- Spot instances available for non-critical workloads
