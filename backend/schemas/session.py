from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["uploaded", "processed", "clustered"]


class ErrorResponse(BaseModel):
    error: str
    message: str


class SessionMetadata(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: datetime
    original_filename: str | None = None
    columns: list[str] = Field(default_factory=list)
    row_count: int | None = None
    k: int | None = None
    recommended_k: int | None = None
    mapping: dict | None = None
    cleaning_report: dict | None = None
    feature_report: dict | None = None
    scaling_report: dict | None = None
    cluster_report: dict | None = None
    optimal_k_report: dict | None = None


class SessionStatusResponse(BaseModel):
    session_id: str
    status: SessionStatus
    created_at: datetime
    original_filename: str | None = None
    columns: list[str] = Field(default_factory=list)
    row_count: int | None = None
    k: int | None = None
    recommended_k: int | None = None
