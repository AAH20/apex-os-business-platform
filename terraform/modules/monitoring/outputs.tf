output "prometheus_endpoint" { value = var.enable_prometheus ? "http://${var.name_prefix}-prometheus-kube-prometheus:9090" : "" }
output "grafana_endpoint" { value = var.enable_grafana ? "http://${var.name_prefix}-grafana:3000" : "" }
output "alertmanager_endpoint" { value = var.enable_alertmanager ? "http://${var.name_prefix}-alertmanager:9093" : "" }
output "loki_endpoint" { value = var.enable_loki ? "http://${var.name_prefix}-loki:3100" : "" }
output "tempo_endpoint" { value = var.enable_tempo ? "http://${var.name_prefix}-tempo:3100" : "" }
