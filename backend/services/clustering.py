"""Fit K-Means on the scaled features stored with one session."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from backend.schemas.clustering import ClusterReport, OptimalKPoint, OptimalKReport
from backend.services.cluster_interpretation import describe_clusters
from backend.services.scaling import FEATURE_COLUMNS, ensure_scaler
from backend.utils.errors import DatasetTooSmallError, InvalidSessionStateError, MachineLearningError
from backend.utils.validation import MIN_SAMPLES, validate_k

MODEL_FILENAME = "model.joblib"
SILHOUETTE_SAMPLE_SIZE = 5000
MIN_CURVE_K = 2
MAX_CURVE_K = 10


def run_kmeans(session, k: int) -> ClusterReport:
    if session.status == "uploaded" or session.frame is None:
        raise InvalidSessionStateError(actual=session.status)
    ensure_scaler(session)
    validate_k(k, len(session.frame))

    scaled = session.scaler.transform(session.frame.loc[:, FEATURE_COLUMNS])
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    try:
        model.fit(scaled)
    except Exception as exc:
        raise MachineLearningError() from exc

    labels = np.asarray(model.labels_, dtype=int)
    session.frame["cluster"] = labels
    centers = session.scaler.inverse_transform(model.cluster_centers_)
    report = ClusterReport(
        k=k,
        inertia=float(model.inertia_),
        clusters=describe_clusters(session.frame, centers),
    )
    session.k = k
    session.model = model
    session.cluster_report = report.model_dump()
    save_model(session.directory, model)
    session.transition("clustered")
    return report


def ensure_named_report(session) -> tuple[dict, bool]:
    report = session.cluster_report or {}
    clusters = report.get("clusters") or []
    if clusters and "cluster_name" in clusters[0]:
        return report, False
    if session.frame is None or "cluster" not in session.frame.columns:
        raise InvalidSessionStateError(actual=session.status)
    centers = None
    if session.model is not None and session.scaler is not None:
        centers = session.scaler.inverse_transform(session.model.cluster_centers_)
    named = describe_clusters(session.frame, centers)
    inertia = report.get("inertia")
    if inertia is None and session.model is not None:
        inertia = float(session.model.inertia_)
    updated = {
        "k": int(report.get("k", session.k or len(named))),
        "inertia": float(inertia or 0.0),
        "clusters": [item.model_dump() for item in named],
    }
    session.cluster_report = updated
    return updated, True


def save_model(directory: Path, model: KMeans) -> None:
    target = directory / MODEL_FILENAME
    temporary = directory / f"{MODEL_FILENAME}.tmp"
    joblib.dump(model, temporary)
    temporary.replace(target)


def delete_model(directory: Path) -> None:
    path = directory / MODEL_FILENAME
    if path.is_file():
        path.unlink()


def load_model(directory: Path) -> KMeans | None:
    path = directory / MODEL_FILENAME
    if not path.is_file():
        return None
    try:
        model = joblib.load(path)
    except Exception:
        return None
    if not isinstance(model, KMeans):
        return None
    if int(model.random_state) != 42 or int(model.n_init) != 10:
        return None
    return model


def attach_cluster_labels(frame: pd.DataFrame | None, model: KMeans | None) -> pd.DataFrame | None:
    if frame is None or model is None:
        return frame
    labels = getattr(model, "labels_", None)
    if labels is None or len(labels) != len(frame):
        return frame
    labeled = frame.copy()
    labeled["cluster"] = np.asarray(labels, dtype=int)
    return labeled


def compute_optimal_k(session) -> OptimalKReport:
    if session.status == "uploaded" or session.frame is None:
        raise InvalidSessionStateError(actual=session.status)
    ensure_scaler(session)
    sample_count = len(session.frame)
    if sample_count < MIN_SAMPLES:
        raise DatasetTooSmallError()

    scaled = session.scaler.transform(session.frame.loc[:, FEATURE_COLUMNS])
    sample_size = min(SILHOUETTE_SAMPLE_SIZE, sample_count)
    sampled = sample_count > SILHOUETTE_SAMPLE_SIZE
    upper = min(MAX_CURVE_K, sample_count - 1)
    points: list[OptimalKPoint] = []
    for k in range(MIN_CURVE_K, upper + 1):
        model = KMeans(n_clusters=k, random_state=42, n_init=10)
        try:
            model.fit(scaled)
            score = silhouette_score(
                scaled,
                model.labels_,
                sample_size=sample_size if sampled else None,
                random_state=42,
            )
        except Exception as exc:
            raise MachineLearningError() from exc
        points.append(
            OptimalKPoint(k=k, inertia=float(model.inertia_), silhouette=float(score))
        )

    recommended = max(points, key=lambda point: (point.silhouette, -point.k))
    report = OptimalKReport(
        sample_count=sample_count,
        silhouette_sample_size=sample_size,
        silhouette_sampled=sampled,
        recommended_k=recommended.k,
        elbow_k=elbow_k(points),
        scores=points,
    )
    session.recommended_k = report.recommended_k
    session.optimal_k_report = report.model_dump()
    return report


def elbow_k(scores: list[OptimalKPoint]) -> int:
    if len(scores) == 1:
        return scores[0].k
    ks = np.array([point.k for point in scores], dtype=float)
    values = np.array([point.inertia for point in scores], dtype=float)
    k_span = float(ks[-1] - ks[0])
    value_span = float(values.max() - values.min())
    k_norm = (ks - ks[0]) / k_span if k_span else np.zeros_like(ks)
    value_norm = (values - values.min()) / value_span if value_span else np.zeros_like(values)
    start = np.array([k_norm[0], value_norm[0]])
    end = np.array([k_norm[-1], value_norm[-1]])
    distances = [
        _line_distance(start, end, np.array([k_norm[index], value_norm[index]]))
        for index in range(len(scores))
    ]
    return int(scores[int(np.argmax(distances))].k)


def _line_distance(start: np.ndarray, end: np.ndarray, point: np.ndarray) -> float:
    line = end - start
    length = float(np.hypot(line[0], line[1]))
    if length == 0:
        return 0.0
    return abs(float(line[0] * (start[1] - point[1]) - line[1] * (start[0] - point[0]))) / length
