# AWS Provider
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.common_tags, {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = "apex-os-business-platform"
    })
  }
}

# Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
  subscription_id = var.azure_subscription_id
  tenant_id       = var.azure_tenant_id
}

# GCP Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "google-beta" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Kubernetes Provider (AWS EKS)
provider "kubernetes" {
  host                   = module.aws_eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.aws_eks.cluster_ca_cert)
  token                  = data.aws_eks_cluster_auth.eks.token
}

provider "helm" {
  kubernetes {
    host                   = module.aws_eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.aws_eks.cluster_ca_cert)
    token                  = data.aws_eks_cluster_auth.eks.token
  }
}

# Kubernetes Provider (Azure AKS)
provider "kubernetes" {
  alias                  = "aks"
  host                   = module.azure_aks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.azure_aks.cluster_ca_cert)
  client_certificate     = module.azure_aks.client_certificate
  client_key             = module.azure_aks.client_key
  password               = module.azure_aks.cluster_password
}

provider "helm" {
  alias = "aks"
  kubernetes {
    host                   = module.azure_aks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.azure_aks.cluster_ca_certificate)
    client_certificate     = module.azure_aks.client_certificate
    client_key             = module.azure_aks.client_key
    password               = module.azure_aks.cluster_password
  }
}

# Kubernetes Provider (GCP GKE)
provider "kubernetes" {
  alias                  = "gke"
  host                   = module.gcp_gke.cluster_endpoint
  cluster_ca_certificate = base64decode(module.gcp_gke.cluster_ca_cert)
  token                  = module.gcp_gke.access_token
}

provider "helm" {
  alias = "gke"
  kubernetes {
    host                   = module.gcp_gke.cluster_endpoint
    cluster_ca_certificate = base64decode(module.gcp_gke.cluster_ca_cert)
    token                  = module.gcp_gke.access_token
  }
}
