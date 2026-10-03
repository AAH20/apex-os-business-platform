"""Deepened capacity planning: forecasting, optimization, cost, performance, scalability."""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ── 1. Resource Forecasting with ML ──────────────────────────────────────────

@dataclass
class ForecastResult:
    predictions: List[float]
    confidence_intervals: List[Tuple[float, float]]
    trend: str
    mape: float


class ResourceForecaster:
    """ML-inspired forecasting using exponential smoothing + trend detection."""

    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        self.alpha = alpha  # level smoothing
        self.beta = beta    # trend smoothing

    def fit_predict(self, history: List[float], horizon: int = 7) -> ForecastResult:
        if len(history) < 3:
            return ForecastResult(
                predictions=[statistics.mean(history)] * horizon if history else [0.0] * horizon,
                confidence_intervals=[(0.0, 0.0)] * horizon,
                trend="insufficient_data", mape=0.0,
            )
        level = history[0]
        trend_val = history[1] - history[0]
        for val in history[1:]:
            prev_level = level
            level = self.alpha * val + (1 - self.alpha) * (level + trend_val)
            trend_val = self.beta * (level - prev_level) + (1 - self.beta) * trend_val
        predictions = [level + (i + 1) * trend_val for i in range(horizon)]
        residuals = [abs(history[i] - (level + i * trend_val)) for i in range(len(history))]
        mape = (sum(residuals) / len(residuals)) / (statistics.mean(history) or 1) * 100
        stdev = statistics.stdev(history) if len(history) > 1 else 0
        ci = [(p - 1.96 * stdev, p + 1.96 * stdev) for p in predictions]
        trend_dir = "increasing" if trend_val > 0.01 else "decreasing" if trend_val < -0.01 else "stable"
        return ForecastResult(predictions, ci, trend_dir, mape)


# ── 2. Capacity Optimization with Right-Sizing ───────────────────────────────

@dataclass
class ResourceProfile:
    cpu_cores: float
    memory_gb: float
    cost_per_hour: float


@dataclass
class RightSizeRecommendation:
    current: ResourceProfile
    recommended: ResourceProfile
    savings_pct: float
    reason: str


class CapacityOptimizer:
    """Right-sizes resource allocations based on utilization percentiles."""

    def __init__(self, target_utilization: float = 0.70, headroom: float = 0.20):
        self.target = target_utilization
        self.headroom = headroom

    def right_size(self, cpu_usage: List[float], mem_usage: List[float],
                   current: ResourceProfile) -> RightSizeRecommendation:
        if not cpu_usage or not mem_usage:
            return RightSizeRecommendation(current, current, 0.0, "no_data")
        cpu_p95 = self._percentile(cpu_usage, 95)
        mem_p95 = self._percentile(mem_usage, 95)
        cpu_factor = max(0.25, min(2.0, cpu_p95 / self.target))
        mem_factor = max(0.25, min(2.0, mem_p95 / self.target))
        rec_cpu = round(current.cpu_cores * cpu_factor, 1)
        rec_mem = round(current.memory_gb * mem_factor, 1)
        rec_cost = current.cost_per_hour * max(cpu_factor, mem_factor)
        recommended = ResourceProfile(rec_cpu, rec_mem, rec_cost)
        savings = (1 - rec_cost / current.cost_per_hour) * 100 if current.cost_per_hour else 0
        reason = f"cpu_p95={cpu_p95:.1f}%, mem_p95={mem_p95:.1f}%, target={self.target:.0%}"
        return RightSizeRecommendation(current, recommended, savings, reason)

    @staticmethod
    def _percentile(data: List[float], pct: float) -> float:
        s = sorted(data)
        idx = int(len(s) * pct / 100)
        return s[min(idx, len(s) - 1)]


# ── 3. Cost Optimization with Reserved Instances ─────────────────────────────

@dataclass
class InstancePlan:
    name: str
    on_demand_rate: float
    reserved_rate: float
    break_even_months: float
    savings_pct: float


@dataclass
class CostRecommendation:
    plans: List[InstancePlan]
    total_on_demand: float
    total_reserved: float
    monthly_savings: float


class CostOptimizer:
    """Recommends reserved instance purchases to minimize cloud spend."""

    def __init__(self, commitment_discount: float = 0.40, min_commitment: int = 12):
        self.discount = commitment_discount
        self.min_commitment = min_commitment

    def optimize(self, workloads: Dict[str, Dict]) -> CostRecommendation:
        plans = []
        total_od = 0.0
        total_rs = 0.0
        for name, wl in workloads.items():
            od_rate = wl.get("on_demand_rate", 0.05)
            rs_rate = od_rate * (1 - self.discount)
            hours = wl.get("steady_state_hours", 24)
            utilization = wl.get("utilization", 0.8)
            monthly_od = od_rate * hours * 30
            monthly_rs = rs_rate * hours * 30
            break_even = self.min_commitment if utilization > 0.6 else float("inf")
            savings = (1 - rs_rate / od_rate) * 100 if od_rate else 0
            plans.append(InstancePlan(name, od_rate, rs_rate, break_even, savings))
            total_od += monthly_od
            total_rs += monthly_rs
        monthly_savings = total_od - total_rs
        return CostRecommendation(plans, total_od, total_rs, monthly_savings)


# ── 4. Performance Modeling with Queuing Theory ───────────────────────────────

@dataclass
class QueueMetrics:
    utilization: float
    avg_queue_length: float
    avg_wait_time: float
    avg_response_time: float
    probability_of_wait: float


