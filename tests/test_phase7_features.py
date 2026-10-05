from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.data_cleaning import load_cleaned_frame
from backend.services.feature_engineering import add_sales_value
from backend.utils.errors import MissingColumnsError, NonNumericValueError
from backend.utils.paths import DATA_DIR

REAL_DATASET = DATA_DIR / "CLEAN-Ecommerce-products-all_categories.csv (1).csv"

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


def test_add_sales_value_multiplies_price_and_quantity():
    frame = pd.DataFrame({"price_usd": [10, 0, 2.5], "qty_sold": [4, 9, 2]})
    result = add_sales_value(frame)
    assert result["sales_value"].tolist() == [40, 0, 5]


def test_add_sales_value_rejects_missing_or_blank_numbers():
    with pytest.raises(MissingColumnsError):
        add_sales_value(pd.DataFrame({"price_usd": [1.0]}))
    with pytest.raises(NonNumericValueError):
        add_sales_value(pd.DataFrame({"price_usd": [1.0, None], "qty_sold": [2.0, 3.0]}))


def test_legacy_cleaned_file_computes_sales_value(tmp_path: Path):
    (tmp_path / "cleaned.csv").write_text(
        "source_row,product_name,category,price_usd,pct_discount,qty_sold\n"
        "1,เสื้อ,cat,10,5,4\n",
        encoding="utf-8",
    )
    frame = load_cleaned_frame(tmp_path)
    assert frame is not None
    assert frame["sales_value"].tolist() == [40]


def test_process_stores_sales_value_and_summary(client, store):
    content = "\n".join(
        [
            "product_name,price,retail_price,units_sold",
            "เสื้อ,10,20,5",
            "ของแถม,0,10,4",
        ]
    )
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("retail.csv", content.encode(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    response = client.post(
        "/api/dataset/process",
        json={
            "session_id": session_id,
            "mapping": {
                "price_usd": "price",
                "pct_discount": None,
                "retail_price": "retail_price",
                "qty_sold": "units_sold",
                "product_name": "product_name",
                "category": None,
            },
        },
    )
    body = response.json()
    assert response.status_code == 200
    assert body["feature_report"] == {
        "row_count": 2,
        "min_sales_value": 0.0,
        "median_sales_value": 25.0,
        "mean_sales_value": 25.0,
        "max_sales_value": 50.0,
    }

    session = store.get(session_id)
    discounts = dict(zip(session.frame["product_name"], session.frame["sales_value"], strict=True))
    assert discounts == {"เสื้อ": 50.0, "ของแถม": 0.0}
    header = (session.directory / "cleaned.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header.endswith("sales_value")

    reloaded = SessionStore(store.base_dir).get(session_id)
    assert reloaded.feature_report["max_sales_value"] == 50.0
    assert reloaded.frame["sales_value"].tolist() == [50.0, 0.0]

    repeated = client.get("/api/dataset/cleaning", params={"session_id": session_id})
    assert repeated.status_code == 200
    assert repeated.json()["feature_report"]["row_count"] == 2


def test_real_shein_sales_value_matches_price_times_quantity(client, store):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")

    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (REAL_DATASET.name, REAL_DATASET.read_bytes(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    response = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": SHEIN_MAPPING},
    )
    assert response.status_code == 200
    report = response.json()["feature_report"]
    frame = store.get(session_id).frame
    expected = frame["price_usd"].to_numpy() * frame["qty_sold"].to_numpy()

    assert report["row_count"] == 35125
    assert len(frame) == 35125
    assert np.allclose(frame["sales_value"].to_numpy(), expected)
    assert report["min_sales_value"] == pytest.approx(float(expected.min()))
    assert report["max_sales_value"] == pytest.approx(float(expected.max()))
    assert report["min_sales_value"] >= 0
