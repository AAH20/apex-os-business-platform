# APEX-OS Business Platform — Compliance Automation Framework

> **Version:** 1.0  
> **Last Updated:** 2026-10-01  
> **Owner:** APEX-OS Platform Engineering  
> **Scope:** SOC 2 Type II · ISO 27001:2022 · GDPR · HIPAA · PCI DSS v4.0

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Shared Compliance Infrastructure](#3-shared-compliance-infrastructure)
4. [SOC 2 Type II Automation](#4-soc-2-type-ii-automation)
5. [ISO 27001:2022 Automation](#5-iso-270012022-automation)
6. [GDPR Automation](#6-gdpr-automation)
7. [HIPAA Automation](#7-hipaa-automation)
8. [PCI DSS v4.0 Automation](#8-pci-dss-v40-automation)
9. [Cross-Framework Control Mapping](#9-cross-framework-control-mapping)
10. [CI/CD Compliance Gates](#10-cicd-compliance-gates)
11. [Monitoring & Continuous Assurance](#11-monitoring--continuous-assurance)
12. [Incident Response & Breach Notification](#12-incident-response--breach-notification)
13. [Roles & Responsibilities](#13-roles--responsibilities)
14. [Appendices](#14-appendices)

---

## 1. Executive Summary

APEX-OS Business Platform operates as a multi-tenant SaaS solution processing business-critical data for customers across regulated industries. This document defines the **compliance automation framework** that ensures continuous adherence to five major regulatory and standards frameworks:

| Framework | Type | Audit Cycle | Primary Driver |
|-----------|------|-------------|----------------|
| **SOC 2 Type II** | Attestation | Annual (6-month observation) | Customer trust, enterprise sales |
| **ISO 27001:2022** | Certification | Annual surveillance + 3-year recert | International operations, ISMS maturity |
| **GDPR** | Regulation | Continuous | EU data subjects, data protection |
| **HIPAA** | Regulation | Continuous + risk analysis | US healthcare customers |
| **PCI DSS v4.0** | Standard | Annual (ROC or SAQ) | Payment card processing |

### Design Principles

- **Policy-as-Code (PaC):** All compliance policies expressed as versioned, machine-readable artifacts.
- **Evidence-as-Code:** Audit evidence collected automatically and stored immutably.
- **Shift-Left Compliance:** Controls validated in CI/CD before deployment.
- **Continuous Monitoring:** Real-time control effectiveness measurement, not point-in-time audits.
- **Least Privilege by Default:** All automation runs with minimal required permissions.
- **Separation of Duties:** No single role can both implement and approve compliance controls.

---

## 2. Architecture Overview

### 2.1 Compliance Automation Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│                    APEX-OS Compliance Automation Stack               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Policy      │  │  Evidence    │  │  Remediation │              │
│  │  Engine      │  │  Collector   │  │  Orchestrator│              │
│  │  (OPA/Rego)  │  │  (Falco+     │  │  (Temporal    │              │
│  │              │  │   custom)    │  │   workflows) │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│  ┌──────┴─────────────────┴─────────────────┴───────┐              │
│  │           Compliance Control Plane                │              │
│  │  ┌─────────┐ ┌──────────┐ ┌───────────┐          │              │
│  │  │Control  │ │Evidence  │ │Audit Log  │          │              │
│  │  │Registry │ │Store     │ │(Immutable)│          │              │
│  │  └─────────┘ └──────────┘ └───────────┘          │              │
│  └──────────────────────┬───────────────────────────┘              │
│                         │                                          │
│  ┌──────────────────────┴───────────────────────────┐              │
│  │              Infrastructure Layer                  │              │
│  │  Terraform · Kubernetes · Vault · AWS/GCP/Azure    │              │
│  └───────────────────────────────────────────────────┘              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Components

| Layer | Component | Purpose |
|-------|-----------|---------|
| **Policy Engine** | Open Policy Agent (OPA) / Rego | Declarative policy evaluation, admission control |
| **Secrets Management** | HashiCorp Vault | Dynamic secrets, encryption key rotation, PKI |
| **Evidence Collection** | Falco + Custom Collectors | Runtime threat detection, config drift detection |
| **Workflow Engine** | Temporal | Remediation workflows, approval chains |
| **Audit Logging** | ImmuDB / AWS QLDB | Tamper-evident audit trail |
| **SIEM** | Elastic Security / Splunk | Log aggregation, correlation, alerting |
| **CSPM** | Wiz / Prisma Cloud | Cloud security posture management |
| **IaC Scanning** | Checkov + tfsec | Terraform/Kubernetes manifest scanning |
| **Container Scanning** | Trivy + Snyk | Image vulnerability scanning |
| **DAST/SAST** | OWASP ZAP + Semgrep | Application security testing |
| **GRC Platform** | Vanta / Drata / Custom | Control mapping, evidence orchestration |

---

## 3. Shared Compliance Infrastructure

### 3.1 Identity & Access Management (IAM)

All frameworks require robust access controls. The shared IAM layer serves as the foundation.

#### 3.1.1 Access Control Policy (Rego)

```rego
# iam/access_control.rego
package apex.iam

import future.keywords.if
import future.keywords.in

# Deny access without MFA for privileged roles
deny[msg] if {
    input.user.role in ["admin", "security-admin", "compliance-officer"]
    not input.user.mfa_verified
    msg := sprintf("MFA required for role %s", [input.user.role])
}

# Deny access outside business hours for sensitive operations
deny[msg] if {
    input.action in ["delete", "modify-policy", "export-data"]
    not is_business_hours(input.timestamp)
    msg := "Sensitive operations only allowed during business hours (06:00-22:00 UTC)"
}

# Deny access from non-approved locations
deny[msg] if {
    input.user.role in ["admin", "security-admin"]
    not input.user.location in data.allowed_admin_locations
    msg := sprintf("Admin access not permitted from %s", [input.user.location])
}

# Require just-in-time access for production
deny[msg] if {
    input.environment == "production"
    not input.user.jit_approved
    msg := "Production access requires JIT approval"
}

is_business_hours(timestamp) if {
    time := time.parse_ns("2006-01-02T15:04:05Z", timestamp)
    [hour, _, _] := time.clock(time)
    hour >= 6
    hour < 22
}
```

#### 3.1.2 Role-Based Access Control Matrix

| Role | SOC 2 | ISO 27001 | GDPR | HIPAA | PCI DSS |
|------|-------|-----------|------|-------|---------|
| Platform Admin | Full | Full | DPO consult | Security Officer | Admin |
| Security Admin | Full | Full | DPO consult | Security Officer | Admin |
| Compliance Officer | Read + Report | Read + Report | DPO | Privacy Officer | QSA liaison |
| Developer | Dev env only | Dev env only | Anonymized data only | No PHI | No CHD |
| Support | Ticket-level | Ticket-level | With consent | Minimum necessary | No CHD |
| Auditor | Read-only | Read-only | Read-only | Read-only | Read-only |

### 3.2 Encryption Standards

#### 3.2.1 Encryption Policy

```yaml
# crypto/encryption-policy.yaml
encryption:
  at_rest:
    algorithm: AES-256-GCM
    key_management: HashiCorp Vault (auto-rotation: 90 days)
    database: Transparent Data Encryption (TDE)
    object_storage: Server-side encryption with customer-managed keys (CMK)
    backup: AES-256-GCM with separate key hierarchy
    
  in_transit:
    minimum_tls: "1.2"
    preferred_tls: "1.3"
    certificate_management: cert-manager with Let's Encrypt / ACM
    service_mesh: mTLS via Istio
    api_gateway: TLS 1.3 with HSTS
    
  key_management:
    hsm: AWS CloudHSM / Azure Dedicated HSM
    rotation_schedule:
      data_encryption_keys: 90 days
      key_encryption_keys: 365 days
      certificates: 60 days
    separation: KEKs stored in HSM, DEKs in Vault
```

#### 3.2.2 Encryption Verification (Automated)

```bash
#!/bin/bash
# scripts/verify-encryption.sh
# Runs as Kubernetes CronJob every 6 hours

set -euo pipefail

echo "=== APEX-OS Encryption Verification ==="

# Verify TLS versions on all endpoints
echo "[*] Checking TLS configuration..."
for endpoint in $(kubectl get ingress -o jsonpath='{.items[*].spec.rules[*].host}'); do
    tls_version=$(openssl s_client -connect "$endpoint:443" -tls1_2 </dev/null 2>/dev/null | grep "Protocol" | awk '{print $3}')
    if [ "$tls_version" != "TLSv1.2" ] && [ "$tls_version" != "TLSv1.3" ]; then
        echo "FAIL: $endpoint supports $tls_version"
        exit 1
    fi
done
echo "[PASS] All endpoints use TLS 1.2+"

# Verify database encryption
echo "[*] Checking database encryption..."
kubectl exec -it postgres-0 -- psql -U admin -c "SELECT * FROM pg_settings WHERE name LIKE '%ssl%';" | grep "on"
echo "[PASS] Database encryption verified"

# Verify Vault seal status
echo "[*] Checking Vault seal status..."
vault status | grep "Sealed" | grep "false"
echo "[PASS] Vault unsealed and operational"

echo "=== All encryption checks passed ==="
```

### 3.3 Audit Logging

#### 3.3.1 Audit Log Schema

```json
{
  "audit_event": {
    "id": "uuid-v4",
    "timestamp": "2026-10-01T12:00:00.000Z",
    "event_type": "authentication | authorization | data_access | data_modification | config_change | admin_action",
    "actor": {
      "type": "user | service | system",
      "id": "string",
      "role": "string",
      "ip_address": "string",
      "mfa_used": "boolean",
      "session_id": "string"
    },
    "resource": {
      "type": "string",
      "id": "string",
      "environment": "string",
      "data_classification": "public | internal | confidential | restricted"
    },
    "action": {
      "type": "string",
      "result": "success | failure | denied",
      "details": {}
    },
    "compliance_context": {
      "frameworks": ["soc2", "iso27001", "gdpr", "hipaa", "pcidss"],
      "control_ids": ["CC6.1", "A.9.4.1", "Art.32", "164.308", "Req 8.2"],
      "data_subject_id": "string (GDPR)",
      "phi_involved": "boolean (HIPAA)",
      "chd_involved": "boolean (PCI DSS)"
    },
    "integrity": {
      "hash": "sha256-of-event",
      "previous_hash": "sha256-of-previous-event",
      "chain_verified": true
    }
  }
}
```

#### 3.3.2 Audit Log Pipeline

```
Application → Fluent Bit → Kafka → Logstash → Elasticsearch
                                         ↓
                                    ImmuDB (immutable copy)
                                         ↓
                                    S3 Glacier (7-year retention)
```

---

## 4. SOC 2 Type II Automation

### 4.1 Trust Services Criteria Mapping

SOC 2 Type II evaluates five Trust Services Criteria (TSC) over an observation period (minimum 6 months).

#### 4.1.1 Control Matrix

| TSC Category | Control ID | Control Description | Automation | Evidence Source |
|-------------|------------|---------------------|------------|-----------------|
| **Security (Common Criteria)** | CC6.1 | Logical access security | OPA admission control + IAM | IAM logs, access reviews |
| | CC6.2 | User access provisioning/deprovisioning | Automated lifecycle workflows | HR system integration, IAM |
| | CC6.3 | Role-based access enforcement | RBAC + ABAC policies | OPA policy evaluations |
| | CC6.4 | Access reviews | Quarterly automated access reviews | Access review reports |
| | CC6.5 | Segregation of duties | SoD policy engine | SoD violation reports |
| | CC6.6 | Encryption for data at rest | TDE + Vault encryption | Encryption verification logs |
| | CC6.7 | Encryption for data in transit | TLS 1.2+ enforcement | TLS scan results |
| | CC6.8 | Network security | Security groups, WAF, IDS/IPS | Network scan results |
| | CC6.9 | Vulnerability management | Continuous scanning + remediation SLA | Vulnerability reports |
| | CC6.10 | Monitoring and alerting | SIEM + alerting rules | Alert logs, incident tickets |
| **Availability** | A1.1 | Capacity monitoring | Auto-scaling policies | CloudWatch metrics |
| | A1.2 | Backup and recovery | Automated backup + DR testing | Backup logs, DR test reports |
| | A1.3 | Incident response | Automated incident workflows | Incident tickets, post-mortems |
| **Processing Integrity** | PI1.1 | Input validation | Schema validation + API gateway | API logs |
| | PI1.2 | Processing monitoring | Data pipeline monitoring | Pipeline logs |
| | PI1.3 | Output validation | Reconciliation jobs | Reconciliation reports |
| **Confidentiality** | C1.1 | Data classification | Automated classification engine | Classification reports |
| | C1.2 | Data handling procedures | DLP policies | DLP alert logs |
| | C1.3 | Data retention and disposal | Retention policies + secure deletion | Deletion certificates |
| **Privacy** | P1.1 | Privacy notice | Versioned privacy policy | Policy version history |
| | P1.2 | Consent management | Consent tracking system | Consent records |
| | P1.3 | Data subject rights | Automated DSR workflows | DSR request logs |
| | P1.4 | Data minimization | Collection limitation policies | Data inventory |

#### 4.1.2 Automated Evidence Collection

```python
# collectors/soc2_evidence_collector.py
"""
SOC 2 Evidence Collector
Runs daily to gather evidence for all Trust Services Criteria.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List
import boto3
import requests
from vault_client import VaultClient

class SOC2EvidenceCollector:
    def __init__(self):
        self.vault = VaultClient()
        self.s3 = boto3.client('s3')
        self.evidence_bucket = "apex-os-compliance-evidence"
        self.date = datetime.utcnow().strftime("%Y-%m-%d")
        
    def collect_all(self) -> Dict:
        """Collect evidence for all SOC 2 controls."""
        evidence = {
            "collection_date": self.date,
            "framework": "SOC2",
            "controls": {}
        }
        
        # CC6 - Logical and Physical Access Controls
        evidence["controls"]["CC6.1"] = self._collect_access_control_evidence()
        evidence["controls"]["CC6.2"] = self._collect_lifecycle_evidence()
        evidence["controls"]["CC6.3"] = self._collect_rbac_evidence()
        evidence["controls"]["CC6.4"] = self._collect_access_review_evidence()
        evidence["controls"]["CC6.5"] = self._collect_sod_evidence()
        evidence["controls"]["CC6.6"] = self._collect_encryption_at_rest_evidence()
        evidence["controls"]["CC6.7"] = self._collect_encryption_in_transit_evidence()
        evidence["controls"]["CC6.8"] = self._collect_network_security_evidence()
        evidence["controls"]["CC6.9"] = self._collect_vulnerability_evidence()
        evidence["controls"]["CC6.10"] = self._collect_monitoring_evidence()
        
        # A - Availability
        evidence["controls"]["A1.1"] = self._collect_capacity_evidence()
        evidence["controls"]["A1.2"] = self._collect_backup_evidence()
        evidence["controls"]["A1.3"] = self._collect_incident_response_evidence()
        
        # PI - Processing Integrity
        evidence["controls"]["PI1.1"] = self._collect_input_validation_evidence()
        evidence["controls"]["PI1.2"] = self._collect_processing_monitoring_evidence()
        evidence["controls"]["PI1.3"] = self._collect_output_validation_evidence()
        
        # C - Confidentiality
        evidence["controls"]["C1.1"] = self._collect_classification_evidence()
        evidence["controls"]["C1.2"] = self._collect_data_handling_evidence()
        evidence["controls"]["C1.3"] = self._collect_retention_evidence()
        
        # P - Privacy
        evidence["controls"]["P1.1"] = self._collect_privacy_notice_evidence()
        evidence["controls"]["P1.2"] = self._collect_consent_evidence()
        evidence["controls"]["P1.3"] = self._collect_dsr_evidence()
        evidence["controls"]["P1.4"] = self._collect_data_minimization_evidence()
        
        # Store evidence with integrity hash
        self._store_evidence(evidence)
        return evidence
    
    def _collect_access_control_evidence(self) -> Dict:
        """CC6.1 - Collect logical access control evidence."""
        # Query IAM system for access policies
        policies = self._query_iam_policies()
        
        # Verify all access is authenticated
        auth_events = self._query_auth_events(days=30)
        
        # Check for unauthorized access attempts
        failed_auth = [e for e in auth_events if e["result"] == "failure"]
        
        return {
            "control_id": "CC6.1",
            "description": "Logical access security",
            "evidence": {
                "active_policies": len(policies),
                "auth_events_30d": len(auth_events),
                "failed_auth_30d": len(failed_auth),
                "failed_auth_rate": len(failed_auth) / max(len(auth_events), 1),
                "mfa_enforcement_rate": self._calculate_mfa_rate(auth_events),
                "policy_violations": self._check_policy_violations()
            },
            "status": "effective" if len(failed_auth) / max(len(auth_events), 1) < 0.05 else "needs_attention",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _collect_encryption_at_rest_evidence(self) -> Dict:
        """CC6.6 - Collect encryption at rest evidence."""
        # Verify database encryption
        db_encryption = self._verify_database_encryption()
        
        # Verify storage encryption
        storage_encryption = self._verify_storage_encryption()
        
        # Verify backup encryption
        backup_encryption = self._verify_backup_encryption()
        
        # Check key rotation status
        key_rotation = self._check_key_rotation()
        
        return {
            "control_id": "CC6.6",
            "description": "Encryption for data at rest",
            "evidence": {
                "database_encryption": db_encryption,
                "storage_encryption": storage_encryption,
                "backup_encryption": backup_encryption,
                "key_rotation_status": key_rotation,
                "algorithm": "AES-256-GCM",
                "hsm_protected": True
            },
            "status": "effective" if all([db_encryption["encrypted"], 
                                           storage_encryption["encrypted"],
                                           backup_encryption["encrypted"]]) else "deficient",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _collect_vulnerability_evidence(self) -> Dict:
        """CC6.9 - Collect vulnerability management evidence."""
        # Run vulnerability scan
        scan_results = self._run_vulnerability_scan()
        
        # Check remediation SLAs
        critical_open = [v for v in scan_results if v["severity"] == "critical" and v["status"] == "open"]
        high_open = [v for v in scan_results if v["severity"] == "high" and v["status"] == "open"]
        
        # SLA: Critical = 24h, High = 7 days, Medium = 30 days, Low = 90 days
        critical_sla_breach = [v for v in critical_open if v["age_hours"] > 24]
        high_sla_breach = [v for v in high_open if v["age_days"] > 7]
        
        return {
            "control_id": "CC6.9",
            "description": "Vulnerability management",
            "evidence": {
                "scan_date": self.date,
                "total_vulnerabilities": len(scan_results),
                "critical_open": len(critical_open),
                "high_open": len(high_open),
                "medium_open": len([v for v in scan_results if v["severity"] == "medium" and v["status"] == "open"]),
                "low_open": len([v for v in scan_results if v["severity"] == "low" and v["status"] == "open"]),
                "critical_sla_breaches": len(critical_sla_breach),
                "high_sla_breaches": len(high_sla_breach),
                "mean_time_to_remediate": self._calculate_mttr(scan_results)
            },
            "status": "effective" if len(critical_sla_breach) == 0 and len(high_sla_breach) == 0 else "needs_attention",
            "collected_at": datetime.utcnow().isoformat()
        }
    
    def _store_evidence(self, evidence: Dict):
        """Store evidence in S3 with integrity verification."""
        key = f"soc2/{self.date}/{hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()}.json"
        
        self.s3.put_object(
            Bucket=self.evidence_bucket,
            Key=key,
            Body=json.dumps(evidence, indent=2),
            ContentType="application/json",
            Metadata={
                "framework": "soc2",
                "date": self.date,
                "integrity-hash": hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
            }
        )
        
        # Also store hash in ImmuDB for tamper evidence
        self._store_integrity_hash(key, evidence)
```

#### 4.1.3 Continuous Control Monitoring

```yaml
# monitoring/soc2-controls.yaml
# Prometheus alerting rules for SOC 2 controls

groups:
  - name: soc2_access_controls
    rules:
      - alert: HighFailedAuthRate
        expr: |
          (
            sum(rate(auth_failures_total[5m])) 
            / 
            sum(rate(auth_attempts_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: critical
          framework: soc2
          control: CC6.1
        annotations:
          summary: "High authentication failure rate detected"
          description: "Failed auth rate is {{ $value | humanizePercentage }} (threshold: 10%)"
          
      - alert: PrivilegedAccessWithoutMFA
        expr: |
          privileged_access_total{mfa_used="false"} > 0
        for: 1m
        labels:
          severity: critical
          framework: soc2
          control: CC6.1
        annotations:
          summary: "Privileged access without MFA detected"
          
      - alert: AccessReviewOverdue
        expr: |
          (time() - last_access_review_timestamp) > 7776000  # 90 days
        for: 1h
        labels:
          severity: warning
          framework: soc2
          control: CC6.4
        annotations:
          summary: "Quarterly access review overdue"

  - name: soc2_encryption
    rules:
      - alert: TLSCertificateExpiringSoon
        expr: |
          (cert_expiry_timestamp - time()) < 1209600  # 14 days
        for: 1h
        labels:
          severity: warning
          framework: soc2
          control: CC6.7
        annotations:
          summary: "TLS certificate expiring in less than 14 days"
          
      - alert: KeyRotationOverdue
        expr: |
          (time() - last_key_rotation_timestamp) > 7776000  # 90 days
        for: 1h
        labels:
          severity: warning
          framework: soc2
          control: CC6.6
        annotations:
          summary: "Encryption key rotation overdue"

  - name: soc2_availability
    rules:
      - alert: BackupFailure
        expr: |
          increase(backup_failures_total[24h]) > 0
        for: 5m
        labels:
          severity: critical
          framework: soc2
          control: A1.2
        annotations:
          summary: "Backup failure detected in last 24 hours"
          
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
          framework: soc2
          control: A1.1
        annotations:
          summary: "P99 latency exceeds 2 seconds"
```

### 4.2 SOC 2 Audit Readiness Workflow

```yaml
# workflows/soc2-audit-readiness.yaml
# Temporal workflow for SOC 2 audit preparation

name: soc2-audit-readiness
schedule: "0 0 1 * *"  # First day of each month

steps:
  - name: collect-evidence
    activity: collect_all_evidence
    retry_policy:
      max_attempts: 3
      initial_interval: 30s
      
  - name: validate-evidence-completeness
    activity: validate_evidence
    input:
      required_controls:
        - CC6.1
        - CC6.2
        - CC6.3
        - CC6.4
        - CC6.5
        - CC6.6
        - CC6.7
        - CC6.8
        - CC6.9
        - CC6.10
        - A1.1
        - A1.2
        - A1.3
        - PI1.1
        - PI1.2
        - PI1.3
        - C1.1
        - C1.2
        - C1.3
        - P1.1
        - P1.2
        - P1.3
        - P1.4
        
  - name: generate-gap-report
    activity: generate_gap_report
    
  - name: create-remediation-tasks
    activity: create_remediation_tasks
    condition: gap_report.has_gaps
    
  - name: notify-stakeholders
    activity: send_notification
    input:
      recipients:
        - compliance@apex-os.com
        - security@apex-os.com
        - cto@apex-os.com
      template: monthly_compliance_report
```

---

## 5. ISO 27001:2022 Automation

### 5.1 ISMS Structure

ISO 27001:2022 requires an Information Security Management System (ISMS) with 93 controls across 4 themes (Annex A).

#### 5.1.1 Control Themes and Automation Coverage

| Theme | Controls | Automated | Partially Automated | Manual |
|-------|----------|-----------|---------------------|--------|
| **A.5** Organizational | 37 | 28 | 7 | 2 |
| **A.6** People | 8 | 5 | 2 | 1 |
| **A.7** Technological | 34 | 29 | 4 | 1 |
| **A.8** Physical | 14 | 10 | 3 | 1 |
| **Total** | **93** | **72 (77%)** | **16 (17%)** | **5 (6%)** |

#### 5.1.2 Key Control Mappings

| ISO Control | Description | Automation | Evidence |
|-------------|-------------|------------|----------|
| A.5.1 | Information security policies | Policy-as-code in Git, versioned | Git history, review records |
| A.5.2 | Information security roles | IAM role definitions | IAM config, org chart |
| A.5.3 | Segregation of duties | SoD policy engine | SoD violation reports |
| A.5.7 | Threat intelligence | Automated threat feeds | Threat intel reports |
| A.5.8 | Information security in project management | CI/CD compliance gates | Pipeline logs |
| A.5.12 | Classification of data | Automated classification engine | Classification reports |
| A.5.13 | Labelling of data | Metadata tagging system | Tagging audit logs |
| A.5.14 | Information transfer | DLP + secure transfer policies | DLP logs |
| A.5.15 | Access control | IAM + RBAC + ABAC | Access logs |
| A.5.16 | Identity management | Automated lifecycle | Lifecycle logs |
| A.5.17 | Authentication information | Vault + MFA | Auth logs |
| A.5.18 | Access rights | Access review automation | Review reports |
| A.5.23 | Information security for use of cloud services | CSPM + CloudTrail | CSPM reports |
| A.5.24 | Information security incident management | Automated incident response | Incident tickets |
| A.5.25 | Assessment and decision on information security events | SIEM correlation | SIEM alerts |
| A.5.26 | Response to information security incidents | Automated playbooks | Playbook execution logs |
| A.5.27 | Learning from information security incidents | Post-mortem automation | Post-mortem docs |
| A.5.28 | Collection of evidence | Evidence collector | Evidence store |
| A.5.30 | ICT readiness for business continuity | DR automation | DR test reports |
| A.6.1 | Screening | Background check integration | Screening records |
| A.6.3 | Information security awareness | Training platform + tracking | Training records |
| A.6.5 | Responsible disclosure | Bug bounty program | Disclosure reports |
| A.6.6 | Protection from legal obligations | Legal hold automation | Legal hold records |
| A.6.7 | Remote working | Zero trust architecture | ZTNA logs |
| A.6.8 | Information security event monitoring | SIEM + UEBA | Monitoring reports |
| A.7.1 | Physical entry controls | Badge system integration | Badge logs |
| A.7.2 | Securing offices, rooms and facilities | Environmental monitoring | Sensor logs |
| A.7.3 | Physical access control | Access control system | Physical access logs |
| A.7.4 | Physical security monitoring | CCTV + analytics | Monitoring logs |
| A.7.5 | Protecting against physical and environmental threats | Environmental controls | Environmental logs |
| A.7.6 | Secure areas | Data center controls | DC audit reports |
| A.7.7 | Clear desk and clear screen | Policy + enforcement | Policy acknowledgments |
| A.7.8 | Equipment siting and protection | Asset management | Asset inventory |
| A.7.9 | Security of assets off-premises | MDM + encryption | MDM logs |
| A.7.10 |Storage media | Media management | Media inventory |
| A.7.11 | Supporting utilities | UPS + generator monitoring | Utility logs |
| A.7.12 | Cabling security | Cable management | Infrastructure docs |
| A.7.13 | Equipment maintenance | Maintenance tracking | Maintenance logs |
| A.7.14 | Secure disposal or re-use of equipment | Disposal certificates | Disposal records |
| A.8.1 | User endpoint devices | MDM + EDR | Endpoint logs |
| A.8.2 | Privileged access rights | PAM solution | PAM logs |
| A.8.3 | Information access restriction | RBAC + ABAC | Access logs |
| A.8.4 | Access to source code | Git branch protection | Git audit logs |
| A.8.5 | Secure authentication | MFA + SSO | Auth logs |
| A.8.6 | Capacity management | Auto-scaling | Capacity reports |
| A.8.7 | Protection against malware | EDR + AV | Malware reports |
| A.8.8 | Management of technical vulnerabilities | Vulnerability management | Vuln reports |
| A.8.9 | Configuration management | IaC + GitOps | Config drift reports |
| A.8.10 | Information deletion | Retention policies | Deletion certificates |
| A.8.11 | Data masking | Dynamic data masking | Masking logs |
| A.8.12 | Data leakage prevention | DLP solution | DLP alerts |
| A.8.13 | Information backup | Automated backups | Backup logs |
| A.8.14 |Redundancy of information processing facilities | Multi-AZ + DR | DR test reports |
| A.8.15 |Logging | Centralized logging | Log integrity reports |
| A.8.16 | Monitoring activities | SIEM + NIDS | Monitoring reports |
| A.8.17 | Clock synchronization | NTP monitoring | NTP sync logs |
| A.8.18 | Use of privileged utility programs | PAM + sudo logging | Privilege logs |
| A.8.19 | Installation of software on operational systems | Change management | Change tickets |
| A.8.20 | Networks security | Network segmentation | Network scan results |
| A.8.21 | Security of network services | Service mesh + mTLS | Mesh logs |
| A.8.22 | Segregation of networks | VPC + subnets | Network topology |
| A.8.23 | Web filtering | WAF + DNS filtering | WAF logs |
| A.8.24 | Use of cryptography | KMS + HSM | Key management logs |
| A.8.25 | Secure development lifecycle | CI/CD security gates | Pipeline logs |
| A.8.26 | Application security requirements | Threat modeling | Threat model docs |
| A.8.27 | Secure architecture and engineering principles | Architecture review | Architecture docs |
| A.8.28 | Secure coding | SAST + DAST | Scan results |
| A.8.29 | Security testing in development and acceptance | Automated security testing | Test reports |
| A.8.30 | Outsourced development | Vendor assessment | Vendor reports |
| A.8.31 | Separation of development, test and production environments | Environment isolation | Environment configs |
| A.8.32 | Change management | Change approval workflow | Change tickets |
| A.8.33 | Test data management | Data anonymization | Anonymization logs |
| A.8.34 | Protection of information systems during audit testing | Audit logging | Audit logs |

### 5.2 Risk Management Automation

```python
# risk_management/risk_engine.py
"""
ISO 27001 Risk Management Engine
Automates risk assessment, treatment planning, and monitoring.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from datetime import datetime, timedelta
import json

class RiskLevel(Enum):
    CRITICAL = "critical"      # Immediate action required
    HIGH = "high"              # Action within 7 days
    MEDIUM = "medium"          # Action within 30 days
    LOW = "low"                # Action within 90 days
    ACCEPTED = "accepted"      # Risk accepted by management

class RiskStatus(Enum):
    IDENTIFIED = "identified"
    ASSESSED = "assessed"
    TREATMENT_PLANNED = "treatment_planned"
    TREATMENT_IN_PROGRESS = "treatment_in_progress"
    TREATED = "treated"
    ACCEPTED = "accepted"
    MONITORING = "monitoring"

@dataclass
class Risk:
    id: str
    title: str
    description: str
    asset: str
    threat: str
    vulnerability: str
    likelihood: int  # 1-5
    impact: int     # 1-5
    risk_score: int  # likelihood * impact
    risk_level: RiskLevel
    status: RiskStatus
    owner: str
    treatment_plan: Optional[str] = None
    residual_risk: Optional[int] = None
    created_at: datetime = None
    review_date: datetime = None

class RiskManagementEngine:
    def __init__(self):
        self.risks = {}
        self.risk_register = []
        
    def calculate_risk_score(self, likelihood: int, impact: int) -> int:
        """Calculate risk score using 5x5 risk matrix."""
        return likelihood * impact
    
    def determine_risk_level(self, score: int) -> RiskLevel:
        """Determine risk level from score."""
        if score >= 20:
            return RiskLevel.CRITICAL
        elif score >= 12:
            return RiskLevel.HIGH
        elif score >= 6:
            return RiskLevel.MEDIUM
        elif score >= 1:
            return RiskLevel.LOW
        else:
            return RiskLevel.ACCEPTED
    
    def identify_risks(self) -> List[Risk]:
        """Automatically identify risks from various sources."""
        risks = []
        
        # Scan for vulnerabilities
        vuln_risks = self._scan_vulnerabilities()
        risks.extend(vuln_risks)
        
        # Check compliance gaps
        compliance_risks = self._check_compliance_gaps()
        risks.extend(compliance_risks)
        
        # Review threat intelligence
        threat_risks = self._review_threat_intel()
        risks.extend(threat_risks)
        
        # Assess third-party risks
        vendor_risks = self._assess_vendor_risks()
        risks.extend(vendor_risks)
        
        return risks
    
    def _scan_vulnerabilities(self) -> List[Risk]:
        """Convert vulnerability scan results to risks."""
        risks = []
        vulns = self._get_open_vulnerabilities()
        
        for vuln in vulns:
            likelihood = self._map_cvss_to_likelihood(vuln["cvss_score"])
            impact = self._assess_business_impact(vuln["asset"])
            score = self.calculate_risk_score(likelihood, impact)
            
            risk = Risk(
                id=f"RISK-VULN-{vuln['id']}",
                title=f"Vulnerability: {vuln['name']}",
                description=vuln["description"],
                asset=vuln["asset"],
                threat="Exploitation of known vulnerability",
                vulnerability=vuln["name"],
                likelihood=likelihood,
                impact=impact,
                risk_score=score,
                risk_level=self.determine_risk_level(score),
                status=RiskStatus.IDENTIFIED,
                owner="security-team",
                created_at=datetime.utcnow(),
                review_date=datetime.utcnow() + timedelta(days=7)
            )
            risks.append(risk)
        
        return risks
    
    def generate_risk_treatment_plan(self, risk: Risk) -> dict:
        """Generate automated risk treatment plan."""
        if risk.risk_level == RiskLevel.CRITICAL:
            return {
                "strategy": "mitigate",
                "actions": [
                    "Immediate patching required",
                    "Implement compensating controls",
                    "Escalate to CISO within 4 hours",
                    "Daily status updates until resolved"
                ],
                "timeline": "24 hours",
                "resources": "Emergency change window"
            }
        elif risk.risk_level == RiskLevel.HIGH:
            return {
                "strategy": "mitigate",
                "actions": [
                    "Schedule emergency change",
                    "Implement temporary controls",
                    "Weekly status updates"
                ],
                "timeline": "7 days",
                "resources": "Priority change window"
            }
        elif risk.risk_level == RiskLevel.MEDIUM:
            return {
                "strategy": "mitigate",
                "actions": [
                    "Include in next sprint",
                    "Implement permanent fix"
                ],
                "timeline": "30 days",
                "resources": "Normal change process"
            }
        else:
            return {
                "strategy": "accept",
                "actions": [
                    "Document risk acceptance",
                    "Review quarterly"
                ],
                "timeline": "90 days",
                "resources": "N/A"
            }
    
    def generate_risk_report(self) -> dict:
        """Generate ISO 27001 risk assessment report."""
        risks = list(self.risks.values())
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_risks": len(risks),
            "by_level": {
                "critical": len([r for r in risks if r.risk_level == RiskLevel.CRITICAL]),
                "high": len([r for r in risks if r.risk_level == RiskLevel.HIGH]),
                "medium": len([r for r in risks if r.risk_level == RiskLevel.MEDIUM]),
                "low": len([r for r in risks if r.risk_level == RiskLevel.LOW]),
                "accepted": len([r for r in risks if r.risk_level == RiskLevel.ACCEPTED])
            },
            "by_status": {
                "identified": len([r for r in risks if r.status == RiskStatus.IDENTIFIED]),
                "assessed": len([r for r in risks if r.status == RiskStatus.ASSESSSED]),
                "treatment_planned": len([r for r in risks if r.status == RiskStatus.TREATMENT_PLANNED]),
                "treatment_in_progress": len([r for r in risks if r.status == RiskStatus.TREATMENT_IN_PROGRESS]),
                "treated": len([r for r in risks if r.status == RiskStatus.TREATED]),
                "accepted": len([r for r in risks if r.status == RiskStatus.ACCEPTED]),
                "monitoring": len([r for r in risks if r.status == RiskStatus.MONITORING])
            },
            "overdue_reviews": len([r for r in risks if r.review_date and r.review_date < datetime.utcnow()]),
            "top_risks": [
                {
                    "id": r.id,
                    "title": r.title,
                    "score": r.risk_score,
                    "level": r.risk_level.value,
                    "status": r.status.value
                }
                for r in sorted(risks, key=lambda x: x.risk_score, reverse=True)[:10]
            ]
        }
```

### 5.3 Statement of Applicability (SoA) Automation

```yaml
# iso27001/statement-of-applicability.yaml
# Auto-generated Statement of Applicability

version: "2026-10-01"
generated_by: "compliance-automation-framework"

controls:
  # A.5 - Organizational Controls
  - id: A.5.1
    title: "Policies for information security"
    applicable: true
    justification: "Required for ISMS governance"
    implementation_status: "implemented"
    automation: "policy-as-code"
    evidence: ["git-history", "policy-review-records"]
    
  - id: A.5.2
    title: "Information security roles and responsibilities"
    applicable: true
    justification: "Required for clear accountability"
    implementation_status: "implemented"
    automation: "iam-role-definitions"
    evidence: ["iam-config", "org-chart"]
    
  - id: A.5.3
    title: "Segregation of duties"
    applicable: true
    justification: "Prevents fraud and error"
    implementation_status: "implemented"
    automation: "sod-policy-engine"
    evidence: ["sod-violation-reports"]
    
  - id: A.5.7
    title: "Threat intelligence"
    applicable: true
    justification: "Proactive threat identification"
    implementation_status: "implemented"
    automation: "automated-threat-feeds"
    evidence: ["threat-intel-reports"]
    
  - id: A.5.8
    title: "Information security in project management"
    applicable: true
    justification: "Security built into projects"
    implementation_status: "implemented"
    automation: "cicd-compliance-gates"
    evidence: ["pipeline-logs"]
    
  - id: A.5.12
    title: "Classification of information"
    applicable: true
    justification: "Data protection foundation"
    implementation_status: "implemented"
    automation: "automated-classification-engine"
    evidence: ["classification-reports"]
    
  - id: A.5.13
    title: "Labelling of information"
    applicable: true
    justification: "Supports classification"
    implementation_status: "implemented"
    automation: "metadata-tagging-system"
    evidence: ["tagging-audit-logs"]
    
  - id: A.5.14
    title: "Information transfer"
    applicable: true
    justification: "Protects data in motion"
    implementation_status: "implemented"
    automation: "dlp-secure-transfer-policies"
    evidence: ["dlp-logs"]
    
  - id: A.5.15
    title: "Access control"
    applicable: true
    justification: "Core security control"
    implementation_status: "implemented"
    automation: "iam-rbac-abac"
    evidence: ["access-logs"]
    
  - id: A.5.16
    title: "Identity management"
    applicable: true
    justification: "Lifecycle management"
    implementation_status: "implemented"
    automation: "automated-lifecycle"
    evidence: ["lifecycle-logs"]
    
  - id: A.5.17
    title: "Authentication information"
    applicable: true
    justification: "Secure authentication"
    implementation_status: "implemented"
    automation: "vault-mfa"
    evidence: ["auth-logs"]
    
  - id: A.5.18
    title: "Access rights"
    applicable: true
    justification: "Regular review required"
    implementation_status: "implemented"
    automation: "access-review-automation"
    evidence: ["review-reports"]
    
  - id: A.5.23
    title: "Information security for use of cloud services"
    applicable: true
    justification: "Cloud-first architecture"
    implementation_status: "implemented"
    automation: "cspm-cloudtrail"
    evidence: ["cspm-reports"]
    
  - id: A.5.24
    title: "Information security incident management"
    applicable: true
    justification: "Required for response"
    implementation_status: "implemented"
    automation: "automated-incident-response"
    evidence: ["incident-tickets"]
    
  - id: A.5.25
    title: "Assessment and decision on information security events"
    applicable: true
    justification: "Event triage"
    implementation_status: "implemented"
    automation: "siem-correlation"
    evidence: ["siem-alerts"]
    
  - id: A.5.26
    title: "Response to information security incidents"
    applicable: true
    justification: "Incident response"
    implementation_status: "implemented"
    automation: "automated-playbooks"
    evidence: ["playbook-execution-logs"]
    
  - id: A.5.27
    title: "Learning from information security incidents"
    applicable: true
    justification: "Continuous improvement"
    implementation_status: "implemented"
    automation: "post-mortem-automation"
    evidence: ["post-mortem-docs"]
    
  - id: A.5.28
    title: "Collection of evidence"
    applicable: true
    justification: "Audit readiness"
    implementation_status: "implemented"
    automation: "evidence-collector"
    evidence: ["evidence-store"]
    
  - id: A.5.30
    title: "ICT readiness for business continuity"
    applicable: true
    justification: "Business resilience"
    implementation_status: "implemented"
    automation: "dr-automation"
    evidence: ["dr-test-reports"]
    
  # A.6 - People Controls
  - id: A.6.1
    title: "Screening"
    applicable: true
    justification: "Personnel security"
    implementation_status: "implemented"
    automation: "background-check-integration"
    evidence: ["screening-records"]
    
  - id: A.6.3
    title: "Information security awareness, education and training"
    applicable: true
    justification: "Human factor security"
    implementation_status: "implemented"
    automation: "training-platform-tracking"
    evidence: ["training-records"]
    
  - id: A.6.5
    title: "Responsible disclosure"
    applicable: true
    justification: "Vulnerability reporting"
    implementation_status: "implemented"
    automation: "bug-bounty-program"
    evidence: ["disclosure-reports"]
    
  - id: A.6.6
    title: "Protection from legal obligations"
    applicable: true
    justification: "Legal compliance"
    implementation_status: "implemented"
    automation: "legal-hold-automation"
    evidence: ["legal-hold-records"]
    
  - id: A.6.7
    title: "Remote working"
    applicable: true
    justification: "Distributed workforce"
    implementation_status: "implemented"
    automation: "zero-trust-architecture"
    evidence: ["ztna-logs"]
    
  - id: A.6.8
    title: "Information security event monitoring"
    applicable: true
    justification: "Continuous monitoring"
    implementation_status: "implemented"
    automation: "siem-ueba"
    evidence: ["monitoring-reports"]
    
  # A.7 - Technological Controls (selected key controls)
  - id: A.7.1
    title: "Physical entry controls"
    applicable: true
    justification: "Physical security"
    implementation_status: "implemented"
    automation: "badge-system-integration"
    evidence: ["badge-logs"]
    
  - id: A.7.4
    title: "Physical access control"
    applicable: true
    justification: "Access restriction"
    implementation_status: "implemented"
    automation: "access-control-system"
    evidence: ["physical-access-logs"]
    
  - id: A.7.5
    title: "Physical security monitoring"
    applicable: true
    justification: "Security monitoring"
    implementation_status: "implemented"
    automation: "cctv-analytics"
    evidence: ["monitoring-logs"]
    
  - id: A.7.8
    title: "Equipment siting and protection"
    applicable: true
    justification: "Asset protection"
    implementation_status: "implemented"
    automation: "asset-management"
    evidence: ["asset-inventory"]
    
  - id: A.7.9
    title: "Security of assets off-premises"
    applicable: true
    justification: "Remote work security"
    implementation_status: "implemented"
    automation: "mdm-encryption"
    evidence: ["mdm-logs"]
    
  - id: A.7.10
    title: "Storage media"
    applicable: true
    justification: "Media security"
    implementation_status: "implemented"
    automation: "media-management"
    evidence: ["media-inventory"]
    
  - id: A.7.14
    title: "Secure disposal or re-use of equipment"
    applicable: true
    justification: "Data destruction"
    implementation_status: "implemented"
    automation: "disposal-certificates"
    evidence: ["disposal-records"]
    
  - id: A.8.1
    title: "User endpoint devices"
    applicable: true
    justification: "Endpoint security"
    implementation_status: "implemented"
    automation: "mdm-edr"
    evidence: ["endpoint-logs"]
    
  - id: A.8.2
    title: "Privileged access rights"
    applicable: true
    justification: "Admin access control"
    implementation_status: "implemented"
    automation: "pam-solution"
    evidence: ["pam-logs"]
    
  - id: A.8.3
    title: "Information access restriction"
    applicable: true
    justification: "Access control"
    implementation_status: "implemented"
    automation: "rbac-abac"
    evidence: ["access-logs"]
    
  - id: A.8.4
    title: "Access to source code"
    applicable: true
    justification: "IP protection"
    implementation_status: "implemented"
    automation: "git-branch-protection"
    evidence: ["git-audit-logs"]
    
  - id: A.8.5
    title: "Secure authentication"
    applicable: true
    justification: "Authentication security"
    implementation_status: "implemented"
    automation: "mfa-sso"
    evidence: ["auth-logs"]
    
  - id: A.8.6
    title: "Capacity management"
    applicable: true
    justification: "Availability"
    implementation_status: "implemented"
    automation: "auto-scaling"
    evidence: ["capacity-reports"]
    
  - id: A.8.7
    title: "Protection against malware"
    applicable: true
    justification: "Malware defense"
    implementation_status: "implemented"
    automation: "edr-av"
    evidence: ["malware-reports"]
    
  - id: A.8.8
    title: "Management of technical vulnerabilities"
    applicable: true
    justification: "Vulnerability management"
    implementation_status: "implemented"
    automation: "vulnerability-management"
    evidence: ["vuln-reports"]
    
  - id: A.8.9
    title: "Configuration management"
    applicable: true
    justification: "Secure configuration"
    implementation_status: "implemented"
    automation: "iac-gitops"
    evidence: ["config-drift-reports"]
    
  - id: A.8.10
    title: "Information deletion"
    applicable: true
    justification: "Data lifecycle"
    implementation_status: "implemented"
    automation: "retention-policies"
    evidence: ["deletion-certificates"]
    
  - id: A.8.11
    title: "Data masking"
    applicable: true
    justification: "Data protection"
    implementation_status: "implemented"
    automation: "dynamic-data-masking"
    evidence: ["masking-logs"]
    
  - id: A.8.12
    title: "Data leakage prevention"
    applicable: true
    justification: "Data protection"
    implementation_status: "implemented"
    automation: "dlp-solution"
    evidence: ["dlp-alerts"]
    
  - id: A.8.13
    title: "Information backup"
    applicable: true
    justification: "Data protection"
    implementation_status: "implemented"
    automation: "automated-backups"
    evidence: ["backup-logs"]
    
  - id: A.8.14
    title: "Redundancy of information processing facilities"
    applicable: true
    justification: "Availability"
    implementation_status: "implemented"
    automation: "multi-az-dr"
    evidence: ["dr-test-reports"]
    
  - id: A.8.15
    title: "Logging"
    applicable: true
    justification: "Audit trail"
    implementation_status: "implemented"
    automation: "centralized-logging"
    evidence: ["log-integrity-reports"]
    
  - id: A.8.16
    title: "Monitoring activities"
    applicable: true
    justification: "Security monitoring"
    implementation_status: "implemented"
    automation: "siem-nids"
    evidence: ["monitoring-reports"]
    
  - id: A.8.17
    title: "Clock synchronization"
    applicable: true
    justification: "Log integrity"
    implementation_status: "implemented"
    automation: "ntp-monitoring"
    evidence: ["ntp-sync-logs"]
    
  - id: A.8.18
    title: "Use of privileged utility programs"
    applicable: true
    justification: "Privilege control"
    implementation_status: "implemented"
    automation: "pam-sudo-logging"
    evidence: ["privilege-logs"]
    
  - id: A.8.19
    title: "Installation of software on operational systems"
    applicable: true
    justification: "Change control"
    implementation_status: "implemented"
    automation: "change-management"
    evidence: ["change-tickets"]
    
  - id: A.8.20
    title: "Networks security"
    applicable: true
    justification: "Network protection"
    implementation_status: "implemented"
    automation: "network-segmentation"
    evidence: ["network-scan-results"]
    
  - id: A.8.21
    title: "Security of network services"
    applicable: true
    justification: "Service security"
    implementation_status: "implemented"
    automation: "service-mesh-mtls"
    evidence: ["mesh-logs"]
    
  - id: A.8.22
    title: "Segregation of networks"
    applicable: true
    justification: "Network isolation"
    implementation_status: "implemented"
    automation: "vpc-subnets"
    evidence: ["network-topology"]
    
  - id: A.8.23
    title: "Web filtering"
    applicable: true
    justification: "Web security"
    implementation_status: "implemented"
    automation: "waf-dns-filtering"
    evidence: ["waf-logs"]
    
  - id: A.8.24
    title: "Use of cryptography"
    applicable: true
    justification: "Encryption"
    implementation_status: "implemented"
    automation: "kms-hsm"
    evidence: ["key-management-logs"]
    
  - id: A.8.25
    title: "Secure development lifecycle"
    applicable: true
    justification: "Secure coding"
    implementation_status: "implemented"
    automation: "cicd-security-gates"
    evidence: ["pipeline-logs"]
    
  - id: A.8.26
    title: "Application security requirements"
    applicable: true
    justification: "App security"
    implementation_status: "implemented"
    automation: "threat-modeling"
    evidence: ["threat-model-docs"]
    
  - id: A.8.27
    title: "Secure architecture and engineering principles"
    applicable: true
    justification: "Secure design"
    implementation_status: "implemented"
    automation: "architecture-review"
    evidence: ["architecture-docs"]
    
  - id: A.8.28
    title: "Secure coding"
    applicable: true
    justification: "Code security"
    implementation_status: "implemented"
    automation: "sast-dast"
    evidence: ["scan-results"]
    
  - id: A.8.29
    title: "Security testing in development and acceptance"
    applicable: true
    justification: "Security testing"
    implementation_status: "implemented"
    automation: "automated-security-testing"
    evidence: ["test-reports"]
    
  - id: A.8.30
    title: "Outsourced development"
    applicable: true
    justification: "Third-party security"
    implementation_status: "implemented"
    automation: "vendor-assessment"
    evidence: ["vendor-reports"]
    
  - id: A.8.31
    title: "Separation of development, test and production environments"
    applicable: true
    justification: "Environment isolation"
    implementation_status: "implemented"
    automation: "environment-isolation"
    evidence: ["environment-configs"]
    
  - id: A.8.32
    title: "Change management"
    applicable: true
    justification: "Change control"
    implementation_status: "implemented"
    automation: "change-approval-workflow"
    evidence: ["change-tickets"]
    
  - id: A.8.33
    title: "Test data management"
    applicable: true
    justification: "Data protection"
    implementation_status: "implemented"
    automation: "data-anonymization"
    evidence: ["anonymization-logs"]
    
  - id: A.8.34
    title: "Protection of information systems during audit testing"
    applicable: true
    justification: "Audit security"
    implementation_status: "implemented"
    automation: "audit-logging"
    evidence: ["audit-logs"]
    
  # A.8 - Physical Controls (selected)
  - id: A.8.1  # Note: This is actually A.7.1 in ISO 27001:2022
    title: "Physical entry controls"
    applicable: true
    justification: "Physical security"
    implementation_status: "implemented"
    automation: "badge-system"
    evidence: ["badge-logs"]
```

---

## 6. GDPR Automation

### 6.1 GDPR Requirements Mapping

| GDPR Article | Requirement | Automation | Evidence |
|-------------|-------------|------------|----------|
| **Art. 5** | Principles relating to processing | Data minimization policies, purpose limitation | Policy configs, data inventory |
| **Art. 6** | Lawfulness of processing | Consent management, legal basis tracking | Consent records, legal basis registry |
| **Art. 7** | Conditions for consent | Consent capture, withdrawal, proof | Consent audit trail |
| **Art. 12-14** | Transparency information | Privacy notice version management | Notice versions, delivery logs |
| **Art. 15** | Right of access (DSAR) | Automated DSR workflow | DSR request logs, response records |
| **Art. 16** | Right to rectification | Data correction workflow | Correction logs |
| **Art. 17** | Right to erasure | Automated deletion workflow | Deletion certificates |
| **Art. 18** | Right to restriction | Processing restriction flags | Restriction logs |
| **Art. 20** | Right to data portability | Automated export workflow | Export logs |
| **Art. 21** | Right to object | Objection handling workflow | Objection records |
| **Art. 22** | Automated decision-making | Human review workflow | Decision logs |
| **Art. 25** | Data protection by design and default | Privacy engineering controls | Design docs, code reviews |
| **Art. 28** | Processor obligations | Vendor management, DPA tracking | DPA records, vendor assessments |
| **Art. 30** | Records of processing | Automated RoPA generation | RoPA document |
| **Art. 32** | Security of processing | Encryption, access control, testing | Security test reports |
| **Art. 33** | Breach notification (72h) | Automated breach detection and notification | Breach logs, notification records |
| **Art. 34** | Communication of breach to data subjects | Automated communication workflow | Communication logs |
| **Art. 35** | Data Protection Impact Assessment | Automated DPIA workflow | DPIA reports |
| **Art. 37** | Data Protection Officer | DPO appointment, contact management | DPO records |
| **Art. 44-49** | International transfers | Transfer mechanism tracking | Transfer records, SCCs |

### 6.2 Data Subject Request (DSR) Automation

```python
# gdpr/dsr_automation.py
"""
GDPR Data Subject Request Automation
Handles all data subject rights requests (Art. 15-22).
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import uuid
import json

class DSRType(Enum):
    ACCESS = "access"                    # Art. 15
    RECTIFICATION = "rectification"      # Art. 16
    ERASURE = "erasure"                  # Art. 17
    RESTRICTION = "restriction"          # Art. 18
    PORTABILITY = "portability"          # Art. 20
    OBJECTION = "objection"              # Art. 21

class DSRStatus(Enum):
    RECEIVED = "received"
    IDENTITY_VERIFIED = "identity_verified"
    IN_PROGRESS = "in_progress"
    DATA_COLLECTED = "data_collected"
    RESPONSE_PREPARED = "response_prepared"
    SENT = "sent"
    COMPLETED = "completed"
    REJECTED = "rejected"
    EXTENDED = "extended"  # Complex request, 2-month extension

@dataclass
class DataSubjectRequest:
    id: str
    type: DSRType
    data_subject_id: str
    data_subject_email: str
    received_at: datetime
    deadline: datetime  # 30 days from receipt (Art. 12(3))
    status: DSRStatus
    identity_verified: bool = False
    data_sources: List[str] = None
    response_data: Dict = None
    rejection_reason: str = None
    extension_reason: str = None
    completed_at: datetime = None

class DSRAutomation:
    """Automated Data Subject Request handler."""
    
    # GDPR requires response within 30 days (Art. 12(3))
    STANDARD_DEADLINE_DAYS = 30
    # Complex requests can be extended by 2 months (Art. 12(3))
    EXTENSION_DAYS = 60
    
    def __init__(self):
        self.requests = {}
        self.data_inventory = self._load_data_inventory()
        
    def receive_request(self, dsr_type: DSRType, data_subject_id: str, 
                        email: str, details: str) -> DataSubjectRequest:
        """Receive and log a new data subject request."""
        request_id = f"DSR-{uuid.uuid4().hex[:8].upper()}"
        
        request = DataSubjectRequest(
            id=request_id,
            type=dsr_type,
            data_subject_id=data_subject_id,
            data_subject_email=email,
            received_at=datetime.utcnow(),
            deadline=datetime.utcnow() + timedelta(days=self.STANDARD_DEADLINE_DAYS),
            status=DSRStatus.RECEIVED,
            data_sources=[]
        )
        
        self.requests[request_id] = request
        
        # Log the request
        self._log_request_received(request)
        
        # Trigger identity verification
        self._initiate_identity_verification(request)
        
        # Notify DPO
        self._notify_dpo(request)
        
        return request
    
    def _initiate_identity_verification(self, request: DataSubjectRequest):
        """Initiate identity verification process."""
        # Send verification email
        verification_token = self._generate_verification_token(request)
        self._send_verification_email(request.data_subject_email, verification_token)
        
        # Log verification initiation
        self._log_event(request.id, "identity_verification_initiated")
    
    def verify_identity(self, request_id: str, token: str) -> bool:
        """Verify data subject identity."""
        request = self.requests.get(request_id)
        if not request:
            return False
        
        if self._validate_verification_token(request, token):
            request.identity_verified = True
            request.status = DSRStatus.IDENTITY_VERIFIED
            self._log_event(request_id, "identity_verified")
            
            # Start processing
            self._process_request(request)
            return True
        
        return False
    
    def _process_request(self, request: DataSubjectRequest):
        """Process the data subject request based on type."""
        request.status = DSRStatus.IN_PROGRESS
        
        if request.type == DSRType.ACCESS:
            self._handle_access_request(request)
        elif request.type == DSRType.ERASURE:
            self._handle_erasure_request(request)
        elif request.type == DSRType.PORTABILITY:
            self._handle_portability_request(request)
        elif request.type == DSRType.RECTIFICATION:
            self._handle_rectification_request(request)
        elif request.type == DSRType.RESTRICTION:
            self._handle_restriction_request(request)
        elif request.type == DSRType.OBJECTION:
            self._handle_objection_request(request)
    
    def _handle_access_request(self, request: DataSubjectRequest):
        """Handle Art. 15 - Right of access."""
        # Collect data from all sources
        data = {}
        for source in self.data_inventory:
            source_data = self._query_data_source(source, request.data_subject_id)
            if source_data:
                data[source] = source_data
                request.data_sources.append(source)
        
        request.response_data = {
            "personal_data": data,
            "processing_purposes": self._get_processing_purposes(request.data_subject_id),
            "data_recipients": self._get_data_recipients(request.data_subject_id),
            "retention_periods": self._get_retention_periods(request.data_subject_id),
            "data_origin": self._get_data_origin(request.data_subject_id),
            "automated_decision_making": self._get_automated_decisions(request.data_subject_id)
        }
        
        request.status = DSRStatus.DATA_COLLECTED
        self._log_event(request.id, "data_collected", sources=request.data_sources)
    
    def _handle_erasure_request(self, request: DataSubjectRequest):
        """Handle Art. 17 - Right to erasure (right to be forgotten)."""
        # Check for legal obligations that prevent erasure
        legal_holds = self._check_legal_holds(request.data_subject_id)
        
        if legal_holds:
            # Cannot fully erase - restrict processing instead
            request.status = DSRStatus.RESTRICTION
            request.rejection_reason = f"Legal holds prevent erasure: {legal_holds}"
            self._apply_processing_restriction(request.data_subject_id, legal_holds)
            self._log_event(request.id, "erasure_restricted", reason=legal_holds)
        else:
            # Proceed with erasure
            deletion_results = {}
            for source in self.data_inventory:
                result = self._delete_data(source, request.data_subject_id)
                deletion_results[source] = result
                request.data_sources.append(source)
            
            request.response_data = {"deletion_results": deletion_results}
            request.status = DSRStatus.DATA_COLLECTED
            self._log_event(request.id, "data_erased", sources=request.data_sources)
    
    def _handle_portability_request(self, request: DataSubjectRequest):
        """Handle Art. 20 - Right to data portability."""
        # Collect data in structured, commonly used, machine-readable format
        data = {}
        for source in self.data_inventory:
            source_data = self._query_data_source(source, request.data_subject_id)
            if source_data:
                data[source] = source_data
        
        # Export as JSON (machine-readable)
        export_data = {
            "export_date": datetime.utcnow().isoformat(),
            "data_subject_id": request.data_subject_id,
            "personal_data": data,
            "format": "JSON"
        }
        
        request.response_data = export_data
        request.status = DSRStatus.DATA_COLLECTED
        self._log_event(request.id, "data_exported_for_portability")
    
    def check_deadlines(self):
        """Check for approaching deadlines and send alerts."""
        now = datetime.utcnow()
        
        for request in self.requests.values():
            if request.status in [DSRStatus.COMPLETED, DSRStatus.REJECTED]:
                continue
            
            days_remaining = (request.deadline - now).days
            
            if days_remaining <= 3 and days_remaining > 0:
                # Send urgent alert
                self._send_deadline_alert(request, days_remaining)
            elif days_remaining <= 0:
                # Deadline breached - escalate
                self._escalate_breach(request)
    
    def generate_dsr_report(self, start_date: datetime, end_date: datetime) -> dict:
        """Generate DSR processing report for audit."""
        requests_in_period = [
            r for r in self.requests.values()
            if start_date <= r.received_at <= end_date
        ]
        
        return {
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_requests": len(requests_in_period),
            "by_type": {
                "access": len([r for r in requests_in_period if r.type == DSRType.ACCESS]),
                "rectification": len([r for r in requests_in_period if r.type == DSRType.RECTIFICATION]),
                "erasure": len([r for r in requests_in_period if r.type == DSRType.ERASURE]),
                "restriction": len([r for r in requests_in_period if r.type == DSRType.RESTRICTION]),
                "portability": len([r for r in requests_in_period if r.type == DSRType.PORTABILITY]),
                "objection": len([r for r in requests_in_period if r.type == DSRType.OBJECTION])
            },
            "by_status": {
                "completed": len([r for r in requests_in_period if r.status == DSRStatus.COMPLETED]),
                "in_progress": len([r for r in requests_in_period if r.status == DSRStatus.IN_PROGRESS]),
                "rejected": len([r for r in requests_in_period if r.status == DSRStatus.REJECTED])
            },
            "average_response_time_hours": self._calculate_avg_response_time(requests_in_period),
            "deadline_compliance_rate": self._calculate_deadline_compliance(requests_in_period),
            "extensions_used": len([r for r in requests_in_period if r.status == DSRStatus.EXTENDED])
        }
```

### 6.3 Consent Management

```yaml
# gdpr/consent-management.yaml
# Consent management configuration

consent:
  # Consent capture settings
  capture:
    method: "explicit_opt_in"  # Art. 7 - must be affirmative action
    granularity: "per_purpose"  # Separate consent for each purpose
    versioned: true  # Track consent form versions
    timestamped: true  # Record exact time of consent
    proof: true  # Store proof of consent
    
  # Consent purposes
  purposes:
    - id: "account_creation"
      name: "Account Creation"
      description: "Creating and managing your account"
      legal_basis: "contract"  # Art. 6(1)(b)
      required: true
      
    - id: "service_delivery"
      name: "Service Delivery"
      description: "Providing the core platform services"
      legal_basis: "contract"
      required: true
      
    - id: "personalization"
      name: "Personalization"
      description: "Personalizing your experience"
      legal_basis: "consent"  # Art. 6(1)(a)
      required: false
      
    - id: "marketing"
      name: "Marketing Communications"
      description: "Sending marketing emails and updates"
      legal_basis: "consent"
      required: false
      
    - id: "analytics"
      name: "Analytics and Improvement"
      description: "Analyzing usage to improve our services"
      legal_basis: "legitimate_interest"  # Art. 6(1)(f)
      required: false
      
    - id: "third_party_sharing"
      name: "Third-Party Sharing"
      description: "Sharing data with trusted partners"
      legal_basis: "consent"
      required: false
      
  # Consent withdrawal
  withdrawal:
    method: "self_service"  # User can withdraw via settings
    effect: "immediate"  # Withdrawal takes effect immediately
    propagation: "automated"  # Automatically propagate to all processors
    confirmation: true  # Send confirmation of withdrawal
    
  # Consent records retention
  retention:
    active_consents: "duration_of_relationship"
    withdrawn_consents: "3_years"  # Proof of consent withdrawal
    audit_trail: "7_years"
```

### 6.4 Data Protection Impact Assessment (DPIA) Automation

```python
# gdpr/dpia_automation.py
"""
GDPR Data Protection Impact Assessment Automation
Required under Art. 35 for high-risk processing.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class DPIAStatus(Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MITIGATION = "needs_mitigation"

@dataclass
class DPIA:
    id: str
    title: str
    processing_activity: str
    data_types: List[str]
    data_subjects: List[str]
    processors: List[str]
    risk_level: RiskLevel
    status: DPIAStatus
    created_at: datetime
    approved_at: Optional[datetime] = None
    mitigation_measures: List[str] = None
    dpo_advice: str = None
    consultation_required: bool = False  # Art. 36 - consult supervisory authority

class DPIAAutomation:
    """Automated DPIA workflow."""
    
    # Thresholds for mandatory DPIA (Art. 35(3))
    MANDATORY_TRIGGERS = [
        "systematic_monitoring",
        "sensitive_data_large_scale",
        "vulnerable_subjects",
        "automated_decision_making",
        "innovative_technology",
        "data_matching",
        "cross_border_transfer"
    ]
    
    def assess_processing_activity(self, activity: dict) -> DPIA:
        """Assess a processing activity and create DPIA if required."""
        
        # Check if DPIA is mandatory
        requires_dpia = self._check_mandatory_triggers(activity)
        
        # Assess risk level
        risk_level = self._assess_risk(activity)
        
        if requires_dpia or risk_level in [RiskLevel.HIGH, RiskLevel.MEDIUM]:
            dpia = DPIA(
                id=f"DPIA-{datetime.utcnow().strftime('%Y%m%d')}-{activity['id']}",
                title=activity["name"],
                processing_activity=activity["description"],
                data_types=activity["data_types"],
                data_subjects=activity["data_subjects"],
                processors=activity.get("processors", []),
                risk_level=risk_level,
                status=DPIAStatus.DRAFT,
                created_at=datetime.utcnow()
            )
            
            # Auto-generate mitigation measures
            dpia.mitigation_measures = self._suggest_mitigations(activity, risk_level)
            
            # Check if supervisory authority consultation required
            dpia.consultation_required = self._check_consultation_required(activity, risk_level)
            
            # Notify DPO
            self._notify_dpo(dpia)
            
            return dpia
        
        return None
    
    def _check_mandatory_triggers(self, activity: dict) -> bool:
        """Check if processing activity triggers mandatory DPIA."""
        for trigger in self.MANDATORY_TRIGGERS:
            if activity.get(trigger, False):
                return True
        return False
    
    def _assess_risk(self, activity: dict) -> RiskLevel:
        """Assess risk level of processing activity."""
        score = 0
        
        # Data sensitivity
        if "special_category" in activity.get("data_types", []):
            score += 3
        elif "personal" in activity.get("data_types", []):
            score += 1
        
        # Scale
        if activity.get("data_subject_count", 0) > 10000:
            score += 2
        elif activity.get("data_subject_count", 0) > 1000:
            score += 1
        
        # Vulnerability of subjects
        if "vulnerable" in activity.get("data_subjects", []):
            score += 2
        
        # Technology
        if activity.get("innovative_technology", False):
            score += 1
        
        # Cross-border
        if activity.get("cross_border", False):
            score += 1
        
        if score >= 5:
            return RiskLevel.HIGH
        elif score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _suggest_mitigations(self, activity: dict, risk_level: RiskLevel) -> List[str]:
        """Suggest mitigation measures based on risk assessment."""
        mitigations = []
        
        if risk_level == RiskLevel.HIGH:
            mitigations.extend([
                "Implement pseudonymization of personal data",
                "Enable data minimization by default",
                "Implement strict access controls with MFA",
                "Enable comprehensive audit logging",
                "Implement data retention limits",
                "Conduct regular penetration testing",
                "Implement encryption at rest and in transit"
            ])
        elif risk_level == RiskLevel.MEDIUM:
            mitigations.extend([
                "Implement access controls",
                "Enable audit logging",
                "Implement data retention limits",
                "Conduct periodic security assessments"
            ])
        else:
            mitigations.extend([
                "Implement basic access controls",
                "Enable standard logging"
            ])
        
        return mitigations
```

### 6.5 Breach Detection and Notification

```python
# gdpr/breach_notification.py
"""
GDPR Breach Detection and Notification Automation
Art. 33 - Notify supervisory authority within 72 hours
Art. 34 - Notify data subjects without undue delay
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional

class BreachType(Enum):
    CONFIDENTIALITY = "confidentiality"  # Unauthorized access
    INTEGRITY = "integrity"              # Unauthorized modification
    AVAILABILITY = "availability"        # Data loss/destruction

class BreachSeverity(Enum):
    LOW = "low"           # Unlikely to result in risk
    MEDIUM = "medium"     # Possible risk to rights and freedoms
    HIGH = "high"         # Likely to result in significant risk
    CRITICAL = "critical" # Likely to result in severe risk

@dataclass
class DataBreach:
    id: str
    detected_at: datetime
    notification_deadline: datetime  # 72 hours from detection
    breach_type: BreachType
    severity: BreachSeverity
    data_subjects_affected: int
    data_types_affected: List[str]
    description: str
    likely_consequences: str
    measures_taken: str
    cross_border: bool
    supervisory_authority_notified: bool = False
    data_subjects_notified: bool = False
    notification_sent_at: Optional[datetime] = None

class BreachNotificationAutomation:
    """Automated breach detection and notification workflow."""
    
    NOTIFICATION_DEADLINE_HOURS = 72  # Art. 33(1)
    
    def __init__(self):
        self.breaches = {}
        self.supervisory_authority = "ICO"  # Information Commissioner's Office
        
    def detect_breach(self, event: dict) -> Optional[DataBreach]:
        """Detect and classify a potential data breach."""
        
        # Analyze security event
        if not self._is_potential_breach(event):
            return None
        
        # Classify breach
        breach_type = self._classify_breach(event)
        severity = self._assess_severity(event)
        
        breach = DataBreach(
            id=f"BREACH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            detected_at=datetime.utcnow(),
            notification_deadline=datetime.utcnow() + timedelta(hours=self.NOTIFICATION_DEADLINE_HOURS),
            breach_type=breach_type,
            severity=severity,
            data_subjects_affected=event.get("affected_subjects", 0),
            data_types_affected=event.get("data_types", []),
            description=event.get("description", ""),
            likely_consequences=self._assess_consequences(event, severity),
            measures_taken=event.get("measures_taken", ""),
            cross_border=event.get("cross_border", False)
        )
        
        self.breaches[breach.id] = breach
        
        # Immediate actions
        self._initiate_breach_protocol(breach)
        
        return breach
    
    def _initiate_breach_protocol(self, breach: DataBreach):
        """Initiate breach response protocol."""
        
        # 1. Notify DPO immediately
        self._notify_dpo(breach)
        
        # 2. If high/critical severity, notify CISO
        if breach.severity in [BreachSeverity.HIGH, BreachSeverity.CRITICAL]:
            self._notify_ciso(breach)
        
        # 3. Start evidence preservation
        self._preserve_evidence(breach)
        
        # 4. Begin impact assessment
        self._assess_impact(breach)
        
        # 5. Prepare notification
        self._prepare_notification(breach)
        
        # 6. Set deadline reminders
        self._set_deadline_reminders(breach)
    
    def _prepare_notification(self, breach: DataBreach):
        """Prepare supervisory authority notification."""
        
        notification = {
            "breach_id": breach.id,
            "detected_at": breach.detected_at.isoformat(),
            "breach_type": breach.breach_type.value,
            "severity": breach.severity.value,
            "data_subjects_affected": breach.data_subjects_affected,
            "data_types_affected": breach.data_types_affected,
            "description": breach.description,
            "likely_consequences": breach.likely_consequences,
            "measures_taken": breach.measures_taken,
            "cross_border": breach.cross_border,
            "contact_details": {
                "dpo": "dpo@apex-os.com",
                "phone": "+1-555-0100"
            }
        }
        
        # Store notification draft
        self._store_notification_draft(breach.id, notification)
        
        # If severity is high/critical, auto-send notification
        if breach.severity in [BreachSeverity.HIGH, BreachSeverity.CRITICAL]:
            self._send_notification(breach, notification)
    
    def _send_notification(self, breach: DataBreach, notification: dict):
        """Send notification to supervisory authority."""
        
        # Send to supervisory authority
        response = self._send_to_supervisory_authority(notification)
        
        if response["status"] == "sent":
            breach.supervisory_authority_notified = True
            breach.notification_sent_at = datetime.utcnow()
            
            # Log notification
            self._log_notification(breach, "supervisory_authority")
            
            # If high risk to data subjects, notify them too (Art. 34)
            if breach.severity in [BreachSeverity.HIGH, BreachSeverity.CRITICAL]:
                self._notify_data_subjects(breach)
    
    def _notify_data_subjects(self, breach: DataBreach):
        """Notify affected data subjects (Art. 34)."""
        
        # Prepare communication
        communication = {
            "subject": "Important Security Notice",
            "breach_description": breach.description,
            "data_affected": breach.data_types_affected,
            "consequences": breach.likely_consequences,
            "measures_taken": breach.measures_taken,
            "recommended_actions": [
                "Change your password",
                "Monitor your account for suspicious activity",
                "Be cautious of phishing attempts"
            ],
            "contact": "dpo@apex-os.com"
        }
        
        # Send to all affected data subjects
        self._send_to_data_subjects(breach, communication)
        breach.data_subjects_notified = True
        
        self._log_notification(breach, "data_subjects")
    
    def check_notification_deadlines(self):
        """Check for approaching notification deadlines."""
        now = datetime.utcnow()
        
        for breach in self.breaches.values():
            if breach.supervisory_authority_notified:
                continue
            
            hours_remaining = (breach.notification_deadline - now).total_seconds() / 3600
            
            if hours_remaining <= 12 and hours_remaining > 0:
                # Urgent alert
                self._send_urgent_alert(breach, hours_remaining)
            elif hours_remaining <= 0:
                # Deadline breached - escalate immediately
                self._escalate_missed_deadline(breach)
```

---

## 7. HIPAA Automation

### 7.1 HIPAA Requirements Mapping

| HIPAA Section | Requirement | Automation | Evidence |
|-------------|-------------|------------|----------|
| **§164.308(a)(1)** | Security Management Process | Risk analysis automation | Risk assessment reports |
| **§164.308(a)(2)** | Assigned Security Responsibility | Role-based access | Security officer designation |
| **§164.308(a)(3)** | Workforce Security | Access management | Access control logs |
| **§164.308(a)(4)** | Information Access Management | RBAC + minimum necessary | Access logs |
| **§164.308(a)(5)** | Security Awareness and Training | Training platform | Training records |
| **§164.308(a)(6)** | Security Incident Procedures | Incident response automation | Incident logs |
| **§164.308(a)(7)** | Contingency Plan | Backup + DR automation | DR test reports |
| **§164.308(a)(8)** | Evaluation | Continuous monitoring | Evaluation reports |
| **§164.308(b)** | Business Associate Contracts | Vendor management | BAA records |
| **§164.310(a)** | Facility Access Controls | Physical access system | Access logs |
| **§164.310(b)** | Workstation Use | Policy enforcement | Policy acknowledgments |
| **§164.310(c)** | Workstation Security | MDM + encryption | Endpoint logs |
| **§164.310(d)** | Device and Media Controls | Asset management | Disposal certificates |
| **§164.312(a)** | Access Control | IAM + unique user IDs | Access logs |
| **§164.312(b)** | Audit Controls | Comprehensive logging | Audit logs |
| **§164.312(c)** | Integrity | Data integrity checks | Integrity reports |
| **§164.312(d)** | Person or Entity Authentication | MFA + SSO | Auth logs |
| **§164.312(e)** | Transmission Security | Encryption in transit | TLS verification |
| **§164.312(e)(1)** | Encryption | End-to-end encryption | Encryption verification |
| **§164.530(c)** | Safeguards | PHI access controls | Access logs |
| **§164.530(d)** | Minimum Necessary | Role-based PHI access | Access logs |
| **§164.530(h)** | Retention | Retention policies | Retention logs |
| **§164.530(i)** | Documentation | Policy management | Policy versions |
| **§164.404-410** | Breach Notification | Automated breach detection | Breach logs |

### 7.2 PHI Access Control

```rego
# hipaa/phi_access_control.rego
package apex.hipaa

import future.keywords.if
import future.keywords.in

# Deny PHI access without treatment relationship
deny[msg] if {
    input.resource.contains_phi == true
    not input.user.treatment_relationship == true
    msg := "PHI access requires treatment relationship"
}

# Deny PHI access for non-authorized roles
deny[msg] if {
    input.resource.contains_phi == true
    not input.user.role in ["doctor", "nurse", "medical_assistant", "billing_staff", "admin"]
    msg := sprintf("Role %s not authorized for PHI access", [input.user.role])
}

# Enforce minimum necessary standard
deny[msg] if {
    input.resource.contains_phi == true
    input.user.role == "billing_staff"
    input.resource.phi_type == "mental_health"
    msg := "Billing staff cannot access mental health PHI (minimum necessary)"
}

# Deny PHI access outside treatment context
deny[msg] if {
    input.resource.contains_phi == true
    input.purpose not in ["treatment", "payment", "healthcare_operations"]
    msg := sprintf("PHI access for purpose %s not permitted", [input.purpose])
}

# Require audit logging for all PHI access
audit_required if {
    input.resource.contains_phi == true
}

# Deny bulk PHI export without approval
deny[msg] if {
    input.action == "bulk_export"
    input.resource.contains_phi == true
    not input.user.bulk_export_approved == true
    msg := "Bulk PHI export requires prior approval"
}

# Deny PHI access from unsecured locations
deny[msg] if {
    input.resource.contains_phi == true
    input.user.location == "public_wifi"
    msg := "PHI access not permitted from public WiFi"
}
```

### 7.3 PHI Audit Logging

```python
# hipaa/phi_audit_logger.py
"""
HIPAA PHI Audit Logger
Comprehensive logging of all PHI access as required by §164.312(b).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import json
import hashlib

@dataclass
class PHIAccessEvent:
    event_id: str
    timestamp: datetime
    user_id: str
    user_role: str
    patient_id: str
    phi_type: str
    access_type: str  # view, create, modify, delete, export
    purpose: str  # treatment, payment, healthcare_operations
    data_elements: List[str]
    source_ip: str
    session_id: str
    mfa_used: bool
    emergency_access: bool = False
    break_glass_reason: Optional[str] = None

class PHIAuditLogger:
    """HIPAA-compliant PHI audit logger."""
    
    # HIPAA requires 6-year retention (§164.530(j)(2))
    RETENTION_YEARS = 6
    
    # PHI types for classification
    PHI_TYPES = {
        "demographic": ["name", "address", "dob", "ssn", "phone", "email"],
        "medical": ["diagnosis", "medications", "lab_results", "vitals", "allergies"],
        "financial": ["insurance", "billing", "payment", "claims"],
        "mental_health": ["psychiatric", "therapy", "substance_abuse"],
        "substance_abuse": ["rehab", "detox", "medication_assisted_treatment"]
    }
    
    def log_phi_access(self, event: PHIAccessEvent):
        """Log a PHI access event."""
        
        # Enrich event with integrity hash
        event_data = {
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "user_id": self._hash_identifier(event.user_id),
            "user_role": event.user_role,
            "patient_id": self._hash_identifier(event.patient_id),
            "phi_type": event.phi_type,
            "access_type": event.access_type,
            "purpose": event.purpose,
            "data_elements": event.data_elements,
            "source_ip": event.source_ip,
            "session_id": event.session_id,
            "mfa_used": event.mfa_used,
            "emergency_access": event.emergency_access,
            "break_glass_reason": event.break_glass_reason
        }
        
        # Calculate integrity hash
        event_hash = self._calculate_hash(event_data)
        event_data["integrity_hash"] = event_hash
        
        # Store in immutable audit log
        self._store_audit_event(event_data)
        
        # Real-time monitoring
        self._check_anomalies(event)
        
        # Alert on suspicious access
        if self._is_suspicious(event):
            self._alert_security_team(event)
    
    def _check_anomalies(self, event: PHIAccessEvent):
        """Check for anomalous PHI access patterns."""
        
        # Check for after-hours access
        if event.timestamp.hour < 6 or event.timestamp.hour > 22:
            if not event.emergency_access:
                self._flag_anomaly(event, "after_hours_access")
        
        # Check for bulk access
        recent_access = self._get_recent_access(event.user_id, minutes=5)
        if len(recent_access) > 50:
            self._flag_anomaly(event, "bulk_access")
        
        # Check for access to celebrity/VIP patient
        if self._is_vip_patient(event.patient_id):
            self._flag_anomaly(event, "vip_patient_access")
        
        # Check for access outside user's department
        if not self._is_same_department(event.user_id, event.patient_id):
            self._flag_anomaly(event, "cross_department_access")
    
    def _is_suspicious(self, event: PHIAccessEvent) -> bool:
        """Determine if PHI access is suspicious."""
        
        # Emergency access without justification
        if event.emergency_access and not event.break_glass_reason:
            return True
        
        # Access to mental health records by non-mental-health staff
        if event.phi_type in ["mental_health", "substance_abuse"]:
            if event.user_role not in ["psychiatrist", "psychologist", "therapist"]:
                return True
        
        # Multiple failed access attempts followed by success
        recent_failures = self._get_recent_failures(event.user_id, minutes=10)
        if len(recent_failures) > 3:
            return True
        
        return False
    
    def generate_phi_access_report(self, patient_id: str, 
                                    start_date: datetime, 
                                    end_date: datetime) -> dict:
        """Generate PHI access report for a patient."""
        
        events = self._query_phi_access(patient_id, start_date, end_date)
        
        return {
            "patient_id": self._hash_identifier(patient_id),
            "report_period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_access_events": len(events),
            "unique_accessors": len(set(e["user_id"] for e in events)),
            "access_by_type": self._group_by_type(events),
            "access_by_purpose": self._group_by_purpose(events),
            "emergency_accesses": len([e for e in events if e["emergency_access"]]),
            "after_hours_accesses": len([e for e in events if self._is_after_hours(e["timestamp"])]),
            "flagged_anomalies": len([e for e in events if e.get("anomaly_flag")])
        }
```

### 7.4 Business Associate Agreement (BAA) Management

```yaml
# hipaa/baa-management.yaml
# Business Associate Agreement tracking

baa_requirements:
  # Required elements per §164.504(e)
  required_elements:
    - permitted_uses_and_disclosures
    - safeguards_implemented
    - reporting_of_security_incidents
    - subcontractor_compliance
    - access_to_phi_by_individuals
    - amendment_of_phi
    - availability_of_phi_for_hhs_audit
    - return_or_destruction_of_phi_termination
    - breach_notification
    
  # BAA tracking
  tracking:
    - vendor_name
    - baa_signed_date
    - baa_expiration_date
    - baa_status  # active, expired, terminated
    - phi_types_shared
    - data_volume_estimate
    - last_security_assessment
    - next_review_date
    - subcontractors_covered
    
  # Automated compliance checks
  compliance_checks:
    - name: "baa_current"
      description: "Verify BAA is not expired"
      frequency: "daily"
      action: "alert_if_expired"
      
    - name: "security_assessment_current"
      description: "Verify vendor security assessment is current"
      frequency: "quarterly"
      action: "alert_if_overdue"
      
    - name: "subcontractor_baa"
      description: "Verify subcontractors have BAAs"
      frequency: "on_new_subcontractor"
      action: "block_phi_access_until_baa_signed"
```

### 7.5 HIPAA Breach Notification

```python
# hipaa/breach_notification.py
"""
HIPAA Breach Notification Automation
§164.404-410 - Breach notification requirements
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Optional

class BreachType(Enum):
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    UNAUTHORIZED_DISCLOSURE = "unauthorized_disclosure"
    UNAUTHORIZED_USE = "unauthorized_use"
  DATA_LOSS = "data_loss"
    DATA_THEFT = "data_theft"
    RANSOMWARE = "ransomware"
    IMPROPER_DISPOSAL = "improper_disposal"

class NotificationRequirement(Enum):
    HHS = "hhs"                    # Secretary of HHS
    MEDIA = "media"                # Media outlets (500+ individuals)
    INDIVIDIDUALS = "individuals"  # Affected individuals
    STATE = "state"                # State attorney general

@dataclass
class HIPAADataBreach:
    id: str
    discovered_date: datetime
    breach_type: BreachType
    phi_types_affected: List[str]
    individuals_affected: int
    description: str
    safeguards_in_place: str
    risk_assessment: str
    notification_requirements: List[NotificationRequirement]
    individuals_notified: bool = False
    hhs_notified: bool = False
    media_notified: bool = False
    state_notified: bool = False
    notification_deadline: datetime = None  # 60 days from discovery

class HIPAABreachNotification:
    """HIPAA breach notification automation."""
    
    # HIPAA requires notification without unreasonable delay, max 60 days (§164.408)
    NOTIFICATION_DEADLINE_DAYS = 60
    
    # Media notification required if 500+ individuals affected (§164.406)
    MEDIA_THRESHOLD = 500
    
    def __init__(self):
        self.breaches = {}
    
    def assess_breach(self, incident: dict) -> HIPAADataBreach:
        """Assess a security incident for HIPAA breach notification requirements."""
        
        # Determine if this is a breach (unauthorized acquisition, access, use, or disclosure)
        is_breach = self._is_reportable_breach(incident)
        
        if not is_breach:
            return None
        
        # Determine notification requirements
        individuals_affected = incident.get("individuals_affected", 0)
        notification_requirements = [NotificationRequirement.INDIVIDIDUALS, NotificationRequirement.HHS]
        
        if individuals_affected >= self.MEDIA_THRESHOLD:
            notification_requirements.append(NotificationRequirement.MEDIA)
            notification_requirements.append(NotificationRequirement.STATE)
        
        breach = HIPAADataBreach(
            id=f"HIPAA-BREACH-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            discovered_date=datetime.utcnow(),
            breach_type=incident["breach_type"],
            phi_types_affected=incident.get("phi_types", []),
            individuals_affected=individuals_affected,
            description=incident["description"],
            safeguards_in_place=incident.get("safeguards", ""),
            risk_assessment=incident.get("risk_assessment", ""),
            notification_requirements=notification_requirements,
            notification_deadline=datetime.utcnow() + timedelta(days=self.NOTIFICATION_DEADLINE_DAYS)
        )
        
        self.breaches[breach.id] = breach
        
        # Initiate notification workflow
        self._initiate_notification_workflow(breach)
        
        return breach
    
    def _initiate_notification_workflow(self, breach: HIPAADataBreach):
        """Initiate breach notification workflow."""
        
        # 1. Notify Privacy Officer immediately
        self._notify_privacy_officer(breach)
        
        # 2. Notify Security Officer
        self._notify_security_officer(breach)
        
        # 3. Preserve evidence
        self._preserve_evidence(breach)
        
        # 4. Conduct risk assessment
        self._conduct_risk_assessment(breach)
        
        # 5. Prepare notifications
        self._prepare_notifications(breach)
        
        # 6. Set deadline reminders
        self._set_deadline_reminders(breach)
    
    def _prepare_notifications(self, breach: HIPAADataBreach):
        """Prepare breach notifications."""
        
        # Individual notification (§164.404)
        if NotificationRequirement.INDIVIDIDUALS in breach.notification_requirements:
            individual_notice = {
                "breach_description": breach.description,
                "phi_types_involved": breach.phi_types_affected,
                "steps_individuals_should_take": [
                    "Review your explanation of benefits",
                    "Monitor your credit reports",
                    "Report suspected identity theft to the FTC"
                ],
                "what_we_are_doing": [
                    "Investigating the incident",
                    "Implementing additional safeguards",
                    "Providing credit monitoring services"
                ],
                "contact_information": {
                    "privacy_officer": "privacy@apex-os.com",
                    "phone": "1-800-555-0100",
                    "tty": "1-800-555-0101"
                }
            }
            self._store_notification_draft(breach.id, "individuals", individual_notice)
        
        # HHS notification (§164.408)
        if NotificationRequirement.HHS in breach.notification_requirements:
            hhs_notice = {
                "covered_entity": "APEX-OS Business Platform",
                "breach_type": breach.breach_type.value,
                "individuals_affected": breach.individuals_affected,
                "phi_types": breach.phi_types_affected,
                "description": breach.description,
                "safeguards": breach.safeguards_in_place,
                "risk_assessment": breach.risk_assessment
            }
            self._store_notification_draft(breach.id, "hhs", hhs_notice)
        
        # Media notification (§164.406)
        if NotificationRequirement.MEDIA in breach.notification_requirements:
            media_notice = {
                "headline": "APEX-OS Business Platform Notifies Patients of Data Breach",
                "breach_description": breach.description,
                "individuals_affected": breach.individuals_affected,
                "contact_information": "privacy@apex-os.com"
            }
            self._store_notification_draft(breach.id, "media", media_notice)
    
    def check_notification_deadlines(self):
        """Check for approaching notification deadlines."""
        now = datetime.utcnow()
        
        for breach in self.breaches.values():
            days_remaining = (breach.notification_deadline - now).days
            
            if days_remaining <= 7 and days_remaining > 0:
                self._send_deadline_alert(breach, days_remaining)
            elif days_remaining <= 0:
                self._escalate_missed_deadline(breach)
```

---

## 8. PCI DSS v4.0 Automation

### 8.1 PCI DSS Requirements Mapping

| PCI DSS Requirement | Description | Automation | Evidence |
|---------------------|-------------|------------|----------|
| **Req 1** | Install and maintain network security controls | Firewall automation, segmentation | Firewall configs, network scans |
| **Req 2** | Apply secure configurations to all systems | CIS benchmarks, IaC scanning | Config compliance reports |
| **Req 3** | Protect stored account data | Tokenization, encryption | Token vault logs, encryption verification |
| **Req 4** | Protect cardholder data with strong cryptography | TLS 1.2+, key management | TLS scan results, key rotation logs |
| **Req 5** | Protect all systems against malware | EDR, AV, anti-malware | Malware scan reports |
| **Req 6** | Develop and maintain secure systems | SDLC, code review, SAST/DAST | Pipeline logs, scan results |
| **Req 7** | Restrict access to system components | RBAC, least privilege | Access control logs |
| **Req 8** | Identify users and authenticate access | MFA, SSO, password policies | Auth logs, MFA enrollment |
| **Req 9** | Restrict physical access to cardholder data | Physical access controls | Badge logs, camera footage |
| **Req 10** | Log and monitor all access to system components | SIEM, log management | Log integrity reports |
| **Req 11** | Test security of systems and networks regularly | Vulnerability scanning, pen testing | Scan reports, pen test reports |
| **Req 12** | Support information security with organizational policies | Policy management | Policy versions, acknowledgments |

### 8.2 Cardholder Data Environment (CDE) Isolation

```rego
# pci/cde_isolation.rego
package apex.pci

import future.keywords.if
import future.keywords.in

# Deny non-CDE access to cardholder data
deny[msg] if {
    input.resource.contains_chd == true
    not input.user.network_zone == "CDE"
    msg := "Cardholder data only accessible from CDE"
}

# Deny CHD storage in non-approved systems
deny[msg] if {
    input.action == "store"
    input.resource.contains_chd == true
    not input.resource.system in data.approved_chd_systems
    msg := "CHD can only be stored in approved systems"
}

# Require tokenization for CHD
deny[msg] if {
    input.action == "store"
    input.resource.contains_chd == true
    not input.resource.tokenized == true
    msg := "CHD must be tokenized before storage"
}

# Deny CHD in logs
deny[msg] if {
    input.action == "log"
    input.resource.contains_chd == true
    msg := "CHD must never appear in logs"
}

# Denay CHD in error messages
deny[msg] if {
    input.action == "error_message"
    input.resource.contains_chd == true
    msg := "CHD must never appear in error messages"
}

# Require encryption for CHD in transit
deny[msg] if {
    input.action == "transmit"
    input.resource.contains_chd == true
    not input.resource.encrypted == true
    msg := "CHD must be encrypted in transit"
}

# Deny CHD access without business need
deny[msg] if {
    input.resource.contains_chd == true
    not input.user.business_need == true
    msg := "CHD access requires documented business need"
}

# Require dual authorization for CHD changes
deny[msg] if {
    input.action == "modify"
    input.resource.contains_chd == true
    not input.user.dual_authorized == true
    msg := "CHD modifications require dual authorization"
}
```

### 8.3 CHD Tokenization

```python
# pci/chd_tokenization.py
"""
PCI DSS CHD Tokenization
Req 3 - Protect stored account data
"""

from dataclasses import dataclass
from typing import Optional, Dict
from datetime import datetime, timedelta
import hashlib
import hmac
import secrets

@dataclass
class TokenVault:
    """PCI-compliant token vault for CHD."""
    
    def tokenize_pan(self, pan: str, merchant_id: str) -> str:
        """
        Tokenize a Primary Account Number (PAN).
        Uses format-preserving tokenization.
        """
        # Validate PAN using Luhn algorithm
        if not self._validate_pan(pan):
            raise ValueError("Invalid PAN")
        
        # Generate unique token
        token = self._generate_token(pan, merchant_id)
        
        # Store mapping in vault (encrypted)
        self._store_token_mapping(token, pan, merchant_id)
        
        # Log tokenization (without PAN)
        self._log_tokenization(token, merchant_id)
        
        return token
    
    def detokenize(self, token: str, requester_id: str, 
                   business_justification: str) -> Optional[str]:
        """
        Retrieve PAN from token.
        Requires business justification and authorization.
        """
        # Verify requester authorization
        if not self._authorize_detokenization(requester_id, business_justification):
            self._log_unauthorized_attempt(requester_id, token)
            return None
        
        # Retrieve PAN from vault
        pan = self._retrieve_pan(token)
        
        if pan:
            # Log detokenization
            self._log_detokenization(token, requester_id, business_justification)
            
            # Alert on detokenization
            self._alert_detokenization(token, requester_id)
        
        return pan
    
    def _generate_token(self, pan: str, merchant_id: str) -> str:
        """Generate a format-preserving token."""
        # Use HMAC-based tokenization
        key = self._get_tokenization_key()
        data = f"{pan}:{merchant_id}:{secrets.token_hex(16)}"
        
        token_hash = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
        
        # Format-preserving: keep first 6 and last 4 digits
        first_six = pan[:6]
        last_four = pan[-4:]
        middle = token_hash[:len(pan) - 10]
        
        token = f"{first_six}{middle}{last_four}"
        
        return token
    
    def _validate_pan(self, pan: str) -> bool:
        """Validate PAN using Luhn algorithm."""
        if not pan.isdigit():
            return False
        
        digits = [int(d) for d in pan]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        
        total = sum(odd_digits)
        for d in even_digits:
            d *= 2
            if d > 9:
                d -= 9
            total += d
        
        return total % 10 == 0
    
    def _store_token_mapping(self, token: str, pan: str, merchant_id: str):
        """Store token-PAN mapping in encrypted vault."""
        # Encrypt PAN before storage
        encrypted_pan = self._encrypt_pan(pan)
        
        # Store in vault
        vault_entry = {
            "token": token,
            "encrypted_pan": encrypted_pan,
            "merchant_id": merchant_id,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat()
        }
        
        self._vault_store(vault_entry)
    
    def _authorize_detokenization(self, requester_id: str, justification: str) -> bool:
        """Authorize detokenization request."""
        # Check if requester has detokenization permission
        if not self._has_permission(requester_id, "detokenize"):
            return False
        
        # Check business justification
        if not justification or len(justification) < 20:
            return False
        
        # Check if requester is in CDE
        if not self._is_in_cde(requester_id):
            return False
        
        return True
    
    def rotate_tokens(self):
        """Rotate all tokens (annual requirement)."""
        tokens = self._get_all_tokens()
        
        for token_entry in tokens:
            # Generate new token
            pan = self._decrypt_pan(token_entry["encrypted_pan"])
            new_token = self._generate_token(pan, token_entry["merchant_id"])
            
            # Update mapping
            self._update_token_mapping(token_entry["token"], new_token)
            
            # Log rotation
            self._log_token_rotation(token_entry["token"], new_token)
```

### 8.4 PCI DSS Network Segmentation

```yaml
# pci/network-segmentation.yaml
# PCI DSS Req 1 - Network security controls

network_segmentation:
  # Cardholder Data Environment (CDE)
  cde:
    description: "Isolated network segment for cardholder data"
    cidr: "10.0.100.0/24"
    vlan: 100
    
    # Inbound rules
    inbound:
      - source: "10.0.200.0/24"  # Payment gateway only
        destination: "10.0.100.0/24"
        ports: [443]
        protocol: "tcp"
        description: "HTTPS from payment gateway"
        
      - source: "10.0.100.0/24"
        destination: "10.0.100.0/24"
        ports: [443, 22]
        protocol: "tcp"
        description: "Internal CDE communication"
    
    # Outbound rules
    outbound:
      - source: "10.0.100.0/24"
        destination: "10.0.200.0/24"
        ports: [443]
        protocol: "tcp"
        description: "HTTPS to payment gateway"
        
      - source: "10.0.100.0/24"
        destination: "10.0.0.0/8"
        ports: []
        protocol: "deny"
        description: "Deny all other outbound"
    
    # Monitoring
    monitoring:
      - ids_enabled: true
      - ips_enabled: true
      - log_all_traffic: true
      - alert_on_anomaly: true
  
  # Non-CDE segments
  non_cde:
    description: "General corporate network"
    cidr: "10.0.0.0/16"
    
    # Rules to CDE
    to_cde:
      - source: "10.0.0.0/16"
        destination: "10.0.100.0/24"
        ports: []
        protocol: "deny"
        description: "Deny all non-CDE to CDE traffic"
  
  # Firewall rules
  firewalls:
    - name: "cde-firewall"
      type: "next-generation"
      rules:
        - action: "allow"
          source: "payment-gateway"
          destination: "cde"
          service: "https"
          logging: true
          
        - action: "deny"
          source: "any"
          destination: "cde"
          service: "any"
          logging: true
          
        - action: "deny"
          source: "cde"
          destination: "internet"
          service: "any"
          logging: true
  
  # Automated verification
  verification:
    frequency: "daily"
    checks:
      - name: "segmentation_test"
        description: "Verify CDE isolation"
        method: "network_scan"
        expected: "no_unauthorized_access"
        
      - name: "firewall_rule_compliance"
        description: "Verify firewall rules"
        method: "config_audit"
        expected: "all_rules_compliant"
        
      - name: "ids_ips_functional"
        description: "Verify IDS/IPS is operational"
        method: "health_check"
        expected: "operational"
```

### 8.5 PCI DSS Vulnerability Management

```python
# pci/vulnerability_management.py
"""
PCI DSS Vulnerability Management
Req 6.3 - Security patches and Req 11.3 - Vulnerability scanning
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class VulnSeverity(Enum):
    CRITICAL = "critical"    # CVSS 9.0-10.0
    HIGH = "high"            # CVSS 7.0-8.9
    MEDIUM = "medium"        # CVSS 4.0-6.9
    LOW = "low"              # CVSS 0.1-3.9
    INFO = "info"            # CVSS 0.0

class PatchStatus(Enum):
    NOT_REQUIRED = "not_required"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"

@dataclass
class Vulnerability:
    id: str
    cve_id: str
    severity: VulnSeverity
    cvss_score: float
    affected_system: str
    affected_component: str
    description: str
    solution: str
    patch_available: bool
    patch_status: PatchStatus
    discovered_date: datetime
    due_date: datetime
    completed_date: Optional[datetime] = None

class PCIVulnerabilityManager:
    """PCI DSS vulnerability management automation."""
    
    # PCI DSS patching SLAs (Req 6.3)
    CRITICAL_PATCH_DAYS = 30    # Critical vulnerabilities
    HIGH_PATCH_DAYS = 30        # High vulnerabilities
    MEDIUM_PATCH_DAYS = 90      # Medium vulnerabilities
    LOW_PATCH_DAYS = 180        # Low vulnerabilities
    
    # PCI DSS scanning requirements (Req 11.3)
    QUARTERLY_SCAN_REQUIRED = True
    ASV_SCAN_REQUIRED = True
    
    def __init__(self):
        self.vulnerabilities = {}
        self.scan_results = []
    
    def process_scan_results(self, scan_results: List[dict]):
        """Process vulnerability scan results."""
        
        for result in scan_results:
            severity = self._map_cvss_to_severity(result["cvss_score"])
            
            vuln = Vulnerability(
                id=f"VULN-{result['id']}",
                cve_id=result.get("cve_id", "N/A"),
                severity=severity,
                cvss_score=result["cvss_score"],
                affected_system=result["system"],
                affected_component=result["component"],
                description=result["description"],
                solution=result.get("solution", ""),
                patch_available=result.get("patch_available", False),
                patch_status=PatchStatus.NOT_REQUIRED,
                discovered_date=datetime.utcnow(),
                due_date=self._calculate_due_date(severity)
            )
            
            self.vulnerabilities[vuln.id] = vuln
            
            # Auto-create remediation ticket
            self._create_remediation_ticket(vuln)
            
            # Check SLA compliance
            self._check_sla_compliance(vuln)
    
    def _calculate_due_date(self, severity: VulnSeverity) -> datetime:
        """Calculate remediation due date based on severity."""
        now = datetime.utcnow()
        
        if severity == VulnSeverity.CRITICAL:
            return now + timedelta(days=self.CRITICAL_PATCH_DAYS)
        elif severity == VulnSeverity.HIGH:
            return now + timedelta(days=self.HIGH_PATCH_DAYS)
        elif severity == VulnSeverity.MEDIUM:
            return now + timedelta(days=self.MEDIUM_PATCH_DAYS)
        else:
            return now + timedelta(days=self.LOW_PATCH_DAYS)
    
    def _check_sla_compliance(self, vuln: Vulnerability):
        """Check if vulnerability is within SLA."""
        now = datetime.utcnow()
        
        if now > vuln.due_date and vuln.patch_status != PatchStatus.COMPLETED:
            # SLA breached
            self._escalate_sla_breach(vuln)
    
    def _escalate_sla_breach(self, vuln: Vulnerability):
        """Escalate SLA breach."""
        # Create high-priority ticket
        self._create_escalation_ticket(vuln)
        
        # Notify security team
        self._notify_security_team(vuln)
        
        # If critical, notify CISO
        if vuln.severity == VulnSeverity.CRITICAL:
            self._notify_ciso(vuln)
    
    def generate_pci_report(self) -> dict:
        """Generate PCI DSS vulnerability management report."""
        
        vulns = list(self.vulnerabilities.values())
        
        return {
            "report_date": datetime.utcnow().isoformat(),
            "total_vulnerabilities": len(vulns),
            "by_severity": {
                "critical": len([v for v in vulns if v.severity == VulnSeverity.CRITICAL]),
                "high": len([v for v in vulns if v.severity == VulnSeverity.HIGH]),
                "medium": len([v for v in vulns if v.severity == VulnSeverity.MEDIUM]),
                "low": len([v for v in vulns if v.severity == VulnSeverity.LOW])
            },
            "by_status": {
                "not_required": len([v for v in vulns if v.patch_status == PatchStatus.NOT_REQUIRED]),
                "scheduled": len([v for v in vulns if v.patch_status == PatchStatus.SCHEDULED]),
                "in_progress": len([v for v in vulns if v.patch_status == PatchStatus.IN_PROGRESS]),
                "completed": len([v for v in vulns if v.patch_status == PatchStatus.COMPLETED]),
                "deferred": len([v for v in vulns if v.patch_status == PatchStatus.DEFERRED])
            },
            "sla_compliance": {
                "compliant": len([v for v in vulns if self._is_sla_compliant(v)]),
                "breached": len([v for v in vulns if not self._is_sla_compliant(v)])
            },
            "critical_open": len([v for v in vulns if v.severity == VulnSeverity.CRITICAL and v.patch_status != PatchStatus.COMPLETED]),
            "high_open": len([v for v in vulns if v.severity == VulnSeverity.HIGH and v.patch_status != PatchStatus.COMPLETED]),
            "mean_time_to_patch": self._calculate_mtp(vulns),
            "last_quarterly_scan": self._get_last_quarterly_scan(),
            "last_asv_scan": self._get_last_asv_scan()
        }
    
    def _is_sla_compliant(self, vuln: Vulnerability) -> bool:
        """Check if vulnerability is SLA compliant."""
        if vuln.patch_status == PatchStatus.COMPLETED:
            return vuln.completed_date <= vuln.due_date
        return datetime.utcnow() <= vuln.due_date
```

### 8.6 PCI DSS Access Control

```yaml
# pci/access-control.yaml
# PCI DSS Req 7 & 8 - Access control and authentication

access_control:
  # Req 7 - Restrict access to system components
  least_privilege:
    default_deny: true
    role_based_access: true
    regular_access_reviews: true
    access_review_frequency: "quarterly"
    
  # Req 8 - Identify users and authenticate access
  authentication:
    mfa_required: true
    mfa_methods:
      - totp
      - hardware_token
      - push_notification
    password_policy:
      minimum_length: 12
      complexity: true
      expiration_days: 90
      history: 4
      lockout_attempts: 6
      lockout_duration_minutes: 30
      
  # User management
  user_management:
    unique_user_ids: true
    shared_accounts: false
    service_accounts:
      managed_by: vault
      rotation: "90_days"
      logging: true
      
  # Access monitoring
  monitoring:
    log_all_access: true
    log_admin_actions: true
    log_failed_attempts: true
    alert_on_suspicious: true
    review_frequency: "daily"
    
  # Automated checks
  automated_checks:
    - name: "mfa_enforcement"
      description: "Verify all users have MFA enabled"
      frequency: "daily"
      action: "alert_non_compliant"
      
    - name: "inactive_accounts"
      description: "Find accounts inactive for 90+ days"
      frequency: "weekly"
      action: "disable_and_alert"
      
    - name: "privileged_access_review"
      description: "Review privileged access"
      frequency: "monthly"
      action: "generate_report"
      
    - name: "password_compliance"
      description: "Check password policy compliance"
      frequency: "daily"
      action: "alert_non_compliant"
```

---

## 9. Cross-Framework Control Mapping

### 9.1 Unified Control Matrix

Many controls across the five frameworks overlap. This mapping enables single implementation, multiple compliance.

| Unified Control | SOC 2 | ISO 27001 | GDPR | HIPAA | PCI DSS |
|----------------|-------|-----------|------|-------|---------|
| **Access Control** | CC6.1-CC6.5 | A.5.15-A.5.18, A.8.2-A.8.3 | Art. 32 | §164.312(a) | Req 7, Req 8 |
| **Encryption** | CC6.6-CC6.7 | A.8.24 | Art. 32 | §164.312(e) | Req 3, Req 4 |
| **Audit Logging** | CC6.10 | A.8.15-A.8.16 | Art. 5(2) | §164.312(b) | Req 10 |
| **Vulnerability Management** | CC6.9 | A.8.8 | Art. 32 | §164.308(a)(8) | Req 6, Req 11 |
| **Incident Response** | A1.3, CC6.10 | A.5.24-A.5.27 | Art. 33-34 | §164.308(a)(6) | Req 12.10 |
| **Data Classification** | C1.1 | A.5.12-A.5.13 | Art. 5(1)(c) | §164.530(c) | Req 3 |
| **Data Retention** | C1.3 | A.8.10 | Art. 5(1)(e) | §164.530(j) | Req 3 |
| **Backup & Recovery** | A1.2 | A.8.13-A.8.14 | Art. 32 | §164.308(a)(7) | Req 12.10 |
| **Security Awareness** | CC6.1 | A.6.3 | Art. 39 | §164.308(a)(5) | Req 12.6 |
| **Vendor Management** | CC6.1 | A.5.19-A.5.22 | Art. 28 | §164.308(b) | Req 12.8 |
| **Change Management** | CC6.1 | A.8.32 | Art. 32 | §164.308(a)(8) | Req 6 |
| **Network Security** | CC6.8 | A.8.20-A.8.23 | Art. 32 | §164.312(e) | Req 1 |
| **Physical Security** | CC6.1 | A.7.1-A.7.14 | Art. 32 | §164.310 | Req 9 |
| **Risk Management** | CC6.1 | A.5.1-A.5.7 | Art. 35 | §164.308(a)(1) | Req 12.1.2 |
| **Business Continuity** | A1.2-A1.3 | A.5.29-A.5.30 | Art. 32 | §164.308(a)(7) | Req 12.10 |

### 9.2 Unified Evidence Store

```yaml
# shared/evidence-store.yaml
# Unified evidence store configuration

evidence_store:
  # Storage configuration
  storage:
    primary: "s3://apex-os-compliance-evidence"
    immutable: "immudb://compliance-audit-log"
    archive: "s3://apex-os-compliance-archive"
    
  # Retention policies
  retention:
    soc2: "7_years"
    iso27001: "3_years"
    gdpr: "duration_of_relationship + 3_years"
    hipaa: "6_years"
    pci_dss: "1_year_minimum"
    
  # Evidence types
  evidence_types:
    - name: "access_logs"
      frameworks: ["soc2", "iso27001", "gdpr", "hipaa", "pci_dss"]
      retention: "7_years"
      encryption: "AES-256-GCM"
      
    - name: "vulnerability_scans"
      frameworks: ["soc2", "iso27001", "hipaa", "pci_dss"]
      retention: "3_years"
      encryption: "AES-256-GCM"
      
    - name: "policy_versions"
      frameworks: ["soc2", "iso27001", "gdpr", "hipaa", "pci_dss"]
      retention: "7_years"
      encryption: "AES-256-GCM"
      
    - name: "training_records"
      frameworks: ["soc2", "iso27001", "hipaa", "pci_dss"]
      retention: "3_years"
      encryption: "AES-256-GCM"
      
    - name: "incident_reports"
      frameworks: ["soc2", "iso27001", "gdpr", "hipaa", "pci_dss"]
      retention: "7_years"
      encryption: "AES-256-GCM"
      
    - name: "consent_records"
      frameworks: ["gdpr"]
      retention: "duration_of_relationship + 3_years"
      encryption: "AES-256-GCM"
      
    - name: "phi_access_logs"
      frameworks: ["hipaa"]
      retention: "6_years"
      encryption: "AES-256-GCM"
      
    - name: "dsr_requests"
      frameworks: ["gdpr"]
      retention: "3_years"
      encryption: "AES-256-GCM"
      
    - name: "risk_assessments"
      frameworks: ["iso27001", "hipaa"]
      retention: "3_years"
      encryption: "AES-256-GCM"
      
    - name: "change_tickets"
      frameworks: ["soc2", "iso27001", "pci_dss"]
      retention: "3_years"
      encryption: "AES-256-GCM"
```

---

## 10. CI/CD Compliance Gates

### 10.1 Pipeline Compliance Gates

```yaml
# cicd/compliance-gates.yaml
# CI/CD pipeline compliance gates

pipeline:
  name: "apex-os-compliance-pipeline"
  
  stages:
    # Stage 1: Code Quality and Security
    - name: "security-scan"
      steps:
        - name: "sast"
          tool: "semgrep"
          config: "security-audit"
          fail_on: "error"
          
        - name: "secrets-detection"
          tool: "gitleaks"
          fail_on: "any_secret"
          
        - name: "dependency-check"
          tool: "snyk"
          fail_on: "critical_vulnerability"
          
        - name: "license-check"
          tool: "fossa"
          fail_on: "non_compliant_license"
    
    # Stage 2: Infrastructure as Code
    - name: "iac-scan"
      steps:
        - name: "terraform-scan"
          tool: "checkov"
          config: "pci_dss,soc2,hipaa"
          fail_on: "critical"
          
        - name: "kubernetes-scan"
          tool: "kube-score"
          fail_on: "critical"
          
        - name: "container-scan"
          tool: "trivy"
          fail_on: "critical"
    
    # Stage 3: Policy Compliance
    - name: "policy-check"
      steps:
        - name: "opa-policy-check"
          tool: "opa"
          policies:
            - "apex.iam"
            - "apex.hipaa"
            - "apex.pci"
            - "apex.gdpr"
          fail_on: "violation"
          
        - name: "data-classification-check"
          tool: "custom"
          fail_on: "unclassified_data"
    
    # Stage 4: Compliance Validation
    - name: "compliance-validation"
      steps:
        - name: "encryption-check"
          tool: "custom"
          checks:
            - "tls_1_2_minimum"
            - "encryption_at_rest"
            - "key_rotation_current"
          fail_on: "non_compliant"
          
        - name: "access-control-check"
          tool: "custom"
          checks:
            - "rbac_configured"
            - "mfa_enforced"
            - "least_privilege"
          fail_on: "non_compliant"
          
        - name: "logging-check"
          tool: "custom"
          checks:
            - "audit_logging_enabled"
            - "log_integrity_verified"
            - "retention_configured"
          fail_on: "non_compliant"
    
    # Stage 5: Deployment Approval
    - name: "approval"
      steps:
        - name: "security-approval"
          required_approvers: ["security-team"]
          condition: "all_checks_passed"
          
        - name: "compliance-approval"
          required_approvers: ["compliance-officer"]
          condition: "production_deployment"
```

### 10.2 Pre-Deployment Compliance Check

```python
# cicd/pre_deployment_check.py
"""
Pre-deployment compliance check.
Runs before any deployment to production.
"""

from typing import Dict, List, Tuple
import json

class PreDeploymentComplianceCheck:
    """Pre-deployment compliance verification."""
    
    def __init__(self):
        self.checks = []
        self.results = []
    
    def run_all_checks(self, deployment: dict) -> Tuple[bool, List[dict]]:
        """Run all pre-deployment compliance checks."""
        
        self.results = []
        all_passed = True
        
        # Security checks
        if not self._check_security_scan(deployment):
            all_passed = False
        
        if not self._check_vulnerabilities(deployment):
            all_passed = False
        
        if not self._check_secrets(deployment):
            all_passed = False
        
        # Compliance checks
        if not self._check_encryption(deployment):
            all_passed = False
        
        if not self._check_access_controls(deployment):
            all_passed = False
        
        if not self._check_logging(deployment):
            all_passed = False
        
        # Policy checks
        if not self._check_policy_compliance(deployment):
            all_passed = False
        
        # Documentation checks
        if not self._check_documentation(deployment):
            all_passed = False
        
        return all_passed, self.results
    
    def _check_security_scan(self, deployment: dict) -> bool:
        """Verify security scan passed."""
        scan_results = deployment.get("security_scan", {})
        
        passed = scan_results.get("status") == "passed"
        self.results.append({
            "check": "security_scan",
            "passed": passed,
            "details": scan_results
        })
        
        return passed
    
    def _check_vulnerabilities(self, deployment: dict) -> bool:
        """Verify no critical/high vulnerabilities."""
        vulns = deployment.get("vulnerabilities", {})
        
        critical = vulns.get("critical", 0)
        high = vulns.get("high", 0)
        
        passed = critical == 0 and high == 0
        self.results.append({
            "check": "vulnerabilities",
            "passed": passed,
            "details": {
                "critical": critical,
                "high": high,
                "threshold": "0 critical, 0 high"
            }
        })
        
        return passed
    
    def _check_secrets(self, deployment: dict) -> bool:
        """Verify no secrets in code."""
        secrets = deployment.get("secrets_found", [])
        
        passed = len(secrets) == 0
        self.results.append({
            "check": "secrets",
            "passed": passed,
            "details": {
                "secrets_found": len(secrets)
            }
        })
        
        return passed
    
    def _check_encryption(self, deployment: dict) -> bool:
        """Verify encryption is configured."""
        encryption = deployment.get("encryption", {})
        
        checks = [
            encryption.get("at_rest", False),
            encryption.get("in_transit", False),
            encryption.get("key_rotation", False)
        ]
        
        passed = all(checks)
        self.results.append({
            "check": "encryption",
            "passed": passed,
            "details": encryption
        })
        
        return passed
    
    def _check_access_controls(self, deployment: dict) -> bool:
        """Verify access controls are configured."""
        access = deployment.get("access_controls", {})
        
        checks = [
            access.get("rbac", False),
            access.get("mfa", False),
            access.get("least_privilege", False)
        ]
        
        passed = all(checks)
        self.results.append({
            "check": "access_controls",
            "passed": passed,
            "details": access
        })
        
        return passed
    
    def _check_logging(self, deployment: dict) -> bool:
        """Verify logging is configured."""
        logging = deployment.get("logging", {})
        
        checks = [
            logging.get("audit_enabled", False),
            logging.get("integrity_verified", False),
            logging.get("retention_configured", False)
        ]
        
        passed = all(checks)
        self.results.append({
            "check": "logging",
            "passed": passed,
            "details": logging
        })
        
        return passed
    
    def _check_policy_compliance(self, deployment: dict) -> bool:
        """Verify policy compliance."""
        policies = deployment.get("policy_compliance", {})
        
        passed = policies.get("compliant", False)
        self.results.append({
            "check": "policy_compliance",
            "passed": passed,
            "details": policies
        })
        
        return passed
    
    def _check_documentation(self, deployment: dict) -> bool:
        """Verify required documentation exists."""
        docs = deployment.get("documentation", {})
        
        required_docs = [
            "architecture_diagram",
            "data_flow_diagram",
            "security_controls",
            "incident_response_plan"
        ]
        
        missing = [doc for doc in required_docs if not docs.get(doc, False)]
        
        passed = len(missing) == 0
        self.results.append({
            "check": "documentation",
            "passed": passed,
            "details": {
                "missing": missing
            }
        })
        
        return passed
```

---

## 11. Monitoring & Continuous Assurance

### 11.1 Compliance Dashboard

```yaml
# monitoring/compliance-dashboard.yaml
# Grafana dashboard configuration

dashboard:
  title: "APEX-OS Compliance Dashboard"
  refresh: "5m"
  
  panels:
    # SOC 2
    - title: "SOC 2 Control Effectiveness"
      type: "stat"
      targets:
        - expr: "soc2_control_effectiveness"
          legend: "{{control_id}}"
      thresholds:
        - value: 95
          color: "green"
        - value: 80
          color: "yellow"
        - value: 0
          color: "red"
    
    # ISO 27001
    - title: "ISO 27001 Risk Level"
      type: "gauge"
      targets:
        - expr: "iso27001_risk_score"
      thresholds:
        - value: 0
          color: "green"
        - value: 12
          color: "yellow"
        - value: 20
          color: "red"
    
    # GDPR
    - title: "GDPR DSR Compliance"
      type: "stat"
      targets:
        - expr: "gdpr_dsr_deadline_compliance"
          legend: "Deadline Compliance"
      thresholds:
        - value: 100
          color: "green"
        - value: 95
          color: "yellow"
        - value: 0
          color: "red"
    
    # HIPAA
    - title: "HIPAA PHI Access Anomalies"
      type: "stat"
      targets:
        - expr: "hipaa_phi_access_anomalies_24h"
          legend: "Anomalies (24h)"
      thresholds:
        - value: 0
          color: "green"
        - value: 5
          color: "yellow"
        - value: 10
          color: "red"
    
    # PCI DSS
    - title: "PCI DSS Vulnerability SLA"
      type: "stat"
      targets:
        - expr: "pci_vulnerability_sla_compliance"
          legend: "SLA Compliance"
      thresholds:
        - value: 100
          color: "green"
        - value: 95
          color: "yellow"
        - value: 0
          color: "red"
```

### 11.2 Continuous Control Monitoring

```python
# monitoring/continuous_monitoring.py
"""
Continuous Control Monitoring
Real-time compliance control effectiveness measurement.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

@dataclass
class ControlStatus:
    control_id: str
    framework: str
    status: str  # effective, needs_attention, deficient
    last_evaluated: datetime
    evidence_count: int
    violations_24h: int
    violations_7d: int
    violations_30d: int
    trend: str  # improving, stable, declining

class ContinuousControlMonitor:
    """Continuous compliance control monitoring."""
    
    def __init__(self):
        self.controls = {}
        self.alerts = []
    
    def evaluate_all_controls(self) -> Dict[str,</longcat_think>
