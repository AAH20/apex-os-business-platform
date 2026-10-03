# APEX-OS Business Platform — Security Policy

## 1. Security Policy

- All code changes require peer review before merge to `main`.
- Secrets (API keys, tokens, credentials) must never be committed; use environment variables or a secrets manager (e.g., Doppler, AWS Secrets Manager).
- Principle of least privilege: services and users receive only the minimum permissions required.
- All dependencies are pinned and audited (`npm audit`, `pip-audit`, `cargo audit`).
- Security bugs are treated as P1 and patched within 24 hours of confirmation.

## 2. Authentication & Authorization

- **Authentication**: OIDC/SAML via enterprise IdP (Auth0, Okta, or Azure AD). Local accounts use bcrypt/argon2id hashing (cost ≥ 12).
- **MFA**: Required for all admin and privileged accounts. TOTP or WebAuthn preferred.
- **Session management**: Short-lived access tokens (15 min) + rotating refresh tokens (7 days, single-use). Tokens stored in `HttpOnly; Secure; SameSite=Strict` cookies.
- **Authorization**: RBAC with roles (`admin`, `manager`, `member`, `viewer`). Enforced server-side on every request via middleware. Resource-level checks for object ownership.
- **Password policy**: Min 12 chars, breach-check via HaveIBeenPwned API, lockout after 5 failed attempts (15-min cooldown).

## 3. Data Protection

- **Encryption at rest**: AES-256 for databases and object storage. Keys managed via KMS (AWS KMS, GCP Cloud KMS) with automatic rotation every 90 days.
- **Encryption in transit**: TLS 1.3 enforced. HSTS header with `max-age=63072000; includeSubDomains; preload`. Internal service-to-service communication uses mTLS.
- **PII handling**: PII fields encrypted at the column level. Data retention: 90 days for logs, 7 years for financial records, then cryptographic erasure.
- **Backups**: Encrypted, tested monthly for restore integrity. Stored in a separate availability zone with immutable snapshots (WORM).

## 4. API Security

- **Rate limiting**: 100 req/min per user, 1000 req/min per IP. 429 responses with `Retry-After` header.
- **Input validation**: Strict schema validation (Zod/Pydantic) on all inputs. Reject unexpected fields. Parameterized queries only — no string concatenation for SQL.
- **CORS**: Whitelist-only origins. No wildcards in production.
- **API versioning**: Breaking changes require new version (`/v1/`, `/v2/`). Deprecated versions receive 6-month notice.
- **Webhook security**: HMAC-SHA256 signature verification with timestamp tolerance of 5 minutes.
- **Error responses**: Generic messages to clients; detailed errors logged internally with correlation IDs.

## 5. Infrastructure Security

- **Network**: VPC with private subnets for compute. Security groups deny-all by default; explicit allow rules only. WAF (AWS WAF/Cloudflare) in front of all public endpoints.
- **Containers**: Non-root user, read-only filesystem, dropped capabilities, distroless base images. Scanned with Trivy/Grype in CI.
- **IaC**: Terraform with `tfsec`/`checkov` scanning. State files encrypted and stored remotely with locking.
- **Monitoring**: Centralized logging (ELK/Loki), alerting on anomalies (failed auth spikes, privilege escalation, unusual data export volumes).
- **Patch management**: OS and dependency patches applied within 7 days of critical CVE release.

## 6. Incident Response

1. **Detection**: Automated alerts from WAF, SIEM, and anomaly detection.
2. **Triage**: Severity assigned within 1 hour (P1: data breach, P2: service degradation, P3: minor).
3. **Containment**: Affected services isolated; credentials rotated; feature flags used to disable vulnerable paths.
4. **Eradication**: Root cause identified; vulnerable code patched; infrastructure rebuilt from known-good IaC.
5. **Recovery**: Services restored with enhanced monitoring. Post-incident review within 48 hours.
6. **Notification**: Affected users notified within 72 hours per GDPR/CCPA. Regulatory bodies notified as required.

**Contact**: security@apex-os.example.com | PGP key available on request.

## 7. Compliance

- **GDPR**: Data processing agreements in place. Right-to-erasure and data-portability endpoints implemented. DPO appointed.
- **SOC 2 Type II**: Controls mapped to Trust Services Criteria. Annual audit by independent firm.
- **PCI DSS**: Cardholder data environment isolated. ASV scans quarterly. SAQ-A for applicable flows.
- **HIPAA** (if applicable): BAAs with all sub-processors. PHI access logged and audited.
- **Accessibility**: WCAG 2.1 AA compliance for all user-facing interfaces.

---

*Last updated: 2026-10-03 | Owner: Security Team | Review cycle: Quarterly*
