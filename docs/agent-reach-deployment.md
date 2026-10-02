# Agent Reach — Deployment Guide

## 1. Kubernetes Deployment

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph Ingress["Ingress Layer"]
        ING[NGINX Ingress Controller]
    end

    subgraph Services["Service Mesh"]
        GW[API Gateway]
        AUTH[Auth Service]
        CORE[Core Engine]
        AGENT[Agent Runtime]
        NOTIF[Notification Svc]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL)]
        REDIS[(Redis)]
        S3[(Object Storage)]
        KAFKA[[Kafka]]
    end

    subgraph Observability["Observability"]
        PROM[Prometheus]
        GRAF[Grafana]
        LOKI[Loki]
        TEMPO[Tempo]
    end

    ING --> GW
    GW --> AUTH
    GW --> CORE
    CORE --> AGENT
    CORE --> NOTIF
    AGENT --> PG
    AGENT --> REDIS
    CORE --> S3
    NOTIF --> KAFKA
    PROM --> GRAF
    LOKI --> GRAF
    TEMPO --> GRAF
```

**Key manifests:** `deploy/k8s/{deployment,service,ingress,hpa,pdb}.yaml`

---

## 2. Multi-Cloud Deployment

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    subgraph GCP["GCP — Primary"]
        GKE[GKE Cluster]
        GCS[GCS Bucket]
        GSQL[(Cloud SQL)]
    end

    subgraph AWS["AWS — Secondary"]
        EKS[EKS Cluster]
        S3A[S3 Bucket]
        RDS[(RDS)]
    end

    subgraph Azure["Azure — DR"]
        AKS[AKS Cluster]
        BLOB[Blob Storage]
        ASQL[(Azure SQL)]
    end

    subgraph Global["Global Layer"]
        DNS[Cloud DNS / Route53]
        CDN[CloudFront + Cloud CDN]
        LB[Global Load Balancer]
    end

    DNS --> LB
    LB --> CDN
    CDN --> GKE
    CDN --> EKS
    CDN --> AKS
    GKE --> GCS
    GKE --> GSQL
    EKS --> S3A
    EKS --> RDS
    AKS --> BLOB
    AKS --> ASQL
```

**Failover:** health-check driven DNS failover; RPO < 5 min, RTO < 15 min.

---

## 3. Edge Deployment

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph Edge["Edge Nodes"]
        E1[Edge Node — US-East]
        E2[Edge Node — EU-West]
        E3[Edge Node — APAC]
    end

    subgraph Regional["Regional Hubs"]
        R1[Regional Hub — US]
        R2[Regional Hub — EU]
        R3[Regional Hub — APAC]
    end

    subgraph Core["Core Cloud"]
        C1[Primary Cluster]
        C2[Standby Cluster]
    end

    E1 --> R1
    E2 --> R2
    E3 --> R3
    R1 --> C1
    R2 --> C1
    R3 --> C1
    C1 -.->|Replication| C2
```

**Edge capabilities:** local inference, cache-first reads, store-and-forward messaging.

---

## 4. CI/CD Pipeline

```mermaid
%%{init: {'theme': 'dark'}}%%
graph LR
    DEV[Developer Push] -->|PR| CI[CI Pipeline]
    CI --> LINT[Lint & Format]
    LINT --> TEST[Unit Tests]
    TEST --> INT[Integration Tests]
    INT --> BUILD[Build Images]
    BUILD --> SCAN[Security Scan]
    SCAN --> PUSH[Push to Registry]
    PUSH --> STAGE[Deploy to Staging]
    STAGE --> E2E[E2E Tests]
    E2E --> MANUAL[Manual Approval]
    MANUAL --> CANARY[Canary Deploy 5%]
    CANARY --> OBSERVE[Observe 30 min]
    OBSERVE -->|Pass| FULL[Full Rollout]
    OBSERVE -->|Fail| ROLLBACK[Auto-Rollback]
```

**Tools:** GitHub Actions → ArgoCD → Kubernetes. Canary via Flagger.

---

## 5. Monitoring Setup

```mermaid
%%{init: {'theme': 'dark'}}%%
graph TD
    subgraph Collection["Collection"]
        OTEL[OpenTelemetry Collector]
        PROM2[Prometheus]
        FLUENT[Fluent Bit]
    end

    subgraph Storage["Storage"]
        TSDB[(Prometheus TSDB)]
        LOKI2[(Loki)]
        TEMP[(Tempo)]
        ELK[(Elasticsearch)]
    end

    subgraph Visualization["Visualization"]
        GRAF2[Grafana Dashboards]
        KIBANA[Kibana]
    end

    subgraph Alerting["Alerting"]
        ALERT[Alertmanager]
        PAGER[PagerDuty]
        SLACK[Slack Webhook]
    end

    subgraph SLO["SLO Tracking"]
        BURN[Error Budget]
        SLO[SLO Dashboard]
    end

    OTEL --> TSDB
    OTEL --> TEMP
    PROM2 --> TSDB
    FLUENT --> LOKI2
    FLUENT --> ELK
    TSDB --> GRAF2
    LOKI2 --> GRAF2
    TEMP --> GRAF2
    ELK --> KIBANA
    TSDB --> ALERT
    ALERT --> PAGER
    ALERT --> SLACK
    TSDB --> BURN
    BURN --> SLO
```

**Key dashboards:** service-latency, agent-throughput, error-rate, cost-per-request.

---

## Quick Reference

| Concern | Tooling |
|---------|---------|
| Container orchestration | Kubernetes (GKE/EKS/AKS) |
| GitOps | ArgoCD |
| CI | GitHub Actions |
| Secrets | External Secrets Operator + Vault |
| Service mesh | Istio |
| Observability | Prometheus + Grafana + Loki + Tempo |
| Log aggregation | Fluent Bit → Loki / Elasticsearch |
| Tracing | OpenTelemetry → Tempo |
| Alerting | Alertmanager → PagerDuty / Slack |
