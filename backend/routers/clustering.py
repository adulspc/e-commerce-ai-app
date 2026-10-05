"""Fit K-Means for one processed session and read that fit again."""

from uuid import UUID

from fastapi import APIRouter, Depends

from backend.dependencies import get_store
from backend.models.session_store import SessionStore
from backend.schemas.clustering import (
    ClusteringRunRequest,
    ClusteringRunResponse,
    OptimalKReport,
    OptimalKResponse,
)
from backend.schemas.session import ErrorResponse
from backend.services.clustering import compute_optimal_k, ensure_named_report, run_kmeans
from backend.utils.errors import InvalidSessionStateError

router = APIRouter(prefix="/api/clustering", tags=["clustering"])


@router.post(
    "/run",
    response_model=ClusteringRunResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def run_clustering(
    body: ClusteringRunRequest,
    store: SessionStore = Depends(get_store),
) -> ClusteringRunResponse:
    session = store.get(str(body.session_id))
    report = run_kmeans(session, body.k)
    store.save(session)
    return _response(session, report.k, report.inertia, report.clusters)


@router.get(
    "/result",
    response_model=ClusteringRunResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def read_clustering(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> ClusteringRunResponse:
    session = store.get(str(session_id))
    if session.status != "clustered" or session.cluster_report is None:
        raise InvalidSessionStateError(actual=session.status)
    report, changed = ensure_named_report(session)
    if changed:
        store.save(session)
    return _response(session, report["k"], report["inertia"], report["clusters"])


@router.get(
    "/optimal-k",
    response_model=OptimalKResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def read_optimal_k(
    session_id: UUID,
    recalculate: bool = False,
    store: SessionStore = Depends(get_store),
) -> OptimalKResponse:
    session = store.get(str(session_id))
    if not recalculate and session.optimal_k_report is not None:
        report = OptimalKReport.model_validate(session.optimal_k_report)
    else:
        report = compute_optimal_k(session)
        store.save(session)
    return OptimalKResponse(session_id=session.session_id, **report.model_dump())


def _response(session, k: int, inertia: float, clusters) -> ClusteringRunResponse:
    return ClusteringRunResponse(
        session_id=session.session_id,
        status=session.status,
        k=k,
        inertia=inertia,
        clusters=clusters,
    )
