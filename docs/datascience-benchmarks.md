# APEX-OS Data Science Benchmarks

> Last updated: 2026-10-02 · Scope: Training, inference, accuracy, feature engineering

---

## 1. Training Benchmarks

### 1.1 Gradient Boosting (GBM) Training — Airline Dataset

100 trees, depth 10, learning rate 0.1. CPU: r4.8xlarge (32 physical cores). GPU: V100.

| Tool | 100K (s) | 1M (s) | 10M (s) | AUC 1M | AUC 10M |
|---|---|---|---|---|---|
| XGBoost (CPU) | 0.4 | 2.7 | 40 | 0.749 | 0.757 |
| LightGBM (CPU) | 2.3 | 4.0 | 20 | 0.765 | 0.792 |
| CatBoost (CPU) | 1.9 | 7.0 | 70 | 0.734 | 0.735 |
| H2O (CPU) | 11 | 12 | 60 | 0.762 | 0.776 |
| XGBoost (GPU) | 0.7 | 1.3 | 5 | 0.748 | 0.756 |
| LightGBM (GPU) | 7 | 9 | 40 | 0.766 | 0.791 |
| CatBoost (GPU) | 1.6 | 3.4 | 23 | 0.735 | 0.737 |

**Key findings:**
- CPU: XGBoost fastest at small scale; LightGBM fastest at 10M rows
- GPU: XGBoost GPU is 8x faster than CPU at 10M rows
- LightGBM benefits most from high core counts (5.6x speedup on 48-core vs 32-core)
- CatBoost has lowest AUC but competitive GPU training time
- H2O has best deployment story for real-time scoring

### 1.2 Deep Learning Training

| Model | GPU | Training Time | Notes |
|---|---|---|---|
| ResNet-50 | 1x A100 | ~8 min/epoch | ImageNet, batch 256 |
| BERT-Large | 4x A100 | ~3.5 days | 40 epochs, 1M steps |
| GPT-2 (1.5B) | 8x A100 | ~2 weeks | 100B tokens |
| Llama 3 70B | 16K H100 | ~54 days | 15T tokens |

**GPU utilization patterns:**
- XGBoost GPU: ~80% GPU, 1 CPU core at 100%
- LightGBM GPU: 5-10% GPU, all CPU cores at 100% (barely uses GPU)
- CatBoost GPU: ~80% GPU, 1 CPU core at 100%

### 1.3 Training Scalability

| Cores | XGBoost Speedup | LightGBM Speedup | CatBoost Speedup |
|---|---|---|---|
| 1 → 16 | 6.5x | 1.5x | 3.5x |
| 1 → 32 | 5.0x | 7.5x | 8.0x |
| 1 → 48 | 2.7x* | 5.6x* | — |

\* Newer hardware (c7i.metal-48xl) vs older (r4.8xlarge)

---

## 2. Inference Benchmarks

### 2.1 LLM Inference — vLLM vs TensorRT-LLM

Llama 3.3 70B on H100, FP8 quantization:

| Metric | vLLM | TensorRT-LLM | Winner |
|---|---|---|---|
| TTFT p95 (100 concurrent) | 1,450 ms | 1,280 ms | TRT-LLM |
| Throughput (10 req) | 650 tok/s | 710 tok/s | TRT-LLM |
| Throughput (50 req) | — | +13% vs vLLM | TRT-LLM |
| Cold start | ~62 s | ~28 min | vLLM |
| Time to production | ~1 min | Hours | vLLM |

**Trade-off:** TensorRT-LLM is 8-13% faster at sustained load but requires compilation. vLLM starts instantly and is better for development/iterative workflows.

### 2.2 Traditional ML Inference

| Framework | Latency (ms) | Throughput (req/s) | Use Case |
|---|---|---|---|
| ONNX Runtime (CPU) | 0.5-2 | 500-2000 | Cross-platform deployment |
| TensorRT (GPU) | 0.1-0.5 | 5000-20000 | NVIDIA production |
| vLLM (LLM) | 50-200 | 100-500 | LLM serving |
| Triton Inference | 1-10 | 1000-5000 | Multi-model serving |
| llama.cpp (CPU) | 10-50 | 10-50 | Edge/local deployment |

### 2.3 MLPerf Inference Benchmarks

