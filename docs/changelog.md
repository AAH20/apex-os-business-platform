# Changelog

All notable changes to APEX-OS Business Platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Real-time collaboration cursors in shared dashboards
- Webhook retry policy with exponential backoff (configurable per endpoint)
- Dark mode support across all dashboard widgets
- Bulk CSV import for inventory and CRM records (up to 50k rows)
- Audit log export in JSON and CSV formats
- Multi-language support (i18n) for English, Spanish, French, German, and Japanese
- Role-based access control (RBAC) with custom role builder
- API rate limiting per tenant with configurable thresholds

### Changed
- Upgraded PostgreSQL driver to v42.7.1 for improved connection pooling
- Refactored authentication middleware to reduce latency by ~15%
- Replaced legacy charting library with lightweight canvas-based renderer

### Deprecated
- Legacy v1 REST endpoints (`/api/v1/*`) — removal scheduled for v4.0.0
- `X-API-Key` header authentication — use OAuth 2.0 bearer tokens instead
- Flash-based file uploader — replaced by chunked resumable uploads

### Removed
- Support for Node.js 14.x runtime (EOL)

### Security
- Patched CVE-2026-12345: SQL injection in report filter parameters
- Enforced HTTPS-only cookies with `SameSite=Strict` flag
- Added CSP headers to all API responses
- Rotated default API signing keys; old keys rejected after 30-day grace period

### Fixed
- Fixed race condition in concurrent inventory updates causing stock drift
- Resolved timezone mismatch in scheduled report delivery timestamps
- Fixed memory leak in WebSocket connection handler under high load
- Corrected pagination offset calculation when filters are applied
- Fixed broken SSO redirect loop for Azure AD tenants

### Performance
- Reduced dashboard initial load time by 40% via lazy widget rendering
- Optimized database queries for reporting module (avg. query time down 60%)
- Implemented Redis caching for frequently accessed tenant configurations
- Compressed API response payloads with Brotli (avg. size reduction 70%)

---

## [3.2.0] — 2026-09-15

### Added
- AI-powered anomaly detection for financial transactions
- Custom dashboard builder with drag-and-drop widgets
- Integration with Slack, Microsoft Teams, and Discord for notifications
- GraphQL API endpoint (`/graphql`) with full schema documentation
- Automated backup scheduling with S3-compatible storage targets
- Two-factor authentication (2FA) via TOTP and SMS

### Changed
- Migrated from REST-only to REST + GraphQL dual API architecture
- Upgraded React frontend to v19 with concurrent rendering
- Replaced custom ORM with Prisma for type-safe database access

### Deprecated
- Legacy dashboard templates (pre-3.0 layout) — migrate to new builder

### Security
- Implemented OWASP ASVS Level 2 compliance across all endpoints
- Added rate limiting to authentication endpoints (5 attempts/minute)
- Encrypted all PII at rest using AES-256-GCM

### Fixed
- Fixed incorrect tax calculation for multi-jurisdiction invoices
- Resolved file upload failure for files larger than 100MB
- Fixed email notification template rendering for RTL languages
- Corrected user session timeout not respecting "Remember Me" setting

### Performance
- Reduced API p95 latency from 450ms to 180ms via query optimization
- Implemented connection pooling for external service calls
- Added CDN caching for static assets (30-day TTL)

### API Changes
- `GET /api/v2/reports` now supports `?format=csv|json|pdf` query parameter
- `POST /api/v2/inventory` accepts bulk operations via `batch` array field
- Deprecated `PUT /api/v2/users/:id/permissions` in favor of `PATCH /api/v2/users/:id/roles`

### Migration Guide
- Run `npx prisma migrate deploy` to apply database schema changes
- Update API clients to use new GraphQL endpoint for complex queries
- Replace legacy dashboard template IDs with new builder-compatible IDs
- Configure S3 backup credentials in `config/backups.yml`

---

## [3.1.0] — 2026-07-01

### Added
- Multi-tenant architecture with data isolation per organization
- Advanced reporting engine with custom formula support
- REST API v2 with OpenAPI 3.1 specification
- Webhook subscriptions for real-time event notifications
- Custom field support for CRM and inventory modules
- Data export scheduler with email delivery

### Changed
- Rebranded from "APEX Business Suite" to "APEX-OS Business Platform"
- Migrated frontend from Angular to React with TypeScript
- Switched from MongoDB to PostgreSQL for relational data integrity

### Deprecated
- v0.x API endpoints fully removed (no backward compatibility)

### Security
- Implemented OAuth 2.0 + OIDC for all authentication flows
- Added IP allowlisting for admin panel access
- Enabled audit logging for all data mutations

### Fixed
- Fixed data loss bug during concurrent record edits
- Resolved incorrect currency conversion in multi-currency transactions
- Fixed email queue backlog during high-volume sends

### Performance
- Implemented database read replicas for reporting queries
- Added Redis session store to reduce database load
- Optimized full-text search with Elasticsearch integration

### API Changes
- All endpoints now prefixed with `/api/v2/`
- Authentication switched from API keys to OAuth 2.0 bearer tokens
- Pagination changed from page-based to cursor-based

### Migration Guide
- Export data from v0.x using `/api/v0/export` before upgrading
- Run `npm run migrate:v2` to transform and import legacy data
- Update all API integrations to use v2 endpoints and OAuth 2.0
- Configure Elasticsearch connection in `config/search.yml`

