# Document Management

## 1. Architecture

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    subgraph Client
        UI[Web UI]
        API[API Gateway]
    end
    subgraph Core
        SVC[Document Service]
        IDX[Search Index]
        STORE[Blob Store]
        DB[(Metadata DB)]
    end
    subgraph Events
        BUS[Event Bus]
        AUDIT[Audit Log]
    end
    UI --> API
    API --> SVC
    SVC --> DB
    SVC --> STORE
    SVC --> IDX
    SVC --> BUS
    BUS --> AUDIT
```

- **Document Service** — CRUD, versioning, permissions, workflow transitions.
- **Blob Store** — immutable file content (S3-compatible).
- **Metadata DB** — document records, tags, ACLs, version pointers.
- **Search Index** — Elasticsearch/OpenSearch for full-text queries.
- **Event Bus** — publishes `document.created`, `document.updated`, `document.deleted` for audit and integrations.

## 2. Document Types

| Type | Extension | MIME | Storage |
|------|-----------|------|---------|
| Contract | `.pdf`, `.docx` | `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | Blob + preview |
| Invoice | `.pdf`, `.xml` | `application/pdf`, `application/xml` | Blob + structured extract |
| Report | `.md`, `.pdf` | `text/markdown`, `application/pdf` | Blob + rendered HTML |
| Policy | `.md` | `text/markdown` | Blob + rendered HTML |
| Spreadsheet | `.xlsx`, `.csv` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `text/csv` | Blob + tabular index |
| Image | `.png`, `.jpg`, `.svg` | `image/png`, `image/jpeg`, `image/svg+xml` | Blob + thumbnail |

Each type defines: allowed MIME types, max size, preview generator, and extraction pipeline.

## 3. Document Workflow

```mermaid
%%{init: {'theme':'dark'}}%%
stateDiagram-v2
    [*] --> Draft
    Draft --> Review: submit
    Review --> Approved: approve
    Review --> Draft: reject
    Approved --> Published: publish
    Published --> Archived: archive
    Archived --> Draft: restore
    Draft --> Deleted: delete
    Review --> Deleted: delete
    Approved --> Deleted: delete
    Published --> Deleted: delete
    Deleted --> [*]
```

- **Draft** — editable, visible to owner and collaborators.
- **Review** — locked for editing; reviewers can approve or reject.
- **Approved** — locked; ready for publication.
- **Published** — read-only; visible to all authorized users.
- **Archived** — read-only; hidden from default search.
- **Deleted** — soft-deleted; recoverable within retention period.

Transitions emit events on the bus. Permissions are enforced at each transition.

## 4. Document Search

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart TD
    Q[User Query] --> P[Query Parser]
    P --> F[Filters]
    P --> FT[Full-Text]
    F --> DB[(Metadata DB)]
    FT --> ES[(Search Index)]
    DB --> R[Results]
    ES --> R
    R --> RNK[Ranking]
    RNK --> OUT[Ranked Results]
```

- **Full-text** — tokenized search over extracted text content (Elasticsearch).
- **Metadata filters** — type, author, date range, tags, status, custom fields.
- **Faceted** — aggregations on type, author, status for drill-down.
- **Ranking** — relevance score + recency boost + user permission weighting.
- **Highlighting** — matched terms highlighted in snippets.

API: `GET /api/v1/documents?q=&type=&author=&status=&tags=&from=&to=&page=`

## 5. Document Versioning

```mermaid
%%{init: {'theme':'dark'}}%%
flowchart LR
    V1[v1.0] --> V2[v1.1]
    V2 --> V3[v1.2]
    V3 --> V4[v2.0]
    V4 --> V5[v2.1]
    V5 --> V6[v2.2]
    V3 -.-> B1[branch: legal-review]
    B1 --> B2[v1.2.1]
    B2 --> M[merge → v2.3]
    V6 --> M
```

- **Immutable versions** — each save creates a new version; content is never mutated.
- **Semantic versioning** — `MAJOR.MINOR` (e.g., `v2.1`); major on structural changes, minor on edits.
- **Branching** — parallel version lines for review tracks; merge creates a new version.
- **Diff** — text diff between any two versions; binary diff via metadata comparison.
- **Rollback** — restore any prior version as the new head (creates a new version, never deletes history).
- **Retention** — configurable per document type; archived versions moved to cold storage.

Version metadata: `version_id`, `parent_id`, `author`, `timestamp`, `change_summary`, `blob_ref`.
