"""Deepened analytics: cohorts, funnels, forecasting, anomalies, correlations."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from statsmodels.tsa.arima.model import ARIMA


# ---------------------------------------------------------------------------
# 1. Cohort Analysis & Retention Tracking
# ---------------------------------------------------------------------------

@dataclass
class CohortResult:
    cohorts: pd.DataFrame
    retention_matrix: pd.DataFrame
    avg_retention: pd.Series


def cohort_analysis(
    df: pd.DataFrame,
    user_col: str = "user_id",
    date_col: str = "event_date",
    periods: int = 12,
) -> CohortResult:
    """Build cohort retention table from user activity events.

    Each user is assigned to a cohort by their first active period (month).
    Retention is the fraction of each cohort active in subsequent periods.
    """
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["period"] = df[date_col].dt.to_period("M")

    first = df.groupby(user_col)["period"].min().rename("cohort")
    df = df.join(first, on=user_col)

    df["periods_since"] = (df["period"] - df["cohort"]).apply(lambda x: x.n)

    active = (
        df.groupby(["cohort", "periods_since"])[user_col]
        .nunique()
        .reset_index()
    )
    sizes = df.groupby("cohort")[user_col].nunique().rename("cohort_size")
    active = active.join(sizes, on="cohort")
    active["retention"] = active[user_col] / active["cohort_size"]

    matrix = active.pivot_table(
        index="cohort", columns="periods_since", values="retention"
    ).iloc[:, : periods + 1]

    avg = matrix.mean(axis=0)
    return CohortResult(cohorts=sizes.to_frame(), retention_matrix=matrix, avg_retention=avg)


# ---------------------------------------------------------------------------
# 2. Funnel Analysis & Conversion Rates
# ---------------------------------------------------------------------------

@dataclass
class FunnelResult:
    steps: pd.DataFrame
    overall_conversion: float
    step_conversion: pd.Series


def funnel_analysis(
    events: pd.DataFrame,
    user_col: str = "user_id",
    event_col: str = "event_name",
    steps: list[str] | None = None,
) -> FunnelResult:
    """Compute per-step and overall conversion through a funnel.

    Steps must be ordered from top to bottom. Each user counts once per step.
    """
    if steps is None:
        steps = events[event_col].value_counts().index.tolist()

    counts = []
    for step in steps:
        n = events.loc[events[event_col] == step, user_col].nunique()
        counts.append(n)

    step_df = pd.DataFrame({"step": steps, "users": counts})
    step_df["pct_of_top"] = step_df["users"] / step_df["users"].iloc[0]
    step_df["step_conversion"] = step_df["users"] / step_df["users"].shift(1)

    overall = step_df["users"].iloc[-1] / step_df["users"].iloc[0]
    return FunnelResult(
        steps=step_df,
        overall_conversion=overall,
        step_conversion=step_df["step_conversion"].dropna(),
    )


# ---------------------------------------------------------------------------
# 3. Time-Series Forecasting (ARIMA)
# ---------------------------------------------------------------------------

@dataclass
class ForecastResult:
    forecast: np.ndarray
    conf_int: np.ndarray
    model_fit: Any


def arima_forecast(
    series: pd.Series,
    order: tuple[int, int, int] = (1, 1, 1),
    steps: int = 7,
) -> ForecastResult:
    """Forecast future values of a time series using ARIMA.

    Automatically falls back to a naive mean forecast if ARIMA fails.
    """
    series = pd.Series(series).dropna()
    if len(series) < 5:
        mean_val = series.mean() if len(series) else 0.0
        return ForecastResult(
            forecast=np.full(steps, mean_val),
            conf_int=np.column_stack([np.full(steps, mean_val), np.full(steps, mean_val)]),
            model_fit=None,
        )

    try:
        model = ARIMA(series, order=order)
        fit = model.fit()
        pred = fit.get_forecast(steps=steps)
        return ForecastResult(
            forecast=pred.predicted_mean.values,
            conf_int=pred.conf_int().values,
            model_fit=fit,
        )
    except Exception:
        last = series.iloc[-1]
        return ForecastResult(
            forecast=np.full(steps, last),
            conf_int=np.column_stack([np.full(steps, last), np.full(steps, last)]),
            model_fit=None,
        )


# ---------------------------------------------------------------------------
# 4. Anomaly Detection (Isolation Forest)
# ---------------------------------------------------------------------------

@dataclass
class AnomalyResult:
    labels: np.ndarray
    scores: np.ndarray
    anomalies: pd.DataFrame


def detect_anomalies(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    contamination: float = 0.05,
    random_state: int = 42,
) -> AnomalyResult:
    """Detect anomalies using Isolation Forest.

    Returns -1 for anomalies, 1 for normal points, plus anomaly scores.
    """
    if feature_cols is None:
        feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    X = df[feature_cols].dropna()
    clf = IsolationForest(
        contamination=contamination, random_state=random_state
    )
    labels = clf.fit_predict(X)
    scores = clf.score_samples(X)

    result_df = X.copy()
    result_df["_label"] = labels
    result_df["_score"] = scores
    anomalies = result_df[result_df["_label"] == -1]

    return AnomalyResult(labels=labels, scores=scores, anomalies=anomalies)


# ---------------------------------------------------------------------------
# 5. Correlation Analysis (Pearson & Spearman)
# ---------------------------------------------------------------------------

@dataclass
class CorrelationResult:
    pearson: pd.DataFrame
    spearman: pd.DataFrame
    strongest_pairs: pd.DataFrame


def correlation_analysis(
    df: pd.DataFrame,
    method: str = "both",
    threshold: float = 0.0,
) -> CorrelationResult:
    """Compute Pearson and/or Spearman correlation matrices.

    Returns sorted strongest absolute-correlation pairs above threshold.
    """
    numeric = df.select_dtypes(include=[np.number])
    pearson = numeric.corr(method="pearson") if method in ("both", "pearson") else None
    spearman = numeric.corr(method="spearman") if method in ("both", "spearman") else None

    pairs: list[dict[str, Any]] = []
    matrices = {"pearson": pearson, "spearman": spearman}
    for name, mat in matrices.items():
        if mat is None:
            continue
        for i, row in enumerate(mat.index):
            for j, col in enumerate(mat.columns):
                if j <= i:
                    continue
                val = mat.iloc[i, j]
                if abs(val) >= threshold:
                    pairs.append(
                        {"var1": row, "var2": col, "method": name, "corr": val}
                    )

    pairs_df = (
        pd.DataFrame(pairs)
        .sort_values("corr", key=np.abs, ascending=False)
        .reset_index(drop=True)
        if pairs
        else pd.DataFrame(columns=["var1", "var2", "method", "corr"])
    )

    return CorrelationResult(
        pearson=pearson if pearson is not None else pd.DataFrame(),
        spearman=spearman if spearman is not None else pd.DataFrame(),
        strongest_pairs=pairs_df,
    )
