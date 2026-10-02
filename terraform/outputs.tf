# =============================================================================
# AWS Outputs
# =============================================================================

output "aws_vpc_id" {
  description = "AWS VPC ID"
  value       = module.aws_vpc.vpc_id
}

output "aws_vpc_cidr" {
  description = "AWS VPC CIDR block"
  value       = module.aws_vpc.vpc_cidr
}

output "aws_private_subnet_ids" {
  description = "AWS private subnet IDs"
  value       = module.aws_vpc.private_subnet_ids
}

output "aws_public_subnet_ids" {
  description = "AWS public subnet IDs"
  value       = module.aws_vpc.public_subnet_ids
}

output "aws_eks_cluster_name" {
  description = "AWS EKS cluster name"
  value       = module.aws_eks.cluster_name
}

output "aws_eks_cluster_endpoint" {
  description = "AWS EKS cluster endpoint"
  value       = module.aws_eks.cluster_endpoint
}

output "aws_eks_cluster_ca_cert" {
  description = "AWS EKS cluster CA certificate"
  value       = module.aws_eks.cluster_ca_cert
  sensitive   = true
}

output "aws_rds_endpoint" {
  description = "AWS RDS endpoint"
  value       = module.aws_rds.endpoint
}

output "aws_rds_port" {
  description = "AWS RDS port"
  value       = module.aws_rds.port
}

output "aws_s3_bucket_names" {
  description = "AWS S3 bucket names"
  value       = module.aws_s3.bucket_names
}

# =============================================================================
# Azure Outputs
# =============================================================================

output "azure_resource_group_name" {
  description = "Azure resource group name"
  value       = module.azure_vnet.resource_group_name
}

output "azure_vnet_id" {
  description = "Azure VNet ID"
  value       = module.azure_vnet.vnet_id
}

output "azure_aks_cluster_name" {
  description = "Azure AKS cluster name"
  value       = module.azure_aks.cluster_name
}

output "azure_aks_cluster_endpoint" {
  description = "Azure AKS cluster endpoint"
  value       = module.azure_aks.cluster_endpoint
}

# =============================================================================
# GCP Outputs
# =============================================================================

output "gcp_vpc_id" {
  description = "GCP VPC ID"
  value       = module.gcp_vpc.vpc_id
}

output "gcp_gke_cluster_name" {
  description = "GCP GKE cluster name"
  value       = module.gcp_gke.cluster_name
}

output "gcp_gke_cluster_endpoint" {
  description = "GCP GKE cluster endpoint"
  value       = module.gcp_gke.cluster_endpoint
}

# =============================================================================
# Kubernetes Outputs
# =============================================================================

output "k8s_namespaces" {
  description = "Created Kubernetes namespaces"
  value       = module.kubernetes_core.namespaces
}

# =============================================================================
# Monitoring Outputs
# =============================================================================

output "monitoring_prometheus_endpoint" {
  description = "Prometheus endpoint"
  value       = module.monitoring.prometheus_endpoint
}

output "monitoring_grafana_endpoint" {
  description = "Grafana endpoint"
  value       = module.monitoring.grafana_endpoint
}

output "monitoring_alertmanager_endpoint" {
  description = "Alertmanager endpoint"
  value       = module.monitoring.alertmanager_endpoint
}

# =============================================================================
# Security Outputs
# =============================================================================

output "security_group_ids" {
  description = "Security group IDs"
  value       = module.security.security_group_ids
}

output "waf_web_acl_id" {
  description = "AWS WAF Web ACL ID"
  value       = module.security.waf_web_acl_id
}
