"""Self-Reflection Module.

Provides self-evaluation, outcome analysis, learning from mistakes,
and improvement suggestion generation.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReflectionLevel(str, Enum):
    """Depth of reflection."""

    SURFACE = "surface"       # Quick assessment
    DETAILED = "detailed"     # Thorough analysis
    DEEP = "deep"             # Introspective with pattern detection


@dataclass
class ReflectionResult:
    """Result of a reflection cycle."""

    reflection_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    level: ReflectionLevel = ReflectionLevel.SURFACE
    score: float = 0.0
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_assessment(self) -> str:
        if self.score >= 0.8:
            return "excellent"
        if self.score >= 0.6:
            return "good"
        if self.score >= 0.4:
            return "fair"
        return "poor"


@dataclass
class Experience:
    """A recorded experience for reflection."""

    task: str
    outcome: str
    success: bool
    score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    experience_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=list)
    feedback: str = ""


class ReflectionEngine:
    """Engine for self-reflection and continuous improvement.

    Analyzes past experiences, identifies patterns,
    and generates improvement suggestions.
    """

    def __init__(self, max_experiences: int = 1000) -> None:
        self._experiences: list[Experience] = []
        self._reflections: list[ReflectionResult] = []
        self._max_experiences = max_experiences
        self._lessons: list[str] = []

    def record_experience(
        self,
        task: str,
        outcome: str,
        success: bool,
        score: float = 0.0,
        feedback: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Experience:
        """Record an experience for future reflection."""
        exp = Experience(
            task=task,
            outcome=outcome,
            success=success,
            score=max(0.0, min(1.0, score)),
            feedback=feedback,
            metadata=metadata or {},
        )
        self._experiences.append(exp)
        if len(self._experiences) > self._max_experiences:
            self._experiences.pop(0)
        return exp

    def reflect(
        self,
        level: ReflectionLevel = ReflectionLevel.SURFACE,
        task_filter: str | None = None,
    ) -> ReflectionResult:
        """Perform self-reflection on recorded experiences."""
        pool = self._experiences
        if task_filter:
            pool = [e for e in pool if task_filter.lower() in e.task.lower()]

        if not pool:
            return ReflectionResult(
                level=level,
                score=0.0,
                summary="No experiences to reflect upon.",
            )

        successes = [e for e in pool if e.success]
        failures = [e for e in pool if not e.success]
        avg_score = sum(e.score for e in pool) / len(pool)

        strengths = self._identify_strengths(successes)
        weaknesses = self._identify_weaknesses(failures)
        improvements = self._generate_improvements(strengths, weaknesses, level)
        lessons = self._extract_lessons(failures)

        for lesson in lessons:
            if lesson not in self._lessons:
                self._lessons.append(lesson)

        result = ReflectionResult(
            level=level,
            score=avg_score,
            summary=self._generate_summary(pool, successes, failures, avg_score),
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
            lessons_learned=lessons,
            metadata={
                "total_experiences": len(pool),
                "success_count": len(successes),
                "failure_count": len(failures),
                "success_rate": len(successes) / len(pool),
            },
        )
        self._reflections.append(result)
        return result

    def get_reflection_history(self) -> list[ReflectionResult]:
        return list(self._reflections)

    def get_lessons_learned(self) -> list[str]:
        return list(self._lessons)

    def get_experience_stats(self) -> dict[str, Any]:
        if not self._experiences:
            return {"total": 0, "success_rate": 0.0, "avg_score": 0.0}
        successes = sum(1 for e in self._experiences if e.success)
        return {
            "total": len(self._experiences),
            "success_rate": successes / len(self._experiences),
            "avg_score": sum(e.score for e in self._experiences) / len(self._experiences),
            "successes": successes,
            "failures": len(self._experiences) - successes,
        }

    def detect_patterns(self) -> list[dict[str, Any]]:
        """Detect recurring patterns in experiences."""
        if len(self._experiences) < 3:
            return []

        patterns: list[dict[str, Any]] = []

        # Detect consecutive failures
        consecutive_failures = 0
        max_consecutive = 0
        for exp in self._experiences:
            if not exp.success:
                consecutive_failures += 1
                max_consecutive = max(max_consecutive, consecutive_failures)
            else:
                consecutive_failures = 0

        if max_consecutive >= 3:
            patterns.append({
                "type": "consecutive_failures",
                "count": max_consecutive,
                "description": f"Detected {max_consecutive} consecutive failures",
            })

        # Detect declining performance
        if len(self._experiences) >= 5:
            recent = self._experiences[-5:]
            older = self._experiences[-10:-5] if len(self._experiences) >= 10 else self._experiences[:5]
            recent_avg = sum(e.score for e in recent) / len(recent)
            older_avg = sum(e.score for e in older) / len(older)
            if recent_avg < older_avg - 0.2:
                patterns.append({
                    "type": "declining_performance",
                    "description": f"Performance declined from {older_avg:.2f} to {recent_avg:.2f}",
                })

        return patterns

    def clear(self) -> None:
        self._experiences.clear()
        self._reflections.clear()
        self._lessons.clear()

    def _identify_strengths(self, successes: list[Experience]) -> list[str]:
        if not successes:
            return []
        strengths = []
        task_types: dict[str, int] = {}
        for exp in successes:
            key = exp.task.split()[0] if exp.task else "unknown"
            task_types[key] = task_types.get(key, 0) + 1
        for task_type, count in sorted(task_types.items(), key=lambda x: -x[1])[:3]:
            if count >= 2:
                strengths.append(f"Consistent success in '{task_type}' tasks ({count} times)")
        return strengths

    def _identify_weaknesses(self, failures: list[Experience]) -> list[str]:
        if not failures:
            return []
        weaknesses = []
        task_types: dict[str, int] = {}
        for exp in failures:
            key = exp.task.split()[0] if exp.task else "unknown"
            task_types[key] = task_types.get(key, 0) + 1
        for task_type, count in sorted(task_types.items(), key=lambda x: -x[1])[:3]:
            if count >= 2:
                weaknesses.append(f"Recurring failures in '{task_type}' tasks ({count} times)")
        return weaknesses

    def _generate_improvements(
        self,
        strengths: list[str],
        weaknesses: list[str],
        level: ReflectionLevel,
    ) -> list[str]:
        improvements = []
        for w in weaknesses:
            improvements.append(f"Address weakness: {w}")
        if level in (ReflectionLevel.DETAILED, ReflectionLevel.DEEP):
            improvements.append("Increase task decomposition granularity")
            improvements.append("Add more verification steps in planning")
        if level == ReflectionLevel.DEEP:
            improvements.append("Implement cross-task learning transfer")
            improvements.append("Build domain-specific heuristics")
        return improvements

    def _extract_lessons(self, failures: list[Experience]) -> list[str]:
        lessons = []
        for exp in failures[-5:]:
            if exp.feedback:
                lessons.append(f"From '{exp.task}': {exp.feedback}")
            else:
                lessons.append(f"Task '{exp.task}' failed — review approach")
        return lessons

    def _generate_summary(
        self,
        pool: list[Experience],
        successes: list[Experience],
        failures: list[Experience],
        avg_score: float,
    ) -> str:
        total = len(pool)
        rate = len(successes) / total if total else 0
        return (
            f"Reflected on {total} experiences: "
            f"{len(successes)} succeeded, {len(failures)} failed "
            f"(success rate: {rate:.0%}, avg score: {avg_score:.2f})"
        )
