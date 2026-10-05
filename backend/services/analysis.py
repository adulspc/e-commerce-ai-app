"""Read clustered products, dashboard figures, and CSV exports.

Scatter points are a stratified sample: at most 2,000 rows and at most 400
rows from each cluster. The sample uses random_state 42.
"""

from __future__ import annotations

import csv
import io

import numpy as np
import pandas as pd

from backend.schemas.analysis import (
    ClusterSummary,
    DashboardSummary,
    ProductDetail,
    ProductPage,
    ProductRow,
    ScatterPoint,
)
from backend.services.cluster_interpretation import explain_product
from backend.services.clustering import ensure_named_report
from backend.services.scaling import FEATURE_COLUMNS
from backend.utils.errors import ClusterNotFoundError, InvalidSessionStateError, ProductNotFoundError

SCATTER_POINT_LIMIT = 2000
SCATTER_PER_CLUSTER = 400
SCATTER_RANDOM_STATE = 42

PRODUCT_EXPORT_COLUMNS = (
    "product_name",
    "category",
    "price_usd",
    "pct_discount",
    "qty_sold",
    "sales_value",
    "cluster",
    "cluster_name",
)
CLUSTER_EXPORT_COLUMNS = (
    "cluster",
    "cluster_name",
    "product_count",
    "avg_price",
    "avg_discount",
    "avg_qty_sold",
    "avg_sales_value",
    "characteristics",
    "recommendations",
)
SORT_FIELDS = ("price_usd", "qty_sold", "sales_value")


def prepare_clustered(session) -> tuple[dict, bool]:
    if session.status != "clustered" or session.frame is None or "cluster" not in session.frame.columns:
        raise InvalidSessionStateError(actual=session.status)
    return ensure_named_report(session)


def cluster_summaries(report: dict) -> list[ClusterSummary]:
    return [_summary(cluster) for cluster in report["clusters"]]


def cluster_detail(report: dict, cluster_id: int) -> ClusterSummary:
    for cluster in report["clusters"]:
        if int(cluster["cluster_id"]) == cluster_id:
            return _summary(cluster)
    raise ClusterNotFoundError()


def list_products(
    session,
    report: dict,
    *,
    search: str | None,
    cluster: int | None,
    category: str | None,
    sort: str | None,
    order: str,
    page: int,
    page_size: int,
) -> ProductPage:
    frame = session.frame
    names = _names(report)
    categories = sorted(
        {str(value) for value in frame["category"].tolist()},
        key=str.casefold,
    )
    view = frame
    needle = (search or "").strip()
    if needle:
        mask = frame["product_name"].astype(str).str.casefold().str.contains(needle.casefold(), regex=False)
        view = frame.loc[mask]
    if cluster is not None:
        view = view.loc[view["cluster"] == cluster]
    if category is not None and category.strip():
        view = view.loc[view["category"].astype(str) == category]
    if sort in SORT_FIELDS:
        view = view.sort_values(
            [sort, "source_row"],
            ascending=[order == "asc", True],
            kind="mergesort",
        )
    else:
        view = view.sort_values("source_row", kind="mergesort")
    total = int(len(view))
    start = (page - 1) * page_size
    page_rows = view.iloc[start : start + page_size]
    return ProductPage(
        session_id=session.session_id,
        page=page,
        page_size=page_size,
        total=total,
        categories=categories,
        products=[_product_row(row, names) for row in page_rows.to_dict(orient="records")],
    )


def product_detail(session, report: dict, product_id: int) -> ProductDetail:
    frame = session.frame
    matches = frame.loc[frame["source_row"] == product_id]
    if matches.empty:
        raise ProductNotFoundError()
    row = matches.iloc[0]
    cluster_id = int(row["cluster"])
    names = _names(report)
    members = frame.loc[frame["cluster"] == cluster_id, FEATURE_COLUMNS]
    means = members.mean().to_dict()
    values = {column: float(row[column]) for column in FEATURE_COLUMNS}
    explanation = explain_product(values, means, names[cluster_id])
    listed = _product_row(row.to_dict(), names)
    return ProductDetail(**listed.model_dump(), explanation=explanation)


def dashboard_summary(session, report: dict) -> DashboardSummary:
    frame = session.frame
    points, sampled = sample_scatter(frame)
    summaries = cluster_summaries(report)
    return DashboardSummary(
        session_id=session.session_id,
        k=int(report["k"]),
        total_products=int(len(frame)),
        average_price=float(frame["price_usd"].mean()),
        average_discount=float(frame["pct_discount"].mean()),
        total_quantity_sold=float(frame["qty_sold"].sum()),
        total_sales_value=float(frame["sales_value"].sum()),
        number_of_clusters=len(summaries),
        clusters=summaries,
        scatter=[
            ScatterPoint(
                price_usd=float(row.price_usd),
                pct_discount=float(row.pct_discount),
                qty_sold=float(row.qty_sold),
                sales_value=float(row.sales_value),
                cluster=int(row.cluster),
            )
            for row in points.itertuples(index=False)
        ],
        scatter_sample_size=int(len(points)),
        scatter_sampled=sampled,
    )


