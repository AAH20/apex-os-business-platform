# New Projects Security Guide

This guide defines the security requirements for all new projects in the APEX-OS Business Platform. Every project must implement controls across five domains: authentication, authorization, data protection, API security, and infrastructure security.

---

## 1. Authentication

### 1.1 Identity Verification

- All user-facing and service-to-service authentication must use OAuth 2.0 / OpenID Connect (OIDC).
- Multi-factor authentication (MFA) is required for all human accounts. TOTP or WebAuthn/FIDO2 are acceptable second factors.
- Machine-to-machine communication must use short-lived tokens (JWT with `exp` ≤ 15 minutes) or mutual TLS (mTLS).
- Never store plaintext passwords. Use bcrypt, scrypt, or Argon2id with per-user salts.
- Session tokens must be cryptographically random (≥ 128 bits entropy) and stored server-side or in `HttpOnly`, `Secure`, `SameSite=Strict` cookies.

### 1.2 Token Lifecycle

- Access tokens: short-lived (≤ 15 minutes).
- Refresh tokens: rotating, single-use, with reuse detection that revokes the entire token family on compromise.
- Token revocation must be immediate upon logout, password change, or account disable.

### 1.3 Credential Handling

- Secrets (API keys, client secrets, signing keys) must be stored in a dedicated secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, Doppler).
- Never hardcode credentials in source code, configuration files, or environment variables committed to version control.
- Rotate credentials on a defined schedule (≤ 90 days for API keys, ≤ 30 days for signing keys) and immediately upon suspected compromise.

---

## 2. Authorization

### 2.1 Access Control Model

- Enforce role-based access control (RBAC) or attribute-based access control (ABAC) for all resources.
- Default-deny: access is denied unless explicitly granted.
- Apply the principle of least privilege: grant the minimum permissions required for a role to function.

### 2.2 Implementation Requirements

- Authorization checks must be enforced server-side on every request. Client-side checks are UX-only and never sufficient.
- Use a centralized authorization policy engine (e.g., OPA, Casbin) for complex or cross-cutting rules.
- Resource-level authorization: verify the authenticated principal has access to the specific resource ID being requested, not just the endpoint.

### 2.3 Administrative Access

- Administrative actions require step-up authentication (re-authentication or MFA challenge).
- All administrative operations must be logged with actor, action, target, and timestamp.
- Break-glass accounts (emergency access) must be monitored, time-limited, and require post-incident review.

---

## 3. Data Protection

### 3.1 Data Classification

- Classify all data assets: Public, Internal, Confidential, Restricted.
- Apply controls proportional to classification level.

### 3.2 Encryption

- **In transit:** TLS 1.2+ (TLS 1.3 preferred) for all network communication. Disable TLS 1.0/1.1 and weak ciphers.
- **At rest:** AES-256 encryption for databases, object storage, and backups.
- **Field-level:** Encrypt sensitive fields (PII, financial data, credentials) with application-layer encryption before storage.

### 3.3 Data Handling

- PII must be minimized: collect only what is necessary, retain only as long as required.
- Data retention policies must be defined and enforced per data class. Automate purging of expired data.
- Mask or redact sensitive data in logs, analytics, and non-production environments.
- Backups must be encrypted, access-controlled, and tested for restore integrity on a regular schedule.

### 3.4 Data Loss Prevention

- Implement egress filtering and monitoring for bulk data exfiltration.
- Use DLP tooling to detect and block unauthorized transmission of sensitive data.

---

## 4. API Security

### 4.1 Input Validation

- Validate all input against a strict schema (type, length, format, allowed values) at the API boundary.
- Reject unexpected fields, malformed payloads, and encoding anomalies.
- Use parameterized queries or ORM with query builder to prevent SQL/NoSQL injection.

### 4.2 Output Encoding

- Encode all output based on context (HTML, JavaScript, URL, CSS) to prevent XSS.
- Set `Content-Type` correctly and include `X-Content-Type-Options: nosniff`.

### 4.3 Rate Limiting & Throttling

- Apply rate limits per client, per user, and per endpoint.
- Return `429 Too Many Requests` with `Retry-After` header when limits are exceeded.
- Implement circuit breakers for downstream dependencies to prevent cascade failures.

### 4.4 API Design

- Use versioning (`/v1/`, `/v2/`) to manage breaking changes.
- Require authentication on all endpoints except explicitly public health checks.
- Implement idempotency keys for mutating operations (POST, PUT, PATCH, DELETE) to prevent duplicate processing.
- Return consistent error responses that do not leak internal details (stack traces, database errors, internal IPs).

### 4.5 CORS & Headers

- Configure CORS with an explicit allowlist of origins. Never use `Access-Control-Allow-Origin: *` for credentialed requests.
- Set security headers: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`.

---

## 5. Infrastructure Security

### 5.1 Network Security

- Segment networks: public-facing services in DMZ, application and data tiers in private subnets.
- Use security groups / firewall rules to enforce least-privilege network access between tiers.
- Deny all inbound traffic by default; allow only required ports and sources.
- Use a WAF (Web Application Firewall) in front of public-facing applications.

### 5.2 Compute & Container Security

- Harden base images: remove unnecessary packages, run as non-root user, use minimal distributions.
- Scan container images for vulnerabilities in CI/CD. Block deployment on critical findings.
- Apply resource limits (CPU, memory, file descriptors) to prevent resource exhaustion attacks.
- Use read-only root filesystems and drop unnecessary Linux capabilities where possible.

### 5.3 Secrets & Configuration Management

- Inject secrets at runtime via a secrets manager; never bake them into images or artifacts.
- Separate configuration from code. Use environment-specific configuration stores.
- Audit all access to secrets and configuration.

### 5.4 Logging & Monitoring

- Centralize logs (application, access, audit, infrastructure) in a tamper-resistant store.
- Alert on authentication failures, authorization denials, privilege escalations, and anomalous data access patterns.
- Retain security logs for a minimum of 90 days (1 year recommended for audit trails).
- Implement distributed tracing to enable incident investigation across service boundaries.

### 5.5 Vulnerability & Patch Management

- Maintain an up-to-date software bill of materials (SBOM) for all services.
- Apply security patches within SLA: critical (≤ 48 hours), high (≤ 7 days), medium (≤ 30 days).
- Conduct regular vulnerability scans and penetration tests. Track remediation to closure.

### 5.6 Incident Response

- Maintain a documented incident response plan covering detection, containment, eradication, recovery, and post-mortem.
- Define escalation paths and on-call rotations.
- Conduct tabletop exercises at least annually.

---

## Compliance Checklist for New Projects

| Control Area | Requirement | Verification |
|---|---|---|
| Authentication | MFA enforced for all human accounts | Auth config review |
| Authorization | Default-deny, least privilege | Policy review |
| Data Protection | TLS 1.2+, AES-256 at rest | Config scan |
| API Security | Input validation, rate limiting | Code review + pen test |
| Infrastructure | Network segmentation, WAF, logging | Architecture review |

---

*This guide is a living document. Update it as threats evolve and new controls are adopted.*