| Model | Framework | Latency (ms) | Throughput |
|---|---|---|---|
| ResNet-50 | vLLM/Triton | 0.5 | 20,000 img/s |
| BERT-Large | TensorRT | 2.0 | 5,000 seq/s |
| GPT-2 | vLLM | 50 | 200 tok/s |
| Llama 3 70B | TRT-LLM | 1,280 | 710 tok/s |

---

## 3. Model Accuracy Benchmarks

### 3.1 Tabular Data — 111 Datasets (McElfresh et al., NeurIPS'23)

| Model | Group | # Best | Avg Rank | Median Rank |
|---|---|---|---|---|
| CatBoost | Tree Ensemble | 19 (17.1%) | 4.9 | 4 |
| LightGBM | Tree Ensemble | 15 (13.5%) | 5.0 | 4 |
| H2O-GBM | Tree Ensemble | 13 (11.7%) | 7.0 | 6 |
| Random Forest | Tree Ensemble | 11 (9.9%) | 6.7 | 6.5 |
| AutoGluon-DL | Deep Learning | 11 (9.9%) | 6.6 | 7 |
| ResNet | Deep Learning | 10 (9.0%) | 7.5 | 8 |
| XGBoost | Tree Ensemble | 5 (4.5%) | 6.4 | 6 |
| TabPFN | Foundation | — | — | 2 |
| TabICL | Foundation | — | — | 3 |

**Key findings:**
- Tree ensembles dominate tabular data (CatBoost + LightGBM = 30.6% of best scores)
- AutoGluon (ensemble) is best overall: 39/111 (35.1%)
- Foundation models (TabPFN, TabICL) competitive but 10,000x slower
- DL models excel on large, dense, fully numeric datasets

### 3.2 Domain-Specific Accuracy

| Domain | Task | Best Model | Score |
|---|---|---|---|
| Dengue prediction | Classification | CatBoost/LightGBM/XGBoost | AUC-ROC > 0.94 |
| Network intrusion | Classification | XGBoost | 99.54% accuracy |
| Movie recommendation | Regression | XGBoost | RMSE 0.902 |
| Solubility prediction | Regression | CatBoost | R² 0.92, MSE 0.34 |
| Student performance | Classification | Random Forest | 90.23% accuracy |
| Fault detection | Classification | TCN | 99.9% accuracy |

### 3.3 Accuracy vs Speed Trade-off

| Model | Accuracy | Training Time | Inference Latency | Best For |
|---|---|---|---|---|
| XGBoost | High | Fast | <1 ms | Production tabular |
| LightGBM | High | Fastest (large data) | <1 ms | Large datasets |
| CatBoost | Highest | Slow | <1 ms | Categorical features |
| TabPFN | High | Zero-shot | 960 s | Small datasets |
| AutoGluon | Highest | Very slow | Varies | Maximum accuracy |

---

## 4. Feature Engineering Benchmarks

### 4.1 Pandas vs Polars — Covertype Dataset (581K rows, 54 features)

| Operation | Pandas (s) | Polars (s) | Speedup |
|---|---|---|---|
| Filtering | 0.0741 | 0.0183 | 4.05x |
| Aggregation | 0.1863 | 0.0083 | 22.32x |
| GroupBy | 0.0873 | 0.0106 | 8.23x |
| Sorting | 0.2027 | 0.0656 | 3.09x |
| Z-score (54 cols) | 0.5154 | 0.0919 | 5.61x |
| CSV read (17M rows) | 9.64 | 0.57 | 16.9x |

### 4.2 Energy Efficiency — Pandas vs Polars

| Dataset Size | Pandas Energy | Polars Energy | Savings |
|---|---|---|---|
| Small (<1M rows) | Baseline | ~Equal | 0% |
| Large (15M rows) | Baseline | ~63% of Pandas | 37% |
| Large (60M rows) | Baseline | ~12.5% of Pandas | 87.5% |

**Key findings:**
- Polars uses all CPU cores by default; Pandas is single-threaded
- Polars is 8x more energy-efficient on large datasets
- Polars has lower memory overhead due to Arrow columnar format
- Pandas has richer API and better ecosystem compatibility

### 4.3 Feature Engineering Pipeline Comparison

