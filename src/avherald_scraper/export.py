"""Write the stored headlines as JSON, CSV, or XLSX.

SQLite stays the working copy so a later run can resume. These writers only
publish a copy of the articles table.
"""

# Annotations can mention helpers defined further down.
from __future__ import annotations

# CSV is a stdlib writer. Headlines contain commas.
import csv

# JSON is the other text format. No extra package.
import json

# XML text must not contain raw control characters.
import re

# XLSX is a zip of XML. The stdlib can build that.
import zipfile

# The database path's stem becomes the export file name.
from pathlib import Path

# Rows come back from SQLite as mappings.
from avherald_scraper.db import Database

# Column order in every export. Matches the articles table.
COLUMNS = (
    "article_id",
    "url",
    "heading",
    "list_date",
    "list_date_iso",
    "icon",
    "category",
    "source_page",
    "first_seen_at",
    "last_seen_at",
)

# Formats this module can publish. sqlite is handled by the database itself.
EXPORT_FORMATS = ("json", "csv", "xlsx")

# Characters XML 1.0 refuses, other than tab, newline, and carriage return.
_ILLEGAL_XML = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def output_path(database_path: Path, fmt: str) -> Path:
    """Return the export path next to the SQLite file."""

    # avherald.sqlite becomes avherald.json, and the folder stays put.
    return database_path.with_suffix(f".{fmt}")


def export_articles(db: Database, fmt: str, database_path: Path) -> Path:
    """Write every stored article in `fmt` and return that path."""

    # One snapshot, in date order, so the file is stable between runs.
    rows = db.fetch_articles()

    # The sibling of the database file.
    path = output_path(database_path, fmt)

    # The parent already exists because the database created it.
    if fmt == "json":
        # Pretty JSON is easier to open by hand.
        _write_json(path, rows)

    # Spreadsheet text.
    elif fmt == "csv":
        # Excel and Pages both open this.
        _write_csv(path, rows)

    # Real workbook, not a renamed CSV.
    elif fmt == "xlsx":
        # OOXML, written without a third-party package.
        _write_xlsx(path, rows)

    # The caller checked the name. This is a programming error.
    else:
        # Fail closed rather than write the wrong kind of file.
        raise ValueError(f"unsupported export format: {fmt}")

    # The summary prints this path.
    return path


def _write_json(path: Path, rows: list[dict[str, str | None]]) -> None:
    """Write a UTF-8 JSON list."""

    # Headlines can contain non-ASCII aircraft and place names.
    text = json.dumps(rows, ensure_ascii=False, indent=2)

    # A trailing newline keeps the file friendly to diffs.
    path.write_text(text + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, str | None]]) -> None:
    """Write a UTF-8 CSV with a header row."""

    # newline="" is what the csv module asks for on every platform.
    with path.open("w", encoding="utf-8", newline="") as handle:
        # QUOTE_MINIMAL still quotes headings that contain commas.
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")

        # The first row names the columns.
        writer.writeheader()

        # None becomes an empty cell, not the word None.
        for row in rows:
            # Copy so we don't mutate the dict the database handed back.
            writer.writerow({key: row.get(key) or "" for key in COLUMNS})


def _write_xlsx(path: Path, rows: list[dict[str, str | None]]) -> None:
    """Write a minimal .xlsx workbook with one sheet."""

    # Header plus one row per article.
    sheet = _sheet_xml(rows)

    # Zip stores forward-slash names. Excel is picky about that.
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as book:
        # Package relationships point at the workbook.
        book.writestr("[Content_Types].xml", _CONTENT_TYPES)

        # The root relationship.
        book.writestr("_rels/.rels", _ROOT_RELS)

        # The workbook names the sheet.
        book.writestr("xl/workbook.xml", _WORKBOOK)

        # The workbook relationship points at the sheet.
        book.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)

        # The cells.
        book.writestr("xl/worksheets/sheet1.xml", sheet)


def _sheet_xml(rows: list[dict[str, str | None]]) -> str:
    """Build the worksheet XML, header first."""

    # Row 1 is the header.
    body = [_row_xml(1, list(COLUMNS))]

    # Data starts at row 2.
    for index, row in enumerate(rows, start=2):
        # Missing values are empty cells.
        values = [row.get(key) or "" for key in COLUMNS]

        # One spreadsheet row.
        body.append(_row_xml(index, values))

    # Join without extra whitespace between rows.
    sheet_rows = "".join(body)

    # The worksheet namespace is the one Excel expects.
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{sheet_rows}</sheetData></worksheet>"
    )


def _row_xml(number: int, values: list[str]) -> str:
    """Build one `<row>` of inline strings."""

    # Cells in this row.
    cells: list[str] = []

    # Column numbers are 1-based.
    for index, value in enumerate(values, start=1):
        # A1, B1, ...
        ref = f"{_column(index)}{number}"

        # Escape before the value goes inside `<t>`.
        text = _xml_text(value)

        # inlineStr avoids a shared-string table.
        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{text}</t></is></c>')

    # The row number matches the cell refs.
    return f'<row r="{number}">{"".join(cells)}</row>'


def _column(number: int) -> str:
    """Turn 1 into A, 27 into AA."""

    # Built from the least significant letter upward.
    letters = ""

    # Keep dividing until the column is consumed.
    while number:
        # Excel columns are base 26, but A is 1, not 0.
        number, remainder = divmod(number - 1, 26)

        # 0 -> A.
        letters = chr(65 + remainder) + letters

    # A for the first column.
    return letters


def _xml_text(value: str) -> str:
    """Escape a cell so the worksheet stays well-formed XML."""

    # Drop characters XML 1.0 will not accept.
    cleaned = _ILLEGAL_XML.sub("", value)

    # Order matters: ampersand first.
    return (
        cleaned.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Package content types. Excel refuses a book that lacks these.
_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""

# Points the package at the workbook part.
_ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

# One sheet, named Articles.
_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Articles" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""

# Points the workbook at the worksheet part.
_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
