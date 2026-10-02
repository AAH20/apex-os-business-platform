# =============================================================================
# APEX-OS Business Platform - Main Terraform Configuration
# =============================================================================
# This is the root module that orchestrates all infrastructure components
# across AWS, Azure, GCP, Kubernetes, Monitoring, and Security.
# =============================================================================

# =============================================================================
# Local Values
# =============================================================================

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(var.common_tags, {
    Environment = var.environment
    Project     = var.project_name
  })

  # Merge environment-specific tags
  environment_tags = var.environment == "prod" ? {
    Criticality = "high"
    Backup      = "required"
  } : var.environment == "staging" ? {
    Criticality = "medium"
    Backup      = "required"
  } : {
    Criticality = "low"
    Backup      = "optional"
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_eks_cluster_auth" "eks" {
  name = module.aws_eks.cluster_name
}

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# =============================================================================
# AWS Infrastructure Module
# =============================================================================

module "aws_vpc" {
  source = "./modules/aws/vpc"

  name_prefix              = local.name_prefix
  vpc_cidr                 = var.aws_vpc_cidr
  private_subnet_cidrs     = var.aws_private_subnet_cidrs
  public_subnet_cidrs      = var.aws_public_subnet_cidrs
  availability_zones       = var.aws_availability_zones
  enable_flow_logs         = var.security_enable_flow_logs
  enable_encryption_at_rest = var.security_enable_encryption_at_rest
  tags                     = local.common_tags
}

module "aws_eks" {
  source = "./modules/aws/eks"

  cluster_name       = "${local.name_prefix}-eks"
  cluster_version    = var.aws_eks_cluster_version
  vpc_id             = module.aws_vpc.vpc_id
  private_subnet_ids = module.aws_vpc.private_subnet_ids
  node_instance_types = var.aws_eks_node_instance_types
  node_desired_size  = var.aws_eks_node_desired_size
  node_min_size      = var.aws_eks_node_min_size
  node_max_size      = var.aws_eks_node_max_size
  tags               = local.common_tags
}

module "aws_rds" {
  source = "./modules/aws/rds"

  identifier           = "${local.name_prefix}-db"
  engine               = var.aws_rds_engine
  engine_version       = var.aws_rds_engine_version
  instance_class       = var.aws_rds_instance_class
  allocated_storage    = var.aws_rds_allocated_storage
  multi_az             = var.aws_rds_multi_az
  vpc_id               = module.aws_vpc.vpc_id
  subnet_ids           = module.aws_vpc.private_subnet_ids
  allowed_cidr_blocks  = var.security_allowed_cidr_blocks
  tags                 = local.common_tags
}

module "aws_s3" {
  source = "./modules/aws/s3"

  bucket_names             = var.aws_s3_bucket_names
  name_prefix              = local.name_prefix
  enable_encryption_at_rest = var.security_enable_encryption_at_rest
  tags                     = local.common_tags
}

module "aws_iam" {
  source = "./modules/aws/iam"

  name_prefix = local.name_prefix
  tags        = local.common_tags
}

# =============================================================================
# Azure Infrastructure Module
# =============================================================================

module "azure_vnet" {
  source = "./modules/azure/vnet"

  name_prefix         = local.name_prefix
  location            = var.azure_location
  resource_group_name = var.azure_resource_group_name
  vnet_cidr           = var.azure_vnet_cidr
  tags                = local.common_tags
}

module "azure_aks" {
  source = "./modules/azure/aks"

  cluster_name         = "${local.name_prefix}-aks"
  location             = var.azure_location
  resource_group_name  = var.azure_resource_group_name
  kubernetes_version   = var.azure_aks_kubernetes_version
  vnet_id              = module.azure_vnet.vnet_id
  subnet_id            = module.azure_vnet.aks_subnet_id
  node_count           = var.azure_aks_node_count
  vm_size              = var.azure_aks_vm_size
  tags                 = local.common_tags
}

module "azure_storage" {
  source = "./modules/azure/storage"

  name_prefix         = local.name_prefix
  location            = var.azure_location
  resource_group_name = var.azure_resource_group_name
  tags                = local.common_tags
}

# =============================================================================
# GCP Infrastructure Module
# =============================================================================

module "gcp_vpc" {
  source = "./modules/gcp/vpc"

  name_prefix    = local.name_prefix
  project_id     = var.gcp_project_id
  region         = var.gcp_region
  vpc_cidr       = var.gcp_vpc_cidr
  tags           = local.common_tags
}

module "gcp_gke" {
  source = "./modules/gcp/gke"

  cluster_name       = "${local.name_prefix}-gke"
  project_id         = var.gcp_project_id
  region             = var.gcp_region
  kubernetes_version = var.gcp_gke_cluster_version
  vpc_id             = module.gcp_vpc.vpc_id
  subnet_id          = module.gcp_vpc.gke_subnet_id
  node_count         = var.gcp_gke_node_count
  machine_type       = var.gcp_gke_machine_type
  tags               = local.common_tags
}

module "gcp_storage" {
  source = "./modules/gcp/storage"

  name_prefix = local.name_prefix
  project_id  = var.gcp_project_id
  region      = var.gcp_region
  tags        = local.common_tags
}

# =============================================================================
# Kubernetes Resources Module
# =============================================================================

module "kubernetes_core" {
  source = "./modules/kubernetes/core"

  namespaces               = var.k8s_namespaces
  enable_istio             = var.k8s_enable_istio
  enable_cert_manager      = var.k8s_enable_cert_manager
  environment              = var.environment
}

# =============================================================================
# Monitoring Stack Module
# =============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  name_prefix              = local.name_prefix
  environment              = var.environment
  retention_days           = var.monitoring_retention_days
  alert_email              = var.monitoring_alert_email
  grafana_admin_password   = var.monitoring_grafana_admin_password
  enable_prometheus        = var.monitoring_enable_prometheus
  enable_grafana           = var.monitoring_enable_grafana
  enable_alertmanager      = var.monitoring_enable_alertmanager
  enable_loki              = var.monitoring_enable_loki
  enable_tempo             = var.monitoring_enable_tempo
  tags                     = local.common_tags
}

# =============================================================================
# Security Groups & Network Policies Module
# =============================================================================

module "security" {
  source = "./modules/security"

  name_prefix                   = local.name_prefix
  environment                   = var.environment
  aws_vpc_id                    = module.aws_vpc.vpc_id
  allowed_cidr_blocks           = var.security_allowed_cidr_blocks
  enable_waf                    = var.security_enable_waf
  enable_shield                 = var.security_enable_shield
  enable_guardduty              = var.security_enable_guardduty
  enable_securityhub            = var.security_enable_securityhub
  enable_flow_logs              = var.security_enable_flow_logs
  enable_encryption_at_rest     = var.security_enable_encryption_at_rest
  enable_encryption_in_transit  = var.security_enable_encryption_in_transit
  tags                          = local.common_tags
}
