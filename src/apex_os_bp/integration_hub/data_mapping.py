"""Data Mapping — transform data between different schemas and formats."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Union


class MappingType(str, Enum):
    DIRECT = "direct"
    RENAME = "rename"
    TRANSFORM = "transform"
    CONSTANT = "constant"
    CONDITIONAL = "conditional"
    NESTED = "nested"
    COLLECTION = "collection"


class MappingDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class FieldMapping:
    source_path: str
    target_path: str
    mapping_type: MappingType = MappingType.DIRECT
    transform: Optional[Callable[[Any], Any]] = None
    default: Any = None
    required: bool = False
    direction: MappingDirection = MappingDirection.BIDIRECTIONAL
    condition: Optional[Callable[[dict], bool]] = None
    nested_mappings: list["FieldMapping"] = field(default_factory=list)
    collection_item_mapping: Optional["FieldMapping"] = None

    def applies_to(self, data: dict, direction: MappingDirection) -> bool:
        if self.direction != MappingDirection.BIDIRECTIONAL and self.direction != direction:
            return False
        if self.condition and not self.condition(data):
            return False
        return True


@dataclass
class MappingResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fields_mapped: int = 0
    fields_skipped: int = 0
    fields_failed: int = 0


class DataMapper:
    """Map data between schemas using configurable field mappings."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._mappings: list[FieldMapping] = []
        self._transforms: dict[str, Callable[[Any], Any]] = {}
        self._register_builtin_transforms()

    def _register_builtin_transforms(self) -> None:
        self._transforms.update({
            "upper": lambda v: str(v).upper() if v is not None else None,
            "lower": lambda v: str(v).lower() if v is not None else None,
            "strip": lambda v: str(v).strip() if v is not None else None,
            "int": lambda v: int(v) if v is not None else None,
            "float": lambda v: float(v) if v is not None else None,
            "str": lambda v: str(v) if v is not None else None,
            "bool": lambda v: bool(v) if v is not None else None,
            "len": lambda v: len(v) if v is not None else None,
            "iso_date": lambda v: v.isoformat() if hasattr(v, "isoformat") else str(v),
            "json_encode": lambda v: json.dumps(v) if v is not None else None,
            "json_decode": lambda v: json.loads(v) if isinstance(v, str) else v,
            "snake_to_camel": lambda v: re.sub(r"_([a-z])", lambda m: m.group(1).upper(), str(v)),
            "camel_to_snake": lambda v: re.sub(r"([A-Z])", lambda m: "_" + m.group(1).lower(), str(v)),
        })

    def add_mapping(self, mapping: FieldMapping) -> None:
        self._mappings.append(mapping)

    def remove_mapping(self, source_path: str, target_path: str) -> None:
        self._mappings = [
            m for m in self._mappings
            if not (m.source_path == source_path and m.target_path == target_path)
        ]

    def register_transform(self, name: str, fn: Callable[[Any], Any]) -> None:
        self._transforms[name] = fn

    def _get_value(self, data: dict, path: str) -> Any:
        """Extract value from nested dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        return current

    def _set_value(self, data: dict, path: str, value: Any) -> None:
        """Set value in nested dict using dot notation."""
        keys = path.split(".")
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _apply_transform(self, value: Any, transform: Union[str, Callable, None]) -> Any:
        if transform is None:
            return value
        if isinstance(transform, str):
            fn = self._transforms.get(transform)
            return fn(value) if fn else value
        return transform(value)

    def map(self, source: dict, direction: MappingDirection = MappingDirection.OUTBOUND) -> MappingResult:
        """Map source data to target schema."""
        result = MappingResult(success=True)
        target: dict[str, Any] = {}

        for mapping in self._mappings:
            if not mapping.applies_to(source, direction):
                result.fields_skipped += 1
                continue

            value = self._get_value(source, mapping.source_path)

            if value is None:
                if mapping.required:
                    result.fields_failed += 1
                    result.errors.append(
                        f"Required field '{mapping.source_path}' is missing"
                    )
                    result.success = False
                    continue
                if mapping.default is not None:
                    value = mapping.default
                else:
                    result.fields_skipped += 1
                    continue

            if mapping.mapping_type == MappingType.CONSTANT:
                value = mapping.default
            elif mapping.mapping_type == MappingType.TRANSFORM and mapping.transform:
                try:
                    value = self._apply_transform(value, mapping.transform)
                except Exception as exc:
                    result.fields_failed += 1
                    result.errors.append(
                        f"Transform failed for '{mapping.source_path}': {exc}"
                    )
                    result.success = False
                    continue
            elif mapping.mapping_type == MappingType.NESTED and mapping.nested_mappings:
                if isinstance(value, dict):
                    nested_result = DataMapper(f"{self.name}_nested")
                    for nm in mapping.nested_mappings:
                        nested_result.add_mapping(nm)
                    nested = nested_result.map(value, direction)
                    value = nested.data
                    if not nested.success:
                        result.errors.extend(nested.errors)
                        result.success = False
            elif mapping.mapping_type == MappingType.COLLECTION and mapping.collection_item_mapping:
                if isinstance(value, list):
                    mapped_items = []
                    for item in value:
                        if isinstance(item, dict):
                            item_mapper = DataMapper(f"{self.name}_item")
                            item_mapper.add_mapping(mapping.collection_item_mapping)
                            item_result = item_mapper.map(item, direction)
                            mapped_items.append(item_result.data)
                        else:
                            mapped_items.append(item)
                    value = mapped_items

            self._set_value(target, mapping.target_path, value)
            result.fields_mapped += 1

        result.data = target
        return result

    def map_many(
        self, sources: list[dict], direction: MappingDirection = MappingDirection.OUTBOUND
    ) -> list[MappingResult]:
        return [self.map(s, direction) for s in sources]

    def reverse_map(self, source: dict) -> MappingResult:
        """Convenience method for inbound mapping."""
        return self.map(source, MappingDirection.INBOUND)

    def validate_schema(self, data: dict, required_fields: list[str]) -> list[str]:
        """Validate that data contains all required fields."""
        missing = []
        for field_path in required_fields:
            if self._get_value(data, field_path) is None:
                missing.append(field_path)
        return missing
