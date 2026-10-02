# =============================================================================
# General Variables
# =============================================================================

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "apex-os"
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project     = "apex-os-business-platform"
    ManagedBy   = "terraform"
    Environment = "dev"
  }
}

# =============================================================================
# AWS Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_availability_zones" {
  description = "AWS availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "aws_vpc_cidr" {
  description = "CIDR block for AWS VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "aws_private_subnet_cidrs" {
  description = "CIDR blocks for AWS private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "aws_public_subnet_cidrs" {
  description = "CIDR blocks for AWS public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "aws_eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "aws_eks_node_instance_types" {
  description = "Instance types for EKS managed node groups"
  type        = list(string)
  default     = ["t3.large"]
}

variable "aws_eks_node_desired_size" {
  description = "Desired number of EKS worker nodes"
  type        = number
  default     = 3
}

variable "aws_eks_node_min_size" {
  description = "Minimum number of EKS worker nodes"
  type        = number
  default     = 2
}

variable "aws_eks_node_max_size" {
  description = "Maximum number of EKS worker nodes"
  type        = number
  default     = 6
}

variable "aws_rds_engine" {
  description = "RDS database engine"
  type        = string
  default     = "postgres"
}

variable "aws_rds_engine_version" {
  description = "RDS database engine version"
  type        = string
  default     = "15.4"
}

variable "aws_rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "aws_rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 100
}

variable "aws_rds_multi_az" {
  description = "Enable Multi-AZ for RDS"
  type        = bool
  default     = true
}

variable "aws_s3_bucket_names" {
  description = "List of S3 bucket names to create"
  type        = list(string)
  default     = ["apex-os-data", "apex-os-backups", "apex-os-logs"]
}

# =============================================================================
# Azure Variables
# =============================================================================

variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = ""
}

variable "azure_tenant_id" {
  description = "Azure tenant ID"
  type        = string
  default     = ""
}

variable "azure_location" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "East US"
}

variable "azure_resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "apex-os-rg"
}

variable "azure_vnet_cidr" {
  description = "CIDR block for Azure VNet"
  type        = string
  default     = "10.1.0.0/16"
}

variable "azure_aks_kubernetes_version" {
  description = "Kubernetes version for AKS cluster"
  type        = string
  default     = "1.28"
}

variable "azure_aks_node_count" {
  description = "Number of AKS worker nodes"
  type        = number
  default     = 3
}

variable "azure_aks_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

# =============================================================================
# GCP Variables
# =============================================================================

variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region for resource deployment"
  type        = string
  default     = "us-central1"
}

variable "gcp_vpc_cidr" {
  description = "CIDR block for GCP VPC"
  type        = string
  default     = "10.2.0.0/16"
}

variable "gcp_gke_cluster_version" {
  description = "Kubernetes version for GKE cluster"
  type        = string
  default     = "1.28"
}

variable "gcp_gke_node_count" {
  description = "Number of GKE worker nodes"
  type        = number
  default     = 3
}

variable "gcp_gke_machine_type" {
  description = "Machine type for GKE nodes"
  type        = string
  default     = "e2-medium"
}

# =============================================================================
# Kubernetes Variables
# =============================================================================

variable "k8s_namespaces" {
  description = "List of Kubernetes namespaces to create"
  type        = list(string)
  default     = ["apex-os-core", "apex-os-data", "apex-os-monitoring", "apex-os-security"]
}

variable "k8s_enable_istio" {
  description = "Enable Istio service mesh"
  type        = bool
  default     = false
}

variable "k8s_enable_cert_manager" {
  description = "Enable cert-manager"
  type        = bool
  default     = true
}

# =============================================================================
# Monitoring Variables
# =============================================================================

variable "monitoring_retention_days" {
  description = "Metrics retention period in days"
  type        = number
  default     = 30
}

variable "monitoring_alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
  default     = "alerts@apex-os.io"
}

variable "monitoring_grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "monitoring_enable_prometheus" {
  description = "Enable Prometheus monitoring"
  type        = bool
  default     = true
}

variable "monitoring_enable_grafana" {
  description = "Enable Grafana dashboards"
  type        = bool
  default     = true
}

variable "monitoring_enable_alertmanager" {
  description = "Enable Alertmanager"
  type        = bool
  default     = true
}

variable "monitoring_enable_loki" {
  description = "Enable Loki log aggregation"
  type        = bool
  default     = true
}

variable "monitoring_enable_tempo" {
  description = "Enable Tempo distributed tracing"
  type        = bool
  default     = true
}

# =============================================================================
# Security Variables
# =============================================================================

variable "security_allowed_cidr_blocks" {
  description = "Allowed CIDR blocks for security groups"
  type        = list(string)
  default     = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
}

variable "security_enable_waf" {
  description = "Enable AWS WAF"
  type        = bool
  default     = true
}

variable "security_enable_shield" {
  description = "Enable AWS Shield Advanced"
  type        = bool
  default     = false
}

variable "security_enable_guardduty" {
  description = "Enable AWS GuardDuty"
  type        = bool
  default     = true
}

variable "security_enable_securityhub" {
  description = "Enable AWS Security Hub"
  type        = bool
  default     = true
}

variable "security_enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "security_enable_encryption_at_rest" {
  description = "Enable encryption at rest for all storage"
  type        = bool
  default     = true
}

variable "security_enable_encryption_in_transit" {
  description = "Enable TLS/SSL encryption in transit"
  type        = bool
  default     = true
}
