# Kubernetes Core Module - Namespaces, RBAC, and core resources for APEX-OS

variable "namespaces" {
  description = "List of namespaces to create"
  type        = list(string)
  default     = ["apex-os-core", "apex-os-data", "apex-os-monitoring", "apex-os-security"]
}

variable "enable_istio" {
  description = "Enable Istio service mesh"
  type        = bool
  default     = false
}

variable "enable_cert_manager" {
  description = "Enable cert-manager"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

# Namespaces
resource "kubernetes_namespace" "main" {
  for_each = toset(var.namespaces)

  metadata {
    name = each.value
    labels = {
      "istio-injection" = var.enable_istio ? "enabled" : "disabled"
      "environment"     = var.environment
      "managed-by"      = "terraform"
    }
  }
}

# Service Account for APEX-OS Core
resource "kubernetes_service_account" "core" {
  metadata {
    name      = "apex-os-core"
    namespace = "apex-os-core"
  }

  depends_on = [kubernetes_namespace.main]
}

# Service Account for APEX-OS Data
resource "kubernetes_service_account" "data" {
  metadata {
    name      = "apex-os-data"
    namespace = "apex-os-data"
  }

  depends_on = [kubernetes_namespace.main]
}

# Cluster Role for APEX-OS Admin
resource "kubernetes_cluster_role" "admin" {
  metadata {
    name = "apex-os-admin"
  }

  rule {
    api_groups = ["*"]
    resources  = ["*"]
    verbs      = ["*"]
  }
}

# Cluster Role Binding for APEX-OS Admin
resource "kubernetes_cluster_role_binding" "admin" {
  metadata {
    name = "apex-os-admin"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = kubernetes_cluster_role.admin.metadata[0].name
  }

  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account.core.metadata[0].name
    namespace = "apex-os-core"
  }
}

# Network Policy - Default Deny All
resource "kubernetes_network_policy" "default_deny" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "default-deny-all"
    namespace = each.value
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress", "Egress"]
  }

  depends_on = [kubernetes_namespace.main]
}

# Network Policy - Allow DNS
resource "kubernetes_network_policy" "allow_dns" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "allow-dns"
    namespace = each.value
  }

  spec {
    pod_selector {}
    policy_types = ["Egress"]

    egress {
      to {
        namespace_selector {
          match_labels = {
            "kubernetes.io/metadata.name" = "kube-system"
          }
        }
        pod_selector {
          match_labels = {
            "k8s-app" = "kube-dns"
          }
        }
      }
      ports {
        protocol = "UDP"
        port     = 53
      }
      ports {
        protocol = "TCP"
        port     = 53
      }
    }
  }

  depends_on = [kubernetes_namespace.main]
}

# Network Policy - Allow Ingress from Same Namespace
resource "kubernetes_network_policy" "allow_same_namespace" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "allow-same-namespace"
    namespace = each.value
  }

  spec {
    pod_selector {}
    policy_types = ["Ingress"]

    ingress {
      from {
        pod_selector {}
      }
    }
  }

  depends_on = [kubernetes_namespace.main]
}

# Resource Quota for each namespace
resource "kubernetes_resource_quota" "namespace_quota" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "quota"
    namespace = each.value
  }

  spec {
    hard = {
      "requests.cpu"       = "10"
      "requests.memory"    = "20Gi"
      "limits.cpu"         = "20"
      "limits.memory"      = "40Gi"
      "pods"               = "50"
      "services"           = "20"
      "persistentvolumeclaims" = "10"
    }
  }

  depends_on = [kubernetes_namespace.main]
}

# Limit Range for each namespace
resource "kubernetes_limit_range" "namespace_limits" {
  for_each = toset(var.namespaces)

  metadata {
    name      = "limits"
    namespace = each.value
  }

  spec {
    limit {
      type = "Container"
      default = {
        cpu    = "500m"
        memory = "512Mi"
      }
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
      max = {
        cpu    = "2"
        memory = "2Gi"
      }
      min = {
        cpu    = "50m"
        memory = "64Mi"
      }
    }
  }

  depends_on = [kubernetes_namespace.main]
}

# Outputs
output "namespaces" {
  value = [for ns in kubernetes_namespace.main : ns.metadata[0].name]
}

output "core_service_account" {
  value = kubernetes_service_account.core.metadata[0].name
}

output "data_service_account" {
  value = kubernetes_service_account.data.metadata[0].name
}
