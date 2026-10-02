# Monitoring Module - Prometheus, Grafana, Alertmanager, Loki, Tempo for APEX-OS

variable "name_prefix" {
  description = "Name prefix for monitoring resources"
  type        = string
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"
}

variable "retention_days" {
  description = "Metrics retention period in days"
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Email address for monitoring alerts"
  type        = string
  default     = "alerts@apex-os.io"
}

variable "grafana_admin_password" {
  description = "Grafana admin password"
  type        = string
  default     = "admin"
  sensitive   = true
}

variable "enable_prometheus" {
  description = "Enable Prometheus"
  type        = bool
  default     = true
}

variable "enable_grafana" {
  description = "Enable Grafana"
  type        = bool
  default     = true
}

variable "enable_alertmanager" {
  description = "Enable Alertmanager"
  type        = bool
  default     = true
}

variable "enable_loki" {
  description = "Enable Loki log aggregation"
  type        = bool
  default     = true
}

variable "enable_tempo" {
  description = "Enable Tempo distributed tracing"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# =============================================================================
# Prometheus
# =============================================================================

resource "helm_release" "prometheus" {
  count = var.enable_prometheus ? 1 : 0

  name       = "${var.name_prefix}-prometheus"
  namespace  = "apex-os-monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "51.0.0"

  values = [
    <<-EOT
    prometheus:
      prometheusSpec:
        retention: ${var.retention_days}d
        retentionSize: "50GB"
        storageSpec:
          volumeClaimTemplate:
            spec:
              storageClassName: gp2
              resources:
                requests:
                  storage: 50Gi
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        additionalScrapeConfigs:
          - job_name: 'apex-os-services'
            kubernetes_sd_configs:
              - role: pod
            relabel_configs:
              - source_labels: [__meta_kubernetes_pod_label_app]
                action: keep
                regex: .+
    EOT
  ]

  depends_on = [kubernetes_namespace.monitoring]
}

# =============================================================================
# Grafana
# =============================================================================

resource "helm_release" "grafana" {
  count = var.enable_grafana ? 1 : 0

  name       = "${var.name_prefix}-grafana"
  namespace  = "apex-os-monitoring"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "grafana"
  version    = "6.60.0"

  values = [
    <<-EOT
    adminPassword: "${var.grafana_admin_password}"
    persistence:
      enabled: true
      size: 10Gi
      storageClassName: gp2
    resources:
      requests:
        cpu: 250m
        memory: 512Mi
      limits:
        cpu: 1000m
        memory: 1Gi
    datasources:
      datasources.yaml:
        apiVersion: 1
        datasources:
          - name: Prometheus
            type: prometheus
            url: http://${var.name_prefix}-prometheus-kube-prometheus:9090
            access: proxy
            isDefault: true
          - name: Loki
            type: loki
            url: http://${var.name_prefix}-loki:3100
            access: proxy
          - name: Tempo
            type: tempo
            url: http://${var.name_prefix}-tempo:3100
            access: proxy
    dashboardProviders:
      dashboardproviders.yaml:
        apiVersion: 1
        providers:
          - name: 'default'
            orgId: 1
            folder: ''
            type: file
            disableDeletion: false
            editable: true
            options:
              path: /var/lib/grafana/dashboards/default
    dashboards:
      default:
        apex-os-overview:
          url: https://raw.githubusercontent.com/apex-os/dashboards/main/overview.json
    EOT
  ]

  depends_on = [helm_release.prometheus]
}

# =============================================================================
# Alertmanager
# =============================================================================

resource "helm_release" "alertmanager" {
  count = var.enable_alertmanager ? 1 : 0

  name       = "${var.name_prefix}-alertmanager"
  namespace  = "apex-os-monitoring"
  repository = "https://prometheus-community.github.io/helm-charts"
  chart      = "kube-prometheus-stack"
  version    = "51.0.0"

  values = [
    <<-EOT
    alertmanager:
      enabled: true
      config:
        global:
          smtp_smarthost: localhost:587
          smtp_from: ${var.alert_email}
        route:
          receiver: default
          group_wait: 30s
          group_interval: 5m
          repeat_interval: 4h
        receivers:
          - name: default
            email_configs:
              - to: ${var.alert_email}
    EOT
  ]

  depends_on = [kubernetes_namespace.monitoring]
}

# =============================================================================
# Loki
# =============================================================================

resource "helm_release" "loki" {
  count = var.enable_loki ? 1 : 0

  name       = "${var.name_prefix}-loki"
  namespace  = "apex-os-monitoring"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "loki"
  version    = "5.30.0"

  values = [
    <<-EOT
    loki:
      auth_enabled: false
      commonConfig:
        replication_factor: 1
      storage:
        type: s3
        bucketNames:
          chunks: ${var.name_prefix}-loki-chunks
          ruler: ${var.name_prefix}-loki-ruler
          admin: ${var.name_prefix}-loki-admin
    singleBinary:
      replicas: 1
      resources:
        requests:
          cpu: 250m
          memory: 512Mi
        limits:
          cpu: 1000m
          memory: 1Gi
    EOT
  ]

  depends_on = [kubernetes_namespace.monitoring]
}

# =============================================================================
# Tempo
# =============================================================================

resource "helm_release" "tempo" {
  count = var.enable_tempo ? 1 : 0

  name       = "${var.name_prefix}-tempo"
  namespace  = "apex-os-monitoring"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "tempo"
  version    = "1.6.0"

  values = [
    <<-EOT
    tempo:
      storage:
        trace:
          backend: s3
          s3:
            bucket: ${var.name_prefix}-tempo-traces
            endpoint: s3.amazonaws.com
      resources:
        requests:
          cpu: 250m
          memory: 512Mi
        limits:
          cpu: 1000m
          memory: 1Gi
    EOT
  ]

  depends_on = [kubernetes_namespace.monitoring]
}

# =============================================================================
# Namespace
# =============================================================================

resource "kubernetes_namespace" "monitoring" {
  metadata {
    name = "apex-os-monitoring"
    labels = {
      "environment" = var.environment
      "managed-by" = "terraform"
    }
  }
}

# Outputs
output "prometheus_endpoint" {
  value = var.enable_prometheus ? "http://${var.name_prefix}-prometheus-kube-prometheus:9090" : ""
}

output "grafana_endpoint" {
  value = var.enable_grafana ? "http://${var.name_prefix}-grafana:3000" : ""
}

output "alertmanager_endpoint" {
  value = var.enable_alertmanager ? "http://${var.name_prefix}-alertmanager:9093" : ""
}

output "loki_endpoint" {
  value = var.enable_loki ? "http://${var.name_prefix}-loki:3100" : ""
}

output "tempo_endpoint" {
  value = var.enable_tempo ? "http://${var.name_prefix}-tempo:3100" : ""
}
