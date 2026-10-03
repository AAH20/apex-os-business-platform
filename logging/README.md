# APEX-OS Business Platform — Logging Setup

Comprehensive logging infrastructure using Fluentd → Logstash → Elasticsearch with S3 archival and log rotation.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌───────────┐     ┌─────────────┐
│ Application │────▶│ Fluentd  │────▶│ Logstash  │────▶│Elasticsearch│
│   Nodes     │     │ (edge)   │     │ (central) │     │  (cluster)  │
└─────────────┘     └──────────┘     └───────────┘     └─────────────┘
                           │                │
                           ▼                ▼
                    ┌──────────┐     ┌──────────┐
                    │  Local   │     │   S3     │
                    │  Buffer  │     │ Archive  │
                    └──────────┘     └──────────┘
```

## Files

| File | Purpose |
|------|---------|
| `fluentd.conf` | Edge log collection and forwarding |
| `logstash.conf` | Central aggregation, parsing, enrichment |
| `logrotate.conf` | Log rotation and retention policies |

## Prerequisites

- Fluentd ≥ 1.14 (`td-agent` package)
- Logstash ≥ 8.0
- Elasticsearch ≥ 8.0
- AWS CLI (for S3 archival)

## Quick Start

### 1. Install Fluentd (edge nodes)

```bash
# macOS
brew install fluentd

# Ubuntu/Debian
curl -fsSL https://toolbelt.treasuredata.com/sh/install-ubuntu-fluentd4.sh | sh

# Copy config
sudo cp fluentd.conf /etc/fluent/fluent.conf
sudo systemctl restart td-agent
```

### 2. Install Logstash (central server)

```bash
# Ubuntu/Debian
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -
echo "deb https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list
sudo apt update && sudo apt install logstash

# Copy config
sudo cp logstash.conf /etc/logstash/conf.d/apex-os.conf
sudo systemctl restart logstash
```

### 3. Install Logrotate

```bash
sudo cp logrotate.conf /etc/logrotate.d/apex-os
sudo logrotate -d /etc/logrotate.d/apex-os  # dry-run test
```

### 4. Environment Variables

```bash
# Fluentd
export LOGSTASH_HOST=logstash.internal
export ES_HOST=es-cluster.internal
export APEX_ENV=production

# Logstash
export ES_HOST=localhost:9200
export ES_USER=elastic
export ES_PASSWORD=changeme
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
export S3_LOG_BUCKET=apex-os-logs
export AWS_REGION=us-east-1
```

## Log Paths

| Log Type | Path | Retention |
|----------|------|-----------|
| Application | `/var/log/apex-os/app*.log` | 30 days |
| Errors | `/var/log/apex-os/error*.log` | 90 days |
| Audit | `/var/log/apex-os/audit*.log` | 365 days (S3: 7 years) |
| Nginx Access | `/var/log/nginx/apex-os-access.log` | 30 days |
| Nginx Error | `/var/log/nginx/apex-os-error.log` | 30 days |
| Docker | `/var/lib/docker/containers/*/*-json.log` | 14 days |
| Fluentd | `/var/log/fluentd/*.log` | 14 days |
| Logstash | `/var/log/logstash/*.log` | 30 days |

## Elasticsearch Indices

- `apex-os-YYYY.MM.DD` — all application logs
- `apex-os-errors-YYYY.MM.DD` — error-only index for alerting

## Kibana Dashboard

1. Navigate to **Stack Management → Index Patterns**
2. Create pattern: `apex-os-*`
3. Set time field: `@timestamp`
4. Import dashboard from `kibana/apex-os-dashboard.json` (if available)

## Monitoring & Alerting

### Health Checks

```bash
# Fluentd
sudo systemctl status td-agent
curl http://localhost:24224/api/plugins.json

# Logstash
curl http://localhost:9600/_node/stats

# Elasticsearch
curl http://localhost:9200/_cluster/health?pretty
```

### Log Volume Alerts

```bash
# Check disk usage
du -sh /var/log/apex-os/
df -h /var/log

# Check Fluentd buffer
ls -lh /var/log/fluentd/buffer/
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Fluentd not forwarding | Check `LOGSTASH_HOST` and network connectivity |
| Logstash pipeline errors | Check `/var/log/logstash/logstash-plain.log` |
| Disk full | Run `sudo logrotate -f /etc/logrotate.d/apex-os` |
| Missing logs | Verify file permissions and `path` patterns |
| Buffer overflow | Increase `queue_limit_length` in fluentd.conf |

## Security Notes

- All inter-service communication uses TLS
- S3 buckets use private ACL and server-side encryption
- Audit logs are immutable (S3 Object Lock recommended)
- Elasticsearch requires authentication
- Fluentd buffer files contain sensitive data — restrict `/var/log/fluentd/`

## License

Internal — APEX-OS Business Platform
