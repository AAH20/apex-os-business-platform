# DeepEval Integration

## 1. Evaluation Framework Overview

APEX-OS uses [DeepEval](https://github.com/confident-ai/deepeval) as its primary LLM evaluation framework. DeepEval provides a pytest-native interface for defining, running, and tracking LLM evaluations as code.

### Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Test Cases     │────▶│  DeepEval    │────▶│  Metrics        │
│  (Golden Set)   │     │  Runner      │     │  (Scores)       │
└─────────────────┘     └──────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │  Confident   │
                        │  AI Cloud    │
                        │  (Dashboard) │
                        └──────────────┘
```

### Core Concepts

- **LLMTestCase**: A single evaluation unit containing input, expected output, actual output, and context.
- **Metric**: A scoring function that compares actual vs. expected behavior.
- **Evaluation Dataset**: A collection of LLMTestCases forming a golden test set.
- **Confident AI**: Optional cloud backend for experiment tracking and dashboards.

### Why DeepEval

- Native pytest integration — evaluations run alongside unit tests.
- 14+ built-in metrics (G-Eval, hallucination, toxicity, bias, etc.).
- Async/concurrent execution for large datasets.
- CI/CD friendly with JSON/CSV export and threshold gating.

---

## 2. Metric Definitions

All metrics are defined in `evals/metrics/` and registered in `evals/registry.py`.

### 2.1 Answer Relevancy

```python
from deepeval.metrics import AnswerRelevancyMetric

relevancy = AnswerRelevancyMetric(
    threshold=0.7,
    model="gpt-4o-mini",
    include_reason=True,
)
```

Measures whether the response addresses the user's query. Scored 0–1; fail if < 0.7.

### 2.2 Faithfulness

```python
from deepeval.metrics import FaithfulnessMetric

faithfulness = FaithfulnessMetric(
    threshold=0.8,
    model="gpt-4o-mini",
)
```

Checks if the response is grounded in the provided context (RAG). Detects hallucinations.

### 2.3 Contextual Precision

```python
from deepeval.metrics import ContextualPrecisionMetric

precision = ContextualPrecisionMetric(threshold=0.6)
```

Measures whether relevant context chunks are ranked higher than irrelevant ones.

### 2.4 Contextual Recall

```python
from deepeval.metrics import ContextualRecallMetric

recall = ContextualRecallMetric(threshold=0.7)
```

Measures whether all information required to answer the query is present in the retrieved context.

### 2.5 Task Completion (G-Eval)

```python
from deepeval.metrics import GEval

task_completion = GEval(
    name="Task Completion",
    criteria="Did the agent complete the user's requested task fully and correctly?",
    evaluation_params=[
        EvaluationParam.LLM_OUTPUT,
        EvaluationParam.EXPECTED_OUTPUT,
    ],
    threshold=0.75,
)
```

Custom G-Eval for agentic task success. Uses LLM-as-judge with structured criteria.

### 2.6 Tool Use Accuracy

```python
tool_accuracy = GEval(
    name="Tool Use Accuracy",
    criteria=(
        "Did the agent call the correct tool(s) with the correct arguments? "
        "Were unnecessary tools avoided?"
    ),
    threshold=0.7,
)
```

Evaluates function-calling correctness for agent workflows.

### 2.7 Toxicity & Bias

```python
from deepeval.metrics import ToxicityMetric, BiasMetric

toxicity = ToxicityMetric(threshold=0.1)
bias = BiasMetric(threshold=0.1)
```

Safety guardrails. Any score above threshold fails the test.

### Metric Summary Table

| Metric | Threshold | Scope | Model |
|---|---|---|---|
| Answer Relevancy | 0.70 | All responses | gpt-4o-mini |
| Faithfulness | 0.80 | RAG responses | gpt-4o-mini |
| Contextual Precision | 0.60 | RAG retrieval | gpt-4o-mini |
| Contextual Recall | 0.70 | RAG retrieval | gpt-4o-mini |
| Task Completion | 0.75 | Agent tasks | gpt-4o |
| Tool Use Accuracy | 0.70 | Agent tasks | gpt-4o |
| Toxicity | 0.10 | All responses | gpt-4o-mini |
| Bias | 0.10 | All responses | gpt-4o-mini |

---

## 3. Test Case Design

Test cases live in `evals/test_cases/` organized by domain.

### 3.1 Directory Structure

```
evals/
├── test_cases/
│   ├── rag/                  # RAG pipeline tests
│   │   ├── simple_qa.json
│   │   ├── multi_hop.json
│   │   └── adversarial.json
│   ├── agent/                # Agent workflow tests
│   │   ├── tool_selection.json
│   │   ├── multi_step.json
│   │   └── error_recovery.json
│   ├── safety/               # Safety guardrail tests
│   │   ├── toxicity.json
│   │   ├── bias.json
│   │   └── jailbreak.json
│   └── regression/           # Historical failure cases
│       └── regression_suite.json
├── metrics/
│   ├── __init__.py
│   ├── custom_metrics.py
│   └── registry.py
├── conftest.py
└── run_evals.py
```

### 3.2 Test Case Schema

Each JSON file contains an array of test cases:

```json
{
  "input": "What is our Q3 revenue forecast?",
  "expected_output": "Q3 revenue is projected at $4.2M based on current pipeline.",
  "retrieved_context": [
    "Q3 pipeline shows $4.2M in committed deals...",
    "Historical Q3 growth rate is 12%..."
  ],
  "tools_called": ["search_crm", "calculate_forecast"],
  "tags": ["rag", "finance", "forecast"],
  "difficulty": "medium",
  "category": "simple_qa"
}
```

### 3.3 Design Principles

- **Golden set curation**: Start with 20–50 high-confidence cases per domain; expand iteratively.
- **Adversarial coverage**: Include edge cases, ambiguous queries, and known failure modes.
- **Difficulty tagging**: Label each case (easy/medium/hard) to track performance stratification.
- **Version control**: Test cases are versioned alongside code; changes require review.
- **No production PII**: All test data is synthetic or anonymized.

### 3.4 Adding a New Test Case

1. Add entry to the appropriate JSON file under `evals/test_cases/`.
2. Include `input`, `expected_output`, and `retrieved_context` (for RAG).
3. Tag with relevant `tags` and `difficulty`.
4. Run the suite locally to verify the case passes with current model.
5. Commit with message: `eval: add <category> test case — <brief description>`.

---

## 4. Automated Evaluation Pipeline

### 4.1 Local Development

```bash
# Run all evaluations
pytest evals/ -v --deepeval

# Run specific category
pytest evals/ -v -k "rag"

# Run with specific model
pytest evals/ -v --model gpt-4o

# Generate report
pytest evals/ -v --deepeval --deepeval-output report.json
```

### 4.2 CI/CD Integration

Defined in `.github/workflows/eval.yml`:

```yaml
name: Evaluation Suite
on:
  pull_request:
    paths:
      - 'src/**'
      - 'evals/**'
      - 'prompts/**'
  schedule:
    - cron: '0 6 * * 1'  # Weekly full run

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -e ".[eval]"
      - name: Run evaluations
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          CONFIDENT_API_KEY: ${{ secrets.CONFIDENT_API_KEY }}
        run: |
          pytest evals/ -v \
            --deepeval \
            --deepeval-output results.json \
            --deepeval-threshold 0.7
      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: eval-results
          path: results.json
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('results.json'));
            // Post summary as PR comment
