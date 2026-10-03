# CRUD Security Documentation

## 1. CRUD Security Policy

### 1.1 Purpose
This document defines the security policies governing all Create, Read, Update, and Delete (CRUD) operations within the APEX-OS Business Platform. It establishes the baseline controls for protecting data integrity, confidentiality, and availability across all CRUD interfaces.

### 1.2 Scope
- All REST and GraphQL API endpoints performing CRUD operations
- Database access layers (ORM, raw queries, stored procedures)
- Admin panels and internal tooling
- Batch import/export jobs
- Third-party integrations with CRUD permissions

### 1.3 Core Principles
- **Least Privilege**: Users and services receive only the minimum CRUD permissions required for their role.
- **Deny by Default**: All CRUD operations are denied unless explicitly authorized.
- **Separation of Duties**: No single role may create, approve, and delete the same record.
- **Auditability**: Every CRUD operation is logged with actor, timestamp, source IP, and affected record ID.
- **Data Minimization**: Only fields necessary for the operation are exposed or accepted.

### 1.4 Roles and Permissions Matrix

| Role | Create | Read | Update | Delete |
|------|--------|------|--------|--------|
| Admin | Yes | Yes | Yes | Yes (soft) |
| Manager | Yes | Yes (scoped) | Yes (scoped) | No |
| Editor | Yes | Yes (scoped) | Yes (own) | No |
| Viewer | No | Yes (scoped) | No | No |
| Service Account | Yes (API) | Yes (API) | Yes (API) | No |

### 1.5 Policy Enforcement
- All CRUD endpoints enforce authorization server-side; client-side checks are UX-only.
- Permission checks occur at the service layer, not the controller layer.
- Cross-tenant CRUD operations are blocked by default; explicit grants required.

---

## 2. CRUD Authentication and Authorization

### 2.1 Authentication
- **Primary**: OAuth 2.0 / OpenID Connect with PKCE for all interactive sessions.
- **Service-to-Service**: mTLS or signed JWTs with short-lived tokens (max 15 minutes).
- **API Keys**: Scoped, rotatable, and stored as salted hashes; never returned after creation.
- **Session Management**: Idle timeout of 15 minutes; absolute timeout of 12 hours; concurrent session limits per role.