class PerformanceModel:
    """M/M/c queuing model for capacity-driven latency prediction."""

    def __init__(self, num_servers: int = 1):
        self.c = num_servers

    def analyze(self, arrival_rate: float, service_rate: float) -> QueueMetrics:
        if arrival_rate <= 0 or service_rate <= 0:
            return QueueMetrics(0, 0, 0, 0, 0)
        rho = arrival_rate / (self.c * service_rate)
        if rho >= 1.0:
            return QueueMetrics(rho, float("inf"), float("inf"), float("inf"), 1.0)
        p0 = self._p0(arrival_rate, service_rate)
        lq = (p0 * (arrival_rate / service_rate) ** self.c * rho) / (
            math.factorial(self.c) * (1 - rho) ** 2
        )
        wq = lq / arrival_rate
        w = wq + 1 / service_rate
        p_wait = (p0 * (arrival_rate / service_rate) ** self.c) / (
            math.factorial(self.c) * (1 - rho)
        )
        return QueueMetrics(rho, lq, wq, w, p_wait)

    def _p0(self, lam: float, mu: float) -> float:
        r = lam / mu
        s = sum(r ** k / math.factorial(k) for k in range(self.c))
        last = (r ** self.c / math.factorial(self.c)) * (1 / (1 - r / self.c))
        return 1.0 / (s + last)

    def required_servers(self, lam: float, mu: float, max_util: float = 0.8) -> int:
        return max(1, math.ceil(lam / (mu * max_util)))


# ── 5. Scalability Testing with Load Testing ─────────────────────────────────

@dataclass
class LoadTestResult:
    concurrent_users: int
    throughput_rps: float
    p95_latency_ms: float
    error_rate: float
    passed: bool


@dataclass
class ScalabilityReport:
    results: List[LoadTestResult]
    max_sustainable_users: int
    bottleneck: str
    recommendation: str


class ScalabilityTester:
    """Simulates load tests and identifies scalability bottlenecks."""

    def __init__(self, target_p95_ms: float = 500, target_error_rate: float = 0.01):
        self.target_p95 = target_p95_ms
        self.target_error = target_error_rate

    def run_load_test(self, max_users: int = 1000, step: int = 100) -> ScalabilityReport:
        results = []
        for users in range(step, max_users + 1, step):
            result = self._simulate(users)
            results.append(result)
        max_sust = max((r.concurrent_users for r in results if r.passed), default=0)
        failed = [r for r in results if not r.passed]
        if failed:
            first_fail = failed[0]
            bottleneck = "latency" if first_fail.p95_latency_ms > self.target_p95 else "errors"
            recommendation = (
                f"Scale horizontally before {first_fail.concurrent_users} users; "
                f"bottleneck: {bottleneck}"
            )
        else:
            bottleneck = "none"
            recommendation = f"System scales to {max_users} users within SLO"
        return ScalabilityReport(results, max_sust, bottleneck, recommendation)

    def _simulate(self, users: int) -> LoadTestResult:
        throughput = users * random.uniform(0.8, 1.2)
        base_latency = 50 + users * 0.3
        p95 = base_latency * random.uniform(1.0, 1.5)
        error_rate = max(0, (users - 500) / 5000) if users > 500 else 0.0
        passed = p95 <= self.target_p95 and error_rate <= self.target_error
        return LoadTestResult(users, round(throughput, 1), round(p95, 1),
                              round(error_rate, 4), passed)


# ── Unified Capacity Planner ─────────────────────────────────────────────────

class CapacityPlanner:
    """Orchestrates forecasting, optimization, cost, performance, and scalability."""

    def __init__(self):
        self.forecaster = ResourceForecaster()
        self.optimizer = CapacityOptimizer()
        self.cost_optimizer = CostOptimizer()
        self.performance_model = PerformanceModel()
        self.scalability_tester = ScalabilityTester()

    def full_analysis(self, cpu_history: List[float], mem_history: List[float],
                      current_profile: ResourceProfile, workloads: Dict,
                      arrival_rate: float, service_rate: float) -> Dict:
        forecast = self.forecaster.fit_predict(cpu_history)
        rightsizing = self.optimizer.right_size(cpu_history, mem_history, current_profile)
        cost = self.cost_optimizer.optimize(workloads)
        perf = self.performance_model.analyze(arrival_rate, service_rate)
        servers_needed = self.performance_model.required_servers(arrival_rate, service_rate)
        scalability = self.scalability_tester.run_load_test()
        return {
            "forecast": {
                "next_7d_cpu": [round(p, 2) for p in forecast.predictions],
                "trend": forecast.trend,
                "mape": round(forecast.mape, 2),
            },
            "rightsizing": {
                "current_cpu": rightsizing.current.cpu_cores,
                "recommended_cpu": rightsizing.recommended.cpu_cores,
                "savings_pct": round(rightsizing.savings_pct, 1),
                "reason": rightsizing.reason,
            },
            "cost": {
                "monthly_on_demand": round(cost.total_on_demand, 2),
                "monthly_reserved": round(cost.total_reserved, 2),
                "monthly_savings": round(cost.monthly_savings, 2),
            },
            "performance": {
                "utilization": round(perf.utilization, 3),
                "avg_response_time_s": round(perf.avg_response_time, 4),
                "servers_needed": servers_needed,
            },
            "scalability": {
                "max_sustainable_users": scalability.max_sustainable_users,
                "bottleneck": scalability.bottleneck,
                "recommendation": scalability.recommendation,
            },
        }