def products_csv(session, report: dict) -> str:
    names = _names(report)
    frame = session.frame.sort_values("source_row", kind="mergesort")
    rows = []
    for row in frame.itertuples(index=False):
        cluster_id = int(row.cluster)
        rows.append(
            [
                row.product_name,
                row.category,
                row.price_usd,
                row.pct_discount,
                row.qty_sold,
                row.sales_value,
                cluster_id,
                names[cluster_id],
            ]
        )
    return _csv(PRODUCT_EXPORT_COLUMNS, rows)


def clusters_csv(report: dict) -> str:
    rows = []
    for cluster in cluster_summaries(report):
        rows.append(
            [
                cluster.cluster_id,
                cluster.cluster_name,
                cluster.product_count,
                cluster.avg_price,
                cluster.avg_discount,
                cluster.avg_qty_sold,
                cluster.avg_sales_value,
                cluster.characteristics,
                " | ".join(cluster.recommendations),
            ]
        )
    return _csv(CLUSTER_EXPORT_COLUMNS, rows)


def allocate_scatter(counts: dict[int, int]) -> dict[int, int]:
    caps = {
        int(cluster_id): min(int(count), SCATTER_PER_CLUSTER)
        for cluster_id, count in counts.items()
        if int(count) > 0
    }
    if not caps or sum(caps.values()) <= SCATTER_POINT_LIMIT:
        return caps
    cluster_ids = sorted(caps)
    allocation = {cluster_id: 0 for cluster_id in cluster_ids}
    if SCATTER_POINT_LIMIT >= len(cluster_ids):
        for cluster_id in cluster_ids:
            allocation[cluster_id] = 1
    remaining_budget = SCATTER_POINT_LIMIT - sum(allocation.values())
    remaining_cap = {
        cluster_id: caps[cluster_id] - allocation[cluster_id] for cluster_id in cluster_ids
    }
    weight = sum(remaining_cap.values())
    if remaining_budget <= 0 or weight <= 0:
        return allocation
    raw = {
        cluster_id: remaining_budget * remaining_cap[cluster_id] / weight
        for cluster_id in cluster_ids
    }
    for cluster_id in cluster_ids:
        allocation[cluster_id] += min(int(raw[cluster_id]), remaining_cap[cluster_id])
    leftover = SCATTER_POINT_LIMIT - sum(allocation.values())
    remainder_order = sorted(
        cluster_ids,
        key=lambda cluster_id: (
            raw[cluster_id] - int(raw[cluster_id]),
            remaining_cap[cluster_id],
            -cluster_id,
        ),
        reverse=True,
    )
    for cluster_id in remainder_order:
        if leftover <= 0:
            break
        if allocation[cluster_id] < caps[cluster_id]:
            allocation[cluster_id] += 1
            leftover -= 1
    return allocation


def sample_scatter(frame: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    work = frame.reset_index(drop=True)
    counts = {int(cluster_id): int(count) for cluster_id, count in work.groupby("cluster").size().items()}
    allocation = allocate_scatter(counts)
    sampled = sum(allocation.values()) < len(work)
    generator = np.random.default_rng(SCATTER_RANDOM_STATE)
    chosen_positions: list[int] = []
    for cluster_id in sorted(allocation):
        positions = np.flatnonzero(work["cluster"].to_numpy() == cluster_id)
        take = allocation[cluster_id]
        if take < len(positions):
            picked = generator.choice(positions, size=take, replace=False)
            picked.sort()
        else:
            picked = positions
        chosen_positions.extend(int(position) for position in picked)
    columns = [*FEATURE_COLUMNS, "cluster"]
    if not chosen_positions:
        return work.loc[:, columns].iloc[0:0], False
    return work.loc[chosen_positions, columns].reset_index(drop=True), sampled


def _summary(cluster: dict) -> ClusterSummary:
    return ClusterSummary(
        cluster_id=int(cluster["cluster_id"]),
        cluster_name=str(cluster["cluster_name"]),
        product_count=int(cluster["product_count"]),
        avg_price=float(cluster["centroid_price_usd"]),
        avg_discount=float(cluster["centroid_pct_discount"]),
        avg_qty_sold=float(cluster["centroid_qty_sold"]),
        avg_sales_value=float(cluster["centroid_sales_value"]),
        characteristics=str(cluster["characteristics"]),
        recommendations=list(cluster["recommendations"]),
    )


def _names(report: dict) -> dict[int, str]:
    return {int(cluster["cluster_id"]): str(cluster["cluster_name"]) for cluster in report["clusters"]}


def _product_row(row: dict, names: dict[int, str]) -> ProductRow:
    cluster_id = int(row["cluster"])
    return ProductRow(
        id=str(int(row["source_row"])),
        product_name=str(row["product_name"]),
        category=str(row["category"]),
        price_usd=float(row["price_usd"]),
        pct_discount=float(row["pct_discount"]),
        qty_sold=float(row["qty_sold"]),
        sales_value=float(row["sales_value"]),
        cluster=cluster_id,
        cluster_name=names[cluster_id],
    )


def _csv(headers: tuple[str, ...], rows: list[list[object]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue()
