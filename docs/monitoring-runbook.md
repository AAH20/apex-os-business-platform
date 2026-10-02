# APEX-OS Monitoring Runbook

## 1. Alert Response Procedures

### 1.1 Alert Severity Levels

| Level | Description | Response Time | Page? |
|-------|-------------|---------------|-------|
| P1 — Critical | Complete outage or data loss | 5 min | Yes, 24/7 |
| P2 — High | Major feature degraded | 15 min | Yes, business hours |
| P3 — Medium | Minor feature issue | 1 hour | No, business hours |
| P4 — Low | Cosmetic or informational | Next business day | No |

### 1.2 Alert Acknowledgment

1. Acknowledge the alert in the monitoring dashboard within the response time.
2. Post in `#incidents` Slack channel: alert name, severity, time detected.
3. Begin investigation using the relevant dashboard links in the alert payload.

### 1.3 Initial Triage (first 5 minutes)

- [ ] Check service health endpoint: `curl -s https://api.apex-os.local/health`
- [ ] Review recent deployments: `kubectl rollout history deployment/<svc> -n apex-os`
- [ ] Check error rate dashboards (Grafana: `apex-os/errors`)
- [ ] Check resource utilization (CPU, memory, disk)
- [ ] Identify affected users/tenants from logs

### 1.4 Communication

- **Internal**: Post status updates in `#incidents` every 15 minutes for P1/P2.
- **External**: Update status page for customer-visible incidents.
- **Stakeholders**: Notify product owner for P1; team lead for P2.

---

## 2. Escalation Matrix

### 2.1 Escalation Path

```
L1 (On-call Engineer)
  └─ 15 min no progress → L2 (Senior Engineer / Team Lead)
       └─ 30 min no progress → L3 (Engineering Manager)
            └─ 60 min no progress → L4 (CTO / VP Engineering)
```

### 2.2 Escalation Triggers

- Incident not resolved within target time
- Multiple services affected
- Data loss or corruption suspected
- Security breach detected
- Customer SLA at risk

### 2.3 Contact Information

| Role | Primary | Secondary | Method |
|------|---------|-----------|--------|
| L1 On-call | PagerDuty rotation | — | Phone + Slack |
| L2 Team Lead | Slack DM | Phone | Slack + Phone |
| L3 Eng Manager | Slack DM | Phone | Slack + Phone |
| L4 CTO | Phone | Slack | Phone |
| Security | security@apex-os.local | PagerDuty | Email + Phone |

---

## 3. Common Incident Scenarios

### 3.1 High Error Rate (>5% 5xx)

**Symptoms**: Elevated 5xx in Grafana, customer complaints.

**Diagnosis**:
```bash
# Check recent logs
kubectl logs -n apex-os deployment/api --tail=500 | grep ERROR

# Check deployment status
kubectl get pods -n apex-os -o wide
kubectl describe pod <pod> -n apex-os
```

**Mitigation**:
1. Roll back last deployment if correlated: `kubectl rollout undo deployment/api -n apex-os`
2. Scale up replicas: `kubectl scale deployment/api --replicas=5 -n apex-os`
3. Enable circuit breaker if downstream dependency is failing.

### 3.2 Database Connection Pool Exhaustion

**Symptoms**: Slow responses, connection timeout errors.

**Diagnosis**:
```sql
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
SELECT * FROM pg_stat_activity WHERE state = 'idle' AND state_change < now() - interval '5 minutes';
```

**Mitigation**:
1. Kill idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle';`
2. Increase pool size temporarily in config.
3. Add read replica if read-heavy workload.

### 3.3 Memory Leak / OOM Kills

**Symptoms**: Pods restarting, `OOMKilled` events.

**Diagnosis**:
```bash
kubectl get events -n apex-os --sort-by='.lastTimestamp' | grep OOM
kubectl top pods -n apex-os
```

**Mitigation**:
1. Increase memory limit temporarily.
2. Capture heap dump before restart: `kubectl exec <pod> -- jmap -dump:format=b,file=/tmp/heap.hprof <pid>`
3. Roll back recent deployment if leak is new.

### 3.4 Certificate Expiry

**Symptoms**: TLS handshake errors, browser warnings.

