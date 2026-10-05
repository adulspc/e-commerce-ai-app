"""Read the status of one analysis session."""

from uuid import UUID

from fastapi import APIRouter, Depends

from backend.dependencies import get_store
from backend.models.session_store import SessionStore
from backend.schemas.session import ErrorResponse, SessionStatusResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get(
    "/{session_id}",
    response_model=SessionStatusResponse,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def read_session(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> SessionStatusResponse:
    session = store.get(str(session_id))
    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        created_at=session.created_at,
        original_filename=session.original_filename,
        columns=list(session.columns),
        row_count=session.row_count,
        k=session.k,
        recommended_k=session.recommended_k,
    )
