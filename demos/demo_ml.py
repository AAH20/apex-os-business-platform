"""ML lifecycle demo: train, evaluate, serve, monitor drift, retrain.

Run: python demos/demo_ml.py
Requires: numpy, scikit-learn (pip install numpy scikit-learn)
"""
import json
import os
import pickle
import random
from datetime import datetime

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    SKLEARN = True
except ImportError:
    SKLEARN = False

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
DRIFT_LOG = os.path.join(os.path.dirname(__file__), "drift_log.jsonl")
random.seed(42)
np.random.seed(42)


def _make_data(n=500, shift=0.0):
    """Binary classification: y = 1 if x0 + x1 + shift > 0."""
    X = np.random.randn(n, 2)
    y = (X[:, 0] + X[:, 1] + shift > 0).astype(int)
    return X, y


# ── 1. Train ────────────────────────────────────────────────────────────────
def train():
    print("\n[1/5] TRAIN")
    X, y = _make_data()
    if SKLEARN:
        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    else:
        idx = np.random.permutation(len(X))
        split = int(0.8 * len(X))
        X_tr, X_te = X[idx[:split]], X[idx[split:]]
        y_tr, y_te = y[idx[:split]], y[idx[split:]]
    if SKLEARN:
        model = RandomForestClassifier(n_estimators=50, random_state=42)
    else:
        model = _TinyModel()
    model.fit(X_tr, y_tr)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    acc = accuracy_score(y_te, model.predict(X_te)) if SKLEARN else model.score(X_te, y_te)
    print(f"  trained on {len(X_tr)} samples → val acc={acc:.3f}  (saved {MODEL_PATH})")
    return model


# ── 2. Evaluate ─────────────────────────────────────────────────────────────
def evaluate(model):
    print("\n[2/5] EVALUATE")
    X, y = _make_data(n=200)
    if SKLEARN:
        preds = model.predict(X)
        acc = accuracy_score(y, preds)
        report = classification_report(y, preds, output_dict=True)
    else:
        preds = [model.predict(x) for x in X]
        acc = float(np.mean(preds == y))
        report = {"accuracy": acc}
    print(f"  accuracy={acc:.3f}")
    print(f"  report={json.dumps(report, default=str)[:200]}")
    return acc


# ── 3. Serve prediction ──────────────────────────────────────────────────────
def serve(model):
    print("\n[3/5] SERVE")
    samples = [[0.5, 0.5], [-1.0, -1.0], [2.0, -0.5]]
    for s in samples:
        if SKLEARN:
            proba = model.predict_proba([s])[0]
            pred = int(model.predict([s])[0])
        else:
            proba = model.predict_proba(s)
            pred = int(proba > 0.5)
        print(f"  input={s} → pred={pred}  P(1)={proba if isinstance(proba, float) else proba[1]:.3f}")


# ── 4. Monitor drift ─────────────────────────────────────────────────────────
def monitor_drift(model):
    print("\n[4/5] MONITOR DRIFT")
    X_ref, y_ref = _make_data(n=200)
    X_new, y_new = _make_data(n=200, shift=1.5)  # shifted distribution
    if SKLEARN:
        acc_ref = accuracy_score(y_ref, model.predict(X_ref))
        acc_new = accuracy_score(y_new, model.predict(X_new))
    else:
        acc_ref = float(np.mean([model.predict(x) for x in X_ref] == y_ref))
        acc_new = float(np.mean([model.predict(x) for x in X_new] == y_new))
    drift = acc_ref - acc_new
    status = "DRIFT" if drift > 0.1 else "OK"
    entry = {"ts": datetime.now().isoformat(), "acc_ref": round(acc_ref, 3),
             "acc_new": round(acc_new, 3), "drift": round(drift, 3), "status": status}
    with open(DRIFT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  ref_acc={acc_ref:.3f}  new_acc={acc_new:.3f}  drift={drift:.3f}  → {status}")
    return drift


# ── 5. Retrain ───────────────────────────────────────────────────────────────
def retrain():
    print("\n[5/5] RETRAIN")
    X, y = _make_data(n=800, shift=1.5)  # retrain on shifted data
    if SKLEARN:
        model = RandomForestClassifier(n_estimators=50, random_state=42)
    else:
        model = _TinyModel()
    model.fit(X, y)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    acc = accuracy_score(y, model.predict(X)) if SKLEARN else model.score(X, y)
    print(f"  retrained on {len(X)} shifted samples → train acc={acc:.3f}")
    return model


# ── Fallback tiny model (no sklearn) ────────────────────────────────────────
class _TinyModel:
    """Perceptron-like fallback so the demo runs without sklearn."""
    def fit(self, X, y, lr=0.1, epochs=50):
        Xb = np.c_[X, np.ones(len(X))]
        self.w = np.zeros(Xb.shape[1])
        for _ in range(epochs):
            for xi, yi in zip(Xb, y):
                self.w += lr * (yi - self._s(xi @ self.w)) * xi
        return self

    def _s(self, z):
        return 1 / (1 + np.exp(-z))

    def predict(self, X):
        if X.ndim == 1:
            return int(self._s(np.append(X, 1.0) @ self.w) > 0.5)
        return (self._s(np.c_[X, np.ones(len(X))] @ self.w) > 0.5).astype(int)

    def predict_proba(self, X):
        if X.ndim == 1:
            p = self._s(np.append(X, 1.0) @ self.w)
            return np.array([1 - p, p])
        p = self._s(np.c_[X, np.ones(len(X))] @ self.w)
        return np.c_[1 - p, p]

    def score(self, X, y):
        return float(np.mean(self.predict(X) == y))


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  APEX-OS ML Lifecycle Demo")
    print(f"  backend: {'scikit-learn' if SKLEARN else 'fallback perceptron'}")
    print("=" * 60)
    model = train()
    evaluate(model)
    serve(model)
    drift = monitor_drift(model)
    if drift > 0.1:
        print("  ↳ drift detected — triggering retrain")
        model = retrain()
        evaluate(model)
    else:
        print("  ↳ no significant drift — skipping retrain")
    print("\nDone.")
