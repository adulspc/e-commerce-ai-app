import uuid

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.utils.paths import DATA_DIR

REAL_DATASET = DATA_DIR / "CLEAN-Ecommerce-products-all_categories.csv (1).csv"

BASIC_MAPPING = {
    "price_usd": "price_usd",
    "pct_discount": "pct_discount",
    "retail_price": None,
    "qty_sold": "qty_sold",
    "product_name": None,
    "category": None,
}

SHEIN_MAPPING = {
    "price_usd": "price_usd",
    "pct_discount": "pct_discount",
    "retail_price": None,
    "qty_sold": "qty_sold",
    "product_name": "product_title",
    "category": "category_name",
}


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _upload(client: TestClient, name: str, content: str):
    return client.post(
        "/api/dataset/upload",
        files={"file": (name, content.encode(), "text/csv")},
    )


def _process(client: TestClient, session_id: str, mapping: dict):
    return client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": mapping},
    )


def test_cleaning_drops_invalid_missing_and_duplicate_rows(client, store):
    content = "\n".join(
        [
            "product_title,category_name,price_usd,pct_discount,qty_sold",
            "เสื้อ,cat,10,0,5",
            "เสื้อ,cat,10,0,5",
            "ว่างส่วนลด,cat,10,,5",
            "ราคาติดลบ,cat,-1,10,5",
            "ส่วนลดเกิน,cat,8,101,5",
            "ไม่ใช่ตัวเลข,cat,abc,10,5",
            "ครบร้อย,cat,3,100,1",
            "ราคาศูนย์,cat,0,10,2",
        ]
    )
    uploaded = _upload(client, "shop.csv", content)
    session_id = uploaded.json()["session_id"]

    early = client.get("/api/dataset/cleaning", params={"session_id": session_id})
    assert early.status_code == 409

    response = _process(client, session_id, SHEIN_MAPPING)
    body = response.json()
    report = body["cleaning_report"]

    assert response.status_code == 200
    assert body["status"] == "processed"
    assert report["rows_before"] == 8
    assert report["rows_after"] == 3
    assert report["duplicate_rows_removed"] == 1
    assert report["missing_values_handled"] == 1
    assert report["missing_discount"] == 1
    assert report["invalid_rows_removed"] == 3
    assert report["rows_before"] == (
        report["rows_after"]
        + report["missing_values_handled"]
        + report["invalid_rows_removed"]
        + report["duplicate_rows_removed"]
    )

    session = store.get(session_id)
    assert session.status == "processed"
    assert list(session.frame.columns) == [
        "source_row",
        "product_name",
        "category",
        "price_usd",
        "pct_discount",
        "qty_sold",
        "sales_value",
    ]
    assert session.frame["sales_value"].tolist() == [50, 3, 0]
    assert session.frame["source_row"].tolist() == [1, 7, 8]
    assert session.frame["pct_discount"].tolist() == [0, 100, 10]
    assert session.frame["price_usd"].tolist() == [10, 3, 0]
    assert session.row_count == 8

    reloaded = SessionStore(store.base_dir).get(session_id)
    assert len(reloaded.frame) == 3
    assert reloaded.cleaning_report["rows_after"] == 3
    assert reloaded.frame["product_name"].tolist()[0] == "เสื้อ"


def test_retail_formula_values(client, store):
    content = "\n".join(
        [
            "product_name,price,retail_price,units_sold",
            "เสื้อ,10,20,5",
            "หารศูนย์,10,0,5",
            "แพงกว่าราคาเต็ม,30,20,5",
            "ลดหมด,0,10,4",
        ]
    )
    uploaded = _upload(client, "retail.csv", content)
    session_id = uploaded.json()["session_id"]
    response = _process(
        client,
        session_id,
        {
            "price_usd": "price",
            "pct_discount": None,
            "retail_price": "retail_price",
            "qty_sold": "units_sold",
            "product_name": "product_name",
            "category": None,
        },
    )
    assert response.status_code == 200
    report = response.json()["cleaning_report"]
    assert report["rows_after"] == 2
    assert report["missing_discount"] == 1
    assert report["invalid_rows_removed"] == 1
    assert response.json()["mapping"]["pct_discount"] is None
    frame = store.get(session_id).frame
    discounts = dict(zip(frame["product_name"], frame["pct_discount"], strict=True))
    assert discounts == {"เสื้อ": 50.0, "ลดหมด": 100.0}


def test_blank_discount_cell_uses_retail_when_both_columns_exist(client, store):
    content = "product_title,price_usd,pct_discount,retail_price,qty_sold\nA,10,,20,5\nB,10,15,40,5\n"
    uploaded = _upload(client, "both.csv", content)
    session_id = uploaded.json()["session_id"]
    response = _process(
        client,
        session_id,
        {
            "price_usd": "price_usd",
            "pct_discount": "pct_discount",
            "retail_price": "retail_price",
            "qty_sold": "qty_sold",
            "product_name": "product_title",
            "category": None,
        },
    )
    assert response.status_code == 200
    frame = store.get(session_id).frame
    discounts = dict(zip(frame["product_name"], frame["pct_discount"], strict=True))
    assert discounts == {"A": 50.0, "B": 15.0}


