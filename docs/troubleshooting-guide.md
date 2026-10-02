# APEX-OS Business Platform — Troubleshooting Guide

## 1. Common Errors and Solutions

### 1.1 Startup / Boot Failures

| Symptom | Likely Cause | Solution |
|---|---|---|
| `Error: Cannot find module '…'` | Missing dependency | Run `npm install` or `pnpm install` in the project root |
| `EADDRINUSE: address already in use` | Port conflict | Kill the process on the port: `lsof -ti:3000 \| xargs kill -9` |
| `ECONNREFUSED` to database | DB not running or wrong URL | Verify DB is up; check `DATABASE_URL` in `.env` |
| `SyntaxError: Unexpected token` | Node version mismatch | Use Node 18+ (check `.nvmrc`); run `nvm use` |
| `Module parse failed: Unexpected character` | Missing webpack/babel loader | Clear cache: `rm -rf node_modules/.cache` and restart |

### 1.2 Authentication Errors

| Symptom | Likely Cause | Solution |
|---|---|---|
| `401 Unauthorized` on API calls | Expired or missing token | Refresh token; verify `Authorization: Bearer <token>` header |
| `403 Forbidden` | Insufficient role/permission | Check user role in admin panel; verify RBAC policy |
| `Invalid JWT signature` | Secret mismatch | Ensure `JWT_SECRET` matches across services |
| Login loop / redirect storm | Cookie domain mismatch | Align `COOKIE_DOMAIN` with app domain; check SameSite policy |
| OAuth callback failure | Redirect URI mismatch | Register exact callback URL in provider console |

### 1.3 Database Errors

| Symptom | Likely Cause | Solution |
|---|---|---|
| `Query timeout` | Slow query or lock contention | Run `EXPLAIN ANALYZE`; add indexes; check for deadlocks |
| `Too many connections` | Connection pool exhausted | Increase `pool.max` or reduce idle timeout |
| `Migration failed` | Schema drift or conflict | Run `migrate:status`; resolve pending migrations manually |
| `Unique constraint violation` | Duplicate key on insert | Use `upsert` or check for existing record before insert |
| `Deadlock detected` | Concurrent transactions | Retry with exponential backoff; reorder operations |

### 1.4 API / Integration Errors

| Symptom | Likely Cause | Solution |
|---|---|---|
| `502 Bad Gateway` | Upstream service down | Check upstream health; verify reverse proxy config |
| `504 Gateway Timeout` | Upstream too slow | Increase timeout; add circuit breaker |
| `429 Too Many Requests` | Rate limit hit | Implement backoff; check rate-limit headers |
| `CORS policy blocked` | Missing CORS headers | Add origin to CORS allowlist in server config |
| Webhook delivery failures | Endpoint unreachable or SSL error | Verify endpoint URL; check TLS cert validity |

---

## 2. Debugging Strategies

### 2.1 Reproduce the Issue
1. Identify the exact steps, inputs, and environment where the error occurs.
2. Capture the full error stack trace and request/response payloads.
3. Note the timestamp — correlate with logs and deployments.

### 2.2 Isolate the Layer
- **Frontend**: Check browser console, network tab, and React/Vue devtools.
- **API**: Use `curl` or Postman to hit the endpoint directly; bypass the UI.
- **Database**: Run the raw query in a DB client to verify results.
- **Infrastructure**: Check container/pod status, resource usage, and network policies.

### 2.3 Add Temporary Logging
```javascript
// Add structured logging at key decision points
console.log('[DEBUG] userId:', userId, 'action:', action, 'payload:', JSON.stringify(payload));
```
- Use log levels (`debug`, `info`, `warn`, `error`) — never log secrets.
- Remove or downgrade debug logs before merging to production.

### 2.4 Use Breakpoints and REPL
- **Node.js**: `node --inspect` + Chrome DevTools, or `ndb`.
- **Python**: `pdb.set_trace()` or `breakpoint()`.
- **Frontend**: Browser DevTools breakpoints; React DevTools for component state.

