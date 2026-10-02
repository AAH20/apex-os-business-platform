"""Data transformer for APEX-OS Business Platform.

Provides a pipeline-based data transformation engine with support for
field mapping, type conversion, validation, filtering, and custom
transform functions. Enables data integration between different
formats and schemas.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class TransformFieldType(str, Enum):
    """Supported field types for transformation."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    DATE = "date"
    LIST = "list"
    DICT = "dict"
    EMAIL = "email"
    URL = "url"
    UUID = "uuid"
    JSON = "json"


class TransformOperation(str, Enum):
    """Built-in transform operations."""

    RENAME = "rename"
    CONVERT = "convert"
    DEFAULT = "default"
    FILTER = "filter"
    MAP = "map"
    FLATTEN = "flatten"
    NEST = "nest"
    CONCAT = "concat"
    SPLIT = "split"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    TRIM = "trim"
    REGEX_REPLACE = "regex_replace"
    CUSTOM = "custom"


@dataclass
class FieldMapping:
    """Maps a source field to a target field with optional transform."""

    source: str
    target: str
    field_type: TransformFieldType = TransformFieldType.STRING
    required: bool = False
    default: Any = None
    operation: Optional[TransformOperation] = None
    operation_config: Dict[str, Any] = field(default_factory=dict)
    custom_transform: Optional[Callable] = None


@dataclass
class ValidationRule:
    """Validation rule for a field."""

    field: str
    rule_type: str  # "required", "min_length", "max_length", "pattern", "range", "enum", "type"
    value: Any = None
    message: str = ""


