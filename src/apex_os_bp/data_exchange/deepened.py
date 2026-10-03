"""Deepened data exchange: import, export, transform, validate, synchronize."""

from __future__ import annotations

import csv
import io
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

class DataImporter:
    """Import data from CSV, JSON, or XML sources."""

    @staticmethod
    def from_csv(source: Union[str, Path, io.StringIO], delimiter: str = ",") -> List[Dict[str, Any]]:
        if isinstance(source, (str, Path)):
            with open(source, newline="", encoding="utf-8") as fh:
                return list(csv.DictReader(fh, delimiter=delimiter))
        return list(csv.DictReader(source, delimiter=delimiter))

    @staticmethod
    def from_json(source: Union[str, Path, io.StringIO]) -> List[Dict[str, Any]]:
        if isinstance(source, (str, Path)):
            with open(source, encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = json.load(source)
        if isinstance(data, dict):
            return [data]
        return data

    @staticmethod
    def from_xml(source: Union[str, Path], item_tag: str = "item") -> List[Dict[str, Any]]:
        tree = ET.parse(source) if isinstance(source, (str, Path)) else ET.ElementTree(ET.fromstring(source))
        root = tree.getroot()
        records: List[Dict[str, Any]] = []
        for elem in root.findall(f".//{item_tag}"):
            record: Dict[str, Any] = {}
            for child in elem:
                record[child.tag] = child.text or ""
            records.append(record)
        return records

    @classmethod
    def import_data(cls, source: Union[str, Path], fmt: str = "auto", **kwargs: Any) -> List[Dict[str, Any]]:
        if fmt == "auto":
            fmt = Path(source).suffix.lstrip(".").lower() if isinstance(source, (str, Path)) else "json"
        dispatch = {"csv": cls.from_csv, "json": cls.from_json, "xml": cls.from_xml}
        if fmt not in dispatch:
            raise ValueError(f"Unsupported import format: {fmt}")
        return dispatch[fmt](source, **kwargs)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class DataExporter:
    """Export data to CSV, JSON, or XML formats."""

    @staticmethod
    def to_csv(data: List[Dict[str, Any]], destination: Optional[Union[str, Path]] = None) -> str:
        if not data:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)
        output = buf.getvalue()
        if destination:
            Path(destination).write_text(output, encoding="utf-8")
        return output

    @staticmethod
    def to_json(data: List[Dict[str, Any]], destination: Optional[Union[str, Path]] = None, indent: int = 2) -> str:
        output = json.dumps(data, indent=indent, default=str)
        if destination:
            Path(destination).write_text(output, encoding="utf-8")
        return output

    @staticmethod
    def to_xml(data: List[Dict[str, Any]], root_tag: str = "root", item_tag: str = "item",
              destination: Optional[Union[str, Path]] = None) -> str:
        root = ET.Element(root_tag)
        for record in data:
            item = ET.SubElement(root, item_tag)
            for key, value in record.items():
                child = ET.SubElement(item, str(key))
                child.text = str(value) if value is not None else ""
        output = ET.tostring(root, encoding="unicode")
        if destination:
            Path(destination).write_text(output, encoding="utf-8")
        return output

    @classmethod
    def export_data(cls, data: List[Dict[str, Any]], fmt: str = "json",
                    destination: Optional[Union[str, Path]] = None, **kwargs: Any) -> str:
        dispatch = {"csv": cls.to_csv, "json": cls.to_json, "xml": cls.to_xml}
        if fmt not in dispatch:
            raise ValueError(f"Unsupported export format: {fmt}")
        return dispatch[fmt](data, destination=destination, **kwargs)


# ---------------------------------------------------------------------------
# Transformation
# ---------------------------------------------------------------------------

class DataTransformer:
    """Transform data using field mappings, renames, and computed fields."""

    def __init__(self, mapping: Optional[Dict[str, str]] = None,
                 computed: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
                 filters: Optional[List[Callable[[Dict[str, Any]], bool]]] = None):
        self.mapping = mapping or {}
        self.computed = computed or {}
        self.filters = filters or []

    def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for record in data:
            if all(f(record) for f in self.filters):
                new_record: Dict[str, Any] = {}
                for old_key, value in record.items():
                    new_key = self.mapping.get(old_key, old_key)
                    new_record[new_key] = value
                for new_key, fn in self.computed.items():
                    new_record[new_key] = fn(record)
                result.append(new_record)
        return result

    def add_mapping(self, old_key: str, new_key: str) -> "DataTransformer":
        self.mapping[old_key] = new_key
        return self

    def add_computed(self, key: str, fn: Callable[[Dict[str, Any]], Any]) -> "DataTransformer":
        self.computed[key] = fn
        return self

    def add_filter(self, fn: Callable[[Dict[str, Any]], bool]) -> "DataTransformer":
        self.filters.append(fn)
        return self


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation failed with {len(errors)} error(s)")