```

### 4.3 Pipeline Stages

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Lint &  │───▶│  Unit    │───▶│  Eval    │───▶│  Deploy  │
│  Type    │    │  Tests   │    │  Suite   │    │  Gate    │
│  Check   │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                                   │
                              ┌────┴────┐
                              │ Metrics │
                              │ > 0.70? │
                              └─────────┘
```

### 4.4 Threshold Gating

- **Hard gate**: All metrics must pass at threshold ≥ 0.70 for merge to `main`.
- **Soft gate**: Warnings for scores between 0.60–0.70; logged but non-blocking.
- **Safety gate**: Toxicity/Bias must be < 0.10 — always hard-gated.

### 4.5 Result Artifacts

Each run produces:
- `results.json` — Full per-case scores and reasons.
- `summary.md` — Human-readable pass/fail summary.
- Confident AI dashboard update (if `CONFIDENT_API_KEY` set).

---

## 5. Continuous Evaluation Strategy

### 5.1 Evaluation Triggers

| Trigger | Scope | Frequency |
|---|---|---|
| PR to `main` | Full suite | Every PR |
| Model/prompt change | Full suite | On merge |
| Weekly cron | Full suite + expanded set | Monday 06:00 UTC |
| Production incident | Regression subset | On demand |
| New feature merge | Domain-specific cases | Per feature |