def test_missing_discount_mapping_is_rejected(client):
    uploaded = _upload(client, "shop.csv", "price_usd,qty_sold\n10,5\n")
    session_id = uploaded.json()["session_id"]
    response = _process(
        client,
        session_id,
        {
            "price_usd": "price_usd",
            "qty_sold": "qty_sold",
            "pct_discount": None,
            "retail_price": None,
            "product_name": None,
            "category": None,
        },
    )
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "missing_columns"
    assert "pct_discount" in body["message"]


def test_duplicate_column_choice_is_rejected(client):
    uploaded = _upload(client, "shop.csv", "price_usd,pct_discount,qty_sold\n10,5,1\n")
    session_id = uploaded.json()["session_id"]
    response = _process(
        client,
        session_id,
        {
            "price_usd": "price_usd",
            "qty_sold": "price_usd",
            "pct_discount": "pct_discount",
            "retail_price": None,
            "product_name": None,
            "category": None,
        },
    )
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "missing_columns"
    assert "ซ้ำ" in body["message"]


def test_unknown_session_and_empty_result(client):
    missing = client.post(
        "/api/dataset/process",
        json={
            "session_id": str(uuid.uuid4()),
            "mapping": BASIC_MAPPING,
        },
    )
    assert missing.status_code == 404
    assert missing.json()["error"] == "session_not_found"

    uploaded = _upload(client, "empty.csv", "price_usd,pct_discount,qty_sold\n10,5,\n")
    response = _process(client, uploaded.json()["session_id"], BASIC_MAPPING)
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "empty_dataset"
    assert "ทำความสะอาด" in body["message"]


def test_reprocess_clears_previous_model(client, store):
    uploaded = _upload(client, "shop.csv", "price_usd,pct_discount,qty_sold\n10,5,1\n12,8,2\n")
    session_id = uploaded.json()["session_id"]
    assert _process(client, session_id, BASIC_MAPPING).status_code == 200

    session = store.get(session_id)
    session.transition("clustered")
    session.model = object()
    session.scaler = object()
    session.k = 3
    session.recommended_k = 4
    store.save(session)

    again = _process(client, session_id, BASIC_MAPPING)
    assert again.status_code == 200
    assert again.json()["status"] == "processed"
    assert session.model is None
    assert session.scaler is not None
    assert int(session.scaler.n_samples_seen_) == 2
    assert session.k is None
    assert session.recommended_k is None


def test_high_sales_row_is_kept(client, store):
    content = "\n".join(
        [
            "product_title,price_usd,pct_discount,qty_sold,category_name",
            "best,759.99,10,10000,cat",
            'comma,"1,430.99",10,3,cat',
        ]
    )
    uploaded = _upload(client, "best.csv", content)
    session_id = uploaded.json()["session_id"]
    response = _process(client, session_id, SHEIN_MAPPING)
    assert response.status_code == 200
    assert response.json()["cleaning_report"]["rows_after"] == 2
    frame = store.get(session_id).frame
    assert frame["qty_sold"].tolist() == [10000, 3]
    assert frame["price_usd"].tolist()[1] == pytest.approx(1430.99)


def test_real_shein_file_cleans_to_expected_rows(client, store):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")

    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (REAL_DATASET.name, REAL_DATASET.read_bytes(), "text/csv")},
    )
    assert uploaded.status_code == 200
    session_id = uploaded.json()["session_id"]

    response = _process(client, session_id, SHEIN_MAPPING)
    body = response.json()
    report = body["cleaning_report"]

    assert response.status_code == 200
    assert report["rows_before"] == 82105
    assert report["rows_after"] == 35125
    assert report["duplicate_rows_removed"] == 1184
    assert report["invalid_rows_removed"] == 0
    assert report["missing_values_handled"] == 45796
    assert report["missing_price"] == 2
    assert report["missing_quantity"] == 27739
    assert report["missing_discount"] == 18055

    frame = store.get(session_id).frame
    assert len(frame) == 35125
    assert frame["price_usd"].max() == pytest.approx(759.99)
    assert frame["pct_discount"].min() >= 0
    assert frame["pct_discount"].max() <= 100
    assert (frame["qty_sold"] >= 0).all()
    assert frame["price_usd"].isna().sum() == 0

    repeated = client.get("/api/dataset/cleaning", params={"session_id": session_id})
    assert repeated.status_code == 200
    assert repeated.json()["cleaning_report"]["rows_after"] == 35125
