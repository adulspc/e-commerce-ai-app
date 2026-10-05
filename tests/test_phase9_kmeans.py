import uuid

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.cluster import KMeans

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
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


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _csv(rows: list[tuple[str, float, float, float]]) -> str:
    lines = ["product_title,price_usd,pct_discount,qty_sold,category_name"]
    lines.extend(f"{name},{price},{discount},{qty},cat" for name, price, discount, qty in rows)
    return "\n".join(lines) + "\n"


def _prepare(client: TestClient, content: str) -> str:
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("shop.csv", content.encode(), "text/csv")},
    )
    assert uploaded.status_code == 200
    session_id = uploaded.json()["session_id"]
    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    assert processed.status_code == 200
    return session_id


def _run(client: TestClient, session_id: str, k: object):
    return client.post("/api/clustering/run", json={"session_id": session_id, "k": k})


def test_kmeans_fits_scaled_rows_and_reloads(client, store):
    rows = [(f"low-{index}", 2 + index * 0.1, 10, 100) for index in range(6)]
    rows += [(f"high-{index}", 80 + index, 5, 10) for index in range(6)]
    rows.append(("bad", -1, 10, 5))
    session_id = _prepare(client, _csv(rows))

    early = client.get("/api/clustering/result", params={"session_id": session_id})
    assert early.status_code == 409

    response = _run(client, session_id, 2)
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "clustered"
    assert body["k"] == 2
    assert body["inertia"] > 0
    counts = [cluster["product_count"] for cluster in body["clusters"]]
    assert sum(counts) == 12
    assert all(count > 0 for count in counts)
    prices = [cluster["centroid_price_usd"] for cluster in body["clusters"]]
    assert max(prices) > 50
    assert min(prices) < 20

    session = store.get(session_id)
    assert isinstance(session.model, KMeans)
    assert session.model.random_state == 42
    assert session.model.n_init == 10
    assert session.frame["cluster"].tolist() == session.model.labels_.tolist()
    assert session.frame["price_usd"].tolist()[0] == pytest.approx(2)
    assert (session.directory / "model.joblib").is_file()

    reloaded = SessionStore(store.base_dir).get(session_id)
    assert reloaded.frame["cluster"].tolist() == session.frame["cluster"].tolist()
    assert reloaded.k == 2

    again = _run(client, session_id, 2)
    assert again.status_code == 200
    assert again.json()["clusters"] == body["clusters"]

    changed = _run(client, session_id, 3)
    assert changed.status_code == 200
    assert changed.json()["k"] == 3
    assert store.get(session_id).model.n_clusters == 3


def test_invalid_k_and_small_datasets_are_rejected(client):
    session_id = _prepare(client, _csv([(f"p{index}", 10 + index, 5, 2) for index in range(12)]))
    for k in (1, 11, True, 2.5):
        response = _run(client, session_id, k)
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_k"

    small_id = _prepare(client, _csv([(f"p{index}", 10 + index, 5, 2) for index in range(9)]))
    small = _run(client, small_id, 2)
    assert small.status_code == 400
    assert small.json()["error"] == "dataset_too_small"

    exact_id = _prepare(client, _csv([(f"p{index}", 10 + index, 5, 2) for index in range(10)]))
    exact = _run(client, exact_id, 10)
    assert exact.status_code == 400
    assert exact.json()["error"] == "k_too_large"


def test_run_requires_a_processed_session(client):
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("shop.csv", _csv([("A", 10, 5, 2)]).encode(), "text/csv")},
    )
    response = _run(client, uploaded.json()["session_id"], 2)
    assert response.status_code == 409
    assert response.json()["error"] == "invalid_session_state"

    missing = _run(client, str(uuid.uuid4()), 2)
    assert missing.status_code == 404
    assert missing.json()["error"] == "session_not_found"


def test_reprocess_removes_the_fitted_model(client, store):
    session_id = _prepare(client, _csv([(f"p{index}", 10 + index, 5, 3) for index in range(12)]))
    assert _run(client, session_id, 2).status_code == 200
    session = store.get(session_id)
    model_path = session.directory / "model.joblib"

    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    assert processed.status_code == 200
    assert session.status == "processed"
    assert session.model is None
    assert session.k is None
    assert not model_path.is_file()
    reread = client.get("/api/clustering/result", params={"session_id": session_id})
    assert reread.status_code == 409


def test_real_shein_file_clusters_from_its_own_rows(client, store):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")

    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (REAL_DATASET.name, REAL_DATASET.read_bytes(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    assert processed.status_code == 200

    response = _run(client, session_id, 3)
    body = response.json()
    assert response.status_code == 200
    frame = store.get(session_id).frame
    counts = [cluster["product_count"] for cluster in body["clusters"]]
    assert sum(counts) == 35125
    assert sorted(frame["cluster"].unique().tolist()) == [0, 1, 2]
    assert frame["price_usd"].max() == pytest.approx(759.99)
    assert np.isfinite(body["inertia"])
    centers = store.get(session_id).scaler.inverse_transform(
        store.get(session_id).model.cluster_centers_
    )
    reported = [
        [
            cluster["centroid_price_usd"],
            cluster["centroid_pct_discount"],
            cluster["centroid_qty_sold"],
            cluster["centroid_sales_value"],
        ]
        for cluster in body["clusters"]
    ]
    assert np.allclose(reported, centers)
