# APEX-OS Monitoring Setup

Comprehensive monitoring stack for the APEX-OS Business Platform using Prometheus, Grafana, and Alertmanager.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Services   │────▶│  Prometheus  │────▶│   Grafana   │
│  (/metrics) │     │  (scraping)  │     │(dashboards) │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │ Alertmanager │
                    │  (alerts)    │
                    └──────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `prometheus.yml` | Prometheus scrape configuration |
| `alert-rules.yml` | Alert rules for critical conditions |
| `grafana-dashboard.json` | Pre-built Grafana dashboard |
| `service-monitor.yaml` | Kubernetes ServiceMonitor CRDs |

## Quick Start

### 1. Deploy Prometheus + Grafana (Kubernetes)

```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.prometheusSpec.ruleFiles={/etc/prometheus/rules/*.yml}

# Apply custom configs
kubectl create configmap prometheus-config \
  --from-file=prometheus.yml \
  --namespace monitoring \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap alert-rules \
  --from-file=alert-rules.yml \
  --namespace monitoring \
  --dry-run=client -o yaml | kubectl apply -f -

# Apply ServiceMonitors
kubectl apply -f service-monitor.yaml
```

### 2. Import Grafana Dashboard

```bash
# Port-forward Grafana
kubectl port-forward svc/monitoring-grafana 3000:80 -n monitoring

# Import dashboard via API
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @grafana-dashboard.json
```

Or via UI: Grafana → Dashboards → Import → Upload JSON.

### 3. Configure Alertmanager

```yaml
# alertmanager-config.yml
global:
  smtp_smarthost: localhost:587
  smtp_from: alerts@apex-os.local

route:
  receiver: default
  group_by: [alertname, service]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: default
    slack_configs:
      - api_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
        channel: '#alerts'
        send_resolved: true
```

## Monitored Services

| Service | Port | Metrics Path |
|---------|------|-------------|
| apex-api | 8080 | /metrics |
| apex-worker | 8080 | /metrics |
| apex-gateway | 8080 | /metrics |
| node-exporter | 9100 | /metrics |
| cadvisor | 8080 | /metrics |
| postgres-exporter | 9187 | /metrics |
| redis-exporter | 9121 | /metrics |
| blackbox-exporter | 9115 | /probe |

## Key Metrics

- **Request Rate**: Requests per second by service
- **Error Rate**: 5xx responses as percentage of total
- **Latency**: p95 and p99 request duration
- **CPU/Memory**: Node and container resource usage
- **Pod Status**: Running/Failed pod counts
- **Database**: Connection count, query performance
- **Redis**: Memory usage, hit rate

## Alert Severity Levels

| Level | Condition | Notification |
|-------|-----------|-------------|
| Critical | Service down, crash looping, disk full | PagerDuty + Slack |
| Warning | High latency, high resource usage | Slack |
| Info | Certificate expiring, config changes | Slack |

## Access URLs

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Prometheus | http://localhost:9090 | None |
| Grafana | http://localhost:3000 | admin / prom-operator |
| Alertmanager | http://localhost:9093 | None |

## Maintenance

```bash
# Reload Prometheus config without restart
curl -X POST http://localhost:9090/-/reload

# Check Prometheus targets
open http://localhost:9090/targets

# View active alerts
open http://localhost:9090/alerts

# Backup Prometheus data
kubectl exec -it prometheus-monitoring-prometheus-0 -n monitoring -- \
  promtool tsdb analyze /prometheus
```

## Troubleshooting

- **No metrics visible**: Check service labels match ServiceMonitor selector
- **Alerts not firing**: Verify Alertmanager config and route settings
- **Dashboard empty**: Confirm Prometheus datasource is configured in Grafana
- **High cardinality**: Reduce label count or increase scrape interval