### 2.5 Binary Search the Problem
- Comment out half the code path — does the error persist?
- Revert to last known-good commit (`git bisect`).
- Disable feature flags one at a time.

### 2.6 Check Recent Changes
```bash
git log --oneline -20
git diff HEAD~5 --stat
```
- Did a deployment coincide with the error?
- Did a config change or env var update land recently?

---

## 3. Log Analysis

### 3.1 Log Locations
| Environment | Path |
|---|---|
| Local dev | Console output / `logs/app.log` |
| Docker | `docker logs <container>` or `docker compose logs -f` |
| Kubernetes | `kubectl logs <pod> --previous` (for crashed pods) |
| Production | Centralized logging (ELK, Datadog, CloudWatch) |

### 3.2 Log Levels and When to Use Them
| Level | Use For |
|---|---|
| `ERROR` | Failures that require immediate attention |
| `WARN` | Recoverable issues, deprecated usage, retries |
| `INFO` | Key business events (user created, order placed) |
| `DEBUG` | Detailed flow tracing (disable in production) |

### 3.3 Searching and Filtering
```bash
# Find all errors in the last hour
grep "$(date -d '1 hour ago' '+%Y-%m-%d %H')" logs/app.log | grep ERROR

# Follow logs in real-time, filtered
tail -f logs/app.log | grep -E "ERROR|WARN"

# Count errors by type
grep ERROR logs/app.log | awk '{print $NF}' | sort | uniq -c | sort -rn

# Search by request ID (distributed tracing)
grep "req-id:abc123" logs/*.log
```

### 3.4 Structured Logging Best Practices
- Use JSON format in production for machine parsing.
- Always include: `timestamp`, `level`, `service`, `requestId`, `userId`, `message`.
- Never log passwords, tokens, PII, or full credit card numbers.
- Use a correlation ID (`requestId`) to trace a request across services.

### 3.5 Key Patterns to Look For
- **Error spikes**: Correlate with deployments or traffic surges.
- **Retry storms**: Same operation retried many times — indicates downstream issue.
- **Memory warnings**: `heap out of memory`, `GC overhead` — see Performance section.
- **Auth failures**: Brute-force attempts or token leaks — see Security section.

---

## 4. Performance Troubleshooting

### 4.1 Identify the Bottleneck
1. **CPU-bound**: High CPU usage, slow computation. Profile with `--prof` (Node) or `cProfile` (Python).
2. **I/O-bound**: Slow DB queries, external API calls. Check query latency and connection pool wait time.
3. **Memory-bound**: Growing heap, frequent GC. Take heap snapshots and compare.
4. **Network-bound**: High latency, packet loss. Use `ping`, `traceroute`, `mtr`.

### 4.2 Database Performance
```sql
-- Find slow queries (PostgreSQL)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check for missing indexes
SELECT * FROM pg_stat_user_tables WHERE seq_scan > 1000 AND idx_scan < 100;

-- Find locks
SELECT * FROM pg_locks WHERE NOT granted;
```
- Add indexes on frequently queried columns.
- Use `EXPLAIN ANALYZE` to verify index usage.
- Cache hot data in Redis; set appropriate TTLs.

### 4.3 API Performance
- **N+1 queries**: Use eager loading or DataLoader pattern.
- **Large payloads**: Paginate results; compress responses (`gzip`/`brotli`).
- **Slow endpoints**: Add response caching; use CDN for static assets.
- **Connection pooling**: Tune pool size based on concurrent load.

### 4.4 Frontend Performance
- **Slow initial load**: Code-split routes; lazy-load heavy components.
- **Large bundle**: Run `webpack-bundle-analyzer`; remove unused deps.
- **Render performance**: Use React.memo, useMemo, useCallback; avoid unnecessary re-renders.
- **Memory leaks**: Check for uncleaned event listeners, intervals, and subscriptions.

