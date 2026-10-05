import csv
import io

import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.cluster_interpretation import ARCHETYPE_PRIORITY, DECISION_SUPPORT

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


def _kept_rows():
    rows = [(f"low-{index}", 2 + index * 0.1, 10, 100, "alpha") for index in range(8)]
    rows += [(f"high-{index}", 80 + index, 5, 10, "beta") for index in range(8)]
    return rows


def _csv() -> str:
    lines = ["product_title,price_usd,pct_discount,qty_sold,category_name"]
    for name, price, discount, qty, category in _kept_rows():
        lines.append(f"{name},{price},{discount},{qty},{category}")
    lines.append("bad,-1,10,5,alpha")
    first = _kept_rows()[0]
    lines.append(f"{first[0]},{first[1]},{first[2]},{first[3]},{first[4]}")
    lines.append("gone,5,10,,alpha")
    return "\n".join(lines) + "\n"


def _upload(client: TestClient, content: str, filename: str = "shop.csv") -> str:
    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (filename, content.encode(), "text/csv")},
    )
    assert uploaded.status_code == 200
    return uploaded.json()["session_id"]


def test_one_dataset_flows_through_cluster_dashboard_products_and_export(client, store):
    assert client.get("/api/health").json() == {"status": "ok"}
    session_id = _upload(client, _csv())
    blocked = client.get("/api/export/products", params={"session_id": session_id})
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "invalid_session_state"
    assert "Traceback" not in blocked.text

    processed = client.post(
        "/api/dataset/process",
        json={"session_id": session_id, "mapping": MAPPING},
    )
    cleaning = processed.json()["cleaning_report"]
    assert processed.status_code == 200
    assert cleaning["rows_before"] == 19
    assert cleaning["rows_after"] == 16
    assert cleaning["invalid_rows_removed"] == 1
    assert cleaning["missing_quantity"] == 1
    assert cleaning["duplicate_rows_removed"] == 1
    assert (
        cleaning["rows_before"]
        == cleaning["rows_after"]
        + cleaning["missing_values_handled"]
        + cleaning["invalid_rows_removed"]
        + cleaning["duplicate_rows_removed"]
    )
    features = processed.json()["feature_report"]
    kept = _kept_rows()
    sales = [price * qty for _name, price, _discount, qty, _category in kept]
    assert features["row_count"] == 16
    assert features["min_sales_value"] == pytest.approx(min(sales))
    assert features["max_sales_value"] == pytest.approx(max(sales))

    session = store.get(session_id)
    assert session.status == "processed"
    assert session.model is None
    assert session.scaler.n_samples_seen_ == 16
    assert list(session.frame["sales_value"]) == pytest.approx(sales)

    optimal = client.get("/api/clustering/optimal-k", params={"session_id": session_id})
    curve = optimal.json()
    assert optimal.status_code == 200
    assert [point["k"] for point in curve["scores"]] == list(range(2, 11))
    best = max(curve["scores"], key=lambda point: (point["silhouette"], -point["k"]))
    assert curve["recommended_k"] == best["k"]
    assert curve["elbow_k"] in range(2, 11)
    assert curve["silhouette_sampled"] is False
    cached = client.get("/api/clustering/optimal-k", params={"session_id": session_id})
    assert cached.json()["scores"] == curve["scores"]
    assert store.get(session_id).model is None
    assert store.get(session_id).status == "processed"

    fitted = client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})
    fit = fitted.json()
    assert fitted.status_code == 200
    assert fit["k"] == 2
    assert sum(cluster["product_count"] for cluster in fit["clusters"]) == 16
    assert {cluster["product_count"] for cluster in fit["clusters"]} == {8}
    assert {cluster["cluster_name"] for cluster in fit["clusters"]} == {
        "Popular Low-Price Products",
        "Premium Low-Volume",
    }
    assert all(cluster["cluster_name"] in ARCHETYPE_PRIORITY for cluster in fit["clusters"])
    assert all(DECISION_SUPPORT in cluster["recommendations"] for cluster in fit["clusters"])
    model = store.get(session_id).model
    assert model.random_state == 42
    assert model.n_init == 10
    assert store.get(session_id).frame["price_usd"].tolist()[0] == pytest.approx(2)

    clusters = client.get("/api/clusters", params={"session_id": session_id}).json()
    assert [item["avg_price"] for item in clusters["clusters"]] == [
        item["centroid_price_usd"] for item in fit["clusters"]
    ]
    detail = client.get("/api/clusters/0", params={"session_id": session_id})
    assert detail.status_code == 200
    assert detail.json()["product_count"] == 8

    dashboard = client.get("/api/dashboard/summary", params={"session_id": session_id}).json()
    assert dashboard["total_products"] == 16
    assert dashboard["number_of_clusters"] == 2
    assert dashboard["scatter_sampled"] is False
    assert len(dashboard["scatter"]) == 16
    assert {point["cluster"] for point in dashboard["scatter"]} == {0, 1}
    assert dashboard["total_quantity_sold"] == pytest.approx(sum(row[3] for row in kept))
    assert dashboard["average_price"] == pytest.approx(sum(row[1] for row in kept) / 16)
    repeated = client.get("/api/dashboard/summary", params={"session_id": session_id}).json()
    assert repeated["scatter"] == dashboard["scatter"]

    products = client.get(
        "/api/products",
        params={"session_id": session_id, "search": "LOW-0", "sort": "price_usd", "order": "asc"},
    ).json()
    assert products["total"] == 1
    assert products["products"][0]["product_name"] == "low-0"
    assert products["products"][0]["sales_value"] == pytest.approx(200)
    product_id = products["products"][0]["id"]
    explained = client.get(f"/api/products/{product_id}", params={"session_id": session_id}).json()
    assert explained["cluster_name"] in explained["explanation"]
    assert any(word in explained["explanation"] for word in ("ใกล้", "สูงกว่า", "ต่ำกว่า"))

    exported = client.get("/api/export/products", params={"session_id": session_id})
    product_rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert exported.headers["content-disposition"] == 'attachment; filename="products.csv"'
    assert len(product_rows) == 16
    low = next(row for row in product_rows if row["product_name"] == "low-0")
    assert float(low["sales_value"]) == pytest.approx(200)
    assert float(low["price_usd"]) * float(low["qty_sold"]) == pytest.approx(float(low["sales_value"]))
    assert {row["cluster_name"] for row in product_rows} == {
        "Popular Low-Price Products",
        "Premium Low-Volume",
    }

    cluster_file = client.get("/api/export/clusters", params={"session_id": session_id})
    cluster_rows = list(csv.DictReader(io.StringIO(cluster_file.content.decode("utf-8-sig"))))
    assert len(cluster_rows) == 2
    assert sum(int(row["product_count"]) for row in cluster_rows) == 16
    assert all(DECISION_SUPPORT in row["recommendations"] for row in cluster_rows)


def test_reprocess_clears_results_and_a_new_upload_is_separate(client, store):
    session_id = _upload(client, _csv())
    client.post("/api/dataset/process", json={"session_id": session_id, "mapping": MAPPING})
    client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})

    again = client.post("/api/dataset/process", json={"session_id": session_id, "mapping": MAPPING})
    assert again.status_code == 200
    session = store.get(session_id)
    assert session.status == "processed"
    assert session.model is None
    assert session.k is None
    assert session.cluster_report is None
    hidden = client.get("/api/dashboard/summary", params={"session_id": session_id})
    assert hidden.status_code == 409

    other_id = _upload(client, _csv(), filename="other.csv")
    assert other_id != session_id
    other = client.get("/api/products", params={"session_id": other_id})
    assert other.status_code == 409
    first = client.get(f"/api/sessions/{session_id}")
    assert first.status_code == 200
    assert first.json()["status"] == "processed"