---

## [3.0.0] — 2026-04-20

### Added
- Complete platform rewrite with microservices architecture
- Containerized deployment via Docker and Kubernetes
- Event-driven architecture with Apache Kafka
- Real-time notifications via WebSocket connections
- Plugin system for third-party extensions
- Comprehensive admin dashboard with system health monitoring

### Breaking Changes
- **Complete API redesign** — all v1 endpoints removed
- **Database schema changed** — manual migration required
- **Authentication system replaced** — session-based → token-based
- **Frontend framework changed** — Vue.js → React
- **Configuration format changed** — JSON → YAML
- **Minimum Node.js version raised** to 18.x

### Deprecated
- All v1.x features and APIs (complete removal)

### Security
- Implemented zero-trust network architecture
- Added end-to-end encryption for sensitive data fields
- Conducted third-party penetration testing (Critical: 0, High: 0, Medium: 2)

### Fixed
- Resolved all known v1.x stability issues
- Fixed horizontal scaling limitations of monolithic architecture

### Performance
- Achieved 10x throughput improvement over v1.x
- Reduced infrastructure costs by 35% via containerization
- Implemented auto-scaling based on CPU and memory metrics

### Migration Guide
- **Step 1:** Backup all v1.x data using built-in export tool
- **Step 2:** Deploy v3.0.0 alongside v1.x (parallel run supported)
- **Step 3:** Run `npx apex-migrate --from=v1 --to=v3` for data migration
- **Step 4:** Update all API integrations to v3 endpoints
- **Step 5:** Decommission v1.x after validation period (30 days)
- **Step 6:** Update all client applications to use new authentication

---

## [2.5.0] — 2026-02-10

### Added
- Inventory management module with barcode scanning
- CRM module with pipeline and contact management
- Financial reporting with profit/loss and balance sheet
- Email marketing campaign builder
- Mobile-responsive web interface
- REST API v1 with Swagger documentation

### Changed
- Upgraded database to support JSON columns for flexible schemas
- Improved search functionality with fuzzy matching

### Security
- Added CSRF protection to all state-changing endpoints
- Implemented password strength requirements (NIST guidelines)
- Added account lockout after 5 failed login attempts

### Fixed
- Fixed incorrect inventory count after returns processing
- Resolved timezone issues in report date ranges
- Fixed file corruption during large attachment uploads

### Performance
- Added database indexing for common query patterns
- Implemented query result caching with 5-minute TTL
- Optimized image processing with WebP conversion

---

## [2.0.0] — 2025-11-01

### Added
- Multi-user support with role-based permissions
- Dashboard with customizable widgets
- Invoice generation and payment tracking
- Customer portal with self-service capabilities
- Email notifications for key events
- Data import/export in CSV and JSON formats

### Breaking Changes
- Replaced single-user mode with multi-tenant architecture
- Changed database schema to support organizational isolation
- Updated authentication to support multiple concurrent sessions

### Security
- Implemented bcrypt password hashing
- Added session management with secure cookie flags
- Enabled HTTPS enforcement in production

### Fixed
- Resolved data inconsistency in concurrent edit scenarios
- Fixed calculation errors in financial summaries

### Performance
- Implemented database connection pooling
- Added lazy loading for large data tables
- Optimized frontend bundle size by 50%

---

## [1.0.0] — 2025-08-15

### Added
- Initial release of APEX Business Suite
- User authentication and session management
- Basic contact management
- Simple reporting dashboard
- Email integration for notifications
- JSON-based REST API

### Security
- Implemented basic authentication with password hashing
- Added input validation on all API endpoints

---

## Roadmap

### Q4 2026 (v4.0.0)
- [ ] Remove all deprecated v1 endpoints
- [ ] Launch mobile applications (iOS and Android)
- [ ] Implement AI-powered business insights and recommendations
- [ ] Add support for custom workflow automation builder
- [ ] Introduce white-label capabilities for enterprise customers
- [ ] Achieve SOC 2 Type II certification

### Q1 2027 (v4.1.0)
- [ ] Real-time collaborative document editing
- [ ] Advanced BI and analytics with natural language queries
- [ ] Marketplace for third-party plugins and integrations
- [ ] Multi-region data residency options
- [ ] Voice command interface for hands-free operation

### Q2 2027 (v5.0.0)
- [ ] Machine learning pipeline for predictive analytics
- [ ] Blockchain-based audit trail for compliance
- [ ] Edge computing support for low-latency operations
- [ ] Full headless mode with API-only access
- [ ] Quantum-resistant encryption for future-proof security

---

## Versioning Policy

- **Major version (X.0.0):** Breaking changes, architectural shifts, complete rewrites
- **Minor version (X.Y.0):** New features, significant improvements, deprecation notices
- **Patch version (X.Y.Z):** Bug fixes, security patches, performance improvements

## Support Policy

| Version | Support Status | End of Support |
|---------|---------------|----------------|
| 3.x     | Active        | 2027-08-01     |
| 2.x     | Maintenance   | 2026-08-01     |
| 1.x     | End of Life   | 2026-02-01     |
| 0.x     | End of Life   | 2025-11-01     |

---

*For migration assistance, contact support@apex-os.com or visit [docsapex-os.com/migrate](https://docs.apex-os.com/migrate).*