### 4.5 Infrastructure Scaling
- **Horizontal**: Add more instances behind a load balancer.
- **Vertical**: Increase CPU/memory for resource-constrained nodes.
- **Auto-scaling**: Configure HPA (Kubernetes) or cloud auto-scaling groups.
- **Queue offload**: Move heavy work to background job queues (Bull, Celery).

### 4.6 Monitoring and Alerting
- Set up dashboards for: request rate, error rate, p95/p99 latency, CPU, memory, disk.
- Alert on: error rate > 1%, p99 latency > 500ms, memory > 85%, disk > 80%.
- Use APM tools (New Relic, Datadog, Jaeger) for distributed tracing.

---

## 5. Security Troubleshooting

### 5.1 Common Vulnerabilities

| Vulnerability | Detection | Mitigation |
|---|---|---|
| **SQL Injection** | Unexpected DB errors; audit logs showing raw SQL in input | Use parameterized queries / ORM; never concatenate user input |
| **XSS** | User input rendered as HTML in browser | Sanitize output; use `Content-Security-Policy` header |
| **CSRF** | Unauthorized state-changing requests | Use CSRF tokens; enforce `SameSite=Strict` cookies |
| **Auth bypass** | Accessing protected routes without valid token | Verify middleware order; test with expired/invalid tokens |
| **Secret leakage** | Secrets in logs, error messages, or client bundles | Use server-side env vars only; scrub error responses |
| **Dependency CVEs** | `npm audit` or `pip-audit` findings | Update dependencies; pin versions; use automated scanning |

### 5.2 Investigating Security Incidents
1. **Preserve evidence**: Snapshot logs, don't restart affected services yet.
2. **Identify scope**: Which users, data, or systems are affected?
3. **Trace the attack vector**: Review access logs for suspicious patterns.
4. **Contain**: Rotate exposed credentials; block malicious IPs.
5. **Eradicate and recover**: Patch the vulnerability; restore from backup if needed.
6. **Post-incident**: Document timeline; update runbooks; add detection rules.

### 5.3 Log Analysis for Security
```bash
# Find failed login attempts
grep "login failed" logs/app.log | awk '{print $1}' | sort | uniq -c | sort -rn

# Find requests from suspicious IPs
grep "POST /api/login" logs/app.log | grep "192.168.1.100"

# Find privilege escalation attempts
grep "role change\|permission grant" logs/audit.log

# Find large data exfiltration (unusual response sizes)
awk '$10 > 1000000 {print}' logs/access.log
```

### 5.4 Authentication and Authorization Issues
- **Token not accepted**: Check clock skew between services (JWT `exp`/`nbf`).
- **Session not persisting**: Verify cookie `Secure`, `HttpOnly`, `SameSite` flags.
- **Permission denied**: Check role hierarchy; verify policy engine evaluation order.
- **OAuth failures**: Verify client ID/secret; check redirect URI matching.

### 5.5 Infrastructure Security
- **Open ports**: Run `nmap` against public endpoints; close unnecessary ports.
- **TLS issues**: Verify certificate chain with `openssl s_client -connect host:443`.
- **Container security**: Run images as non-root; scan with Trivy or Snyk.
- **Network policies**: Restrict pod-to-pod traffic; use service mesh mTLS.

### 5.6 Security Headers Checklist
Verify these headers are present on all responses:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### 5.7 Incident Response Contacts
- **Security team**: security@company.com / #security Slack channel
- **On-call engineer**: PagerDuty rotation
- **Escalation**: CISO for confirmed breaches; legal for data exposure

---

## Quick Reference: Diagnostic Commands

```bash
# Check service health
curl -s http://localhost:3000/health | jq .

# Check disk usage
df -h

# Check memory usage
free -m

# Check top processes
top -o cpu

# Check network connections
netstat -tuln | grep LISTEN

# Check recent deployments
kubectl rollout history deployment/app

# Tail logs with color
tail -f logs/app.log | ccze -A

# Test database connection
psql $DATABASE_URL -c "SELECT 1;"
```

---

*Last updated: 2026-10-02*
