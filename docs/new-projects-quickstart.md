# New Projects Quickstart

Quickstart guides for all APEX-OS Business Platform projects.

---

## 1. Agent-Reach Quickstart

AI-powered customer engagement and outreach automation.

### Installation

```bash
git clone https://github.com/apex-os/agent-reach.git && cd agent-reach
pip install -r requirements.txt && pip install -e .
```

### Configuration

`.env`:
```env
AGENT_REACH_API_KEY=your_api_key_here
AGENT_REACH_BASE_URL=https://api.apex-os.com/agent-reach
AGENT_REACH_LOG_LEVEL=INFO
```

`config/agent_reach.yaml`:
```yaml
agent:
  name: my-agent
  model: gpt-4
  temperature: 0.7
channels: [email, sms, whatsapp]
rate_limiting:
  requests_per_minute: 60
```

### First Steps

```bash
agent-reach --version
agent-reach init
agent-reach health-check
agent-reach send --channel email --to test@example.com --message "Hello"
agent-reach serve --port 8080
```

---

## 2. Big Data Quickstart

Distributed data processing and analytics.

### Installation

```bash
git clone https://github.com/apex-os/big-data.git && cd big-data
# Requires Java 17+
./mvnw clean package -DskipTests
```

### Configuration

`config/bigdata.yaml`:
```yaml
cluster:
  name: apex-big-data
  workers: 4
  memory_per_worker: 4g
storage:
  type: s3
  bucket: apex-big-data-logs
processing:
  engine: spark
  spark_version: "3.5.0"
```

Environment:
```bash
export BIGDATA_HOME=/path/to/big-data
export SPARK_HOME=/path/to/spark
```

### First Steps

```bash
./scripts/start-cluster.sh
./bin/bigdata-submit --class com.apexos.WordCount --master local[4] apps/wordcount.jar /input /output
./bin/bigdata-status
open http://localhost:4040
./scripts/stop-cluster.sh
```

---

## 3. Data Science Quickstart

ML model training, experimentation, and deployment.

### Installation

```bash
git clone https://github.com/apex-os/data-science.git && cd data-science
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
```

### Configuration

`config/datascience.yaml`:
```yaml
project:
  name: my-ds-project
  experiment_tracking: mlflow
mlflow:
  tracking_uri: http://localhost:5000
compute:
  accelerator: gpu
  gpu_type: nvidia-tesla-t4
data:
  warehouse: snowflake
```

Environment:
```bash
export MLFLOW_TRACKING_URI=http://localhost:5000
export SNOWFLAKE_USER=your_user
export SNOWFLAKE_PASSWORD=your_password
```

### First Steps

```bash
ds init my-project
mlflow server --host 0.0.0.0 --port 5000
ds train --config configs/experiment.yaml --output runs/
ds compare --runs runs/exp1,runs/exp2
ds deploy --model runs/exp1/model --endpoint production
ds notebook --port 8888
```

---

## 4. Continuous BI Quickstart

Real-time business intelligence dashboards and reporting.

### Installation

```bash
git clone https://github.com/apex-os/continuous-bi.git && cd continuous-bi
# Requires Node.js 18+
npm install && npm run build
```

### Configuration

`.env`:
```env
DATABASE_URL=postgresql://user:pass@localhost:5432/continuous_bi
REDIS_URL=redis://localhost:6379
API_PORT=3000
JWT_SECRET=your_jwt_secret_here
REFRESH_INTERVAL_MINUTES=5
```

`config/dashboards.yaml`:
```yaml
dashboards:
  - name: Executive Overview
    refresh: 5m
    widgets:
      - {type: kpi, source: revenue_daily}
      - {type: chart, source: sales_trend}
  - name: Operations Monitor
    refresh: 1m
    widgets:
      - {type: gauge, source: system_health}
```

### First Steps

```bash
npm run migrate && npm run seed
npm run dev
open http://localhost:3000
npm test
```

---

## 5. Unified Platform Quickstart

Integrates all APEX-OS projects into a single cohesive experience.

### Prerequisites

All individual projects installed (Sections 1–4).

### Installation

```bash
git clone https://github.com/apex-os/unified-platform.git && cd unified-platform
make install
```

### Configuration

`.env`:
```env
APEX_OS_ENV=development
APEX_OS_PORT=8080
APEX_OS_SECRET_KEY=generate_a_strong_secret
AGENT_REACH_ENABLED=true
AGENT_REACH_URL=http://localhost:8081
BIGDATA_ENABLED=true
BIGDATA_URL=http://localhost:8082
DATASCIENCE_ENABLED=true
DATASCIENCE_URL=http://localhost:8083
CONTINUOUS_BI_ENABLED=true
CONTINUOUS_BI_URL=http://localhost:8084
DATABASE_URL=postgresql://user:pass@localhost:5432/apex_os
REDIS_URL=redis://localhost:6379
KAFKA_BROKERS=localhost:9092
```

`config/unified.yaml`:
```yaml
platform:
  name: APEX-OS Business Platform
  version: 1.0.0
  modules: [agent_reach, big_data, data_science, continuous_bi]
integrations:
  event_bus: kafka
  shared_cache: redis
  unified_auth: true
```

### First Steps

```bash
make setup
make start
open http://localhost:8080
make health-check
make logs
make stop
make test
```

### Docker Deployment

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## Next Steps

- [Architecture Overview](../architecture/overview.md)
- [API Reference](../api/README.md)
- [Community Forum](https://community.apex-os.com)
- [Release Notes](../CHANGELOG.md)
