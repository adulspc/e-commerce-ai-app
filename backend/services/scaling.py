"""Fit one StandardScaler on the four model features of a session."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from backend.schemas.dataset import FeatureScale, ScalingReport
from backend.utils.errors import InvalidSessionStateError, MissingColumnsError, NonNumericValueError

FEATURE_COLUMNS = ["price_usd", "pct_discount", "qty_sold", "sales_value"]
SCALER_FILENAME = "scaler.joblib"


def fit_scaler(frame: pd.DataFrame) -> tuple[StandardScaler, ScalingReport]:
    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise MissingColumnsError(missing)

    values = frame.loc[:, FEATURE_COLUMNS]
    matrix = values.to_numpy(dtype="float64")
    if matrix.size == 0 or not np.isfinite(matrix).all():
        raise NonNumericValueError()

    scaler = StandardScaler()
    scaler.fit(values)
    return scaler, report_from_scaler(scaler)


def report_from_scaler(scaler: StandardScaler) -> ScalingReport:
    names = [str(name) for name in scaler.feature_names_in_]
    features = [
        FeatureScale(
            feature=name,
            mean=float(scaler.mean_[index]),
            std=float(scaler.scale_[index]),
            constant=bool(np.isclose(scaler.var_[index], 0.0)),
        )
        for index, name in enumerate(names)
    ]
    return ScalingReport(sample_count=int(scaler.n_samples_seen_), features=features)


def ensure_scaler(session) -> ScalingReport:
    if session.scaler is not None and session.scaling_report is not None:
        return ScalingReport.model_validate(session.scaling_report)
    if session.frame is None:
        raise InvalidSessionStateError(actual=session.status)
    scaler, report = fit_scaler(session.frame)
    session.scaler = scaler
    session.scaling_report = report.model_dump()
    save_scaler(session.directory, scaler)
    return report


def save_scaler(directory: Path, scaler: StandardScaler) -> None:
    target = directory / SCALER_FILENAME
    temporary = directory / f"{SCALER_FILENAME}.tmp"
    joblib.dump(scaler, temporary)
    temporary.replace(target)


def load_scaler(directory: Path) -> StandardScaler | None:
    path = directory / SCALER_FILENAME
    if not path.is_file():
        return None
    try:
        scaler = joblib.load(path)
    except Exception:
        return None
    if not isinstance(scaler, StandardScaler):
        return None
    names = [str(name) for name in getattr(scaler, "feature_names_in_", [])]
    if names != FEATURE_COLUMNS:
        return None
    return scaler
