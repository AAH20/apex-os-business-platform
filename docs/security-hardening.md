# APEX-OS Business Platform — Security Hardening Guide

**Version:** 1.0.0  
**Last Updated:** 2026-10-01  
**Scope:** Network Security · Application Security · Data Security · Identity Security · Compliance

---

## Table of Contents

1. [Network Security](#1-network-security)
2. [Application Security](#2-application-security)
3. [Data Security](#3-data-security)
4. [Identity Security](#4-identity-security)
5. [Compliance](#5-compliance)
6. [Hardening Checklist Summary](#6-hardening-checklist-summary)

---

## 1. Network Security

### 1.1 VPC & Subnet Architecture

| Control | Status | Recommendation |
|---------|--------|----------------|
| VPC isolation | ✅ Implemented | AWS VPC `10.0.0.0/16`, Azure VNet `10.1.0.0/16`, GCP VPC `10.2.0.0/16` — maintain separate CIDRs per cloud to prevent overlap in hybrid scenarios |
| Public/private subnet separation | ✅ Implemented | Private subnets (`10.0.1-3.0/24`) for workloads; public subnets (`10.0.101-103.0/24`) for load balancers only |
| Multi-AZ deployment | ✅ Implemented | 3 AZs across all clouds — maintain for high availability and fault isolation |
| VPC Flow Logs | ✅ Enabled | `security_enable_flow_logs = true` — ship to CloudWatch/S3 for forensic analysis |

**Actions:**

- [ ] Restrict `security_allowed_cidr_blocks` to specific corporate CIDRs — current default `10.0.0.0/8` is overly broad for production
- [ ] Enable VPC Flow Logs with 1-minute granularity in production
- [ ] Implement AWS Network Firewall or Azure Firewall for east-west traffic inspection
- [ ] Deploy AWS PrivateLink / Azure Private Link for S3, RDS, and other PaaS endpoints to avoid public internet traversal

### 1.2 Security Groups & Firewalls

| Control | Status | Recommendation |
|---------|--------|----------------|
| Security groups | ✅ Module exists | Enforce least-privilege: only required ports between tiers |
| AWS WAF | ✅ Enabled | `security_enable_waf = true` — attach to ALB/CloudFront |
| AWS Shield Advanced | ❌ Disabled | Enable for production DDoS protection |
| GuardDuty | ✅ Enabled | Continuous threat detection |
| Security Hub | ✅ Enabled | Centralized security posture management |

**Actions:**

- [ ] Enable AWS Shield Advanced (`security_enable_shield = true`) for production
- [ ] Configure WAF rules: OWASP Top 10, rate limiting, geo-blocking, bot detection
- [ ] Implement security group rules referencing security groups (not CIDRs) for intra-VPC traffic
- [ ] Add AWS Network Firewall with egress filtering to block known-bad IPs/domains
- [ ] Enable Azure DDoS Protection Standard on Azure VNet
- [ ] Enable GCP Cloud Armor for GKE ingress

### 1.3 Kubernetes Network Policies

| Control | Status | Recommendation |
|---------|--------|----------------|
| NetworkPolicy resources | ✅ Defined in Helm | Default-deny ingress/egress, allow only intra-platform traffic |
| Istio service mesh | ❌ Disabled | Enable for mTLS and fine-grained traffic control |
| Namespace isolation | ✅ 4 namespaces | `apex-os-core`, `apex-os-data`, `apex-os-monitoring`, `apex-os-security` |

**Actions:**

- [ ] Enable Istio service mesh (`k8s_enable_istio = true`) for production — provides mTLS, traffic encryption, and observability
- [ ] Expand NetworkPolicy rules to cover DNS (port 53), monitoring (Prometheus scrape), and cert-manager
- [ ] Implement default-deny policies for all namespaces, then explicitly allow required flows
- [ ] Use Cilium or Calico for enhanced network policy (L3-L7 filtering, eBPF-based)
- [ ] Enable Istio PeerAuthentication with `STRICT` mTLS mode
- [ ] Configure Istio AuthorizationPolicy for service-to-service access control

### 1.4 Ingress & TLS

| Control | Status | Recommendation |
|---------|--------|----------------|
| Ingress controller | ✅ NGINX | With cert-manager integration |
| TLS termination | ✅ Enabled | `nginx.ingress.kubernetes.io/ssl-redirect: "true"` |
| Certificate management | ✅ cert-manager | Let's Encrypt production issuer |
| Proxy body size limit | ✅ 50MB | Appropriate for API workloads |
| Rate limiting | ✅ 100 req/s | Per-IP rate limit at ingress |

**Actions:**

- [ ] Enable HSTS header (`nginx.ingress.kubernetes.io/hsts: "max-age=31536000; includeSubDomains"`)
- [ ] Configure OCSP stapling for TLS certificates
- [ ] Implement mutual TLS (mTLS) between services via Istio
- [ ] Add `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` headers
- [ ] Use AWS ACM or Azure Key Vault for certificate management instead of self-signed
- [ ] Enable ingress access logging for audit trail

---

## 2. Application Security

### 2.1 Container Security

| Control | Status | Recommendation |
|---------|--------|----------------|
| Non-root containers | ✅ `runAsNonRoot: true`, `runAsUser: 1000` | Enforce in all deployments |
| Read-only root filesystem | ✅ `readOnlyRootFilesystem: true` | Prevents runtime filesystem modification |
| Drop all capabilities | ✅ `capabilities.drop: [ALL]` | Minimal privilege principle |
| No privilege escalation | ✅ `allowPrivilegeEscalation: false` | Prevents container escape |
| Resource limits | ✅ CPU/memory set | Prevents resource exhaustion attacks |
| Image pull policy | ⚠️ `IfNotPresent` | Change to `Always` for immutable tags |

**Actions:**

- [ ] Set `imagePullPolicy: Always` and use immutable image tags (SHA digests, not `latest`)
- [ ] Scan images with Trivy, Snyk, or AWS ECR image scanning in CI/CD pipeline
- [ ] Sign images with Cosign/Notation and verify signatures at admission time
- [ ] Implement Pod Security Standards (PSS) — `restricted` profile for all namespaces
- [ ] Use ephemeral containers for debugging instead of `kubectl exec`
- [ ] Enable seccomp profiles (`RuntimeDefault` or custom)
- [ ] Set `seccompProfile.type: RuntimeDefault` on all pod specs

### 2.2 Secrets Management

| Control | Status | Recommendation |
|---------|--------|----------------|
| Hardcoded secrets | ❌ **Critical** | `postgresql.auth.password: "changeme"`, `redis.auth.password: "changeme"` in values.yaml |
| Grafana admin password | ❌ **Critical** | Default `"admin"` in Terraform variables |
| Secret externalization | ❌ Not implemented | No External Secrets Operator or Vault integration |

**Actions:**

- [ ] **IMMEDIATE:** Remove all hardcoded passwords from `values.yaml` — use Kubernetes Secrets or external vault
- [ ] Deploy HashiCorp Vault or AWS Secrets Manager for dynamic secret injection
- [ ] Implement External Secrets Operator to sync vault secrets to Kubernetes Secrets
- [ ] Rotate all default passwords immediately in all environments
- [ ] Use short-lived database credentials via Vault database secrets engine
- [ ] Enable automatic secret rotation (AWS Secrets Manager rotation Lambda)
- [ ] Never commit secrets to Git — use `.gitignore` and pre-commit hooks (gitleaks)

### 2.3 API Security

| Control | Status | Recommendation |
|---------|--------|----------------|
| API authentication | ⚠️ Not visible in chart | Implement OAuth2/OIDC or API key authentication |
| Input validation | ⚠️ Application-level | Enforce at API gateway and application layer |
| Rate limiting | ✅ Ingress-level | Add application-level rate limiting per user/tenant |
| CORS configuration | ⚠️ Not visible | Restrict CORS to known origins |

**Actions:**

- [ ] Implement OAuth2/OIDC authentication (Keycloak, Auth0, or AWS Cognito)
- [ ] Add request validation at the API gateway (Kong, Ambassador, or Istio)
- [ ] Implement per-tenant rate limiting and quota management
- [ ] Enable API request/response logging (sanitized of PII)
- [ ] Add OpenAPI/Swagger documentation with security schemes defined
- [ ] Implement idempotency keys for POST/PUT endpoints

### 2.4 Supply Chain Security

| Control | Status | Recommendation |
|---------|--------|----------------|
| SBOM generation | ❌ Not implemented | Generate Software Bill of Materials |
| Dependency scanning | ❌ Not implemented | Scan for known vulnerabilities |
| Image provenance | ❌ Not implemented | No signing or attestation |
| Helm chart signing | ❌ Not implemented | Sign charts with Cosign/Helm plugin |

**Actions:**

- [ ] Generate SBOM with Syft for each release
- [ ] Integrate dependency scanning (OWASP Dependency-Check, Snyk) in CI/CD
- [ ] Sign container images with Cosign and verify at admission
- [ ] Sign Helm charts and verify signatures before deployment
- [ ] Implement admission control with OPA/Gatekeeper or Kyverno
- [ ] Use private container registry (ECR, ACR, GCR) — avoid Docker Hub for production

---

## 3. Data Security

### 3.1 Encryption at Rest

| Control | Status | Recommendation |
|---------|--------|----------------|
| S3 encryption | ✅ Enabled | `security_enable_encryption_at_rest = true` |
| RDS encryption | ✅ Enabled | Via `security_enable_encryption_at_rest` |
| EBS/EKS encryption | ⚠️ Verify | Ensure EBS encryption is enabled for EKS nodes |
| Azure Storage encryption | ✅ Default | Azure Storage Service Encryption (SSE) with Microsoft-managed keys |
| GCP Storage encryption | ✅ Default | Google-managed encryption keys |
| PostgreSQL encryption | ⚠️ Verify | Enable TDE or use encrypted EBS volumes |
| Redis encryption | ❌ Not configured | Enable Redis AUTH and TLS |

**Actions:**

- [ ] Use customer-managed keys (CMK) via AWS KMS, Azure Key Vault, or GCP Cloud KMS instead of default encryption
- [ ] Enable RDS Performance Insights with encryption
- [ ] Configure Redis with TLS and strong AUTH password
- [ ] Enable PostgreSQL `sslmode: verify-full` for all connections
- [ ] Encrypt all Kubernetes Secrets with KMS (encryption provider)
- [ ] Implement S3 bucket policies denying unencrypted uploads
- [ ] Enable S3 Object Lock for backup buckets (WORM compliance)

### 3.2 Encryption in Transit

| Control | Status | Recommendation |
|---------|--------|----------------|
| TLS in transit | ✅ Enabled | `security_enable_encryption_in_transit = true` |
| Ingress TLS | ✅ Enabled | cert-manager with Let's Encrypt |
| Service-to-service TLS | ❌ Not mTLS | Enable Istio for automatic mTLS |
| Database TLS | ⚠️ Verify | Enforce TLS for all DB connections |
| Redis TLS | ❌ Not configured | Enable TLS for Redis |

**Actions:**

- [ ] Enable Istio service mesh for automatic mTLS between all services
- [ ] Enforce TLS 1.2+ only — disable TLS 1.0/1.1
- [ ] Configure PostgreSQL with `sslmode: verify-full` and CA certificate validation
- [ ] Enable Redis TLS with certificate-based authentication
- [ ] Use AWS PrivateLink/Service Endpoints to keep traffic off public internet
- [ ] Implement certificate pinning for mobile/API clients

### 3.3 Data Backup & Recovery

| Control | Status | Recommendation |
|---------|--------|----------------|
| RDS backups | ✅ Multi-AZ | Enable automated backups with 35-day retention |
| S3 backups | ✅ Bucket exists | `apex-os-backups` bucket configured |
| EKS backups | ❌ Not visible | Implement Velero for cluster backup |
| Backup encryption | ✅ Via at-rest encryption | Verify backup encryption is enabled |
| Cross-region replication | ❌ Not configured | For disaster recovery |

**Actions:**

- [ ] Deploy Velero for Kubernetes resource and persistent volume backup
- [ ] Enable cross-region replication for S3 backup buckets
- [ ] Configure RDS snapshots with cross-region copy
- [ ] Implement backup restoration testing schedule (monthly)
- [ ] Define RPO/RTO targets and document recovery procedures
- [ ] Enable point-in-time recovery (PITR) for PostgreSQL
- [ ] Encrypt all backup data with separate KMS keys

### 3.4 Data Classification & Handling

| Control | Status | Recommendation |
|---------|--------|----------------|
| Data classification | ❌ Not implemented | Define data classification levels |
| PII handling | ❌ Not visible | Implement PII detection and masking |
| Data retention policies | ❌ Not defined | Define retention per data type |

**Actions:**

- [ ] Classify data: Public, Internal, Confidential, Restricted
- [ ] Implement PII detection (AWS Macie, Azure Purview, or DLP tools)
- [ ] Define data retention policies per classification level
- [ ] Implement data masking for non-production environments
- [ ] Enable audit logging for all data access
- [ ] Implement data loss prevention (DLP) policies

---

## 4. Identity Security

### 4.1 Authentication & Authorization

| Control | Status | Recommendation |
|---------|--------|----------------|
| Kubernetes RBAC | ⚠️ Default | Define explicit RBAC roles and bindings |
| Service accounts | ✅ Created per component | Use dedicated SAs with minimal permissions |
| OIDC integration | ❌ Not configured | Integrate with corporate identity provider |
| MFA | ❌ Not visible | Enforce MFA for all human access |
| API authentication | ⚠️ Not visible | Implement OAuth2/OIDC for API access |

**Actions:**

- [ ] Define RBAC roles: `apex-os-admin`, `apex-os-developer`, `apex-os-viewer`, `apex-os-ci`
- [ ] Integrate Kubernetes with OIDC provider (Keycloak, Azure AD, Okta)
- [ ] Enforce MFA for all administrative access
- [ ] Implement just-in-time (JIT) access for privileged operations
- [ ] Use short-lived tokens (1-hour expiry) for service accounts
- [ ] Disable default service account token mounting (`automountServiceAccountToken: false`)
- [ ] Implement admission control to prevent privileged containers

### 4.2 Cloud IAM

| Control | Status | Recommendation |
|---------|--------|----------------|
| AWS IAM | ✅ Module exists | Enforce least-privilege IAM policies |
| Azure AD integration | ⚠️ Not visible | Integrate AKS with Azure AD |
| GCP IAM | ⚠️ Not visible | Integrate GKE with Cloud IAM |
| Cross-cloud identity | ❌ Not implemented | Federate identities across clouds |

**Actions:**

- [ ] Implement AWS IAM Access Analyzer to identify external access
- [ ] Enable Azure AD authentication for AKS (disable local accounts)
- [ ] Enable GKE Workload Identity for pod-level GCP authentication
- [ ] Use IAM roles for service accounts (IRSA) in EKS
- [ ] Implement permission boundaries for IAM roles
- [ ] Enable AWS IAM Identity Center (SSO) for multi-account access
- [ ] Rotate access keys every 90 days (or use temporary credentials only)

### 4.3 Secrets & Credential Management

| Control | Status | Recommendation |
|---------|--------|----------------|
| Vault integration | ❌ Not implemented | Deploy HashiCorp Vault |
| Dynamic secrets | ❌ Not implemented | Use Vault database secrets engine |
| Credential rotation | ❌ Not automated | Implement automated rotation |
| Audit logging | ⚠️ Partial | Enable cloud audit trails |

**Actions:**

- [ ] Deploy HashiCorp Vault in HA mode with auto-unseal
- [ ] Configure Vault database secrets engine for dynamic PostgreSQL/Redis credentials
- [ ] Implement automatic credential rotation (30-day policy)
- [ ] Enable AWS CloudTrail, Azure Activity Log, GCP Cloud Audit Logs
- [ ] Ship audit logs to centralized SIEM (Splunk, ELK, or cloud-native)
- [ ] Implement break-glass procedures for emergency access

---

## 5. Compliance

### 5.1 Regulatory Frameworks

| Framework | Applicability | Key Requirements |
|-----------|--------------|------------------|
| **SOC 2** | SaaS/Cloud | Security, availability, confidentiality controls |
| **ISO 27001** | Enterprise | ISMS, risk management, continuous improvement |
| **GDPR** | EU data subjects | Data protection, right to erasure, breach notification |
| **HIPAA** | Healthcare | PHI encryption, access controls, audit trails |
| **PCI DSS** | Payment card data | Network segmentation, encryption, access control |
| **FedRAMP** | US government | NIST 800-53 controls, continuous monitoring |

### 5.2 Audit & Logging

| Control | Status | Recommendation |
|---------|--------|----------------|
| Cloud audit trails | ⚠️ Partial | Enable CloudTrail, Activity Log, Audit Logs |
| Kubernetes audit logs | ❌ Not configured | Enable API server audit logging |
| Application logs | ✅ Loki configured | Centralized log aggregation |
| Metrics | ✅ Prometheus configured | Monitoring and alerting |
| Tracing | ✅ Tempo configured | Distributed tracing |
| Log retention | ⚠️ 30 days | Increase for compliance (1+ year) |

**Actions:**

- [ ] Enable Kubernetes API server audit logging with request/response logging
- [ ] Configure CloudTrail with log file validation and S3 bucket encryption
- [ ] Increase log retention to 365+ days for compliance
- [ ] Implement log integrity protection (write-once storage)
- [ ] Configure real-time alerting for security events (SIEM integration)
- [ ] Enable Azure Diagnostic Settings for all Azure resources
- [ ] Enable GCP Cloud Audit Logs for all services

### 5.3 Vulnerability Management

| Control | Status | Recommendation |
|---------|--------|----------------|
| Container scanning | ❌ Not implemented | Scan images in CI/CD |
| Infrastructure scanning | ❌ Not implemented | Scan Terraform/Helm for misconfigurations |
| Penetration testing | ❌ Not scheduled | Conduct annual pen tests |
| Patch management | ⚠️ Manual | Automate OS and dependency patching |

**Actions:**

- [ ] Integrate Trivy/Grype for container image scanning in CI/CD
- [ ] Run Checkov or tfsec on Terraform code in CI/CD
- [ ] Run kube-bench for Kubernetes CIS benchmark compliance
- [ ] Run kube-hunter for Kubernetes penetration testing
- [ ] Implement automated patching for EKS/AKS/GKE node pools
- [ ] Conduct annual third-party penetration testing
- [ ] Establish vulnerability disclosure program (VDP)

### 5.4 Security Monitoring & Incident Response

| Control | Status | Recommendation |
|---------|--------|----------------|
| SIEM integration | ❌ Not visible | Integrate with Splunk/ELK/Security Hub |
| Alerting | ✅ Alertmanager | Configure security-specific alerts |
| Incident response plan | ❌ Not documented | Create and test IR plan |
| Forensics capability | ⚠️ Partial | VPC Flow Logs + audit logs |

**Actions:**

- [ ] Integrate Prometheus/Alertmanager with PagerDuty/Opsgenie for security alerts
- [ ] Create incident response runbooks for common scenarios
- [ ] Implement automated incident response (AWS Systems Manager Automation)
- [ ] Conduct tabletop exercises quarterly
- [ ] Define escalation paths and communication templates
- [ ] Implement forensic snapshot capability for compromised resources

---

## 6. Hardening Checklist Summary

### Critical (Immediate Action Required)

| # | Component | Issue | Priority |
|---|-----------|-------|----------|
| 1 | Secrets | Hardcoded passwords in `values.yaml` (`changeme`) | **P0** |
| 2 | Secrets | Default Grafana admin password (`admin`) | **P0** |
| 3 | Identity | No OIDC/SSO integration for Kubernetes | **P0** |
| 4 | Data | Redis has no TLS or strong AUTH | **P0** |
| 5 | Network | Overly broad CIDR `10.0.0.0/8` in security groups | **P1** |
| 6 | Application | No image scanning or signing in CI/CD | **P1** |
| 7 | Data | No cross-region backup replication | **P1** |
| 8 | Network | Istio service mesh disabled (no mTLS) | **P1** |

### High (Complete Within 30 Days)

| # | Component | Issue | Priority |
|---|-----------|-------|----------|
| 9 | Network | AWS Shield Advanced disabled | P1 |
| 10 | Compliance | Kubernetes audit logging not configured | P1 |
| 11 | Data | No KMS customer-managed keys | P1 |
| 12 | Identity | No RBAC roles defined | P1 |
| 13 | Application | No Pod Security Standards enforcement | P1 |
| 14 | Secrets | No Vault or external secrets integration | P1 |
| 15 | Compliance | No vulnerability scanning in CI/CD | P1 |

### Medium (Complete Within 90 Days)

| # | Component | Issue | Priority |
|---|-----------|-------|----------|
| 16 | Network | No egress filtering / network firewall | P2 |
| 17 | Data | No data classification or PII handling | P2 |
| 18 | Compliance | No SBOM generation | P2 |
| 19 | Identity | No MFA enforcement | P2 |
| 20 | Monitoring | No SIEM integration | P2 |
| 21 | Compliance | No incident response plan | P2 |
| 22 | Network | No PrivateLink for PaaS services | P2 |
| 23 | Data | No backup restoration testing | P2 |

### Low (Complete Within 180 Days)

| # | Component | Issue | Priority |
|---|-----------|-------|----------|
| 24 | Compliance | No penetration testing schedule | P3 |
| 25 | Network | No ingress access logging | P3 |
| 26 | Application | No API gateway with request validation | P3 |
| 27 | Data | No data retention policies | P3 |
| 28 | Compliance | No vulnerability disclosure program | P3 |
| 29 | Monitoring | No forensic snapshot capability | P3 |
| 30 | Identity | No just-in-time access | P3 |

---

## Appendix A: Security Contacts

| Role | Contact | Responsibility |
|------|---------|----------------|
| Security Team | security@apex-os.io | Vulnerability reports, security inquiries |
| Incident Response | ir@apex-os.io | Security incidents, breach notification |
| Compliance | compliance@apex-os.io | Audit requests, compliance questions |

## Appendix B: References

- [CIS Kubernetes Benchmark](https://www.cisecurity.org/benchmark/kubernetes)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NSA/CISA Kubernetes Hardening Guide](https://media.defense.gov/2022/Aug/29/2003066362/-1/-1/0/CTR_KUBERNETES_HARDENING_GUIDANCE_1.2_20220829.PDF)
- [Terraform Security Best Practices](https://developer.hashicorp.com/terraform/tutorials/security)

---

*This document should be reviewed and updated quarterly or after significant infrastructure changes.*
