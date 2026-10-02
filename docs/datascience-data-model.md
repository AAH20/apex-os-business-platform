# Data Science Data Model

> APEX-OS Business Platform — ML data architecture reference.
> All diagrams use the dark theme for readability.

---

## 1. Feature Store Schema

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    FEATURE_GROUP ||--o{ FEATURE : contains
    FEATURE ||--o{ FEATURE_VALUE : materializes
    FEATURE_VIEW ||--o{ FEATURE : projects
    FEATURE_GROUP ||--o{ FEATURE_VIEW : consumed_by
    DATA_SOURCE ||--o{ FEATURE_GROUP : ingests
    ENTITY ||--o{ FEATURE_VALUE : keyed_by

    FEATURE_GROUP {
        string group_id PK
        string name
        string description
        string entity_type
        string event_timestamp_col
        string created_at
        string owner
        json tags
    }
    FEATURE {
        string feature_id PK
        string group_id FK
        string name
        string dtype
        string description
        boolean is_primary_key
        boolean is_event_timestamp
        json transformation
        int ttl_seconds
    }
    FEATURE_VALUE {
        string feature_id FK
        string entity_key
        timestamp event_timestamp
        string value
        timestamp created_at
    }
    FEATURE_VIEW {
        string view_id PK
        string group_id FK
        string name
        string description
        string sql_or_code
        string schedule
        string created_at
    }
    DATA_SOURCE {
        string source_id PK
        string name
        string type
        string connection_string
        string schema
        string table_or_topic
    }
    ENTITY {
        string entity_id PK
        string name
        string description
        string join_key
    }
```

---

## 2. Model Registry Schema

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    MODEL ||--o{ MODEL_VERSION : has
    MODEL_VERSION ||--|| MODEL_ARTIFACT : packages
    MODEL_VERSION ||--o{ MODEL_DEPLOYMENT : deployed_as
    MODEL_VERSION ||--o{ MODEL_METRIC : evaluated_by
    STAGE_TRANSITION ||--|| MODEL_VERSION : transitions

    MODEL {
        string model_id PK
        string name
        string description
        string owner
        string framework
        string created_at
        string current_stage
    }
    MODEL_VERSION {
        string version_id PK
        string model_id FK
        string version
        string stage
        string run_id FK
        string created_at
        string created_by
        string description
    }
    MODEL_ARTIFACT {
        string artifact_id PK
        string version_id FK
        string uri
        string format
        string checksum
        int size_bytes
        string created_at
    }
    MODEL_DEPLOYMENT {
        string deployment_id PK
        string version_id FK
        string environment
        string endpoint
        string status
        string deployed_at
        string deployed_by
    }
    MODEL_METRIC {
        string metric_id PK
        string version_id FK
        string name
        float value
        string dataset_version
        timestamp computed_at
    }
    STAGE_TRANSITION {
        string transition_id PK
        string version_id FK
        string from_stage
        string to_stage
        string reason
        string approved_by
        timestamp transitioned_at
    }
```

---

## 3. Experiment Tracking Schema

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    EXPERIMENT ||--o{ RUN : contains
    RUN ||--o{ PARAM : logs
    RUN ||--o{ METRIC : logs
    RUN ||--o{ ARTIFACT : produces
    RUN ||--o{ TAG : tagged_with
    RUN ||--o{ SYSTEM_METRIC : records

    EXPERIMENT {
        string experiment_id PK
        string name
        string description
        string owner
        string project
        string created_at
        string status
    }
    RUN {
        string run_id PK
        string experiment_id FK
        string run_name
        string status
        string started_at
        string ended_at
        string git_commit
        string code_version
        string user
    }
    PARAM {
        string param_id PK
        string run_id FK
        string key
        string value
    }
    METRIC {
        string metric_id PK
        string run_id FK
        string key
        float value
        int step
        timestamp logged_at
    }
    ARTIFACT {
        string artifact_id PK
        string run_id FK
        string name
        string uri
        string type
        int size_bytes
        string created_at
    }
    TAG {
        string tag_id PK
        string run_id FK
        string key
        string value
    }
    SYSTEM_METRIC {
        string sys_metric_id PK
        string run_id FK
        string metric_name
        float value
        timestamp recorded_at
    }
```

---

## 4. Dataset Versioning Schema

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    DATASET ||--o{ DATASET_VERSION : has
    DATASET_VERSION ||--o{ DATASET_SPLIT : contains
    DATASET_VERSION ||--o{ DATASET_STATISTIC : summarizes
    DATASET_VERSION ||--o{ DATASET_LINEAGE : traces
    DATASET_VERSION ||--o{ DATASET_TAG : tagged_with

    DATASET {
        string dataset_id PK
        string name
        string description
        string owner
        string domain
        string created_at
        string current_version
    }
    DATASET_VERSION {
        string version_id PK
        string dataset_id FK
        string version
        string uri
        string format
        string checksum
        int row_count
        int size_bytes
        string created_at
        string created_by
        string description
    }
    DATASET_SPLIT {
        string split_id PK
        string version_id FK
        string split_name
        int row_count
        float percentage
        string uri
    }
    DATASET_STATISTIC {
        string stat_id PK
        string version_id FK
        string column_name
        string stat_type
        float value
        string computed_at
    }
    DATASET_LINEAGE {
        string lineage_id PK
        string version_id FK
        string upstream_version_id
        string transformation
        string created_at
    }
    DATASET_TAG {
        string tag_id PK
        string version_id FK
        string key
        string value
    }
```

---

## 5. Label Management

```mermaid
%%{init: {'theme': 'dark'}}%%
erDiagram
    LABEL_SCHEMA ||--o{ LABEL_DEFINITION : defines
    LABELING_TASK ||--o{ ANNOTATION : contains
    LABELING_TASK ||--|| LABEL_SCHEMA : uses
    ANNOTATION ||--|| LABEL_DEFINITION : conforms_to
    ANNOTATION ||--o{ ANNOTATION_REVIEW : reviewed_by
    DATASET_VERSION ||--o{ LABELING_TASK : annotates
    USER ||--o{ ANNOTATION : creates
    USER ||--o{ ANNOTATION_REVIEW : performs

    LABEL_SCHEMA {
        string schema_id PK
        string name
        string description
        string version
        string created_at
        string created_by
    }
    LABEL_DEFINITION {
        string label_def_id PK
        string schema_id FK
        string name
        string description
        string value_type
        json allowed_values
        boolean is_required
    }
    LABELING_TASK {
        string task_id PK
        string schema_id FK
        string dataset_version_id FK
        string name
        string status
        string assigned_to
        string created_at
        string due_date
        string priority
    }
    ANNOTATION {
        string annotation_id PK
        string task_id FK
        string label_def_id FK
        string annotator_id FK
        string entity_key
        string value
        float confidence
        string created_at
        string updated_at
    }
    ANNOTATION_REVIEW {
        string review_id PK
        string annotation_id FK
        string reviewer_id FK
        string decision
        string comment
        string reviewed_at
    }
    USER {
        string user_id PK
        string username
        string email
        string role
    }
```

---

## Entity Relationship Summary

| Domain | Core Entities | Key Relationships |
|--------|--------------|-------------------|
| Feature Store | FeatureGroup, Feature, FeatureValue, FeatureView | Group → Features → Values; View projects Features |
| Model Registry | Model, ModelVersion, Artifact, Deployment | Model → Versions → Artifacts/Deployments |
| Experiment Tracking | Experiment, Run, Param, Metric, Artifact | Experiment → Runs → Params/Metrics/Artifacts |
| Dataset Versioning | Dataset, Version, Split, Statistic, Lineage | Dataset → Versions → Splits/Stats/Lineage |
| Label Management | Schema, Task, Annotation, Review | Schema → Task → Annotations → Reviews |

---

## Conventions

- All primary keys are UUIDs or ULIDs.
- All timestamps are UTC ISO 8601.
- All `*_at` fields are auto-populated.
- Soft deletes via `deleted_at` timestamp (not shown for brevity).
- JSON columns store flexible metadata (tags, transformations, allowed values).
- Foreign keys are logical; enforcement is application-level for cross-service references.