@dataclass
class TransformResult:
    """Result of a transformation operation."""

    data: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dropped: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if transformation succeeded."""
        return not self.errors and not self.dropped


class DataTransformer:
    """Pipeline-based data transformer."""

    def __init__(self):
        self._mappings: List[FieldMapping] = []
        self._validators: List[ValidationRule] = []
        self._pre_processors: List[Callable] = []
        self._post_processors: List[Callable] = []
        self._filter_conditions: List[Callable] = []
        self._stats: Dict[str, int] = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "dropped": 0,
        }

    def add_mapping(self, mapping: FieldMapping) -> "DataTransformer":
        """Add a field mapping."""
        self._mappings.append(mapping)
        return self

    def add_validator(self, rule: ValidationRule) -> "DataTransformer":
        """Add a validation rule."""
        self._validators.append(rule)
        return self

    def add_pre_processor(self, processor: Callable) -> "DataTransformer":
        """Add a pre-processing function."""
        self._pre_processors.append(processor)
        return self

    def add_post_processor(self, processor: Callable) -> "DataTransformer":
        """Add a post-processing function."""
        self._post_processors.append(processor)
        return self

    def add_filter(self, condition: Callable) -> "DataTransformer":
        """Add a filter condition. If any returns False, the record is dropped."""
        self._filter_conditions.append(condition)
        return self

    def transform(self, source: Dict[str, Any]) -> TransformResult:
        """Transform a single record."""
        self._stats["processed"] += 1

        # Pre-process
        data = dict(source)
        for processor in self._pre_processors:
            data = processor(data)

        # Filter
        for condition in self._filter_conditions:
            if not condition(data):
                self._stats["dropped"] += 1
                return TransformResult(
                    data={},
                    dropped=True,
                    metadata={"reason": "filtered"},
                )

        # Apply mappings
        result: Dict[str, Any] = {}
        errors: List[str] = []
        warnings: List[str] = []

        for mapping in self._mappings:
            value = self._get_nested(data, mapping.source)

            if value is None:
                if mapping.required:
                    errors.append(f"Required field '{mapping.source}' is missing")
                    continue
                if mapping.default is not None:
                    result[mapping.target] = mapping.default
                continue

            # Apply transform
            try:
                transformed = self._apply_transform(value, mapping)
                self._set_nested(result, mapping.target, transformed)
            except Exception as e:
                if mapping.required:
                    errors.append(f"Transform failed for '{mapping.source}': {e}")
                else:
                    warnings.append(f"Transform failed for '{mapping.source}': {e}")

        # Validate
        for rule in self._validators:
            field_value = self._get_nested(result, rule.field)
            error = self._validate_field(field_value, rule)
            if error:
                errors.append(error)

        # Post-process
        for processor in self._post_processors:
            result = processor(result)

        if errors:
            self._stats["failed"] += 1
        else:
            self._stats["succeeded"] += 1

        return TransformResult(
            data=result,
            errors=errors,
            warnings=warnings,
        )

    def transform_batch(self, sources: List[Dict[str, Any]]) -> List[TransformResult]:
        """Transform a batch of records."""
        return [self.transform(src) for src in sources]

    def _get_nested(self, data: Dict[str, Any], path: str) -> Any:
        """Get a value from a nested dict using dot notation."""
        keys = path.split(".")
        current: Any = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return None
        return current

    def _set_nested(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set a value in a nested dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _apply_transform(self, value: Any, mapping: FieldMapping) -> Any:
        """Apply transformation to a value."""
        if mapping.custom_transform:
            return mapping.custom_transform(value)

        op = mapping.operation
        if op is None:
            return self._convert_type(value, mapping.field_type)

        config = mapping.operation_config

        if op == TransformOperation.RENAME:
            return value

        if op == TransformOperation.CONVERT:
            return self._convert_type(value, mapping.field_type)

        if op == TransformOperation.UPPERCASE:
            return str(value).upper()

        if op == TransformOperation.LOWERCASE:
            return str(value).lower()

        if op == TransformOperation.TRIM:
            return str(value).strip()

        if op == TransformOperation.CONCAT:
            separator = config.get("separator", " ")
            parts = config.get("fields", [])
            values = [str(self._get_nested({"_v": value}, "_v"))]
            return separator.join(values)

        if op == TransformOperation.SPLIT:
            separator = config.get("separator", ",")
            return str(value).split(separator)

        if op == TransformOperation.REGEX_REPLACE:
            pattern = config.get("pattern", "")
            replacement = config.get("replacement", "")
            return re.sub(pattern, replacement, str(value))

        if op == TransformOperation.MAP:
            mapping_dict = config.get("mapping", {})
            return mapping_dict.get(value, value)

        if op == TransformOperation.FLATTEN:
            if isinstance(value, dict):
                return {
                    f"{config.get('prefix', '')}{k}": v
                    for k, v in value.items()
                }
            return value

        if op == TransformOperation.NEST:
            target_path = config.get("path", "")
            if target_path:
                nested: Dict[str, Any] = {}
                current = nested
                keys = target_path.split(".")
                for key in keys[:-1]:
                    current[key] = {}
                    current = current[key]
                current[keys[-1]] = value
                return nested
            return value

        if op == TransformOperation.DEFAULT:
            if value is None or value == "":
                return config.get("value")
            return value

        return value

    def _convert_type(self, value: Any, field_type: TransformFieldType) -> Any:
        """Convert a value to the target type."""
        if value is None:
            return None

        if field_type == TransformFieldType.STRING:
            return str(value)
        if field_type == TransformFieldType.INTEGER:
            return int(value)
        if field_type == TransformFieldType.FLOAT:
            return float(value)
        if field_type == TransformFieldType.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        if field_type == TransformFieldType.LIST:
            if isinstance(value, list):
                return value
            return [value]
        if field_type == TransformFieldType.DICT:
            if isinstance(value, dict):
                return value
            return {"value": value}
        if field_type == TransformFieldType.JSON:
            import json

            if isinstance(value, str):
                return json.loads(value)
            return json.loads(json.dumps(value))
        if field_type == TransformFieldType.EMAIL:
            return str(value).lower().strip()
        if field_type == TransformFieldType.URL:
            return str(value).strip()
        if field_type == TransformFieldType.UUID:
            return str(value)

        return value

    def _validate_field(self, value: Any, rule: ValidationRule) -> Optional[str]:
        """Validate a field value against a rule. Returns error message or None."""
        if rule.rule_type == "required":
            if value is None or value == "":
                return rule.message or f"Field '{rule.field}' is required"
        elif rule.rule_type == "min_length":
            if value is not None and len(str(value)) < int(rule.value):
                return rule.message or f"Field '{rule.field}' is too short"
        elif rule.rule_type == "max_length":
            if value is not None and len(str(value)) > int(rule.value):
                return rule.message or f"Field '{rule.field}' is too long"
        elif rule.rule_type == "pattern":
            if value is not None and not re.match(str(rule.value), str(value)):
                return rule.message or f"Field '{rule.field}' does not match pattern"
        elif rule.rule_type == "range":
            if value is not None:
                min_val, max_val = rule.value
                try:
                    num_val = float(value)
                    if not (min_val <= num_val <= max_val):
                        return rule.message or f"Field '{rule.field}' out of range"
                except (TypeError, ValueError):
                    return rule.message or f"Field '{rule.field}' is not a number"
        elif rule.rule_type == "enum":
            if value is not None and value not in rule.value:
                return rule.message or f"Field '{rule.field}' not in allowed values"
        elif rule.rule_type == "type":
            type_map = {
                "string": str,
                "integer": int,
                "float": float,
                "boolean": bool,
                "list": list,
                "dict": dict,
            }
            expected = type_map.get(rule.value)
            if expected and value is not None and not isinstance(value, expected):
                return rule.message or f"Field '{rule.field}' has wrong type"
        return None

    @property
    def stats(self) -> Dict[str, int]:
        """Get transformation statistics."""
        return dict(self._stats)

    def reset_stats(self) -> None:
        """Reset statistics."""
        self._stats = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "dropped": 0,
        }


class TransformPipeline:
    """Chains multiple transformers into a pipeline."""

    def __init__(self):
        self._stages: List[DataTransformer] = []

    def add_stage(self, transformer: DataTransformer) -> "TransformPipeline":
        """Add a transformation stage."""
        self._stages.append(transformer)
        return self

    def execute(self, source: Dict[str, Any]) -> TransformResult:
        """Execute the pipeline on a record."""
        current = source
        all_errors: List[str] = []
        all_warnings: List[str] = []

        for i, stage in enumerate(self._stages):
            result = stage.transform(current)
            if result.dropped:
                return TransformResult(
                    data={},
                    dropped=True,
                    metadata={"dropped_at_stage": i},
                )
            current = result.data
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        return TransformResult(
            data=current,
            errors=all_errors,
            warnings=all_warnings,
        )

    def execute_batch(self, sources: List[Dict[str, Any]]) -> List[TransformResult]:
        """Execute the pipeline on a batch of records."""
        return [self.execute(src) for src in sources]
