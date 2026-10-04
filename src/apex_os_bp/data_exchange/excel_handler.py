"""Excel (XLSX) import/export handler using stdlib only.

XLSX files are ZIP archives containing XML files. This module reads and writes
them using zipfile and xml.etree.ElementTree without external dependencies.
"""
from __future__ import annotations

import re
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from xml.etree import ElementTree as ET

from apex_os_bp.data_exchange.exceptions import ImportError, ExportError
from apex_os_bp.data_exchange.models import DataRecord, DataSchema, ImportResult

# Excel XML namespaces
NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# Excel epoch (January 1, 1900, with the Lotus 1-2-3 bug for Feb 29, 1900)
EXCEL_EPOCH = datetime(1899, 12, 30)


class ExcelHandler:
    """Handler for Excel XLSX import and export operations."""

    def __init__(self, schema: Optional[DataSchema] = None, encoding: str = "utf-8"):
        self.schema = schema
        self.encoding = encoding

    def import_data(
        self,
        source: Union[str, Path],
        schema: Optional[DataSchema] = None,
        sheet_name: Optional[str] = None,
        has_header: bool = True,
    ) -> ImportResult:
        """Import data from an XLSX file.

        Args:
            source: Path to XLSX file.
            schema: Schema for validation. Uses instance schema if not provided.
            sheet_name: Name of the sheet to read. Uses first sheet if not provided.
            has_header: Whether the first row is a header.

        Returns:
            ImportResult with details of the import operation.
        """
        schema = schema or self.schema
        result = ImportResult(success=True)

        try:
            path = Path(source)
            if not path.exists():
                raise ImportError(f"Excel file not found: {path}")

            with zipfile.ZipFile(path, "r") as zf:
                # Read shared strings
                shared_strings = self._read_shared_strings(zf)

                # Read workbook to find sheet
                sheet_file = self._find_sheet_file(zf, sheet_name)

                # Read sheet data
                rows = self._read_sheet(zf, sheet_file, shared_strings)
        except ImportError:
            raise
        except Exception as e:
            raise ImportError(f"Failed to read Excel file: {e}") from e

        if not rows:
            result.add_warning("Excel sheet is empty")
            return result

        # Determine headers
        if has_header:
            headers = [str(cell) for cell in rows[0]]
            data_rows = rows[1:]
        else:
            if schema:
                headers = [col.name for col in schema.columns]
            else:
                headers = [f"column_{i}" for i in range(len(rows[0]))]
            data_rows = rows

        # Parse data rows
        records: List[DataRecord] = []
        for row_idx, row in enumerate(data_rows, start=2 if has_header else 1):
            record_data: Dict[str, Any] = {}
            for col_idx, header in enumerate(headers):
                value = row[col_idx] if col_idx < len(row) else ""
                # Type conversion based on schema
                if schema:
                    col = schema.get_column(header)
                    if col and value != "":
                        value = self._convert_value(value, col.data_type)
                record_data[header] = value

            record = DataRecord(data=record_data, row_number=row_idx, source="excel")

            # Validate against schema
            if schema:
                errors = schema.validate_record(record_data)
                if errors:
                    result.records_failed += 1
                    for err in errors:
                        result.add_error(f"Row {row_idx}: {err}")
                    continue

            records.append(record)
            result.records_imported += 1

        result.metadata = {
            "format": "xlsx",
            "headers": headers,
            "total_rows": len(data_rows),
            "records": records,
        }

        if result.records_failed > 0:
            result.success = False

        return result

    def export_data(
        self,
        records: List[DataRecord],
        destination: Union[str, Path],
        schema: Optional[DataSchema] = None,
        sheet_name: str = "Sheet1",
        include_header: bool = True,
    ) -> None:
        """Export data records to an XLSX file.

        Args:
            records: List of DataRecord objects to export.
            destination: Path to output XLSX file.
            schema: Schema for column ordering.
            sheet_name: Name of the worksheet.
            include_header: Whether to include a header row.
        """
        schema = schema or self.schema

        # Determine headers
        if schema:
            headers = [col.name for col in schema.columns]
        elif records:
            headers = list(records[0].data.keys())
        else:
            headers = []

        try:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Build sheet data
            sheet_rows: List[List[Any]] = []
            if include_header and headers:
                sheet_rows.append(headers)
            for record in records:
                row = []
                for header in headers:
                    value = record.data.get(header, "")
                    if value is None:
                        value = ""
                    row.append(value)
                sheet_rows.append(row)

            # Write XLSX
            self._write_xlsx(path, sheet_name, sheet_rows)
        except ExportError:
            raise
        except Exception as e:
            raise ExportError(f"Failed to write Excel file: {e}") from e

    def _read_shared_strings(self, zf: zipfile.ZipFile) -> List[str]:
        """Read shared strings table from XLSX."""
        strings: List[str] = []
        try:
            with zf.open("xl/sharedStrings.xml") as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for si in root.findall(f"{{{NS_MAIN}}}si"):
                    # Concatenate all text nodes within this string item
                    text_parts = []
                    for t in si.iter(f"{{{NS_MAIN}}}t"):
                        if t.text:
                            text_parts.append(t.text)
                    strings.append("".join(text_parts))
        except (KeyError, ET.ParseError):
            pass
        return strings

    def _find_sheet_file(self, zf: zipfile.ZipFile, sheet_name: Optional[str]) -> str:
        """Find the sheet XML file path within the XLSX archive."""
        # Read workbook.xml to get sheet names and their rIds
        with zf.open("xl/workbook.xml") as f:
            tree = ET.parse(f)
            root = tree.getroot()

        sheets = root.findall(f".//{{{NS_MAIN}}}sheet")
        if not sheets:
            raise ImportError("No sheets found in Excel workbook")

        # Read relationships to map rId -> file path
        with zf.open("xl/_rels/workbook.xml.rels") as f:
            rel_tree = ET.parse(f)
            rel_root = rel_tree.getroot()

        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        rid_to_target: Dict[str, str] = {}
        for rel in rel_root.findall(f"{{{rel_ns}}}Relationship"):
            rid = rel.get("Id", "")
            target = rel.get("Target", "")
            rid_to_target[rid] = target

        # Find the requested sheet or default to first
        for sheet in sheets:
            name = sheet.get("name", "")
            if sheet_name and name == sheet_name:
                rid = sheet.get(f"{{{NS_REL}}}id", "")
                target = rid_to_target.get(rid, "")
                if target:
                    if not target.startswith("xl/"):
                        target = "xl/" + target
                    return target

        # Default to first sheet
        first_sheet = sheets[0]
        rid = first_sheet.get(f"{{{NS_REL}}}id", "")
        target = rid_to_target.get(rid, "")
        if target:
            if not target.startswith("xl/"):
                target = "xl/" + target
            return target

        # Fallback to standard path
        return "xl/worksheets/sheet1.xml"

    def _read_sheet(
        self, zf: zipfile.ZipFile, sheet_file: str, shared_strings: List[str]
    ) -> List[List[Any]]:
        """Read all rows from a worksheet."""
        rows: List[List[Any]] = []
        with zf.open(sheet_file) as f:
            tree = ET.parse(f)
            root = tree.getroot()

        for row in root.findall(f".//{{{NS_MAIN}}}row"):
            row_data: List[Any] = []
            for cell in row.findall(f"{{{NS_MAIN}}}c"):
                cell_type = cell.get("t", "")
                value_elem = cell.find(f"{{{NS_MAIN}}}v")

                if value_elem is None or value_elem.text is None:
                    # Check for inline string
                    is_elem = cell.find(f"{{{NS_MAIN}}}is")
                    if is_elem is not None:
                        text_parts = []
                        for t in is_elem.iter(f"{{{NS_MAIN}}}t"):
                            if t.text:
                                text_parts.append(t.text)
                        row_data.append("".join(text_parts))
                    else:
                        row_data.append("")
                    continue

                raw_value = value_elem.text

                if cell_type == "s":
                    # Shared string reference
                    idx = int(raw_value)
                    row_data.append(shared_strings[idx] if idx < len(shared_strings) else "")
                elif cell_type == "b":
                    # Boolean
                    row_data.append(raw_value == "1")
                elif cell_type == "str":
                    # Formula string result
                    row_data.append(raw_value)
                else:
                    # Number or date
                    try:
                        num = float(raw_value)
                        if num == int(num):
                            row_data.append(int(num))
                        else:
                            row_data.append(num)
                    except ValueError:
                        row_data.append(raw_value)

            rows.append(row_data)

        return rows

    def _write_xlsx(self, path: Path, sheet_name: str, rows: List[List[Any]]) -> None:
        """Write data to an XLSX file."""
        # Build sheet XML
        sheet_xml = self._build_sheet_xml(rows)

        # Build shared strings
        shared_strings: List[str] = []
        string_index: Dict[str, int] = {}

        def get_string_index(s: str) -> int:
            if s not in string_index:
                string_index[s] = len(shared_strings)
                shared_strings.append(s)
            return string_index[s]

        # Replace string values with shared string references
        sheet_xml = self._replace_strings_with_refs(sheet_xml, get_string_index)

        # Build workbook XML
        workbook_xml = self._build_workbook_xml(sheet_name)

        # Build relationships
        workbook_rels = self._build_workbook_rels()
        root_rels = self._build_root_rels()
        content_types = self._build_content_types()

        # Build shared strings XML
        shared_strings_xml = self._build_shared_strings_xml(shared_strings)

        # Write ZIP archive
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            if shared_strings:
                zf.writestr("xl/sharedStrings.xml", shared_strings_xml)

    def _build_sheet_xml(self, rows: List[List[Any]]) -> str:
        """Build worksheet XML content."""
        ns_decl = f'xmlns="{NS_MAIN}" xmlns:r="{NS_REL}"'
        lines = [f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
        lines.append(f"<worksheet {ns_decl}>")
        lines.append("<sheetData>")

        for row_idx, row in enumerate(rows, start=1):
            row_ref = str(row_idx)
            lines.append(f'<row r="{row_ref}">')
            for col_idx, value in enumerate(row):
                cell_ref = f"{self._col_letter(col_idx)}{row_ref}"
                if isinstance(value, str):
                    # Will be replaced with shared string ref later
                    lines.append(f'<c r="{cell_ref}" t="str"><v>{self._escape_xml(value)}</v></c>')
                elif isinstance(value, bool):
                    lines.append(f'<c r="{cell_ref}" t="b"><v>{1 if value else 0}</v></c>')
                elif isinstance(value, (int, float)):
                    lines.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
                elif isinstance(value, datetime):
                    serial = self._datetime_to_serial(value)
                    lines.append(f'<c r="{cell_ref}"><v>{serial}</v></c>')
                else:
                    str_val = str(value) if value is not None else ""
                    lines.append(f'<c r="{cell_ref}" t="str"><v>{self._escape_xml(str_val)}</v></c>')
            lines.append("</row>")

        lines.append("</sheetData>")
        lines.append("</worksheet>")
        return "\n".join(lines)

    def _replace_strings_with_refs(self, sheet_xml: str, get_index) -> str:
        """Replace string cell values with shared string references."""
        # Pattern matches <c r="..." t="str"><v>text</v></c>
        pattern = re.compile(r'<c r="([A-Z]+\d+)" t="str"><v>(.*?)</v></c>')

        def replacer(match):
            cell_ref, text = match.groups()
            idx = get_index(text)
            return f'<c r="{cell_ref}" t="s"><v>{idx}</v></c>'

        return pattern.sub(replacer, sheet_xml)

    def _build_workbook_xml(self, sheet_name: str) -> str:
        """Build workbook XML."""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{NS_MAIN}" xmlns:r="{NS_REL}">'
            "<sheets>"
            f'<sheet name="{self._escape_xml(sheet_name)}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

    def _build_workbook_rels(self) -> str:
        """Build workbook relationships XML."""
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{rel_ns}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
            "</Relationships>"
        )

    def _build_root_rels(self) -> str:
        """Build root relationships XML."""
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{rel_ns}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _build_content_types(self) -> str:
        """Build [Content_Types].xml."""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>"
        )

    def _build_shared_strings_xml(self, strings: List[str]) -> str:
        """Build shared strings XML."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<sst xmlns="{NS_MAIN}" count="{len(strings)}" uniqueCount="{len(strings)}">',
        ]
        for s in strings:
            lines.append(f"<si><t>{self._escape_xml(s)}</t></si>")
        lines.append("</sst>")
        return "\n".join(lines)

    def _convert_value(self, value: Any, data_type: str) -> Any:
        """Convert a value to the appropriate type."""
        if value is None or value == "":
            return value
        try:
            if data_type == "integer":
                return int(float(value)) if isinstance(value, (int, float, str)) else value
            elif data_type == "float":
                return float(value) if isinstance(value, (int, float, str)) else value
            elif data_type == "boolean":
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ("true", "1", "yes")
            elif data_type == "date":
                if isinstance(value, (int, float)):
                    return EXCEL_EPOCH + timedelta(days=float(value))
                return value
            else:
                return str(value)
        except (ValueError, TypeError):
            return value

    @staticmethod
    def _col_letter(col_idx: int) -> str:
        """Convert column index to Excel column letter (0 -> A, 25 -> Z, 26 -> AA)."""
        result = ""
        col_idx += 1
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape special XML characters."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    @staticmethod
    def _datetime_to_serial(dt: datetime) -> float:
        """Convert datetime to Excel serial number."""
        delta = dt - EXCEL_EPOCH
        return delta.days + delta.seconds / 86400.0
