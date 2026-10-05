"""Drop rows that cannot be used as K-Means features.

Blank discount stays blank. A discount is calculated from retail price only
when that cell has no discount and retail price is usable. High sales stay
in the table. apply_cleaning then stores sales_value on the same table.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backend.schemas.dataset import CleaningReport, ColumnMappingInput
from backend.services.dataset_io import read_csv_rows
from backend.services.feature_engineering import add_sales_value, summarize_features
from backend.services.clustering import delete_model
from backend.services.scaling import ensure_scaler
from backend.utils.errors import (
    EmptyDatasetError,
    InvalidCsvError,
    MissingColumnsError,
    NonNumericValueError,
)

CLEANED_FILENAME = "cleaned.csv"
SOURCE_FILENAME = "source.csv"
_BASE_COLUMNS = [
    "source_row",
    "product_name",
    "category",
    "price_usd",
    "pct_discount",
    "qty_sold",
]
_OUTPUT_COLUMNS = [*_BASE_COLUMNS, "sales_value"]


def apply_cleaning(session, mapping: ColumnMappingInput) -> CleaningReport:
    path = session.directory / SOURCE_FILENAME
    if not path.is_file():
        raise InvalidCsvError("ไม่พบไฟล์ของชุดข้อมูลนี้ ลองอัปโหลดอีกครั้ง")

    columns, rows = read_csv_rows(path.read_bytes())
    table = pd.DataFrame.from_records(rows, columns=columns)
    cleaned, report = clean_table(table, mapping)
    if report.rows_after == 0:
        raise EmptyDatasetError("หลังทำความสะอาดไม่เหลือรายการที่ใช้วิเคราะห์")

    cleaned = add_sales_value(cleaned)
    feature_report = summarize_features(cleaned)
    cleaned.to_csv(session.directory / CLEANED_FILENAME, index=False, encoding="utf-8")
    session.mapping = mapping.model_dump()
    session.cleaning_report = report.model_dump()
    session.feature_report = feature_report.model_dump()
    session.frame = cleaned
    session.scaler = None
    session.scaling_report = None
    ensure_scaler(session)
    session.model = None
    session.k = None
    session.recommended_k = None
    session.cluster_report = None
    session.optimal_k_report = None
    delete_model(session.directory)
    session.transition("processed")
    return report


def load_cleaned_frame(directory: Path) -> pd.DataFrame | None:
    path = directory / CLEANED_FILENAME
    if not path.is_file():
        return None
    try:
        frame = pd.read_csv(path, encoding="utf-8")
        if not set(_BASE_COLUMNS).issubset(frame.columns):
            return None
        present = [column for column in _OUTPUT_COLUMNS if column in frame.columns]
        frame = frame.loc[:, present].copy()
        frame["source_row"] = pd.to_numeric(frame["source_row"], errors="coerce").astype("int64")
        frame["product_name"] = frame["product_name"].fillna("").astype(str)
        frame["category"] = frame["category"].fillna("").astype(str)
        for column in ("price_usd", "pct_discount", "qty_sold"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame = add_sales_value(frame)
        frame = frame.loc[:, _OUTPUT_COLUMNS]
    except (OSError, ValueError, pd.errors.ParserError, MissingColumnsError, NonNumericValueError):
        return None
    return frame


def clean_table(
    table: pd.DataFrame,
    mapping: ColumnMappingInput,
) -> tuple[pd.DataFrame, CleaningReport]:
    columns = [str(column) for column in table.columns]
    _validate_mapping(columns, mapping)

    price_num, price_missing, price_invalid = _numbers(table[mapping.price_usd])
    qty_num, qty_missing, qty_invalid = _numbers(table[mapping.qty_sold])
    discount_num, discount_missing, discount_invalid = _discount_numbers(table, mapping)

    if mapping.retail_price:
        retail_num, retail_missing, retail_invalid = _numbers(table[mapping.retail_price])
        discount_num, discount_missing, discount_invalid = _fill_discount(
            price_num,
            price_missing,
            price_invalid,
            retail_num,
            retail_missing,
            retail_invalid,
            discount_num,
            discount_missing,
            discount_invalid,
        )

    price_bad = _below_zero(price_num, price_missing, price_invalid)
    qty_bad = _below_zero(qty_num, qty_missing, qty_invalid)
    discount_bad = _outside_percent(discount_num, discount_missing, discount_invalid)

    invalid_row = price_bad | qty_bad | discount_bad
    missing_row = ~invalid_row & (price_missing | qty_missing | discount_missing)
    valid_row = ~invalid_row & ~missing_row

    names = _labels(table, mapping.product_name)
    categories = _labels(table, mapping.category)
    valid_index = table.index[valid_row]
    dedupe = pd.DataFrame(
        {
            "product_name": names.loc[valid_index].to_numpy(),
            "category": categories.loc[valid_index].to_numpy(),
            "price_usd": price_num.loc[valid_index].to_numpy(),
            "pct_discount": discount_num.loc[valid_index].to_numpy(),
            "qty_sold": qty_num.loc[valid_index].to_numpy(),
        }
    )
    duplicate_mask = dedupe.duplicated(keep="first").to_numpy()
    keep = ~duplicate_mask
    source_rows = np.arange(1, len(table) + 1, dtype=np.int64)[valid_row.to_numpy()][keep]

    cleaned = pd.DataFrame(
        {
            "source_row": source_rows,
            "product_name": names.loc[valid_index].to_numpy()[keep],
            "category": categories.loc[valid_index].to_numpy()[keep],
            "price_usd": price_num.loc[valid_index].to_numpy()[keep],
            "pct_discount": discount_num.loc[valid_index].to_numpy()[keep],
            "qty_sold": qty_num.loc[valid_index].to_numpy()[keep],
        }
    )
    missing_price = int((~invalid_row & price_missing).sum())
    missing_quantity = int((~invalid_row & ~price_missing & qty_missing).sum())
    missing_discount = int((~invalid_row & ~price_missing & ~qty_missing & discount_missing).sum())
    report = CleaningReport(
        rows_before=len(table),
        rows_after=int(keep.sum()),
        missing_values_handled=int(missing_row.sum()),
        duplicate_rows_removed=int(duplicate_mask.sum()),
        invalid_rows_removed=int(invalid_row.sum()),
        missing_price=missing_price,
        missing_quantity=missing_quantity,
        missing_discount=missing_discount,
    )
    return cleaned, report


def _validate_mapping(columns: list[str], mapping: ColumnMappingInput) -> None:
    selected = {
        "price_usd": mapping.price_usd,
        "qty_sold": mapping.qty_sold,
        "pct_discount": mapping.pct_discount,
        "retail_price": mapping.retail_price,
        "product_name": mapping.product_name,
        "category": mapping.category,
    }
    chosen = {field: column for field, column in selected.items() if column}
    missing = [field for field, column in chosen.items() if column not in columns]
    if mapping.pct_discount is None and mapping.retail_price is None:
        missing.append("pct_discount")
    if missing:
        raise MissingColumnsError(missing)
    names = list(chosen.values())
    if len(names) != len(set(names)):
        raise MissingColumnsError(message="คอลัมน์เดียวกันถูกใช้ซ้ำ เลือกคนละคอลัมน์")


def _discount_numbers(
    table: pd.DataFrame,
    mapping: ColumnMappingInput,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    if mapping.pct_discount:
        return _numbers(table[mapping.pct_discount])
    missing = pd.Series(True, index=table.index)
    invalid = pd.Series(False, index=table.index)
    return pd.Series(np.nan, index=table.index, dtype="float64"), missing, invalid


def _fill_discount(
    price_num: pd.Series,
    price_missing: pd.Series,
    price_invalid: pd.Series,
    retail_num: pd.Series,
    retail_missing: pd.Series,
    retail_invalid: pd.Series,
    discount_num: pd.Series,
    discount_missing: pd.Series,
    discount_invalid: pd.Series,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    retail_values = retail_num.to_numpy(dtype="float64")
    price_values = price_num.to_numpy(dtype="float64")
    usable_retail = (
        ~retail_missing.to_numpy()
        & ~retail_invalid.to_numpy()
        & np.isfinite(retail_values)
        & (retail_values != 0)
    )
    can_derive = (
        discount_missing.to_numpy()
        & ~discount_invalid.to_numpy()
        & ~price_missing.to_numpy()
        & ~price_invalid.to_numpy()
        & np.isfinite(price_values)
        & usable_retail
    )
    derived = np.full(len(price_num), np.nan)
    derived[can_derive] = (
        (retail_values[can_derive] - price_values[can_derive]) / retail_values[can_derive]
    ) * 100
    derived = np.round(derived, 4)
    good = can_derive & np.isfinite(derived) & (derived >= 0) & (derived <= 100)
    bad = can_derive & ~good

    filled = discount_num.to_numpy(dtype="float64").copy()
    filled[good] = derived[good]
    missing = discount_missing.to_numpy().copy()
    missing[can_derive] = False
    invalid = discount_invalid.to_numpy().copy()
    invalid[bad] = True
    return (
        pd.Series(filled, index=price_num.index),
        pd.Series(missing, index=price_num.index),
        pd.Series(invalid, index=price_num.index),
    )


def _numbers(series: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    text = series.fillna("").astype(str).str.strip().str.replace(",", "", regex=False)
    missing = text.eq("")
    parsed = pd.to_numeric(text.where(~missing, np.nan), errors="coerce")
    invalid = ~missing.to_numpy() & ~np.isfinite(parsed.to_numpy(dtype="float64"))
    return parsed, missing, pd.Series(invalid, index=series.index)


def _below_zero(values: pd.Series, missing: pd.Series, invalid: pd.Series) -> pd.Series:
    present = ~missing.to_numpy()
    numeric = values.to_numpy(dtype="float64")
    bad = invalid.to_numpy().copy()
    bad |= present & ~np.isfinite(numeric)
    bad |= present & np.isfinite(numeric) & (numeric < 0)
    return pd.Series(bad, index=values.index)


def _outside_percent(values: pd.Series, missing: pd.Series, invalid: pd.Series) -> pd.Series:
    present = ~missing.to_numpy()
    numeric = values.to_numpy(dtype="float64")
    finite = np.isfinite(numeric)
    bad = invalid.to_numpy().copy()
    bad |= present & ~finite
    bad |= present & finite & ((numeric < 0) | (numeric > 100))
    return pd.Series(bad, index=values.index)


def _labels(table: pd.DataFrame, column: str | None) -> pd.Series:
    if not column:
        return pd.Series([""] * len(table), index=table.index, dtype="object")
    return table[column].fillna("").astype(str).str.strip()
