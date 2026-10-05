"""Upload a CSV, preview it, and clean it with a confirmed column mapping."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from backend.dependencies import get_store
from backend.models.session_store import SessionStore
from backend.schemas.dataset import (
    ColumnMappingInput,
    DatasetCleaningResponse,
    DatasetUploadResponse,
    FeatureReport,
    ProcessRequest,
    ScalingReport,
    SuggestedMapping,
)
from backend.schemas.session import ErrorResponse
from backend.services.data_cleaning import apply_cleaning
from backend.services.feature_engineering import summarize_features
from backend.services.scaling import ensure_scaler
from backend.services.dataset_io import missing_required, parse_csv_bytes, suggest_mapping
from backend.utils.errors import InvalidCsvError, InvalidSessionStateError

router = APIRouter(prefix="/api/dataset", tags=["dataset"])
SOURCE_NAME = "source.csv"


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    responses={400: {"model": ErrorResponse}},
)
async def upload_dataset(
    file: UploadFile = File(...),
    store: SessionStore = Depends(get_store),
) -> DatasetUploadResponse:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".csv"):
        raise InvalidCsvError("รองรับเฉพาะไฟล์นามสกุล .csv")

    content = await file.read()
    parsed = parse_csv_bytes(content)
    session = store.create(original_filename=filename)
    (session.directory / SOURCE_NAME).write_bytes(content)
    session.columns = parsed.columns
    session.row_count = parsed.row_count
    store.save(session)
    return _response(session.session_id, filename, parsed.columns, parsed.preview, parsed.row_count)


@router.get(
    "/preview",
    response_model=DatasetUploadResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def preview_dataset(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> DatasetUploadResponse:
    session = store.get(str(session_id))
    path = session.directory / SOURCE_NAME
    if not path.is_file():
        raise InvalidCsvError("ไม่พบไฟล์ของชุดข้อมูลนี้ ลองอัปโหลดอีกครั้ง")
    parsed = parse_csv_bytes(path.read_bytes())
    filename = session.original_filename or "upload.csv"
    return _response(session.session_id, filename, parsed.columns, parsed.preview, parsed.row_count)


@router.post(
    "/process",
    response_model=DatasetCleaningResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def process_dataset(
    body: ProcessRequest,
    store: SessionStore = Depends(get_store),
) -> DatasetCleaningResponse:
    session = store.get(str(body.session_id))
    apply_cleaning(session, body.mapping)
    store.save(session)
    return _cleaning_response(session)


@router.get(
    "/cleaning",
    response_model=DatasetCleaningResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
def read_cleaning(
    session_id: UUID,
    store: SessionStore = Depends(get_store),
) -> DatasetCleaningResponse:
    session = store.get(str(session_id))
    if session.cleaning_report is None or session.mapping is None:
        raise InvalidSessionStateError(actual=session.status)
    if session.scaling_report is None or session.scaler is None:
        ensure_scaler(session)
        store.save(session)
    return _cleaning_response(session)


def _cleaning_response(session) -> DatasetCleaningResponse:
    return DatasetCleaningResponse(
        session_id=session.session_id,
        status=session.status,
        filename=session.original_filename,
        mapping=ColumnMappingInput.model_validate(session.mapping),
        cleaning_report=session.cleaning_report,
        feature_report=_feature_report(session),
        scaling_report=_scaling_report(session),
    )


def _scaling_report(session) -> ScalingReport:
    if session.scaling_report is not None:
        return ScalingReport.model_validate(session.scaling_report)
    return ensure_scaler(session)


def _feature_report(session) -> FeatureReport:
    if session.feature_report is not None:
        return FeatureReport.model_validate(session.feature_report)
    if session.frame is not None and {"price_usd", "qty_sold"}.issubset(session.frame.columns):
        return summarize_features(session.frame)
    raise InvalidSessionStateError(actual=session.status)


def _response(
    session_id: str,
    filename: str,
    columns: list[str],
    preview: list[dict[str, str]],
    row_count: int,
) -> DatasetUploadResponse:
    mapping: SuggestedMapping = suggest_mapping(columns)
    return DatasetUploadResponse(
        session_id=session_id,
        filename=filename,
        columns=columns,
        row_count=row_count,
        preview=preview,
        suggested_mapping=mapping,
        missing_required=missing_required(mapping),
    )
