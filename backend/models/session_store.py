"""In-memory sessions with a metadata file under data/sessions/<id>/."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.models.session import AnalysisSession
from backend.schemas.session import SessionMetadata
from backend.utils.errors import SessionNotFoundError
from backend.utils.paths import SESSIONS_DIR


class SessionStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or SESSIONS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, AnalysisSession] = {}
        self._lock = threading.Lock()

    def create(self, original_filename: str | None = None) -> AnalysisSession:
        session_id = str(uuid.uuid4())
        directory = self._directory(session_id)
        directory.mkdir(parents=True, exist_ok=False)
        session = AnalysisSession(
            session_id=session_id,
            status="uploaded",
            created_at=datetime.now(timezone.utc),
            directory=directory,
            original_filename=original_filename,
        )
        with self._lock:
            self._sessions[session_id] = session
        self.save(session)
        return session

    def get(self, session_id: str) -> AnalysisSession:
        canonical = _canonical_id(session_id)
        with self._lock:
            cached = self._sessions.get(canonical)
            if cached is not None:
                return cached
        session = self._read(canonical)
        with self._lock:
            self._sessions[canonical] = session
        return session

    def save(self, session: AnalysisSession) -> None:
        metadata = SessionMetadata(
            session_id=session.session_id,
            status=session.status,
            created_at=session.created_at,
            original_filename=session.original_filename,
            columns=list(session.columns),
            row_count=session.row_count,
            k=session.k,
            recommended_k=session.recommended_k,
            mapping=session.mapping,
            cleaning_report=session.cleaning_report,
            feature_report=session.feature_report,
            scaling_report=session.scaling_report,
            cluster_report=session.cluster_report,
            optimal_k_report=session.optimal_k_report,
        )
        payload = metadata.model_dump(mode="json")
        path = session.directory / "meta.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)

    def _directory(self, session_id: str) -> Path:
        return self.base_dir / session_id

    def _read(self, session_id: str) -> AnalysisSession:
        path = self._directory(session_id) / "meta.json"
        if not path.is_file():
            raise SessionNotFoundError()
        metadata = SessionMetadata.model_validate_json(path.read_text(encoding="utf-8"))
        if metadata.session_id != session_id:
            raise SessionNotFoundError()
        directory = self._directory(session_id)
        frame = _load_frame(directory)
        model = _load_model(directory)
        return AnalysisSession(
            session_id=metadata.session_id,
            status=metadata.status,
            created_at=metadata.created_at,
            directory=directory,
            original_filename=metadata.original_filename,
            columns=list(metadata.columns),
            row_count=metadata.row_count,
            k=metadata.k,
            recommended_k=metadata.recommended_k,
            mapping=metadata.mapping,
            cleaning_report=metadata.cleaning_report,
            feature_report=metadata.feature_report,
            scaling_report=metadata.scaling_report,
            cluster_report=metadata.cluster_report,
            optimal_k_report=metadata.optimal_k_report,
            frame=_attach_labels(frame, model),
            scaler=_load_scaler(directory),
            model=model,
        )


def _load_frame(directory: Path):
    from backend.services.data_cleaning import load_cleaned_frame

    return load_cleaned_frame(directory)


def _load_scaler(directory: Path):
    from backend.services.scaling import load_scaler

    return load_scaler(directory)


def _load_model(directory: Path):
    from backend.services.clustering import load_model

    return load_model(directory)


def _attach_labels(frame, model):
    from backend.services.clustering import attach_cluster_labels

    return attach_cluster_labels(frame, model)


def _canonical_id(session_id: str) -> str:
    try:
        parsed = uuid.UUID(session_id)
    except ValueError as exc:
        raise SessionNotFoundError() from exc
    return str(parsed)


session_store = SessionStore()
