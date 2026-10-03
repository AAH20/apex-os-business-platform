#!/usr/bin/env python3
"""DataScience Demo — Model training, evaluation, feature importance, experiment tracking, deployment."""

import json
import random
import time
from datetime import datetime, timedelta

random.seed(42)


def banner(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def demo_model_training():
    banner("1. MODEL TRAINING DEMO")
    print("Training a RandomForest classifier on synthetic data...")
    n_samples, n_features = 1000, 10
    X = [[random.gauss(0, 1) for _ in range(n_features)] for _ in range(n_samples)]
    y = [1 if sum(row[:3]) > 0 else 0 for row in X]
    n_trees = 5
    trees = []
    for t in range(n_trees):
        sample_idx = random.choices(range(n_samples), k=n_samples // 2)
        trees.append({"tree_id": t, "samples": len(sample_idx), "depth": random.randint(4, 8)})
        time.sleep(0.05)
    train_acc = 0.85 + random.random() * 0.1
    print(f"  ✓ Trained {n_trees} trees on {n_samples} samples × {n_features} features")
    print(f"  ✓ Training accuracy: {train_acc:.2%}")
    print(f"  ✓ Trees: {json.dumps(trees[:2], indent=4)}")


def demo_model_evaluation():
    banner("2. MODEL EVALUATION DEMO")
    print("Evaluating model on held-out test set...")
    y_true = [random.choice([0, 1]) for _ in range(200)]
    y_pred = [t if random.random() > 0.15 else 1 - t for t in y_true]
    tp = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(y_true, y_pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y_true, y_pred) if a == 1 and b == 0)
    accuracy = (tp + tn) / len(y_true)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    print(f"  ✓ Accuracy:  {accuracy:.2%}")
    print(f"  ✓ Precision: {precision:.2%}")
    print(f"  ✓ Recall:    {recall:.2%}")
    print(f"  ✓ F1 Score:  {f1:.2%}")
    print(f"  ✓ Confusion Matrix: TP={tp}  FP={fp}  FN={fn}  TN={tn}")


def demo_feature_importance():
    banner("3. FEATURE IMPORTANCE DEMO")
    print("Computing feature importance via permutation...")
    features = [f"feature_{i}" for i in range(10)]
    importances = sorted([(f, random.random()) for f in features], key=lambda x: x[1], reverse=True)
    total = sum(v for _, v in importances)
    print(f"  {'Rank':<6}{'Feature':<16}{'Importance':>12}{'Cumulative':>12}")
    print(f"  {'-' * 46}")
    cum = 0.0
    for rank, (feat, imp) in enumerate(importances, 1):
        cum += imp / total
        bar = "█" * int(imp / total * 30)
        print(f"  {rank:<6}{feat:<16}{imp / total:>11.1%}{cum:>11.1%}  {bar}")


def demo_experiment_tracking():
    banner("4. EXPERIMENT TRACKING DEMO")
    print("Logging experiments to local tracker...")
    experiments = []
    for run_id in range(1, 4):
        exp = {
            "run_id": f"run-{run_id:03d}",
            "timestamp": (datetime.now() - timedelta(hours=run_id)).isoformat(),
            "params": {"lr": 0.01 * run_id, "epochs": 10 * run_id, "batch_size": 32},
            "metrics": {
                "loss": round(0.5 / run_id + random.random() * 0.1, 4),
                "accuracy": round(0.7 + 0.08 * run_id + random.random() * 0.02, 4),
            },
            "status": "completed",
        }
        experiments.append(exp)
        print(f"  ✓ Logged {exp['run_id']}: loss={exp['metrics']['loss']}, acc={exp['metrics']['accuracy']}")
    best = min(experiments, key=lambda e: e["metrics"]["loss"])
    print(f"\n  🏆 Best run: {best['run_id']} (loss={best['metrics']['loss']})")


def demo_model_deployment():
    banner("5. MODEL DEPLOYMENT DEMO")
    print("Deploying model to staging environment...")
    deployment = {
        "model_name": "customer-churn-v2",
        "version": "2.1.0",
        "environment": "staging",
        "endpoint": "https://api.apex-os.local/v2/predict",
        "status": "deploying",
    }
    print(f"  → Registering model: {deployment['model_name']} v{deployment['version']}")
    time.sleep(0.1)
    print(f"  → Provisioning endpoint: {deployment['endpoint']}")
    time.sleep(0.1)
    deployment["status"] = "live"
    print(f"  ✓ Deployment status: {deployment['status']}")
    test_payload = {"features": [0.5, -0.3, 1.2, 0.8, -0.1]}
    print(f"  → Test prediction: {json.dumps(test_payload)}")
    prediction = {"churn_probability": 0.23, "risk_tier": "low"}
    print(f"  ✓ Response: {json.dumps(prediction)}")


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         APEX-OS DataScience Demo Suite                      ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    demo_model_training()
    demo_model_evaluation()
    demo_feature_importance()
    demo_experiment_tracking()
    demo_model_deployment()
    print(f"\n{'─' * 60}")
    print("  All DataScience demos completed successfully!")
    print(f"{'─' * 60}\n")
