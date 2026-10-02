# APEX-OS Security Audit Checklist

## 1. Authentication Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 1.1 | Critical | Enforce MFA for all user accounts, especially admins | Review auth config; attempt login without MFA |
| 1.2 | Critical | Use strong password policy (min 12 chars, complexity) | Inspect password validation logic; test weak passwords |
| 1.3 | High | Implement account lockout after 5 failed attempts | Test brute-force; verify lockout triggers |
| 1.4 | High | Use secure session tokens (JWT with expiry, rotation) | Inspect token generation; test token reuse after logout |
| 1.5 | High | Set session timeout (idle 30 min, absolute 8 hr) | Verify timeout config; test idle session expiry |
| 1.6 | Medium | Hash passwords with bcrypt/argon2 (cost ≥ 12) | Inspect password storage; verify hash algorithm |
| 1.7 | Medium | Prevent credential stuffing with rate limiting | Test rapid login attempts from single IP |
| 1.8 | Medium | Secure password reset flow (time-limited tokens) | Request reset; test token reuse and expiry |
| 1.9 | Low | Display generic error messages on login failure | Attempt login with wrong credentials; check response |
| 1.10 | Low | Log all authentication events (success/failure) | Trigger login events; verify audit log entries |

## 2. Authorization Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 2.1 | Critical | Enforce RBAC on all API endpoints | Test each role against unauthorized endpoints |
| 2.2 | Critical | Validate object-level permissions (ownership) | Attempt to access another user's resources by ID |
| 2.3 | High | Deny by default — no implicit permissions | Review middleware; test unauthenticated requests |
| 2.4 | High | Separate admin and user role privileges | Verify admin-only routes reject standard users |
| 2.5 | High | Implement principle of least privilege for service accounts | Review service account scopes; test over-privileged access |
| 2.6 | Medium | Validate JWT claims and scopes on every request | Craft tokens with modified claims; test rejection |
| 2.7 | Medium | Prevent privilege escalation via parameter manipulation | Modify role/permission fields in requests |
| 2.8 | Low | Document all roles and their permissions | Review access control matrix documentation |

## 3. Data Protection Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 3.1 | Critical | Encrypt data at rest (AES-256) for all databases | Inspect DB encryption config; verify disk encryption |
| 3.2 | Critical | Enforce TLS 1.2+ for all data in transit | Test with SSL Labs; verify TLS version and cipher suites |
| 3.3 | High | Encrypt sensitive fields (PII, financial) individually | Inspect field-level encryption; verify key management |
| 3.4 | High | Use secure key management (KMS, HSM, or Vault) | Review key storage; verify no hardcoded keys |
| 3.5 | High | Mask sensitive data in logs and error messages | Trigger errors; inspect logs for PII leakage |
| 3.6 | Medium | Implement data retention and deletion policies | Verify retention config; test data purging |
| 3.7 | Medium | Secure backups with encryption and access controls | Inspect backup config; test restore from backup |
| 3.8 | Medium | Validate and sanitize all user inputs | Test with XSS/SQLi payloads; verify sanitization |
| 3.9 | Low | Classify data by sensitivity level | Review data classification documentation |

## 4. API Security Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 4.1 | Critical | Validate and sanitize all input parameters | Fuzz endpoints with malformed data; check responses |
| 4.2 | Critical | Implement rate limiting per user/IP | Send burst requests; verify throttling |
| 4.3 | High | Use CORS whitelist — no wildcard origins | Inspect CORS headers; test cross-origin requests |
| 4.4 | High | Validate Content-Type and reject unexpected types | Send requests with wrong Content-Type headers |
| 4.5 | High | Implement request size limits | Send oversized payloads; verify rejection |
| 4.6 | Medium | Use API versioning and deprecation strategy | Verify versioned endpoints; test deprecated ones |
| 4.7 | Medium | Return consistent error format without stack traces | Trigger 500 errors; inspect response body |
| 4.8 | Medium | Log API access with request/response metadata | Make API calls; verify audit trail |
| 4.9 | Low | Document all endpoints with OpenAPI/Swagger | Review API documentation completeness |
| 4.10 | Low | Implement idempotency for mutation endpoints | Send duplicate requests; verify no duplicate effects |

## 5. Infrastructure Security Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 5.1 | Critical | Keep all systems patched and up to date | Run vulnerability scanner; check OS/package versions |
| 5.2 | Critical | Disable unused ports and services | Run nmap scan; verify only required ports open |
| 5.3 | High | Use network segmentation (VPCs, subnets, firewalls) | Review network config; test inter-segment traffic |
| 5.4 | High | Deploy WAF in front of application | Test with common attack payloads; verify WAF blocks |
| 5.5 | High | Enable DDoS protection (rate limiting, CDN) | Simulate traffic spike; verify mitigation |
| 5.6 | High | Use secrets management — no env vars for secrets | Inspect deployment config; verify Vault/KMS usage |
| 5.7 | Medium | Implement container security (non-root, read-only FS) | Inspect container configs; verify security contexts |
| 5.8 | Medium | Enable centralized logging and monitoring | Verify log aggregation; test alerting rules |
| 5.9 | Medium | Use infrastructure-as-code with security scanning | Review IaC templates; run tfsec/checkov |
| 5.10 | Low | Document network architecture and data flows | Review architecture diagrams and data flow docs |

## 6. Compliance Audit

| # | Severity | Description | Verification Method |
|---|----------|-------------|---------------------|
| 6.1 | Critical | Maintain GDPR compliance (data subject rights) | Test data export/erasure requests; verify response |
| 6.2 | Critical | Enforce data residency requirements | Verify data storage locations; check cross-border transfers |
| 6.3 | High | Implement consent management for data processing | Verify consent capture; test consent withdrawal |
| 6.4 | High | Maintain audit trails for all data access | Review access logs; verify tamper-proof storage |
| 6.5 | High | Conduct regular penetration testing (annual minimum) | Review pen test reports; verify remediation |
| 6.6 | High | Maintain incident response plan and run tabletop exercises | Review IR plan; verify contact lists and procedures |
| 6.7 | Medium | Ensure third-party vendor security assessments | Review vendor security questionnaires and SOC 2 reports |
| 6.8 | Medium | Implement data processing agreements (DPAs) with vendors | Verify DPAs are signed and current |
| 6.9 | Medium | Maintain security awareness training for all staff | Review training records; verify completion rates |
| 6.10 | Low | Document security policies and procedures | Review policy docs; verify annual review cycle |
