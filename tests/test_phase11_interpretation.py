import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.cluster_interpretation import (
    ARCHETYPE_PRIORITY,
    DECISION_SUPPORT,
    describe_clusters,
    explain_product,
    nearest_cluster,
)
from backend.services.clustering import ensure_named_report
from backend.utils.errors import InvalidSessionStateError
from backend.utils.paths import DATA_DIR

REAL_DATASET = DATA_DIR / "CLEAN-Ecommerce-products-all_categories.csv (1).csv"

MAPPING = {
    "price_usd": "price_usd",
    "pct_discount": "pct_discount",
    "retail_price": None,
    "qty_sold": "qty_sold",
    "product_name": "product_title",
    "category": "category_name",
}


def _frame(rows: list[tuple[int, float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["cluster", "price_usd", "pct_discount", "qty_sold", "sales_value"],
    )


def _repeat(cluster: int, price: float, discount: float, qty: float, sales: float, count: int = 10):
    return [(cluster, price, discount, qty, sales) for _ in range(count)]


def test_names_follow_the_strongest_pattern():
    high_low = describe_clusters(
        _frame(_repeat(0, 10, 10, 100, 100) + _repeat(1, 10, 10, 1, 1))
    )
    assert [item.cluster_name for item in high_low] == [
        "High Value / Best Sellers",
        "Low Performance",
    ]

    price_split = describe_clusters(
        _frame(_repeat(0, 2, 10, 100, 200) + _repeat(1, 100, 10, 5, 500))
    )
    assert {item.cluster_name for item in price_split} == {
        "Popular Low-Price Products",
        "Premium Low-Volume",
    }

    promotion = describe_clusters(
        _frame(_repeat(0, 10, 80, 10, 100) + _repeat(1, 10, 5, 10, 100))
    )
    assert promotion[0].cluster_name == "Promotion Driven"
    assert promotion[1].cluster_name == "Balanced Mix"

    shared = describe_clusters(
        _frame(
            _repeat(0, 10, 10, 100, 100)
            + _repeat(1, 10, 10, 100, 100)
            + _repeat(2, 10, 10, 1, 1)
        )
    )
    assert shared[0].cluster_name == shared[1].cluster_name == "High Value / Best Sellers"

    flat = describe_clusters(_frame(_repeat(0, 10, 10, 10, 10)))
    assert flat[0].cluster_name == "Balanced Mix"
    assert "ใกล้ค่าเฉลี่ยทั้งตาราง" in flat[0].characteristics
    assert flat[0].recommendations[-1] == DECISION_SUPPORT


def test_product_explanation_uses_the_cluster_mean_and_nearest_center():
    text = explain_product(
        {"price_usd": 110, "pct_discount": 80, "qty_sold": 10, "sales_value": 100},
        {"price_usd": 100, "pct_discount": 10, "qty_sold": 10, "sales_value": 50},
        "Balanced Mix",
    )
    assert "ใกล้ค่าเฉลี่ยของกลุ่ม" in text
    assert "ส่วนลดสูงกว่าค่าเฉลี่ยของกลุ่ม" in text
    assert "มูลค่าการขายสูงกว่าค่าเฉลี่ยของกลุ่ม" in text

    centers = np.array([[0.0, 0.0, 0.0, 0.0], [10.0, 0.0, 0.0, 0.0]])
    assert nearest_cluster(np.array([0.2, 0.0, 0.0, 0.0]), centers) == 0
    assert nearest_cluster(np.array([9.0, 0.0, 0.0, 0.0]), centers) == 1


def test_saved_report_without_names_is_filled():
    frame = _frame(_repeat(0, 10, 10, 100, 100) + _repeat(1, 10, 10, 1, 1))
    session = type("Session", (), {})()
    session.status = "clustered"
    session.k = 2
    session.model = None
    session.scaler = None
    session.frame = frame
    session.cluster_report = {
        "k": 2,
        "inertia": 3.0,
        "clusters": [
            {"cluster_id": 0, "product_count": 10},
            {"cluster_id": 1, "product_count": 10},
        ],
    }

    report, changed = ensure_named_report(session)
    assert changed is True
    assert report["clusters"][0]["cluster_name"] == "High Value / Best Sellers"
    session.frame = frame.drop(columns=["cluster"])
    session.cluster_report = {
        "k": 2,
        "inertia": 3.0,
        "clusters": [{"cluster_id": 0, "product_count": 10}],
    }
    with pytest.raises(InvalidSessionStateError):
        ensure_named_report(session)


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_run_returns_names_from_the_fitted_rows(client):
    lines = ["product_title,price_usd,pct_discount,qty_sold,category_name"]
    for index in range(10):
        lines.append(f"low-{index},2,10,100,cat")
    for index in range(10):
        lines.append(f"high-{index},100,10,5,cat")
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("shop.csv", ("\n".join(lines) + "\n").encode(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    client.post("/api/dataset/process", json={"session_id": session_id, "mapping": MAPPING})
    response = client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})
    body = response.json()
    assert response.status_code == 200
    names = {cluster["cluster_name"] for cluster in body["clusters"]}
    assert names == {"Popular Low-Price Products", "Premium Low-Volume"}
    assert all(DECISION_SUPPORT in cluster["recommendations"] for cluster in body["clusters"])


def test_real_shein_names_come_from_cluster_means(client, store):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")

    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (REAL_DATASET.name, REAL_DATASET.read_bytes(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    client.post("/api/dataset/process", json={"session_id": session_id, "mapping": MAPPING})
    response = client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})
    body = response.json()
    assert response.status_code == 200
    session = store.get(session_id)
    expected = describe_clusters(
        session.frame,
        session.scaler.inverse_transform(session.model.cluster_centers_),
    )
    assert [cluster["cluster_name"] for cluster in body["clusters"]] == [
        item.cluster_name for item in expected
    ]
    assert all(cluster["cluster_name"] in ARCHETYPE_PRIORITY for cluster in body["clusters"])
    assert sum(cluster["product_count"] for cluster in body["clusters"]) == 35125