**Diagnosis**:
```bash
echo | openssl s_client -connect api.apex-os.local:443 2>/dev/null | openssl x509 -noout -dates
```

**Mitigation**:
1. Renew certificate via cert-manager: `kubectl delete certificate <cert> -n apex-os`
2. Verify ingress controller picks up new cert.
3. Update cert expiry monitoring alert threshold to 30 days.

### 3.5 Disk Space Full

**Symptoms**: Write failures, pod evictions.

**Diagnosis**:
```bash
kubectl exec -n apex-os <pod> -- df -h
kubectl exec -n apex-os <pod> -- du -sh /var/log/*
```

**Mitigation**:
1. Clear old logs: `kubectl exec -n apex-os <pod> -- find /var/log -name "*.gz" -mtime +7 -delete`
2. Expand PVC: `kubectl edit pvc <pvc-name> -n apex-os`
3. Add log rotation if not present.

---

## 4. Recovery Procedures

### 4.1 Service Restart

```bash
# Rolling restart
kubectl rollout restart deployment/<svc> -n apex-os

# Verify
kubectl rollout status deployment/<svc> -n apex-os
```

### 4.2 Database Failover

1. Promote standby: `pg_ctl promote -D /var/lib/postgresql/data`
2. Update connection string in secret: `kubectl edit secret db-credentials -n apex-os`
3. Restart connection pooler pods.
4. Verify application connectivity.

### 4.3 Cache Flush (Redis)

```bash
# Flush specific DB
kubectl exec -n apex-os redis-0 -- redis-cli -n 1 FLUSHDB

# Verify
kubectl exec -n apex-os redis-0 -- redis-cli -n 1 DBSIZE
```

### 4.4 Full Environment Restore

1. Take etcd snapshot: `ETCDCTL_API=3 etcdctl snapshot save /tmp/etcd-snapshot.db`
2. Restore from backup: `ETCDCTL_API=3 etcdctl snapshot restore /tmp/etcd-snapshot.db`
3. Verify cluster health: `kubectl get nodes`
4. Restore persistent volumes from Velero backup: `velero restore create --from-backup <backup-name>`

### 4.5 Verification Checklist

- [ ] All pods running: `kubectl get pods -n apex-os`
- [ ] Health endpoints returning 200
- [ ] Error rate back to baseline (<0.1%)
- [ ] Latency back to baseline (p99 <200ms)
- [ ] No new alerts firing
- [ ] Customer-facing functionality verified

---

## 5. Post-Incident Review Template

### 5.1 Incident Summary

| Field | Value |
|-------|-------|
| Incident ID | INC-YYYY-MM-DD-### |
| Severity | P1 / P2 / P3 / P4 |
| Start Time | YYYY-MM-DD HH:MM UTC |
| End Time | YYYY-MM-DD HH:MM UTC |
| Duration | X hours Y minutes |
| Author | Name |
| Review Date | YYYY-MM-DD |

### 5.2 Timeline

| Time (UTC) | Event | Actor |
|------------|-------|-------|
| HH:MM | Alert fired | Monitoring |
| HH:MM | Acknowledged | On-call |
| HH:MM | Mitigation applied | On-call |
| HH:MM | Resolved | On-call |

### 5.3 Root Cause

- **What happened**: Brief description of the failure.
- **Why it happened**: Underlying cause (code bug, config change, capacity, etc.).
- **Why it wasn't caught earlier**: Gap in monitoring/testing.

### 5.4 Impact

- **Users affected**: Number or percentage.
- **Services affected**: List of impacted services.
- **Data loss**: Yes/No, details.
- **SLA impact**: Minutes/hours of SLA breach.

### 5.5 Action Items

| # | Action | Owner | Priority | Due Date | Status |
|---|--------|-------|----------|----------|--------|
| 1 | Fix root cause | Name | High | YYYY-MM-DD | Open |
| 2 | Add monitoring gap | Name | Medium | YYYY-MM-DD | Open |
| 3 | Update runbook | Name | Low | YYYY-MM-DD | Open |

### 5.6 Lessons Learned

- What went well?
- What could be improved?
- What should we stop doing?

### 5.7 Follow-up

- [ ] All action items assigned
- [ ] Monitoring gaps addressed
- [ ] Runbook updated if needed
- [ ] Incident reviewed in team meeting
