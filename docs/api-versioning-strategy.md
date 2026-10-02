# API Versioning Strategy

## 1. Versioning Scheme

APEX-OS uses **Semantic Versioning 2.0.0** for all public APIs.

| Component | Format | Example |
|-----------|--------|---------|
| Major | `v{MAJOR}` | `v2` |
| Minor | `v{MAJOR}.{MINOR}` | `v2.1` |
| Patch | `v{MAJOR}.{MINOR}.{PATCH}` | `v2.1.3` |

- **Major**: Breaking changes (removals, renames, type changes).
- **Minor**: Backwards-compatible additions (new endpoints, new fields).
- **Patch**: Backwards-compatible fixes (bug fixes, doc corrections).

Versions are exposed via URL path (`/api/v2/...`) and the `X-API-Version` response header.

## 2. Deprecation Policy

| Phase | Duration | Behavior |
|-------|----------|----------|
| **Announcement** | — | Deprecation notice in changelog + `Deprecation` header on affected endpoints |
| **Sunset window** | 90 days minimum | Endpoint returns `200 OK` with `Deprecation` and `Sunset` headers |
| **End-of-life** | After sunset date | Endpoint returns `410 Gone` with migration link |

Rules:
- Deprecated endpoints remain functional for the full sunset window.
- No new features are added to deprecated endpoints.
- Deprecation timelines are published in the changelog at least 90 days before sunset.
- Clients receive email/webhook notification when a deprecated endpoint they call is scheduled for removal.

## 3. Breaking Changes Policy

A **breaking change** is any modification that requires client code changes:

- Removing or renaming an endpoint, field, or enum value.
- Changing a field's type or nullability.
- Tightening validation (e.g., adding a required field).
- Changing authentication or authorization semantics.
- Removing a previously guaranteed SLA.

Rules:
- Breaking changes **only** land in a new major version.
- A new major version is published at least 6 months before the previous major is retired.
- Breaking changes are never backported to minor or patch releases.
- Every breaking change must include a migration guide (see §4).

## 4. Migration Guides

Each major version ships with a migration guide at `docs/migrations/v{N}-to-v{N+1}.md`.

A migration guide includes:

1. **Summary** — what changed and why.
2. **Breaking changes table** — old → new mapping.
3. **Code examples** — before/after snippets in TypeScript, Python, and cURL.
4. **Rollback plan** — how to revert if migration fails.
5. **Timeline** — key dates (announcement, sunset, EOL).

Migration guides are linked from:
- The changelog entry for the new major version.
- The `Sunset` header on deprecated endpoints.
- The developer portal migration hub.

## 5. Compatibility Matrix

| API Version | Status | Released | Sunset Date | EOL Date |
|-------------|--------|----------|-------------|----------|
| `v1` | Deprecated | 2024-01-15 | 2025-06-01 | 2025-09-01 |
| `v2` | Current | 2025-01-10 | — | — |
| `v3` | Beta | 2026-08-01 | — | — |

Legend:
- **Current**: Fully supported, receives all updates.
- **Beta**: Preview only, no SLA, may change without notice.
- **Deprecated**: Functional but scheduled for removal.
- **EOL**: Removed, returns `410 Gone`.

### Client SDK Compatibility

| SDK | Minimum API | Maximum API |
|-----|-------------|-------------|
| `@apex-os/sdk` v3.x | v1 | v2 |
| `@apex-os/sdk` v4.x | v2 | v3 |
| `apex-os-python` v2.x | v1 | v2 |
| `apex-os-python` v3.x | v2 | v3 |

---

**Last updated**: 2026-10-02
