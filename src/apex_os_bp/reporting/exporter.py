"""Report export — export reports to PDF, CSV, and Excel formats."""

from __future__ import annotations

import csv
import io
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from apex_os_bp.reporting.builder import ReportResult


class ExportFormat(str, Enum):
    """Supported export formats."""

    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    HTML = "html"


@dataclass
class ExportResult:
    """Result of an export operation."""

    format: ExportFormat
    file_path: str
    file_size: int
    row_count: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error: str | None = None


class ReportExporter:
    """Exports report results to various file formats."""

    def __init__(self, output_dir: str | None = None) -> None:
        self._output_dir = output_dir or tempfile.gettempdir()
        self._export_history: list[ExportResult] = []

    def export(
        self,
        result: ReportResult,
        format: ExportFormat,
        filename: str | None = None,
    ) -> ExportResult:
        """Export a report result to the specified format."""
        if filename is None:
            filename = f"report_{result.definition.id}_{int(datetime.utcnow().timestamp())}"

        try:
            if format == ExportFormat.CSV:
                return self._export_csv(result, filename)
            if format == ExportFormat.EXCEL:
                return self._export_excel(result, filename)
            if format == ExportFormat.PDF:
                return self._export_pdf(result, filename)
            if format == ExportFormat.JSON:
                return self._export_json(result, filename)
            if format == ExportFormat.HTML:
                return self._export_html(result, filename)
            raise ValueError(f"Unsupported export format: {format}")
        except Exception as exc:
            export_result = ExportResult(
                format=format,
                file_path="",
                file_size=0,
                row_count=0,
                error=str(exc),
            )
            self._export_history.append(export_result)
            return export_result

    def _export_csv(self, result: ReportResult, filename: str) -> ExportResult:
        """Export to CSV format."""
        path = os.path.join(self._output_dir, f"{filename}.csv")
        columns = [c.name for c in result.definition.columns if c.visible]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            for row in result.rows:
                writer.writerow({c: row.get(c, "") for c in columns})
        size = os.path.getsize(path)
        export_result = ExportResult(
            format=ExportFormat.CSV,
            file_path=path,
            file_size=size,
            row_count=len(result.rows),
        )
        self._export_history.append(export_result)
        return export_result

    def _export_excel(self, result: ReportResult, filename: str) -> ExportResult:
        """Export to Excel format (using openpyxl if available, else XML spreadsheet)."""
        path = os.path.join(self._output_dir, f"{filename}.xlsx")
        columns = [c for c in result.definition.columns if c.visible]
        col_names = [c.name for c in columns]

        try:
            from openpyxl import Workbook

            wb = Workbook()
            ws = wb.active
            ws.title = result.definition.name[:31]  # Excel sheet name limit
            ws.append([c.label for c in columns])
            for row in result.rows:
                ws.append([row.get(c, "") for c in col_names])
            wb.save(path)
        except ImportError:
            # Fallback: write as XML Spreadsheet 2003
            path = os.path.join(self._output_dir, f"{filename}.xls")
            self._write_xml_spreadsheet(path, result, columns, col_names)

        size = os.path.getsize(path)
        export_result = ExportResult(
            format=ExportFormat.EXCEL,
            file_path=path,
            file_size=size,
            row_count=len(result.rows),
        )
        self._export_history.append(export_result)
        return export_result

    def _write_xml_spreadsheet(
        self,
        path: str,
        result: ReportResult,
        columns: list[Any],
        col_names: list[str],
    ) -> None:
        """Write an XML Spreadsheet 2003 file as Excel fallback."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?mso-application progid="Excel.Sheet"?>',
            '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
            ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
            f"<Worksheet ss:Name=\"{result.definition.name[:31]}\">",
            "<Table>",
        ]
        # Header row
        lines.append("<Row>")
        for c in columns:
            lines.append(
                f'<Cell><Data ss:Type="String">{c.label}</Data></Cell>'
            )
        lines.append("</Row>")
        # Data rows
        for row in result.rows:
            lines.append("<Row>")
            for c in col_names:
                val = row.get(c, "")
                lines.append(
                    f'<Cell><Data ss:Type="String">{val}</Data></Cell>'
                )
            lines.append("</Row>")
        lines.append("</Table>")
        lines.append("</Worksheet>")
        lines.append("</Workbook>")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _export_pdf(self, result: ReportResult, filename: str) -> ExportResult:
        """Export to PDF format."""
        path = os.path.join(self._output_dir, f"{filename}.pdf")
        columns = [c for c in result.definition.columns if c.visible]
        col_names = [c.name for c in columns]

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                SimpleDocTemplate,
                Table,
                TableStyle,
                Paragraph,
                Spacer,
            )

            doc = SimpleDocTemplate(path, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph(result.definition.name, styles["Title"]))
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(
                f"Generated: {result.generated_at.isoformat()}",
                styles["Normal"],
            ))
            elements.append(Spacer(1, 12))

            table_data = [[c.label for c in columns]]
            for row in result.rows:
                table_data.append([str(row.get(c, "")) for c in col_names])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
            ]))
            elements.append(table)
            doc.build(elements)
        except ImportError:
            # Fallback: write a simple text-based PDF placeholder
            self._write_simple_pdf(path, result, columns, col_names)

        size = os.path.getsize(path)
        export_result = ExportResult(
            format=ExportFormat.PDF,
            file_path=path,
            file_size=size,
            row_count=len(result.rows),
        )
        self._export_history.append(export_result)
        return export_result

    def _write_simple_pdf(
        self,
        path: str,
        result: ReportResult,
        columns: list[Any],
        col_names: list[str],
    ) -> None:
        """Write a minimal valid PDF without external dependencies."""
        lines = [
            f"Report: {result.definition.name}",
            f"Generated: {result.generated_at.isoformat()}",
            f"Total rows: {result.total_count}",
            "",
            " | ".join(c.label for c in columns),
            "-" * 60,
        ]
        for row in result.rows:
            lines.append(" | ".join(str(row.get(c, "")) for c in col_names))
        content = "\n".join(lines)

        # Build a minimal PDF with correct xref offsets
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length " + str(len(content) + 100).encode() + b" >>\nstream\nBT\n/F1 10 Tf\n72 720 Td\n(" + content[:3000].encode() + b") Tj\nET\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(len(pdf))
            pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

        xref_pos = len(pdf)
        pdf += f"xref\n0 {len(objects) + 1}\n".encode()
        pdf += b"0000000000 65535 f \n"
        for offset in offsets[1:]:
            pdf += f"{offset:010d} 00000 n \n".encode()
        pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()

        with open(path, "wb") as f:
            f.write(bytes(pdf))

    def _export_json(self, result: ReportResult, filename: str) -> ExportResult:
        """Export to JSON format."""
        import json

        path = os.path.join(self._output_dir, f"{filename}.json")
        data = {
            "report_name": result.definition.name,
            "report_type": result.definition.report_type.value,
            "generated_at": result.generated_at.isoformat(),
            "total_count": result.total_count,
            "execution_time_ms": result.execution_time_ms,
            "columns": [
                {"name": c.name, "label": c.label, "type": c.data_type}
                for c in result.definition.columns
                if c.visible
            ],
            "rows": result.rows,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        size = os.path.getsize(path)
        export_result = ExportResult(
            format=ExportFormat.JSON,
            file_path=path,
            file_size=size,
            row_count=len(result.rows),
        )
        self._export_history.append(export_result)
        return export_result

    def _export_html(self, result: ReportResult, filename: str) -> ExportResult:
        """Export to HTML format."""
        path = os.path.join(self._output_dir, f"{filename}.html")
        columns = [c for c in result.definition.columns if c.visible]
        col_names = [c.name for c in columns]

        rows_html = ""
        for row in result.rows:
            cells = "".join(
                f"<td>{row.get(c, '')}</td>" for c in col_names
            )
            rows_html += f"<tr>{cells}</tr>\n"

        headers_html = "".join(
            f"<th>{c.label}</th>" for c in columns
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{result.definition.name}</title>
<style>
body {{ font-family: sans-serif; margin: 20px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #4CAF50; color: white; }}
tr:nth-child(even) {{ background-color: #f2f2f2; }}
.meta {{ color: #666; margin-bottom: 20px; }}
</style>
</head>
<body>
<h1>{result.definition.name}</h1>
<div class="meta">
<p>Generated: {result.generated_at.isoformat()}</p>
<p>Total rows: {result.total_count}</p>
<p>Execution time: {result.execution_time_ms:.2f}ms</p>
</div>
<table>
<thead><tr>{headers_html}</tr></thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        size = os.path.getsize(path)
        export_result = ExportResult(
            format=ExportFormat.HTML,
            file_path=path,
            file_size=size,
            row_count=len(result.rows),
        )
        self._export_history.append(export_result)
        return export_result

    def get_history(self) -> list[ExportResult]:
        """Get export history."""
        return list(self._export_history)

    def get_history_by_format(
        self, format: ExportFormat
    ) -> list[ExportResult]:
        """Get export history filtered by format."""
        return [r for r in self._export_history if r.format == format]
