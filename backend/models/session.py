"""One uploaded dataset and the model fitted on it."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.schemas.session import SessionStatus
from backend.utils.errors import InvalidSessionStateError

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "uploaded": {"processed"},
    "processed": {"processed", "clustered"},
    "clustered": {"processed", "clustered"},
}


@dataclass
class AnalysisSession:
    session_id: str
    status: SessionStatus
    created_at: datetime
    directory: Path
    original_filename: str | None = None
    columns: list[str] = field(default_factory=list)
    row_count: int | None = None
    k: int | None = None
    recommended_k: int | None = None
    mapping: dict | None = None
    cleaning_report: dict | None = None
    feature_report: dict | None = None
    scaling_report: dict | None = None
    cluster_report: dict | None = None
    optimal_k_report: dict | None = None
    frame: Any = None
    scaler: Any = None
    model: Any = None

    def transition(self, new_status: SessionStatus) -> None:
        allowed = ALLOWED_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise InvalidSessionStateError(actual=self.status)
        self.status = new_status
