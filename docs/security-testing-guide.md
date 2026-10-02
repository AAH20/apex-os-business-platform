# Security Testing Guide

## 1. Security Testing Strategy

### Objectives
- Identify and remediate security vulnerabilities before production deployment
- Validate security controls across application, infrastructure, and API layers
- Ensure compliance with OWASP Top 10, ASVS, and organizational security policies
- Establish continuous security testing integrated into CI/CD pipelines

### Scope
- **Application Layer**: Web UI, REST APIs, GraphQL endpoints, WebSocket connections
- **Infrastructure Layer**: Cloud resources, containers, Kubernetes clusters, network segments
- **Data Layer**: Databases, caches, object storage, backup systems
- **Identity Layer**: Authentication, authorization, session management, SSO integrations
- **Integration Layer**: Third-party APIs, webhooks, message queues

### Testing Methodology
| Phase | Activities | Frequency |
|-------|-----------|-----------|
| Threat Modeling | STRIDE analysis, attack surface mapping | Per major release |
| Static Analysis | SAST scanning, dependency checks | Every commit |
| Dynamic Analysis | DAST scanning, fuzzing | Daily (staging), Weekly (production-like) |
| Penetration Testing | Manual exploitation, social engineering | Quarterly |
| Compliance Audit | Policy validation, control verification | Bi-annually |

### Risk Classification
- **Critical**: Remote code execution, authentication bypass, data exfiltration — fix within 24 hours
- **High**: SQL injection, privilege escalation, sensitive data exposure — fix within 7 days
- **Medium**: CSRF, security misconfigurations, weak cryptography — fix within 30 days
- **Low**: Information disclosure, missing security headers — fix within 90 days

### Roles and Responsibilities
- **Security Team**: Strategy definition, tooling, pentest execution, compliance audits
- **Development Teams**: Remediation, secure coding practices, unit-level security tests
- **DevOps/SRE**: Infrastructure scanning, secret management, network security controls
- **QA Engineers**: Security regression tests, test environment management

---

## 2. Penetration Testing

### Engagement Types
- **Black Box**: No prior knowledge; simulates external attacker
- **Gray Box**: Limited credentials and architecture knowledge; simulates insider threat
- **White Box**: Full source code and infrastructure access; comprehensive assessment

### Testing Phases

#### 2.1 Reconnaissance
- Passive OSINT: subdomain enumeration, certificate transparency logs, leaked credentials
- Active scanning: port scanning (Nmap), service fingerprinting, technology identification
- Content discovery: directory brute-forcing, API endpoint enumeration, JS file analysis

#### 2.2 Vulnerability Discovery
- **OWASP Top 10 Focus Areas**:
  - Broken Access Control (IDOR, privilege escalation, path traversal)
  - Cryptographic Failures (weak algorithms, improper key management, plaintext storage)
  - Injection (SQLi, NoSQLi, OS command injection, LDAP injection, XSS)
  - Insecure Design (business logic flaws, race conditions, workflow bypass)
  - Security Misconfiguration (default credentials, verbose errors, open cloud storage)
  - Vulnerable Components (known CVEs in dependencies)
  - Authentication Failures (credential stuffing, session fixation, JWT weaknesses)
  - Data Integrity Failures (deserialization, SSRF, XXE)
  - Logging Failures (insufficient audit trails, log injection)
  - SSRF (internal service access, cloud metadata theft)

#### 2.3 Exploitation
- Proof-of-concept development for each confirmed vulnerability
- Lateral movement simulation within container/network boundaries
- Privilege escalation paths (container escape, IAM policy abuse)
- Data access demonstration (read-only proof, no exfiltration of PII)

#### 2.4 Post-Exploitation
- Persistence mechanism identification
- Lateral movement potential assessment
- Blast radius analysis
- Detection evasion testing (WAF bypass, log manipulation)

### Tools
| Category | Tools |
|----------|-------|
| Network Scanning | Nmap, Masscan, RustScan |
| Web Probing | Burp Suite Pro, OWASP ZAP, ffuf, gobuster |
| API Testing | Postman, Insomnia, RESTler, Schemathesis |
| Cloud Security | Prowler, ScoutSuite, Pacu, CloudSploit |
| Container Security | Trivy, Grype, kube-bench, kube-hunter |
| Exploitation Framework | Metasploit, SQLMap, Commix, XSStrike |

### Reporting
- Executive summary with risk ratings and business impact
- Technical findings with reproduction steps, evidence, and CVSS scores
- Remediation guidance with code examples and configuration snippets
- Retest verification for all remediated findings

---

## 3. Vulnerability Scanning

### Automated Scanning Pipeline

#### 3.1 Static Application Security Testing (SAST)
```yaml
# Example CI integration
sast_scan:
  stage: test
  script:
    - semgrep --config=auto --json --output=semgrep-results.json
    - bandit -r src/ -f json -o bandit-results.json
    - sonar-scanner -Dsonar.securityAnalysis=true
  artifacts:
    reports:
      sast: [semgrep-results.json, bandit-results.json]
```
- **Tools**: Semgrep, Bandit, SonarQube, Checkmarx, CodeQL
- **Coverage**: Source code, infrastructure-as-code (Terraform, CloudFormation), Dockerfiles
- **Frequency**: Every pull request merge

