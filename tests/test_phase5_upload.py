import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.dataset_io import MAX_UPLOAD_BYTES, parse_csv_bytes
from backend.utils.errors import InvalidCsvError
from backend.utils.paths import DATA_DIR

REAL_DATASET = DATA_DIR / "CLEAN-Ecommerce-products-all_categories.csv (1).csv"


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload(client: TestClient, name: str, content: bytes, content_type: str = "text/csv"):
    return client.post(
        "/api/dataset/upload",
        files={"file": (name, content, content_type)},
    )


def test_upload_suggests_aliases_and_preview(client, store):
    content = "product_name,price,retail_price,units_sold\nเสื้อ,10,20,5\n".encode()
    response = _upload(client, "shop.csv", content)
    body = response.json()

    assert response.status_code == 200
    assert body["row_count"] == 1
    assert body["preview"] == [
        {
            "product_name": "เสื้อ",
            "price": "10",
            "retail_price": "20",
            "units_sold": "5",
        }
    ]
    assert body["suggested_mapping"]["price_usd"] == "price"
    assert body["suggested_mapping"]["retail_price"] == "retail_price"
    assert body["suggested_mapping"]["qty_sold"] == "units_sold"
    assert body["suggested_mapping"]["product_name"] == "product_name"
    assert body["suggested_mapping"]["pct_discount"] is None
    assert body["missing_required"] == []

    session = store.get(body["session_id"])
    assert session.status == "uploaded"
    assert session.row_count == 1
    assert (session.directory / "source.csv").read_bytes() == content

    preview = client.get("/api/dataset/preview", params={"session_id": body["session_id"]})
    assert preview.status_code == 200
    assert preview.json()["preview"] == body["preview"]


def test_upload_reads_utf8_bom(client):
    content = b"\xef\xbb\xbfprice_usd,qty_sold,pct_discount\n1.5,3,10\n"
    response = _upload(client, "bom.csv", content)
    body = response.json()
    assert response.status_code == 200
    assert body["suggested_mapping"]["price_usd"] == "price_usd"
    assert body["suggested_mapping"]["qty_sold"] == "qty_sold"
    assert body["suggested_mapping"]["pct_discount"] == "pct_discount"


def test_semicolon_file_is_read(client):
    content = "title;final_price_usd;quantity_sold;category\nA;1.5;3;shoes\n".encode()
    response = _upload(client, "semi.csv", content)
    body = response.json()
    assert response.status_code == 200
    assert body["suggested_mapping"]["price_usd"] == "final_price_usd"
    assert body["suggested_mapping"]["qty_sold"] == "quantity_sold"
    assert body["suggested_mapping"]["product_name"] == "title"
    assert body["suggested_mapping"]["category"] == "category"
    assert body["missing_required"] == ["pct_discount"]


def test_each_upload_creates_a_new_session(client):
    content = b"price_usd,qty_sold,pct_discount\n1,2,3\n"
    first = _upload(client, "a.csv", content).json()["session_id"]
    second = _upload(client, "b.csv", content).json()["session_id"]
    assert first != second


def test_reject_non_csv_extension(client):
    response = _upload(client, "notes.txt", b"price_usd,qty_sold\n1,2\n")
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "invalid_csv"
    assert ".csv" in body["message"]


def test_reject_header_only_file(client):
    response = _upload(client, "empty.csv", b"price_usd,qty_sold\n")
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "empty_dataset"


def test_reject_duplicate_columns(client):
    response = _upload(client, "dup.csv", b"price,price\n1,2\n")
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "invalid_csv"
    assert "ซ้ำ" in body["message"]


def test_reject_one_column_file(client):
    response = _upload(client, "one.csv", "hello\nworld\n".encode())
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_csv"


def test_preview_unknown_session(client):
    response = client.get("/api/dataset/preview", params={"session_id": str(uuid.uuid4())})
    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"


def test_file_size_guard():
    with pytest.raises(InvalidCsvError):
        parse_csv_bytes(b"x" * (MAX_UPLOAD_BYTES + 1))


def test_real_shein_file_mapping(client):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")
    content = Path(REAL_DATASET).read_bytes()
    response = _upload(client, REAL_DATASET.name, content)
    body = response.json()

    assert response.status_code == 200
    assert body["row_count"] == 82105
    assert body["columns"][3:6] == ["price_usd", "pct_discount", "qty_sold"]
    mapping = body["suggested_mapping"]
    assert mapping["price_usd"] == "price_usd"
    assert mapping["pct_discount"] == "pct_discount"
    assert mapping["qty_sold"] == "qty_sold"
    assert mapping["product_name"] == "product_title"
    assert mapping["category"] == "category_name"
    assert mapping["retail_price"] is None
    assert body["missing_required"] == []
    assert len(body["preview"]) == 20
    assert body["preview"][0]["price_usd"] == "2.03"
    assert "Massage Gun" in body["preview"][0]["product_title"]
