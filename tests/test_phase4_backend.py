import uuid

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.utils.errors import (
    DatasetTooSmallError,
    InvalidKError,
    InvalidSessionStateError,
    KTooLargeError,
    MissingColumnsError,
)
from backend.utils.validation import validate_k


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_missing_session_returns_thai_message(client):
    missing = uuid.uuid4()
    response = client.get(f"/api/sessions/{missing}")
    body = response.json()
    assert response.status_code == 404
    assert body["error"] == "session_not_found"
    assert "อัปโหลด" in body["message"]


def test_invalid_session_id_is_rejected(client):
    response = client.get("/api/sessions/not-a-uuid")
    body = response.json()
    assert response.status_code == 422
    assert body["error"] == "invalid_request"
    assert "ไม่ถูกต้อง" in body["message"]


def test_session_roundtrip_reloads_from_disk(store):
    created = store.create(original_filename="products.csv")
    created.columns = ["price_usd", "qty_sold"]
    created.row_count = 120
    store.save(created)

    reloaded = SessionStore(store.base_dir)
    session = reloaded.get(created.session_id)
    assert session.status == "uploaded"
    assert session.original_filename == "products.csv"
    assert session.columns == ["price_usd", "qty_sold"]
    assert session.row_count == 120
    assert session.frame is None
    assert session.scaler is None
    assert session.model is None


def test_session_endpoint_returns_saved_status(client, store):
    created = store.create(original_filename="products.csv")
    response = client.get(f"/api/sessions/{created.session_id}")
    body = response.json()
    assert response.status_code == 200
    assert body["session_id"] == created.session_id
    assert body["status"] == "uploaded"
    assert body["original_filename"] == "products.csv"
    assert body["k"] is None


def test_status_transition_rules(store):
    session = store.create()
    session.transition("processed")
    assert session.status == "processed"
    session.transition("clustered")
    assert session.status == "clustered"
    with pytest.raises(InvalidSessionStateError):
        session.transition("uploaded")


def test_validate_k_rules():
    validate_k(4, 100)
    with pytest.raises(InvalidKError):
        validate_k(1, 100)
    with pytest.raises(InvalidKError):
        validate_k(11, 100)
    with pytest.raises(DatasetTooSmallError):
        validate_k(2, 9)
    with pytest.raises(KTooLargeError):
        validate_k(10, 10)


def test_missing_columns_message_lists_fields():
    error = MissingColumnsError(["price_usd", "qty_sold"])
    assert error.code == "missing_columns"
    assert "price_usd" in error.message
    assert "qty_sold" in error.message


def test_unexpected_error_hides_internal_detail(client):
    def explode():
        raise RuntimeError("secret database password")

    app.dependency_overrides[get_store] = explode
    response = client.get(f"/api/sessions/{uuid.uuid4()}")
    body = response.json()
    assert response.status_code == 500
    assert body["error"] == "server_error"
    assert "secret" not in body["message"]