#### 3.2 Software Composition Analysis (SCA)
```bash
# Dependency vulnerability scanning
pip-audit --format=json --output=dependency-report.json
npm audit --json > npm-audit-report.json
trivy fs --scanners vuln --format json -o trivy-fs-report.json .
```
- **Tools**: pip-audit, npm audit, Snyk, Dependabot, Trivy, Grype
- **Scope**: Direct and transitive dependencies, container base images
- **Policy**: Block builds with Critical/High CVEs; warn on Medium

#### 3.3 Dynamic Application Security Testing (DAST)
```bash
# OWASP ZAP baseline scan
zap-baseline.py -t https://staging.example.com \
  -r zap-baseline-report.html \
  -J zap-baseline-report.json \
  -w zap-baseline-report.md
```
- **Tools**: OWASP ZAP, Burp Suite Enterprise, Acunetix, Netsparker
- **Scope**: Staging environments, pre-production, production (read-only mode)
- **Frequency**: Daily automated scans; full scan weekly

#### 3.4 Infrastructure and Cloud Scanning
```bash
# Kubernetes security scanning
kube-bench run --targets node,etcd,policies --json > kube-bench-report.json
kube-hunter --remote 10.0.0.0/24 --log json > kube-hunter-report.json

# Cloud security posture
prowler aws --output json -o prowler-report.json
scout2 --report-dir ./scout2-report
```
- **Tools**: Prowler, ScoutSuite, kube-bench, kube-hunter, Terrascan, Checkov
- **Scope**: Cloud accounts, Kubernetes clusters, Terraform state, network configurations
- **Frequency**: Continuous (event-driven) + weekly full assessment

#### 3.5 Container and Image Scanning
```bash
# Image vulnerability scanning
trivy image --severity HIGH,CRITICAL --format json -o image-report.json myapp:latest
grype myapp:latest -o json > grype-report.json

# Runtime security
falco -r rules/falco_rules.yaml -o json_output=true
```
- **Tools**: Trivy, Grype, Falco, Sysdig, Aqua Security
- **Scope**: Base images, application images, runtime behavior monitoring
- **Frequency**: Pre-deployment gate + continuous runtime monitoring

### Scan Result Management
- Centralized dashboard for all scan results (DefectDojo, Faraday, or custom SIEM)
- Deduplication and false-positive suppression workflows
- SLA tracking per severity level
- Trend analysis and metrics reporting

---

## 4. Security Code Review

### Review Process
1. **Pre-Review**: Automated SAST/SCA gates must pass before manual review
2. **Reviewer Assignment**: At least one security-trained reviewer per PR
3. **Checklist-Based Review**: Structured review using security checklists
4. **Findings Documentation**: Inline PR comments with severity and remediation guidance
5. **Approval Gate**: Security sign-off required for auth, crypto, and data-handling changes

### Security Code Review Checklist

#### Authentication and Authorization
- [ ] Multi-factor authentication enforced for privileged operations
- [ ] Password policies meet NIST 800-63B guidelines
- [ ] Session tokens are cryptographically random and properly invalidated
- [ ] RBAC/ABAC policies follow principle of least privilege
- [ ] JWT validation includes signature, issuer, audience, and expiration checks
- [ ] OAuth flows use PKCE for public clients

#### Input Validation and Output Encoding
- [ ] All user inputs validated server-side (whitelist approach)
- [ ] Parameterized queries used for all database interactions
- [ ] Output encoding context-aware (HTML, JavaScript, URL, CSS)
- [ ] File uploads validated by content-type and magic bytes, not extension
- [ ] Request size limits enforced (body, headers, URL length)

#### Cryptography
- [ ] Approved algorithms only (AES-256-GCM, ChaCha20-Poly1305, RSA-2048+, ECDSA P-256+)
- [ ] Keys managed via KMS/Vault; never hardcoded or in source control
- [ ] Random values generated via CSPRNG (crypto/rand, secrets module)
- [ ] TLS 1.2+ enforced; weak cipher suites disabled
- [ ] Certificate pinning for mobile and service-to-service communication

#### Data Protection
- [ ] PII encrypted at rest and in transit
- [ ] Data retention policies implemented with automated purging
- [ ] Database connections use TLS and credential rotation
- [ ] Secrets injected via environment variables or secret managers
- [ ] Logging excludes sensitive data (passwords, tokens, PII)

#### Error Handling and Logging
- [ ] Generic error messages to users; detailed logs internally
- [ ] Security-relevant events logged (auth failures, privilege changes, data access)
- [ ] Log injection prevented via structured logging
- [ ] Stack traces never exposed in production responses

#### API Security
- [ ] Rate limiting per endpoint and per client
- [ ] API versioning and deprecation strategy
- [ ] CORS policies restrictive (no wildcard in production)
- [ ] Request signing or mTLS for service-to-service APIs
- [ ] Pagination limits to prevent resource exhaustion