| Approach | 10M rows | 100M rows | Relative Speed |
|---|---|---|---|
| Pandas (naive) | 120 s | OOM | 1x |
| Pandas (optimized) | 45 s | 600 s | 2.7x |
| Polars (eager) | 8 s | 90 s | 15x |
| Polars (lazy) | 5 s | 45 s | 24x |
| Polars (streaming) | 6 s | 30 s | 20x |
| DuckDB | 10 s | 120 s | 12x |

### 4.4 Recommendation by Data Size

| Data Size | Recommended Tool | Reason |
|---|---|---|
| < 500K rows | Pandas | Richer API, no learning curve |
| 500K – 20M rows | Polars | 5-20x faster, lower memory |
| 20M – 100M rows | Polars (lazy) | Query optimization, streaming |
| > 100M rows | Polars (streaming) or PySpark | Out-of-core processing |
| GPU available | CuDF | 10-100x faster than CPU |

---

## 5. Optimization Recommendations

### 5.1 Training Optimization

1. **Use LightGBM for large datasets** — fastest training at 10M+ rows, best AUC
2. **Use XGBoost GPU when available** — 8x speedup over CPU for large datasets
3. **Use CatBoost for categorical features** — native handling, no preprocessing needed
4. **Use AutoGluon for maximum accuracy** — ensemble of best models, 35% win rate
5. **Leverage newer CPUs** — 48-core machines give 2.7-5.6x speedup for GBMs
6. **Avoid hyperthreading** — physical cores only for GBM training
7. **Use mixed precision** — FP16/BF16 for deep learning training (2x speedup)

### 5.2 Inference Optimization

1. **Use vLLM for LLM serving** — fastest time-to-production, good throughput
2. **Use TensorRT-LLM for production LLMs** — 8-13% faster at sustained load
3. **Use ONNX Runtime for traditional ML** — cross-platform, optimized kernels
4. **Use TensorRT for NVIDIA GPUs** — lowest latency for production
5. **Quantize models** — INT8/FP8 gives 2-4x speedup with <1% accuracy loss
6. **Batch requests** — dynamic batching improves throughput 5-10x
7. **Use Triton Inference Server** — multi-model serving, dynamic batching

### 5.3 Accuracy Optimization

1. **Start with CatBoost/LightGBM** — best baseline for tabular data
2. **Use AutoGluon for ensemble** — 35% best-score rate across 111 datasets
3. **Try TabPFN for small datasets** — zero-shot, competitive accuracy
4. **Feature engineering matters most** — often 10-20% accuracy improvement
5. **Use cross-validation** — 10-fold CV for robust estimates
6. **Tune hyperparameters** — 5-15% improvement over defaults
7. **Handle class imbalance** — SMOTE, class weights, or focal loss

### 5.4 Feature Engineering Optimization

1. **Use Polars for large datasets** — 5-20x faster than Pandas
2. **Use Polars lazy evaluation** — query optimization, predicate pushdown
3. **Use Polars streaming** — process data larger than RAM
4. **Use Arrow format** — columnar, zero-copy, cache-efficient
5. **Parallelize with Polars** — uses all CPU cores by default
6. **Use DuckDB for SQL-like operations** — fast analytical queries
7. **Cache intermediate results** — avoid recomputation in pipelines

### 5.5 General Recommendations

| Priority | Recommendation | Impact | Effort |
|---|---|---|---|
| 1 | Switch to Polars for large data | 5-20x speedup | Low |
| 2 | Use LightGBM for tabular | Best speed/accuracy | Low |
| 3 | Quantize models for inference | 2-4x speedup | Medium |
| 4 | Use AutoGluon for ensembles | +5-10% accuracy | Low |
| 5 | Implement model caching | 10-100x latency reduction | Medium |
| 6 | Use TensorRT for NVIDIA GPUs | 2-5x inference speedup | Medium |
| 7 | Adopt MLOps pipeline | Faster iteration, reproducibility | High |

---

## References

- Szilard et al. "GBM-perf: Performance of various open source GBM implementations" (2024)
- McElfresh et al. "When Do Neural Nets Outperform Boosted Trees on Tabular Data?" NeurIPS'23
- Gorishniy et al. "Tabular Data: Is Deep Learning all you need?" (2024)
- vLLM vs TensorRT-LLM benchmarks (2025-2026)
- Pandas vs Polars benchmarks (2024)
- MLPerf Inference Benchmarks (2024-2025)
- NeuSight: "Forecasting GPU Performance for Deep Learning Training and Inference" (2024)
