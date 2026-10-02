# Changelog

All notable changes to the APEX-OS Business Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Real-time collaboration presence indicators on shared dashboards
- Webhook event subscriptions for order lifecycle transitions
- Bulk CSV import for product catalog with validation preview
- Dark mode theme support across all dashboard views
- API rate limiting headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`)
- Audit log export in JSON and CSV formats
- Multi-currency support with automatic FX rate refresh
- Role-based access control (RBAC) for workspace-level permissions
- Slack integration for order and inventory alerts
- Automated backup scheduling with configurable retention policies

### Changed
- Upgraded authentication to OAuth 2.1 with PKCE flow
- Replaced legacy REST v1 endpoints with REST v2 (v1 deprecated)
- Improved dashboard rendering performance by 40% via virtualized lists
- Migrated from Webpack to Vite for faster dev builds and HMR
- Updated default session timeout from 8 hours to 2 hours
- Redesigned settings page with tabbed navigation
- Enhanced search to support fuzzy matching and filters

### Deprecated
- REST API v1 endpoints (removal planned for v3.0.0)
- Legacy webhook payload format `v1` (use `v2`)
- `GET /api/v1/users/me/preferences` (replaced by `/api/v2/users/me/settings`)
- Old dashboard widget `summary-card` (use `metric-card`)
- Node.js 16 runtime support (minimum is now Node.js 18)

### Removed
- Legacy Flash-based file uploader (replaced by resumable chunk upload)
- Deprecated `X-API-Key` header authentication (use Bearer tokens)
- Unused `legacy-reports` module

### Fixed
- Resolved race condition in concurrent inventory updates
- Fixed timezone discrepancy in scheduled report delivery
- Corrected pagination offset bug on large datasets (>10k rows)
- Fixed memory leak in WebSocket connection pool
- Resolved CSV export encoding issues for non-Latin characters
- Fixed incorrect tax calculation for multi-jurisdiction orders
- Corrected email template variable interpolation edge cases
- Fixed session token refresh loop on expired refresh tokens

### Security
- Patched CVE-2026-12345: Updated `jsonwebtoken` to v9.0.2
- Enforced HTTPS-only cookies with `SameSite=Strict`
- Added CSP headers to all API responses
- Rotated default API signing keys
- Implemented brute-force protection on login endpoints

---

## [2.4.0] — 2026-09-15

### Added
- GraphQL API gateway with schema stitching
- Custom dashboard builder with drag-and-drop widgets
- Inventory forecasting using exponential smoothing
- Multi-language support (EN, ES, FR, DE, JA)
- SSO/SAML 2.0 integration for enterprise workspaces
- Data retention policies with automated purging
- Public REST API documentation via OpenAPI 3.1 spec

### Changed
- Replaced MongoDB with PostgreSQL for transactional data
- Migrated job queue from BullMQ to Temporal for workflow orchestration
- Upgraded React 18 → 19 with concurrent rendering
- Consolidated microservice health checks into unified `/healthz` endpoint
- Improved error messages with actionable remediation steps

### Deprecated
- Legacy MongoDB connection strings (use PostgreSQL DSN)
- `bullmq` job definitions (migrate to Temporal workflows)
- v1 dashboard layout format (auto-migrated on first load)

### Removed
- Deprecated `reports-v1` service (merged into `analytics-v2`)
- Legacy SOAP API endpoints

### Fixed
- Fixed deadlock in concurrent order processing
- Resolved N+1 query issue in product listing endpoint
- Corrected currency rounding in financial reports
- Fixed file upload size limit not respecting nginx config
- Resolved intermittent 502 errors from API gateway

### Security
- Upgraded OpenSSL to 3.3.4
- Added HSTS header with preload directive
- Implemented input sanitization for all user-generated content

---

## [2.3.0] — 2026-07-01

### Added
- Order management workflow with state machine transitions
- Supplier portal with self-service onboarding
- Automated low-stock alerts via email and SMS
- REST API v2 with cursor-based pagination
- Webhook retry mechanism with exponential backoff
- Data export to S3-compatible storage
- Two-factor authentication (TOTP) for user accounts

### Changed
- Refactored monolith into modular monolith with clear boundaries
- Upgraded TypeScript to 5.5 with strict mode enabled
- Replaced custom logger with structured JSON logging (pino)
- Improved database connection pooling with PgBouncer
- Enhanced CI/CD pipeline with canary deployments

### Deprecated
- Legacy order status strings (use enum values)
- `X-Request-ID` header (replaced by `X-Correlation-ID`)
- v1 authentication tokens (migrate to v2 JWT format)

### Removed
- Deprecated `inventory-v1` REST endpoints
- Legacy cron-based job scheduler

### Fixed
- Fixed incorrect stock deduction on order cancellation
- Resolved timezone bug in daily aggregation jobs
- Fixed memory spike during large CSV imports
- Corrected email notification template rendering
- Fixed CORS preflight failures for custom headers

### Security
- Implemented row-level security in PostgreSQL
- Added rate limiting per API key
- Enforced password complexity requirements

---

## [2.2.0] — 2026-04-20

### Added
- Product catalog with variant support (size, color, material)
- Purchase order approval workflow
- Integration with Stripe for payment processing
- Real-time inventory tracking with WebSocket updates
- Custom report builder with chart library
- User activity audit trail
- Docker Compose setup for local development

### Changed
- Migrated frontend from Create React App to Next.js
- Replaced Redux with Zustand for state management
- Upgraded Node.js runtime to v20 LTS
- Improved database indexing for common query patterns
- Refactored authentication middleware for better testability

### Deprecated
- Legacy product SKU format (use new UUID-based identifiers)
- `redux` store (migrate to Zustand stores)
- v1 payment webhook format

### Removed
- Deprecated `catalog-v1` GraphQL schema
- Legacy admin panel (replaced by new dashboard)

### Fixed
- Fixed duplicate order creation on network retry
- Resolved inventory sync delay across warehouses
- Fixed broken image upload for HEIC format
- Corrected discount stacking calculation
- Fixed session persistence across browser restarts

### Security
- Added CSRF protection for state-changing endpoints
- Implemented secure password hashing with Argon2id
- Added security headers (X-Frame-Options, X-Content-Type-Options)

---

## [2.1.0] — 2026-02-10

### Added
- User management with role-based permissions
- Order tracking with status history
- Basic inventory management with stock levels
- Email notifications for order updates
- REST API v1 with token authentication
- Swagger/OpenAPI documentation
- Health check endpoints for monitoring

### Changed
- Initial public release of APEX-OS Business Platform
- Established core domain models (Order, Product, User, Inventory)
- Set up CI/CD with GitHub Actions
- Configured production deployment on AWS ECS

### Fixed
- Fixed initial database migration ordering
- Resolved CORS configuration for cross-origin requests
- Fixed email delivery failures for certain SMTP providers

---

## [2.0.0] — 2025-12-01

### Added
- Complete platform rewrite with modular architecture
- Multi-tenant workspace support
- Event-driven architecture with message bus
- Comprehensive test suite (unit, integration, E2E)
- Infrastructure as Code with Terraform
- Observability stack (Prometheus, Grafana, Loki)

### Changed
- **BREAKING**: Replaced legacy monolith with service-oriented architecture
- **BREAKING**: New database schema (not backward-compatible with v1.x)
- **BREAKING**: API authentication changed from session-based to token-based
- **BREAKING**: All v1 API endpoints removed
- Migrated from JavaScript to TypeScript
- Replaced MySQL with PostgreSQL
- Switched from AWS Lambda to containerized ECS services

### Removed
- All v1.x legacy code and endpoints
- Legacy admin interface
- Old reporting engine

### Security
- Implemented OWASP Top 10 mitigations
- Added automated dependency vulnerability scanning
- Enforced TLS 1.3 for all connections

---

## [1.3.0] — 2025-09-15

### Added
- Basic order management
- Product catalog (single variant only)
- User authentication with email/password
- Simple dashboard with key metrics
- CSV export for orders and products

### Changed
- Improved page load performance by 30%
- Updated UI component library

### Fixed
- Fixed login redirect loop
- Resolved timezone display issues
- Fixed CSV export for large datasets

---

## [1.2.0] — 2025-07-01

### Added
- Inventory tracking
- Email notifications
- Basic reporting
- User roles (admin, manager, viewer)

### Changed
- Refactored database layer for better performance
- Improved error handling across services

### Fixed
- Fixed data inconsistency in inventory counts
- Resolved email template rendering issues

---

## [1.1.0] — 2025-05-01

### Added
- Product management
- Order creation and tracking
- Basic user authentication
- Admin dashboard

### Changed
- Initial beta release

### Fixed
- Fixed initial bug fixes from alpha testing

---

## [1.0.0] — 2025-03-01

### Added
- Initial alpha release of APEX-OS Business Platform
- Core domain models and database schema
- Basic CRUD operations for products and orders
- Simple web interface

---

[Unreleased]: https://github.com/apex-os/business-platform/compare/v2.4.0...HEAD
[2.4.0]: https://github.com/apex-os/business-platform/compare/v2.3.0...v2.4.0
[2.3.0]: https://github.com/apex-os/business-platform/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/apex-os/business-platform/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/apex-os/business-platform/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/apex-os/business-platform/compare/v1.3.0...v2.0.0
[1.3.0]: https://github.com/apex-os/business-platform/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/apex-os/business-platform/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/apex-os/business-platform/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/apex-os/business-platform/releases/tag/v1.0.0
