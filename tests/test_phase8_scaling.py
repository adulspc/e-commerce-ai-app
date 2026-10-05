import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.preprocessing import StandardScaler

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.scaling import FEATURE_COLUMNS, fit_scaler
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


def test_constant_feature_scales_to_zero():
    frame = pd.DataFrame(
        {
            "price_usd": [5.0, 5.0],
            "pct_discount": [10.0, 30.0],
            "qty_sold": [1.0, 3.0],
            "sales_value": [5.0, 15.0],
        }
    )
    scaler, report = fit_scaler(frame)
    scaled = scaler.transform(frame[FEATURE_COLUMNS])

    assert report.features[0].feature == "price_usd"
    assert report.features[0].constant is True
    assert np.allclose(scaled[:, 0], 0.0)
    assert np.allclose(scaled.mean(axis=0), 0.0, atol=1e-8)


def test_process_fits_scaler_on_kept_rows_only(client, store):
    content = "\n".join(
        [
            "product_title,price_usd,pct_discount,qty_sold,category_name",
            "A,10,10,1,cat",
            "B,30,30,3,cat",
            "C,-1,10,5,cat",
        ]
    )
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("shop.csv", content.encode(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    response = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": SHEIN_MAPPING},
    )
    body = response.json()
    assert response.status_code == 200
    report = body["scaling_report"]
    assert report["sample_count"] == 2
    assert [item["feature"] for item in report["features"]] == FEATURE_COLUMNS
    means = {item["feature"]: item["mean"] for item in report["features"]}
    assert means["price_usd"] == pytest.approx(20)
    assert means["pct_discount"] == pytest.approx(20)
    assert means["qty_sold"] == pytest.approx(2)
    assert means["sales_value"] == pytest.approx(50)

    session = store.get(session_id)
    assert isinstance(session.scaler, StandardScaler)
    assert session.model is None
    assert session.frame["price_usd"].tolist() == [10, 30]
    scaled = session.scaler.transform(session.frame[FEATURE_COLUMNS])
    assert np.allclose(scaled.mean(axis=0), 0, atol=1e-8)
    assert np.allclose(scaled.std(axis=0), 1, atol=1e-8)
    assert (session.directory / "scaler.joblib").is_file()

    reloaded = SessionStore(store.base_dir).get(session_id)
    reloaded_scaled = reloaded.scaler.transform(session.frame[FEATURE_COLUMNS])
    assert np.allclose(reloaded_scaled, scaled)

    repeated = client.get("/api/dataset/cleaning", params={"session_id": session_id})
    assert repeated.status_code == 200
    assert repeated.json()["scaling_report"]["sample_count"] == 2


def test_real_shein_file_is_standardized(client, store):
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
    assert response.json()["scaling_report"]["sample_count"] == 35125

    session = store.get(session_id)
    frame = session.frame
    scaled = session.scaler.transform(frame[FEATURE_COLUMNS])
    assert scaled.shape == (35125, 4)
    assert np.allclose(scaled.mean(axis=0), 0, atol=1e-6)
    assert np.allclose(scaled.std(axis=0), 1, atol=1e-6)
    assert frame["price_usd"].max() == pytest.approx(759.99)
    assert session.model is None