### 2.2 Authorization Model
- **RBAC (Role-Based Access Control)**: Coarse-grained roles gate access to CRUD resources.
- **ABAC (Attribute-Based Access Control)**: Fine-grained policies evaluate record attributes (owner, tenant, status, classification).
- **ReBAC (Relationship-Based Access Control)**: Used for hierarchical data (e.g., manager can CRUD direct reports' records).

### 2.3 CRUD Authorization Checks
1. **Authentication**: Verify caller identity via valid token/session.
2. **Authorization**: Evaluate RBAC role + ABAC attributes + ReBAC relationships.
3. **Ownership Validation**: For Update/Delete, verify the caller owns the record or has explicit delegation.
4. **Tenant Isolation**: Enforce tenant ID matching on all CRUD queries.
5. **Rate Limiting**: Per-user and per-endpoint throttling to prevent abuse.

### 2.4 Token Security
- Access tokens: JWT with `sub`, `roles`, `tenant_id`, `exp`, `jti` claims.
- Refresh tokens: Opaque, rotated on use, bound to device fingerprint.
- Token revocation: Immediate via `jti` denylist on logout or compromise.

### 2.5 Multi-Factor Authentication (MFA)
- Required for all Admin and Manager roles.
- Required for Delete operations on sensitive records (financial, PII).
- TOTP or WebAuthn/FIDO2 supported; SMS fallback deprecated.

---

## 3. CRUD Data Protection

### 3.1 Data Classification
| Level | Examples | CRUD Restrictions |
|-------|----------|-------------------|
| Public | Product catalogs | Open read; authenticated write |
| Internal | Analytics, configs | Authenticated read; role-based write |
| Confidential | Customer records | Owner/role-based CRUD; encrypted at rest |
| Restricted | PII, financial data | Strict ABAC; MFA for delete; field-level encryption |

### 3.2 Encryption
- **At Rest**: AES-256-GCM for database storage; envelope encryption with KMS-managed DEKs.
- **In Transit**: TLS 1.3 minimum; HSTS enforced; certificate pinning for mobile clients.
- **Field-Level**: Sensitive fields (SSN, payment data) encrypted with per-record keys before storage.
- **Backup**: Encrypted with separate keys; tested restore procedures quarterly.

### 3.3 Input Validation
- **Schema Validation**: All CRUD payloads validated against strict JSON Schema / Protobuf definitions.
- **Type Enforcement**: Reject unexpected types; coerce only where safe.
- **Length Limits**: Enforced at API gateway and database layer.
- **Content-Type Enforcement**: Reject mismatched content types.
- **File Uploads**: MIME-type verification, size limits, virus scanning, and storage outside web root.

### 3.4 Output Filtering
- **Field-Level Redaction**: Sensitive fields masked or omitted based on caller permissions.
- **Serialization**: Use DTOs/serializers; never expose raw ORM entities.
- **Error Messages**: Generic for clients; detailed logs only server-side (no stack traces or SQL in responses).

### 3.5 Data Retention and Deletion
- **Soft Delete**: Default for all records; `deleted_at` timestamp set; excluded from queries.
- **Hard Delete**: Requires Admin + MFA; logged with reason; cascaded per retention policy.
- **Retention Policies**: Configurable per data class; automated purging after expiry.
- **Right to Erasure**: GDPR/CCPA-compliant deletion workflows with verification.

### 3.6 Audit Logging
- Every CRUD operation logged to append-only audit store.
- Log entries: `timestamp`, `actor_id`, `action`, `resource_type`, `resource_id`, `changes` (diff), `ip`, `user_agent`, `correlation_id`.
- Audit logs immutable; retained for minimum 1 year; accessible only to Security and Compliance roles.

---

## 4. CRUD API Security

### 4.1 Transport Security
- TLS 1.3 required; TLS 1.2 minimum with secure cipher suites.
- HSTS header with `includeSubDomains` and `preload`.
- API gateway terminates TLS; internal mTLS between services.

### 4.2 Request Security
- **CSRF Protection**: SameSite=Strict cookies + CSRF tokens for state-changing operations.
- **CORS**: Strict origin whitelist; credentials only for trusted domains.
- **Content Security Policy**: Restrictive CSP headers on all API responses.
- **Rate Limiting**: Token bucket per user/IP; 429 with `Retry-After` header.

### 4.3 Endpoint Protection
- **Idempotency**: Create/Update endpoints support `Idempotency-Key` header to prevent duplicate operations.
- **Pagination**: Mandatory for Read endpoints; max page size enforced (default 100, max 1000).
- **Filtering**: Whitelist allowed filter fields; reject arbitrary query parameters.
- **Sorting**: Whitelist allowed sort fields; prevent injection via sort parameters.

### 4.4 Injection Prevention
- **SQL Injection**: Parameterized queries only; ORM with query builder; no string concatenation.
- **NoSQL Injection**: Input sanitization; operator whitelisting; schema validation.
- **Command Injection**: No shell execution with user input; strict input validation.
- **XSS**: Output encoding; Content-Type enforcement; CSP headers.

### 4.5 API Versioning and Deprecation
- Version in URL path (`/v1/`) or header.
- Deprecated versions return `Deprecation` and `Sunset` headers.
- Breaking changes require new version; minimum 6-month deprecation window.

### 4.6 Webhook Security
- Payloads signed with HMAC-SHA256; signature in `X-APEX-Signature` header.
- Timestamp tolerance window of 5 minutes to prevent replay.
- Endpoint URL validation; HTTPS-only delivery.
- Retry with exponential backoff; dead-letter queue for failed deliveries.

### 4.7 Error Handling
- Standardized error format: `{ "error": { "code", "message", "details", "request_id" } }`.
- No internal details leaked; correlation ID for support tracing.
- Appropriate HTTP status codes: 400, 401, 403, 404, 409, 422, 429, 500.

---

## 5. CRUD Infrastructure Security

### 5.1 Network Security
- **VPC Isolation**: Database and internal services in private subnets; no public IPs.
- **Security Groups**: Least-privilege ingress/egress; deny all by default.
- **API Gateway**: Single entry point; WAF (Web Application Firewall) with OWASP rules.
- **DDoS Protection**: Cloud provider DDoS mitigation; rate limiting at edge.

### 5.2 Database Security
- **Access Control**: Database users with minimal privileges; no root/application co-mingling.
- **Encryption**: TDE (Transparent Data Encryption) enabled; backups encrypted.
- **Auditing**: Database audit logs enabled; monitored for anomalous CRUD patterns.
- **Patching**: Automated security patches within 30 days of release.
- **Backups**: Encrypted, tested regularly; stored in separate availability zone.

### 5.3 Secrets Management
- All credentials, API keys, and tokens stored in a dedicated secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager).
- Automatic rotation: database credentials every 90 days; API keys every 180 days.
- No secrets in code, environment variables, or configuration files.
- Dynamic secrets for short-lived database access where supported.

### 5.4 Container and Runtime Security
- **Images**: Built from minimal base images; scanned for vulnerabilities; signed with cosign.
- **Runtime**: Non-root user; read-only filesystem; dropped capabilities; seccomp profiles.
- **Orchestration**: Pod security policies; network policies; resource limits.
- **Service Mesh**: mTLS between services; authorization policies at mesh layer.

### 5.5 Monitoring and Incident Response
- **SIEM Integration**: All CRUD audit logs streamed to SIEM for correlation and alerting.
- **Anomaly Detection**: ML-based detection of unusual CRUD patterns (bulk deletes, off-hours access, privilege escalation).
- **Alerting**: Real-time alerts for: failed auth spikes, unauthorized access attempts, bulk data exports, schema changes.
- **Incident Response Plan**: Documented runbooks for data breach, unauthorized access, and data integrity incidents.
- **Forensics**: Immutable audit logs and point-in-time recovery for investigation.

### 5.6 Compliance and Governance
- **Standards**: SOC 2 Type II, ISO 27001, GDPR, CCPA compliance maintained.
- **Penetration Testing**: Annual third-party pen test; quarterly automated vulnerability scans.
- **Access Reviews**: Quarterly review of all CRUD permissions; orphaned access revoked.
- **Data Processing Agreements**: Maintained for all subprocessors with CRUD access.

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-10-03 | Security Team | Initial release |

## References
- OWASP API Security Top 10
- NIST Cybersecurity Framework
- CIS Benchmarks
- APEX-OS Architecture Documentation
