"""Continuous BI advanced features: alerting, anomaly detection, predictive analytics, NL queries, collaborative filtering."""
from __future__ import annotations
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


# ── Real-time Alerting ──────────────────────────────────────────────
@dataclass
class AlertRule:
    name: str
    condition: Callable[[dict], bool]
    severity: str = "info"
    channel: str = "default"

@dataclass
class Alert:
    rule: str
    message: str
    severity: str
    timestamp: float
    data: dict = field(default_factory=dict)

class AlertEngine:
    def __init__(self):
        self.rules: list[AlertRule] = []
        self.alerts: list[Alert] = []
        self._handlers: list[Callable] = []

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)

    def on_alert(self, handler: Callable) -> None:
        self._handlers.append(handler)

    def evaluate(self, event: dict) -> list[Alert]:
        triggered = []
        for rule in self.rules:
            if rule.condition(event):
                alert = Alert(rule.name, f"Rule '{rule.name}' triggered", rule.severity, event.get("timestamp", 0), event)
                self.alerts.append(alert)
                triggered.append(alert)
                for h in self._handlers:
                    h(alert)
        return triggered


# ── Anomaly Detection ──────────────────────────────────────────────
class ZScoreAnomalyDetector:
    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold
        self._values: list[float] = []

    def update(self, value: float) -> bool:
        is_anomaly = False
        if len(self._values) >= 2:
            mean = sum(self._values) / len(self._values)
            variance = sum((v - mean) ** 2 for v in self._values) / len(self._values)
            std = math.sqrt(variance) if variance > 0 else 0
            if std > 0:
                is_anomaly = abs(value - mean) / std > self.threshold
        self._values.append(value)
        return is_anomaly


# ── Predictive Analytics ───────────────────────────────────────────
class LinearPredictor:
    def __init__(self):
        self._x: list[float] = []
        self._y: list[float] = []

    def fit(self, x: list[float], y: list[float]) -> None:
        self._x, self._y = list(x), list(y)

    def predict(self, x: float) -> float:
        if not self._x:
            return 0.0
        n = len(self._x)
        mx = sum(self._x) / n
        my = sum(self._y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(self._x, self._y))
        den = sum((xi - mx) ** 2 for xi in self._x)
        slope = num / den if den else 0
        return my + slope * (x - mx)


# ── Natural Language Queries ───────────────────────────────────────
class NLQueryEngine:
    def __init__(self):
        self._metrics: dict[str, list[float]] = {}

    def register(self, name: str, values: list[float]) -> None:
        self._metrics[name] = values

    def query(self, text: str) -> dict[str, Any]:
        text = text.lower()
        result: dict[str, Any] = {}
        for name, values in self._metrics.items():
            if name.lower() in text:
                if "avg" in text or "average" in text:
                    result[name] = sum(values) / len(values) if values else 0
                elif "max" in text:
                    result[name] = max(values) if values else 0
                elif "min" in text:
                    result[name] = min(values) if values else 0
                elif "sum" in text or "total" in text:
                    result[name] = sum(values)
                else:
                    result[name] = values
        return result


# ── Collaborative Filtering ────────────────────────────────────────
class CollaborativeFilter:
    def __init__(self):
        self._ratings: dict[str, dict[str, float]] = defaultdict(dict)

    def add_rating(self, user: str, item: str, rating: float) -> None:
        self._ratings[user][item] = rating

    def recommend(self, user: str, n: int = 5) -> list[tuple[str, float]]:
        if user not in self._ratings:
            return []
        user_ratings = self._ratings[user]
        scores: dict[str, float] = defaultdict(float)
        sims: dict[str, float] = defaultdict(float)
        for other, other_ratings in self._ratings.items():
            if other == user:
                continue
            common = set(user_ratings) & set(other_ratings)
            if not common:
                continue
            sim = sum(user_ratings[i] * other_ratings[i] for i in common)
            for item, rating in other_ratings.items():
                if item not in user_ratings:
                    scores[item] += sim * rating
                    sims[item] += abs(sim)
        ranked = [(item, scores[item] / sims[item]) for item in scores if sims[item] > 0]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:n]
