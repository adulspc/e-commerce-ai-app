"""Cluster reading, dashboard summary, product explorer, and CSV export."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from backend.dependencies import get_store
from backend.models.session_store import SessionStore
from backend.schemas.analysis import (
    ClusterDetailResponse,
    ClusterListResponse,
    DashboardSummary,
    ProductDetail,
    ProductPage,
)
from backend.schemas.session import ErrorResponse
from backend.services.analysis import (
    cluster_detail,
    cluster_summaries,
    clusters_csv,
    dashboard_summary,
    list_products,
    prepare_clustered,
    product_detail,
    products_csv,
)

router = APIRouter(tags=["analysis"])

_ERRORS = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def _report(session_id: UUID, store: SessionStore) -> tuple[object, dict]:
    session = store.get(str(session_id))
    report, changed = prepare_clustered(session)
    if changed:
        store.save(session)
    return session, report


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/clusters", response_model=ClusterListResponse, responses=_ERRORS)
def read_clusters(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> ClusterListResponse:
    session, report = _report(session_id, store)
    return ClusterListResponse(
        session_id=session.session_id,
        k=int(report["k"]),
        clusters=cluster_summaries(report),
    )


@router.get("/api/clusters/{cluster_id}", response_model=ClusterDetailResponse, responses=_ERRORS)
def read_cluster(
    cluster_id: int,
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> ClusterDetailResponse:
    session, report = _report(session_id, store)
    summary = cluster_detail(report, cluster_id)
    return ClusterDetailResponse(session_id=session.session_id, **summary.model_dump())


@router.get("/api/products", response_model=ProductPage, responses=_ERRORS)
def read_products(
    session_id: UUID,
    search: str | None = None,
    cluster: int | None = None,
    category: str | None = None,
    sort: Literal["price_usd", "qty_sold", "sales_value"] | None = None,
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    store: SessionStore = Depends(get_store),
) -> ProductPage:
    session, report = _report(session_id, store)
    return list_products(
        session,
        report,
        search=search,
        cluster=cluster,
        category=category,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/api/products/{product_id}", response_model=ProductDetail, responses=_ERRORS)
def read_product(
    product_id: int,
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> ProductDetail:
    session, report = _report(session_id, store)
    return product_detail(session, report, product_id)


@router.get("/api/dashboard/summary", response_model=DashboardSummary, responses=_ERRORS)
def read_dashboard(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> DashboardSummary:
    session, report = _report(session_id, store)
    return dashboard_summary(session, report)


@router.get("/api/export/products", responses=_ERRORS)
def export_products(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> Response:
    session, report = _report(session_id, store)
    return _csv_response(products_csv(session, report), "products.csv")


@router.get("/api/export/clusters", responses=_ERRORS)
def export_clusters(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> Response:
    _session, report = _report(session_id, store)
    return _csv_response(clusters_csv(report), "clusters.csv")
