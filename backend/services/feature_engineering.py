"""Build sales_value from the cleaned price_usd and qty_sold columns.

Cleaning already resolves pct_discount. This step multiplies price by
quantity on every remaining row and summarizes that feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.schemas.dataset import FeatureReport
from backend.utils.errors import MissingColumnsError, NonNumericValueError


def add_sales_value(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in ("price_usd", "qty_sold") if column not in frame.columns]
    if missing:
        raise MissingColumnsError(missing)

    result = frame.copy()
    price = pd.to_numeric(result["price_usd"], errors="coerce").to_numpy(dtype="float64")
    quantity = pd.to_numeric(result["qty_sold"], errors="coerce").to_numpy(dtype="float64")
    if not np.isfinite(price).all() or not np.isfinite(quantity).all():
        raise NonNumericValueError()

    result["sales_value"] = price * quantity
    return result


def summarize_features(frame: pd.DataFrame) -> FeatureReport:
    if "sales_value" not in frame.columns:
        frame = add_sales_value(frame)
    values = pd.to_numeric(frame["sales_value"], errors="coerce")
    if values.empty or not np.isfinite(values.to_numpy(dtype="float64")).all():
        raise NonNumericValueError()
    return FeatureReport(
        row_count=int(len(frame)),
        min_sales_value=float(values.min()),
        median_sales_value=float(values.median()),
        mean_sales_value=float(values.mean()),
        max_sales_value=float(values.max()),
    )