### 5.2 Golden Set Maintenance

- **Weekly review**: Team reviews new production failures; high-value failures are added to `regression/`.
- **Monthly pruning**: Remove cases that no longer reflect current behavior or are redundant.
- **Quarterly audit**: Full review of all test cases for coverage gaps and bias.

### 5.3 Production Monitoring (Online Eval)

```python
# evals/online/production_eval.py
from deepeval import evaluate
from deepeval.tracing import trace, observe

@observe(type="llm")
def production_call(user_input: str) -> str:
    """Wrapped production call — automatically logged for eval."""
    return agent.run(user_input)

# Nightly batch: sample 100 production conversations, score with DeepEval
```

- Sample 1% of production traffic for continuous scoring.
- Flag conversations scoring below threshold for human review.
- Track metric drift over time via Confident AI dashboards.

### 5.4 Metric Drift Detection

```python
# evals/monitoring/drift.py
def detect_drift(current_scores: list[float], baseline: list[float]) -> bool:
    """Alert if mean score drops > 2 std devs from baseline."""
    import numpy as np
    baseline_mean = np.mean(baseline)
    baseline_std = np.std(baseline)
    current_mean = np.mean(current_scores)
    return current_mean < (baseline_mean - 2 * baseline_std)
```

### 5.5 Feedback Loop

```
Production Traffic ──▶ Sample & Log ──▶ Score with DeepEval
                                           │
                                           ▼
                                    Low Scores Detected
                                           │
                         ┌─────────────────┼─────────────────┐
                         ▼                 ▼                  ▼
                   Add to Golden    Tune Prompt/      File Bug
                   Set (regression)  RAG Config       (code defect)
```

### 5.6 Key Performance Indicators

| KPI | Target | Measurement |
|---|---|---|
| Eval suite pass rate | > 95% | Per CI run |
| Mean Answer Relevancy | > 0.80 | Weekly aggregate |
| Mean Faithfulness | > 0.85 | Weekly aggregate |
| Regression case count | Trending down | Monthly |
| Time-to-detect regression | < 24 hours | Incident tracking |
| Eval cost per run | < $5 | Per CI run |

### 5.7 Responsibilities

- **ML Engineers**: Maintain metrics, thresholds, and golden set.
- **Product Managers**: Review production eval dashboards weekly.
- **QA Engineers**: Manage CI pipeline and artifact storage.
- **On-call Engineers**: Respond to eval-triggered alerts within 4 business hours.

---

## Appendix: Quick Reference

```bash
# Install eval dependencies
pip install -e ".[eval]"

# Run full suite locally
pytest evals/ -v --deepeval

# Run with Confident AI tracking
pytest evals/ -v --deepeval --confident-api-key $CONFIDENT_API_KEY

# Debug a single test case
pytest evals/ -v -k "test_case_name" --deepeval --deepeval-verbose

# Export results as CSV
pytest evals/ -v --deepeval --deepeval-output results.csv --deepeval-format csv
```

For more details, see the [DeepEval documentation](https://deepeval.com/docs/getting-started).