@dataclass
class FieldSchema:
    name: str
    required: bool = True
    field_type: type = str
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    custom_validator: Optional[Callable[[Any], bool]] = None


class DataValidator:
    """Validate data records against a schema of field definitions."""

    def __init__(self, fields: List[FieldSchema]):
        self.fields = {f.name: f for f in fields}

    def validate(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        errors: List[str] = []
        valid_records: List[Dict[str, Any]] = []
        for idx, record in enumerate(data):
            record_errors = self._validate_record(record, idx)
            if record_errors:
                errors.extend(record_errors)
            else:
                valid_records.append(record)
        if errors:
            raise ValidationError(errors)
        return valid_records

    def _validate_record(self, record: Dict[str, Any], idx: int) -> List[str]:
        errors: List[str] = []
        for name, schema in self.fields.items():
            value = record.get(name)
            if value is None or value == "":
                if schema.required:
                    errors.append(f"Record {idx}: field '{name}' is required")
                continue
            if not isinstance(value, schema.field_type):
                try:
                    value = schema.field_type(value)
                except (ValueError, TypeError):
                    errors.append(f"Record {idx}: field '{name}' must be {schema.field_type.__name__}")
                    continue
            if schema.min_length is not None and len(str(value)) < schema.min_length:
                errors.append(f"Record {idx}: field '{name}' below min_length {schema.min_length}")
            if schema.max_length is not None and len(str(value)) > schema.max_length:
                errors.append(f"Record {idx}: field '{name}' exceeds max_length {schema.max_length}")
            if schema.allowed_values and value not in schema.allowed_values:
                errors.append(f"Record {idx}: field '{name}' value '{value}' not in allowed set")
            if schema.custom_validator and not schema.custom_validator(value):
                errors.append(f"Record {idx}: field '{name}' failed custom validation")
        return errors


# ---------------------------------------------------------------------------
# Synchronization
# ---------------------------------------------------------------------------

class ConflictStrategy(Enum):
    SOURCE_WINS = "source_wins"
    TARGET_WINS = "target_wins"
    TIMESTAMP = "timestamp"
    MANUAL = "manual"


@dataclass
class SyncResult:
    inserted: int = 0
    updated: int = 0
    conflicts: int = 0
    skipped: int = 0
    details: List[str] = field(default_factory=list)


class DataSynchronizer:
    """Synchronize data between source and target with conflict resolution."""

    def __init__(self, key_field: str = "id", strategy: ConflictStrategy = ConflictStrategy.TIMESTAMP,
                 timestamp_field: str = "updated_at"):
        self.key_field = key_field
        self.strategy = strategy
        self.timestamp_field = timestamp_field

    def sync(self, source: List[Dict[str, Any]], target: List[Dict[str, Any]]) -> SyncResult:
        target_map: Dict[Any, Dict[str, Any]] = {r[self.key_field]: r for r in target}
        result = SyncResult()
        for src_record in source:
            key = src_record.get(self.key_field)
            if key not in target_map:
                target_map[key] = src_record
                result.inserted += 1
                result.details.append(f"Inserted record {key}")
            else:
                tgt_record = target_map[key]
                resolution = self._resolve_conflict(src_record, tgt_record)
                if resolution == "source":
                    target_map[key] = src_record
                    result.updated += 1
                    result.details.append(f"Updated record {key} (source wins)")
                elif resolution == "target":
                    result.skipped += 1
                    result.details.append(f"Skipped record {key} (target wins)")
                else:
                    result.conflicts += 1
                    result.details.append(f"Conflict on record {key} (manual resolution needed)")
        return result

    def _resolve_conflict(self, source: Dict[str, Any], target: Dict[str, Any]) -> str:
        if self.strategy == ConflictStrategy.SOURCE_WINS:
            return "source"
        if self.strategy == ConflictStrategy.TARGET_WINS:
            return "target"
        if self.strategy == ConflictStrategy.TIMESTAMP:
            src_ts = source.get(self.timestamp_field, "")
            tgt_ts = target.get(self.timestamp_field, "")
            return "source" if src_ts >= tgt_ts else "target"
        return "conflict"


# ---------------------------------------------------------------------------
# Convenience pipeline
# ---------------------------------------------------------------------------

def run_pipeline(source: Union[str, Path], source_fmt: str = "auto",
                 mapping: Optional[Dict[str, str]] = None,
                 schema: Optional[List[FieldSchema]] = None,
                 export_fmt: str = "json",
                 destination: Optional[Union[str, Path]] = None) -> str:
    """Full pipeline: import → transform → validate → export."""
    data = DataImporter.import_data(source, fmt=source_fmt)
    if mapping:
        data = DataTransformer(mapping=mapping).transform(data)
    if schema:
        data = DataValidator(schema).validate(data)
    return DataExporter.export_data(data, fmt=export_fmt, destination=destination)
