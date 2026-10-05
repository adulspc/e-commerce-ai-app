"""Read an uploaded CSV and suggest columns for the four model features."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass

from backend.schemas.dataset import SuggestedMapping
from backend.utils.errors import EmptyDatasetError, InvalidCsvError

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_ROWS = 200_000
MAX_COLUMNS = 200
PREVIEW_ROWS = 20

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "price_usd": ("price_usd", "final_price_usd", "price", "final_price"),
    "qty_sold": ("qty_sold", "units_sold", "quantity_sold"),
    "pct_discount": (
        "pct_discount",
        "discount",
        "discount_percentage",
        "discount_percent",
    ),
    "retail_price": (
        "retail_price",
        "initial_price_usd",
        "initial_price",
        "original_price",
    ),
    "product_name": ("product_title", "product_name", "name", "title"),
    "category": ("category_name", "category"),
}


@dataclass
class ParsedDataset:
    columns: list[str]
    preview: list[dict[str, str]]
    row_count: int


def read_csv_rows(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    if len(content) > MAX_UPLOAD_BYTES:
        raise InvalidCsvError("ไฟล์ใหญ่เกิน 50 MB")
    if not content.strip():
        raise EmptyDatasetError()

    text = _decode(content)
    sample = text[:8192]
    reader = csv.reader(io.StringIO(text), _dialect(sample))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise EmptyDatasetError() from exc
    except csv.Error as exc:
        raise InvalidCsvError() from exc

    columns = [cell.strip() for cell in header]
    named = [column for column in columns if column]
    if len(named) < 2:
        raise InvalidCsvError("ไฟล์ CSV ต้องมีอย่างน้อย 2 คอลัมน์")
    if len(columns) > MAX_COLUMNS:
        raise InvalidCsvError("ไฟล์มีจำนวนคอลัมน์มากเกินไป")
    if len(columns) != len(set(columns)):
        raise InvalidCsvError("มีชื่อคอลัมน์ซ้ำกัน")

    rows: list[dict[str, str]] = []
    width = len(columns)
    try:
        for raw in reader:
            if not raw or all(not cell.strip() for cell in raw):
                continue
            values = [cell.strip() for cell in raw]
            if len(values) < width:
                values.extend([""] * (width - len(values)))
            rows.append(dict(zip(columns, values[:width], strict=True)))
            if len(rows) > MAX_ROWS:
                raise InvalidCsvError("ไฟล์มีจำนวนแถวมากเกิน 200,000 แถว")
    except csv.Error as exc:
        raise InvalidCsvError() from exc

    if not rows:
        raise EmptyDatasetError()
    return columns, rows


def parse_csv_bytes(content: bytes) -> ParsedDataset:
    columns, rows = read_csv_rows(content)
    return ParsedDataset(
        columns=columns,
        preview=rows[:PREVIEW_ROWS],
        row_count=len(rows),
    )


def suggest_mapping(columns: list[str]) -> SuggestedMapping:
    normalized: dict[str, str] = {}
    for column in columns:
        key = _normalize(column)
        if key and key not in normalized:
            normalized[key] = column

    used: set[str] = set()
    chosen: dict[str, str | None] = {}
    for field, aliases in FIELD_ALIASES.items():
        match = None
        for alias in aliases:
            column = normalized.get(alias)
            if column and column not in used:
                match = column
                used.add(column)
                break
        chosen[field] = match
    return SuggestedMapping(**chosen)


def missing_required(mapping: SuggestedMapping) -> list[str]:
    missing: list[str] = []
    if mapping.price_usd is None:
        missing.append("price_usd")
    if mapping.qty_sold is None:
        missing.append("qty_sold")
    if mapping.pct_discount is None and mapping.retail_price is None:
        missing.append("pct_discount")
    return missing


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp874", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise InvalidCsvError("อ่านตัวอักษรในไฟล์ไม่ได้ บันทึกไฟล์เป็น CSV แบบ UTF-8 แล้วลองอีกครั้ง")


def _dialect(sample: str) -> type[csv.Dialect]:
    delimiter = ","
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        sniffed = None
    if sniffed and sniffed.delimiter in ",;\t":
        delimiter = sniffed.delimiter

    class _ExcelDialect(csv.excel):
        pass

    _ExcelDialect.delimiter = delimiter
    return _ExcelDialect


def _normalize(name: str) -> str:
    return re.sub(r"[\s\-]+", "_", name.strip().lower())
