# DataScience Benchmarks

Comprehensive benchmark suite for the APEX-OS DataScience module. Covers model training speed, evaluation accuracy, feature engineering performance, deployment latency, and overall performance metrics.

## 1. Model Training Speed

| Benchmark | Dataset | Model | Metric | Target |
|-----------|---------|-------|--------|--------|
| train_logreg_iris | Iris (150×4) | Logistic Regression | sec/epoch | < 0.05 |
| train_randomforest_100 | Synthetic 10K×20 | Random Forest (100 trees) | sec total | < 2.0 |
| train_xgboost_1000 | Synthetic 100K×50 | XGBoost (1000 rounds) | sec total | < 15.0 |
| train_nn_mnist_small | MNIST subset 10K | 3-layer MLP | sec/epoch | < 1.0 |
| train_svm_rbf | Synthetic 5K×10 | SVM RBF kernel | sec total | < 3.0 |
| train_gbm_500 | Synthetic 50K×30 | Gradient Boosting (500 iters) | sec total | < 10.0 |

**Measurement protocol:** Warm-up run excluded; report median of 5 runs. CPU-only unless GPU explicitly noted.

## 2. Model Evaluation Accuracy

| Benchmark | Dataset | Model | Metric | Target |
|-----------|---------|-------|--------|--------|
| eval_accuracy_iris | Iris | Logistic Regression | accuracy | ≥ 0.95 |
| eval_f1_binary | Synthetic binary 10K | Random Forest | F1-score | ≥ 0.90 |
| eval_auc_roc | Synthetic binary 50K | XGBoost | AUC-ROC | ≥ 0.92 |
| eval_precision_recall | Imbalanced 20K (1:10) | Gradient Boosting | PR-AUC | ≥ 0.75 |
| eval_regression_housing | California Housing | Ridge Regression | R² | ≥ 0.60 |
| eval_multiclass_mnist | MNIST 10K | MLP | accuracy | ≥ 0.95 |

**Measurement protocol:** 5-fold cross-validation; report mean ± std. Fixed random seed (42) for reproducibility.

## 3. Feature Engineering Performance

| Benchmark | Input | Transform | Metric | Target |
|-----------|-------|-----------|--------|--------|
| fe_onehot_100cols | 100K rows, 100 cat cols | One-Hot Encoding | sec total | < 1.5 |
| fe_standard_scaler | 1M rows × 50 num cols | StandardScaler | sec total | < 2.0 |
| fe_pca_100d | 50K rows × 100 features | PCA → 20 components | sec total | < 3.0 |
| fe_text_tfidf | 10K docs, avg 200 words | TF-IDF (max 5000) | sec total | < 2.5 |
| fe_datetime_extract | 500K timestamps | Extract 8 datetime features | sec total | < 1.0 |
| fe_interactions_50 | 100K rows × 50 cols | Pairwise interactions (top 20) | sec total | < 4.0 |

**Measurement protocol:** Median of 3 runs. Memory peak tracked via `tracemalloc`.

## 4. Model Deployment Latency

| Benchmark | Model | Payload | Metric | Target |
|-----------|-------|---------|--------|--------|
| deploy_lr_single | Logistic Regression | 1 sample JSON | p50 latency | < 1 ms |
| deploy_lr_batch | Logistic Regression | 1000 samples | p50 throughput | > 5000 req/s |
| deploy_rf_single | Random Forest (100) | 1 sample JSON | p50 latency | < 5 ms |
| deploy_xgb_single | XGBoost (1000) | 1 sample JSON | p50 latency | < 10 ms |
| deploy_nn_single | MLP (3-layer) | 1 sample JSON | p50 latency | < 3 ms |
| deploy_cold_start | Any serialized model | First request after load | cold start time | < 500 ms |

**Measurement protocol:** Model serialized via joblib/pickle. Server: FastAPI + uvicorn, 4 workers. Load test via `locust` or `wrk`. Report p50/p95/p99.

## 5. Performance Metrics

### 5.1 Resource Utilization

| Metric | Tool | Target |
|--------|------|--------|
| Peak CPU training | `psutil` | < 90% single core |
| Peak memory training | `tracemalloc` | < 4 GB |
| Peak CPU inference | `psutil` | < 50% single core |
| Peak memory inference | `psutil` | < 2 GB |
| Disk I/O (model save/load) | `time.perf_counter` | < 200 ms |

### 5.2 Scalability

| Benchmark | Scaling Factor | Metric | Target |
|-----------|---------------|--------|--------|
| scale_rows_10x | 10K → 100K rows | Training time ratio | < 8x (sub-linear) |
| scale_features_10x | 10 → 100 features | Training time ratio | < 10x (linear) |
| scale_concurrent_10x | 1 → 10 concurrent | Inference p99 | < 2x baseline |

### 5.3 End-to-End Pipeline

| Benchmark | Stages | Metric | Target |
|-----------|--------|--------|--------|
| e2e_train_deploy | Load → FE → Train → Eval → Deploy | total wall time | < 30s (small dataset) |
| e2e_retrain_loop | Full pipeline × 5 iterations | avg iteration time | < 25s |
| e2e_model_refresh | Swap model in running server | downtime | < 1s (zero-downtime) |

## Running the Benchmarks

```bash
# Install dependencies
pip install -r requirements-benchmarks.txt

# Run all benchmarks
pytest benchmarks/datascience/ -v --benchmark-only

# Run specific category
pytest benchmarks/datascience/test_training.py -v
pytest benchmarks/datascience/test_evaluation.py -v
pytest benchmarks/datascience/test_feature_engineering.py -v
pytest benchmarks/datascience/test_deployment.py -v

# Generate report
pytest benchmarks/datascience/ --benchmark-json=results.json
python scripts/benchmark_report.py results.json
```

## Environment

- Python ≥ 3.9
- scikit-learn ≥ 1.3
- xgboost ≥ 2.0
- FastAPI ≥ 0.100
- pytest-benchmark ≥ 4.0
- psutil ≥ 5.9
