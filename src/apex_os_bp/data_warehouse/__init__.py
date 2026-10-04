"""Data Warehouse System for APEX-OS Business Platform.

Provides ETL pipelines, data modeling, data quality, data governance,
and data catalog capabilities.
"""

from .etl import ETLPipeline, ETLStage, ETLResult, ETLError, ExtractStage, TransformStage, LoadStage, ValidateStage
from .modeling import (
    StarSchema,
    Dimension,
    FactTable,
    Column,
    DataType,
    Relationship,
)
from .quality import (
    DataQualityEngine,
    QualityRule,
    QualityCheckResult,
    QualityReport,
    RuleType,
)
from .governance import (
    DataGovernance,
    GovernancePolicy,
    DataLineage,
    AccessLevel,
    SensitivityLevel,
    AuditEvent,
)
from .catalog import (
    DataCatalog,
    CatalogEntry,
    CatalogTag,
    SearchResult,
    AssetType,
    AssetStatus,
)

__all__ = [
    "ETLPipeline",
    "ETLStage",
    "ETLResult",
    "ETLError",
    "ExtractStage",
    "TransformStage",
    "LoadStage",
    "ValidateStage",
    "StarSchema",
    "Dimension",
    "FactTable",
    "Column",
    "DataType",
    "Relationship",
    "DataQualityEngine",
    "QualityRule",
    "QualityCheckResult",
    "QualityReport",
    "RuleType",
    "DataGovernance",
    "GovernancePolicy",
    "DataLineage",
    "AccessLevel",
    "SensitivityLevel",
    "AuditEvent",
    "DataCatalog",
    "CatalogEntry",
    "CatalogTag",
    "SearchResult",
    "AssetType",
    "AssetStatus",
]
