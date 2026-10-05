import uuid

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.schemas.clustering import OptimalKPoint
from backend.services.clustering import elbow_k
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
    session_id = uploaded.json()["session_id"]
    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    assert processed.status_code == 200
    return session_id


def test_elbow_uses_the_bend_and_ties_pick_the_smaller_k():
    flat = [OptimalKPoint(k=k, inertia=100 - k, silhouette=0.2) for k in range(2, 7)]
    assert elbow_k(flat) == 2

    bent = [
        OptimalKPoint(k=2, inertia=100, silhouette=0.95),
        OptimalKPoint(k=3, inertia=80, silhouette=0.4),
        OptimalKPoint(k=4, inertia=30, silhouette=0.3),
        OptimalKPoint(k=5, inertia=20, silhouette=0.2),
        OptimalKPoint(k=6, inertia=18, silhouette=0.1),
    ]
    assert elbow_k(bent) != 2
    tied = [
        OptimalKPoint(k=2, inertia=50, silhouette=0.5),
        OptimalKPoint(k=3, inertia=20, silhouette=0.2),
        OptimalKPoint(k=4, inertia=10, silhouette=0.5),
    ]
    chosen = max(tied, key=lambda point: (point.silhouette, -point.k))
    assert chosen.k == 2


def test_optimal_k_reports_both_scores_and_caches(client, store):
    rows = [(f"low-{index}", 2 + index * 0.01, 10, 80) for index in range(20)]
    rows += [(f"high-{index}", 90 + index, 4, 8) for index in range(20)]
    session_id = _prepare(client, _csv(rows))

    response = client.get("/api/clustering/optimal-k", params={"session_id": session_id})
    body = response.json()
    assert response.status_code == 200
    assert body["sample_count"] == 40
    assert body["silhouette_sampled"] is False
    assert body["silhouette_sample_size"] == 40
    assert [point["k"] for point in body["scores"]] == list(range(2, 11))
    silhouettes = [point["silhouette"] for point in body["scores"]]
    assert body["recommended_k"] == body["scores"][silhouettes.index(max(silhouettes))]["k"]
    assert body["recommended_k"] == 2
    assert body["elbow_k"] in range(2, 11)
    assert body["scores"][0]["inertia"] > body["scores"][-1]["inertia"]
    assert store.get(session_id).recommended_k == 2
    assert store.get(session_id).model is None

    cached = client.get("/api/clustering/optimal-k", params={"session_id": session_id})
    assert cached.json() == body

    fitted = client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})
    matched = next(point for point in body["scores"] if point["k"] == 2)
    assert fitted.json()["inertia"] == pytest.approx(matched["inertia"])


def test_optimal_k_requires_enough_processed_rows(client):
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": ("shop.csv", _csv([("A", 10, 5, 2)]).encode(), "text/csv")},
    )
    early = client.get(
        "/api/clustering/optimal-k",
        params={"session_id": uploaded.json()["session_id"]},
    )
    assert early.status_code == 409

    small_id = _prepare(client, _csv([(f"p{index}", 10 + index, 5, 2) for index in range(9)]))
    small = client.get("/api/clustering/optimal-k", params={"session_id": small_id})
    assert small.status_code == 400
    assert small.json()["error"] == "dataset_too_small"

    missing = client.get("/api/clustering/optimal-k", params={"session_id": str(uuid.uuid4())})
    assert missing.status_code == 404


def test_reprocess_clears_the_saved_curve(client, store):
    rows = [(f"p{index}", 10 + index, 8, 4) for index in range(12)]
    session_id = _prepare(client, _csv(rows))
    assert client.get("/api/clustering/optimal-k", params={"session_id": session_id}).status_code == 200

    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    assert processed.status_code == 200
    session = store.get(session_id)
    assert session.recommended_k is None
    assert session.optimal_k_report is None


def test_real_shein_curve_samples_silhouette(client, store):
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

    response = client.get("/api/clustering/optimal-k", params={"session_id": session_id})
    body = response.json()
    assert response.status_code == 200
    assert body["sample_count"] == 35125
    assert body["silhouette_sampled"] is True
    assert body["silhouette_sample_size"] == 5000
    assert [point["k"] for point in body["scores"]] == list(range(2, 11))
    assert all(-1 <= point["silhouette"] <= 1 for point in body["scores"])
    best = max(body["scores"], key=lambda point: (point["silhouette"], -point["k"]))
    assert body["recommended_k"] == best["k"]
    assert body["elbow_k"] in range(2, 11)
    assert body["scores"][0]["inertia"] > body["scores"][-1]["inertia"]
    assert store.get(session_id).model is None
    assert store.get(session_id).recommended_k == body["recommended_k"]