### Secure Coding Standards
- Follow OWASP Secure Coding Practices
- Language-specific guidelines: PEP 8 + Bandit (Python), ESLint Security (JS/TS), gosec (Go)
- Pre-commit hooks for secret detection (gitleaks, truffleHog)
- IDE plugins for real-time security linting

### Review Tools
| Purpose | Tools |
|---------|-------|
| Secret Detection | gitleaks, truffleHog, GitGuardian |
| Code Quality | SonarQube, Semgrep, CodeQL |
| Dependency Review | Dependabot, Snyk, npm audit |
| IaC Security | Checkov, tfsec, cfn-nag |
| Container Security | Hadolint, Dockle, Trivy |

---

## 5. Compliance Testing

### Regulatory Frameworks

#### 5.1 GDPR (General Data Protection Regulation)
- **Data Mapping**: Inventory all personal data processing activities
- **Consent Management**: Verify consent capture, storage, and withdrawal mechanisms
- **Data Subject Rights**: Test access, rectification, erasure, and portability workflows
- **Breach Notification**: Validate 72-hour notification procedures
- **DPIA**: Data Protection Impact Assessment for high-risk processing
- **Cross-Border Transfers**: Verify SCCs, adequacy decisions, or binding corporate rules

#### 5.2 SOC 2 (Service Organization Control 2)
- **Trust Services Criteria**: Security, Availability, Confidentiality, Processing Integrity, Privacy
- **Control Testing**: Design effectiveness and operating effectiveness
- **Evidence Collection**: Audit logs, policy documents, change records
- **Continuous Monitoring**: Automated control validation and exception alerting

#### 5.3 PCI DSS (Payment Card Industry Data Security Standard)
- **Scope Validation**: Cardholder data environment (CDE) segmentation testing
- **Requirement 1**: Firewall configuration review and network segmentation testing
- **Requirement 2**: Default password and security parameter verification
- **Requirement 3**: PAN storage encryption and truncation validation
- **Requirement 4**: TLS enforcement for cardholder data in transit
- **Requirement 5**: Anti-malware coverage and update verification
- **Requirement 6**: Secure development practices and vulnerability management
- **Requirement 7**: Access control and need-to-know restrictions
- **Requirement 8**: Unique IDs, MFA, and authentication testing
- **Requirement 9**: Physical security controls (if applicable)
- **Requirement 10**: Logging and audit trail completeness
- **Requirement 11**: Vulnerability scanning and penetration testing
- **Requirement 12**: Information security policy review

#### 5.4 HIPAA (Health Insurance Portability and Accountability Act)
- **PHI Identification**: Locate all protected health information stores and flows
- **Access Controls**: Role-based access, minimum necessary standard, unique user IDs
- **Audit Controls**: PHI access logging and review procedures
- **Integrity Controls**: PHI alteration detection and prevention
- **Transmission Security**: Encryption for PHI in transit and at rest
- **Breach Risk Assessment**: Documented risk analysis and mitigation

#### 5.5 ISO 27001/27002
- **ISMS Scope**: Information security management system boundaries
- **Risk Assessment**: Asset inventory, threat identification, risk treatment plan
- **Annex A Controls**: 93 controls across 4 themes (organizational, people, physical, technological)
- **Statement of Applicability**: Justification for control inclusion/exclusion
- **Internal Audit**: Scheduled ISMS compliance verification

### Compliance Testing Activities

#### Policy and Procedure Review
- Security policies current, approved, and communicated
- Incident response plan tested via tabletop exercises
- Business continuity and disaster recovery plans validated
- Vendor and third-party risk assessments completed

#### Technical Control Validation
```bash
# Example: Verify TLS configuration
testssl.sh --severity HIGH https://api.example.com

# Example: Verify security headers
curl -sI https://example.com | grep -iE "(strict-transport-security|x-frame-options|x-content-type-options|content-security-policy)"

# Example: Verify encryption at rest
aws rds describe-db-instances --query 'DBInstances[].StorageEncrypted'
```

#### Audit Trail Verification
- Log completeness: all security events captured with required fields
- Log integrity: tamper-evident storage and chain of custody
- Log retention: meets regulatory minimums (e.g., 1 year for PCI DSS)
- Log review: documented periodic review process with sign-off

#### Evidence Collection and Reporting
- Automated evidence gathering where possible (screenshots, exports, scan reports)
- Gap analysis with remediation timelines and responsible parties
- Management review and sign-off documentation
- External audit support and auditor evidence requests

### Continuous Compliance
- Policy-as-code for security baselines (Open Policy Agent, Sentinel)
- Automated compliance scanning in CI/CD (Chef InSpec, AWS Config Rules)
- Compliance dashboards with real-time posture visibility
- Quarterly internal audits and annual external audits

---

## Appendix

### Key References
- OWASP Top 10 (2021)
- OWASP ASVS (Application Security Verification Standard)
- OWASP Testing Guide v4.2
- NIST Cybersecurity Framework (CSF 2.0)
- NIST SP 800-53 (Security and Privacy Controls)
- MITRE ATT&CK Framework
- CISA Zero Trust Maturity Model

### Document Control
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-02 | Security Team | Initial release |
