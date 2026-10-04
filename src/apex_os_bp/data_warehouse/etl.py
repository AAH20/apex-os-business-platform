"""ETL Pipeline module for data warehouse.

Provides Extract, Transform, Load pipeline infrastructure with
stage-based processing, error handling, and result tracking.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ETLError(Exception):
    """Base exception for ETL operations."""

    def __init__(self, message: str, stage: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.stage = stage
        self.details = details or {}


class ETLStage(Enum):
    """Enumeration of ETL pipeline stages."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"
    VALIDATE = "validate"


@dataclass
class ETLResult:
    """Result of an ETL pipeline execution."""

    success: bool
    stage: ETLStage
    records_processed: int = 0
    records_failed: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def merge(self, other: ETLResult) -> ETLResult:
        """Merge another ETLResult into this one."""
        return ETLResult(
            success=self.success and other.success,
            stage=other.stage,
            records_processed=self.records_processed + other.records_processed,
            records_failed=self.records_failed + other.records_failed,
            errors=self.errors + other.errors,
            metadata={**self.metadata, **other.metadata},
            duration_ms=self.duration_ms + other.duration_ms,
        )


class PipelineStage(ABC, Generic[T]):
    """Abstract base class for pipeline stages."""

    def __init__(self, name: str):
        self.name = name
        self._next: Optional[PipelineStage] = None

    def set_next(self, stage: PipelineStage) -> PipelineStage:
        """Set the next stage in the pipeline."""
        self._next = stage
        return stage

    def execute(self, data: T) -> ETLResult:
        """Execute this stage and pass result to next."""
        result = self._process(data)
        if self._next and result.success:
            next_result = self._next.execute(data)
            result = result.merge(next_result)
        return result

    @abstractmethod
    def _process(self, data: T) -> ETLResult:
        """Process the data. Must be implemented by subclasses."""


class ExtractStage(PipelineStage[Dict[str, Any]]):
    """Extract stage - pulls data from source."""

    def __init__(self, name: str, extractor: Callable[[], List[Dict[str, Any]]]):
        super().__init__(name)
        self.extractor = extractor

    def _process(self, data: Dict[str, Any]) -> ETLResult:
        try:
            records = self.extractor()
            return ETLResult(
                success=True,
                stage=ETLStage.EXTRACT,
                records_processed=len(records),
                metadata={"source": self.name, "records": records},
            )
        except Exception as e:
            logger.error(f"Extract failed: {e}")
            return ETLResult(
                success=False,
                stage=ETLStage.EXTRACT,
                errors=[str(e)],
                metadata={"source": self.name},
            )


class TransformStage(PipelineStage[List[Dict[str, Any]]]):
    """Transform stage - applies transformations to data."""

    def __init__(self, name: str, transformer: Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]):
        super().__init__(name)
        self.transformer = transformer

    def _process(self, data: List[Dict[str, Any]]) -> ETLResult:
        try:
            transformed = self.transformer(data)
            return ETLResult(
                success=True,
                stage=ETLStage.TRANSFORM,
                records_processed=len(transformed),
                metadata={"transformer": self.name},
            )
        except Exception as e:
            logger.error(f"Transform failed: {e}")
            return ETLResult(
                success=False,
                stage=ETLStage.TRANSFORM,
                errors=[str(e)],
                metadata={"transformer": self.name},
            )


class LoadStage(PipelineStage[List[Dict[str, Any]]]):
    """Load stage - loads data into destination."""

    def __init__(self, name: str, loader: Callable[[List[Dict[str, Any]]], int]):
        super().__init__(name)
        self.loader = loader

    def _process(self, data: List[Dict[str, Any]]) -> ETLResult:
        try:
            count = self.loader(data)
            return ETLResult(
                success=True,
                stage=ETLStage.LOAD,
                records_processed=count,
                metadata={"destination": self.name},
            )
        except Exception as e:
            logger.error(f"Load failed: {e}")
            return ETLResult(
                success=False,
                stage=ETLStage.LOAD,
                errors=[str(e)],
                metadata={"destination": self.name},
            )


class ValidateStage(PipelineStage[List[Dict[str, Any]]]):
    """Validate stage - validates data quality before loading."""

    def __init__(self, name: str, validator: Callable[[List[Dict[str, Any]]], tuple[bool, List[str]]]):
        super().__init__(name)
        self.validator = validator

    def _process(self, data: List[Dict[str, Any]]) -> ETLResult:
        is_valid, errors = self.validator(data)
        return ETLResult(
            success=is_valid,
            stage=ETLStage.VALIDATE,
            records_processed=len(data) if is_valid else 0,
            records_failed=len(data) if not is_valid else 0,
            errors=errors,
            metadata={"validator": self.name},
        )


class ETLPipeline:
    """Orchestrates ETL pipeline execution."""

    def __init__(self, name: str):
        self.name = name
        self._stages: List[PipelineStage] = []
        self._results: List[ETLResult] = []

    def add_stage(self, stage: PipelineStage) -> ETLPipeline:
        """Add a stage to the pipeline."""
        self._stages.append(stage)
        return self

    def execute(self, initial_data: Optional[Dict[str, Any]] = None) -> List[ETLResult]:
        """Execute the full pipeline."""
        if not self._stages:
            raise ETLError("No stages defined in pipeline")

        self._results = []
        data = initial_data or {}

        for stage in self._stages:
            result = stage.execute(data)
            self._results.append(result)
            if not result.success:
                break

        return self._results

    @property
    def results(self) -> List[ETLResult]:
        """Get the results of the last execution."""
        return self._results

    @property
    def success(self) -> bool:
        """Check if the last execution was successful."""
        return all(r.success for r in self._results) if self._results else False

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the last execution."""
        return {
            "pipeline": self.name,
            "success": self.success,
            "stages_executed": len(self._results),
            "total_records_processed": sum(r.records_processed for r in self._results),
            "total_records_failed": sum(r.records_failed for r in self._results),
            "total_errors": sum(len(r.errors) for r in self._results),
            "total_duration_ms": sum(r.duration_ms for r in self._results),
        }
