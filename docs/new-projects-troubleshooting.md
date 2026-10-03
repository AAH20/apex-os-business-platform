# New Projects — Troubleshooting Guide

## 1. Common Issues and Solutions

### Project Creation Fails

| Symptom | Likely Cause | Solution |
|---|---|---|
| "Project name already exists" | Duplicate slug in database | Use a unique name or append a suffix |
| "Invalid configuration" | Malformed `project.yaml` | Validate schema with `apex validate project.yaml` |
| "Permission denied" | Insufficient IAM role | Grant `projects:create` permission to your role |
| "Quota exceeded" | Project limit reached | Request quota increase or archive unused projects |
| "Template not found" | Template ID typo or deleted | Run `apex templates list` to see available templates |

### Project Won't Start

```bash
# Check project status
apex project status <project-id>

# View recent logs
apex logs <project-id> --tail 50

# Common fixes
apex project restart <project-id>
apex project repair <project-id>   # re-links resources
```

### Dependencies Not Resolving

- Ensure `requirements.txt` or `package.json` is at the project root
- Run `apex deps sync <project-id>` to force re-resolution
- Check the private registry mirror is reachable: `curl -s $APEX_REGISTRY/health`

### Environment Variables Missing

```bash
# List expected vs. actual env vars
apex env diff <project-id>

# Set a variable
apex env set <project-id> KEY=value

# Reload without restart
apex env reload <project-id>
```

---

## 2. Debugging Strategies

### Structured Log Inspection

```bash
# Follow logs in real-time
apex logs <project-id> --follow

# Filter by severity
apex logs <project-id> --level ERROR

# Search across all services
apex logs <project-id> --grep "timeout" --since 1h
```

### Interactive Debugging

```bash
# Open a shell inside the project container
apex shell <project-id>

# Run a one-off debug command
apex exec <project-id> -- python -c "import app; print(app.config)"

# Attach the debugger (Python)
apex exec <project-id> -- python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m app
```

### Request Tracing

Every request is assigned a trace ID. Use it to follow the full call chain:

```bash
apex trace <trace-id> --format tree
apex trace <trace-id> --format json > trace.json
```

### State Inspection

```bash
# Dump current project state
apex project export <project-id> --format yaml

# Compare with last known-good state
apex project diff <project-id> --against <snapshot-id>
```

### Common Debugging Patterns

1. **Reproduce locally** — `apex local run` mirrors the cloud environment
2. **Bisect recent changes** — `apex project rollback <project-id> --step 1` then re-test
3. **Check resource limits** — `apex project metrics <project-id>` shows CPU/memory/disk
4. **Enable verbose mode** — set `APEX_LOG_LEVEL=debug` in the project env

---

## 3. Performance Troubleshooting

### Identifying Bottlenecks

```bash
# Top resource consumers
apex project top <project-id>

# Slow endpoints (p50/p95/p99)
apex project endpoints <project-id> --sort p95

# Database query analysis
apex project db-stats <project-id> --slow-queries
```

### High CPU

- **Cause:** Inefficient loops, missing indexes, or undersized instances
- **Fix:** Scale horizontally (`apex project scale <project-id> --replicas N`) or vertically (`--instance-type large`)
- **Verify:** Watch `apex project metrics <project-id> --watch` after the change

### High Memory

- **Cause:** Memory leaks, large in-memory caches, or OOM-killed containers
- **Fix:** Enable swap (`apex project config <project-id> --swap 1Gi`), reduce cache TTL, or profile with `apex exec <project-id> -- python -m memray run -o profile.bin -m app`

### Slow Database Queries

```bash
# Find queries over 200ms
apex project db-stats <project-id> --threshold 200

# Explain a specific query
apex project db-explain <project-id> "SELECT * FROM orders WHERE status='pending'"
```

- Add missing indexes: `apex project db-index <project-id> --table orders --column status`
- Enable query caching for read-heavy workloads

### Network Latency

- Use `apex project endpoints <project-id> --region` to check cross-region calls
- Enable connection pooling: `apex project config <project-id> --pool-size 20`
- Consider CDN for static assets: `apex project cdn enable <project-id>`

### Build Performance

- Use layer caching: ensure `Dockerfile` orders commands from least to most volatile
- Enable remote build cache: `apex project config <project-id> --build-cache remote`
- Parallelize test suites: `apex project config <project-id> --test-parallel 4`

---

## 4. Security Troubleshooting

### Authentication Failures

```bash
# Check auth configuration
apex project auth status <project-id>

# Test a token
apex auth verify <token>

# Rotate keys
apex project auth rotate-keys <project-id>
```

- **401 Unauthorized** — Token expired or invalid; refresh with `apex auth login`
- **403 Forbidden** — Valid token but missing scope; check IAM policy with `apex auth whoami --scopes`

### Secrets Leakage

```bash
# Scan for committed secrets
apex security scan <project-id> --type secrets

# Rotate a compromised secret
apex env rotate <project-id> --key DATABASE_URL

# Audit secret access
apex security audit <project-id> --resource secrets --since 7d
```

### Network Security

```bash
# List exposed endpoints
apex project network <project-id> --exposed

# Check TLS configuration
apex security scan <project-id> --type tls

# Review firewall rules
apex project network <project-id> --firewall
```

- Ensure internal services are not publicly exposed
- Verify TLS certificates are valid and not expiring within 30 days
- Restrict ingress to known CIDR blocks where possible

### Vulnerability Scanning

```bash
# Full dependency scan
apex security scan <project-id> --type dependencies

# Container image scan
apex security scan <project-id> --type container

# Generate a compliance report
apex security report <project-id> --format pdf --output report.pdf
```

- Critical CVEs should be patched within 24 hours
- Use `apex security policy set <project-id> --fail-on critical` to block deployments with critical vulnerabilities

### Audit and Compliance

```bash
# Who accessed this project?
apex security audit <project-id> --resource project --since 30d

# What changed recently?
apex security audit <project-id> --resource config --since 7d

# Export audit trail
apex security audit <project-id> --format csv --output audit.csv
```

### Incident Response

1. **Isolate** — `apex project network <project-id> --deny-all`
2. **Preserve evidence** — `apex logs <project-id> --since 24h > evidence.log`
3. **Rotate credentials** — `apex project auth rotate-keys <project-id> && apex env rotate <project-id> --all`
4. **Investigate** — review audit logs and trace suspicious requests
5. **Restore** — `apex project restore <project-id> --from <known-good-snapshot>`

---

## Quick Reference

| Task | Command |
|---|---|
| Project status | `apex project status <id>` |
| View logs | `apex logs <id> --tail 100` |
| Restart | `apex project restart <id>` |
| Open shell | `apex shell <id>` |
| Run command | `apex exec <id> -- <cmd>` |
| Metrics | `apex project metrics <id>` |
| Security scan | `apex security scan <id>` |
| Export state | `apex project export <id>` |
| Debug locally | `apex local run` |
