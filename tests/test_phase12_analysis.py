import csv
import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.dependencies import get_store
from backend.main import app
from backend.models.session_store import SessionStore
from backend.services.analysis import SCATTER_PER_CLUSTER, SCATTER_POINT_LIMIT, allocate_scatter, sample_scatter
from backend.services.cluster_interpretation import DECISION_SUPPORT
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

ENDPOINTS = (
    "/api/clusters",
    "/api/clusters/0",
    "/api/products",
    "/api/products/1",
    "/api/dashboard/summary",
    "/api/export/products",
    "/api/export/clusters",
)


@pytest.fixture
def store(tmp_path):
    return SessionStore(tmp_path)


@pytest.fixture
def client(store):
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _csv(rows: list[tuple[str, float, float, float, str]]) -> str:
    lines = ["product_title,price_usd,pct_discount,qty_sold,category_name"]
    lines.extend(
        f'"{name}",{price},{discount},{qty},{category}'
        for name, price, discount, qty, category in rows
    )
    return "\n".join(lines) + "\n"


def _prepare(client: TestClient, content: str, k: int = 2) -> str:
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
    if k:
        fitted = client.post("/api/clustering/run", json={"session_id": session_id, "k": k})
        assert fitted.status_code == 200
    return session_id


def _shop_rows() -> list[tuple[str, float, float, float, str]]:
    rows = [(f"low-{index}", 2 + index * 0.1, 10, 100, "alpha") for index in range(8)]
    rows += [(f"high-{index}", 80 + index, 5, 10, "beta") for index in range(8)]
    rows.append(("shirt, red", 3, 10, 90, "alpha"))
    return rows


def test_reading_before_clustering_is_rejected(client):
    session_id = _prepare(client, _csv(_shop_rows()), k=0)
    for path in ENDPOINTS:
        response = client.get(path, params={"session_id": session_id})
        assert response.status_code == 409
        assert response.json()["error"] == "invalid_session_state"


def test_missing_session_is_not_found(client):
    response = client.get(
        "/api/products",
        params={"session_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 404
    assert response.json()["error"] == "session_not_found"


def test_products_can_be_filtered_sorted_and_explained(client):
    session_id = _prepare(client, _csv(_shop_rows()))
    listed = client.get(
        "/api/products",
        params={"session_id": session_id, "page_size": 5, "sort": "price_usd", "order": "asc"},
    )
    body = listed.json()
    assert listed.status_code == 200
    assert body["total"] == 17
    assert body["page"] == 1
    assert len(body["products"]) == 5
    prices = [item["price_usd"] for item in body["products"]]
    assert prices == sorted(prices)
    assert set(body["categories"]) == {"alpha", "beta"}

    searched = client.get(
        "/api/products",
        params={"session_id": session_id, "search": "LOW-1"},
    )
    assert [item["product_name"] for item in searched.json()["products"]] == ["low-1"]

    alpha = client.get(
        "/api/products",
        params={"session_id": session_id, "category": "alpha", "page_size": 100},
    )
    assert alpha.json()["total"] == 9
    assert {item["category"] for item in alpha.json()["products"]} == {"alpha"}

    cluster_id = body["products"][0]["cluster"]
    same_cluster = client.get(
        "/api/products",
        params={"session_id": session_id, "cluster": cluster_id, "page_size": 100},
    )
    assert same_cluster.json()["total"] > 0
    assert {item["cluster"] for item in same_cluster.json()["products"]} == {cluster_id}

    empty = client.get("/api/products", params={"session_id": session_id, "cluster": 99})
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    beyond = client.get("/api/products", params={"session_id": session_id, "page": 50})
    assert beyond.status_code == 200
    assert beyond.json()["products"] == []
    assert beyond.json()["total"] == 17

    product_id = body["products"][0]["id"]
    detail = client.get(f"/api/products/{product_id}", params={"session_id": session_id})
    detail_body = detail.json()
    assert detail.status_code == 200
    assert detail_body["id"] == product_id
    assert detail_body["cluster_name"] in detail_body["explanation"]
    assert any(word in detail_body["explanation"] for word in ("ใกล้", "สูงกว่า", "ต่ำกว่า"))

    missing = client.get("/api/products/999999", params={"session_id": session_id})
    assert missing.status_code == 404
    assert missing.json()["error"] == "product_not_found"


def test_invalid_product_query_is_rejected(client):
    session_id = _prepare(client, _csv(_shop_rows()))
    for params in (
        {"session_id": session_id, "page": 0},
        {"session_id": session_id, "page_size": 101},
        {"session_id": session_id, "sort": "name"},
    ):
        response = client.get("/api/products", params=params)
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_request"


def test_clusters_match_the_fit_and_reject_unknown_ids(client):
    session_id = _prepare(client, _csv(_shop_rows()))
    fitted = client.get("/api/clustering/result", params={"session_id": session_id}).json()
    listed = client.get("/api/clusters", params={"session_id": session_id})
    body = listed.json()
    assert listed.status_code == 200
    assert body["k"] == 2
    assert sum(item["product_count"] for item in body["clusters"]) == 17
    assert [item["cluster_name"] for item in body["clusters"]] == [
        item["cluster_name"] for item in fitted["clusters"]
    ]
    assert [item["avg_price"] for item in body["clusters"]] == [
        item["centroid_price_usd"] for item in fitted["clusters"]
    ]
    assert all(DECISION_SUPPORT in item["recommendations"] for item in body["clusters"])

    first = body["clusters"][0]
    detail = client.get(f"/api/clusters/{first['cluster_id']}", params={"session_id": session_id})
    assert detail.status_code == 200
    assert detail.json()["cluster_name"] == first["cluster_name"]
    assert detail.json()["product_count"] == first["product_count"]

    missing = client.get("/api/clusters/9", params={"session_id": session_id})
    assert missing.status_code == 404
    assert missing.json()["error"] == "cluster_not_found"


def test_dashboard_uses_the_fitted_rows_and_a_stable_sample(client):
    session_id = _prepare(client, _csv(_shop_rows()))
    first = client.get("/api/dashboard/summary", params={"session_id": session_id})
    second = client.get("/api/dashboard/summary", params={"session_id": session_id})
    body = first.json()
    assert first.status_code == 200
    assert body["total_products"] == 17
    assert body["number_of_clusters"] == 2
    assert body["k"] == 2
    assert body["scatter_sampled"] is False
    assert body["scatter_sample_size"] == 17
    assert len(body["scatter"]) == 17
    assert {point["cluster"] for point in body["scatter"]} <= {0, 1}
    assert body["total_quantity_sold"] == pytest.approx(sum(row[3] for row in _shop_rows()))
    assert body["average_price"] == pytest.approx(sum(row[1] for row in _shop_rows()) / 17)
    assert first.json()["scatter"] == second.json()["scatter"]


def test_exports_are_csv_files(client):
    session_id = _prepare(client, _csv(_shop_rows()))
    products = client.get("/api/export/products", params={"session_id": session_id})
    assert products.status_code == 200
    assert "text/csv" in products.headers["content-type"]
    assert products.headers["content-disposition"] == 'attachment; filename="products.csv"'
    product_rows = list(csv.DictReader(io.StringIO(products.content.decode("utf-8-sig"))))
    assert list(product_rows[0]) == [
        "product_name",
        "category",
        "price_usd",
        "pct_discount",
        "qty_sold",
        "sales_value",
        "cluster",
        "cluster_name",
    ]
    assert len(product_rows) == 17
    assert any(row["product_name"] == "shirt, red" for row in product_rows)

    clusters = client.get("/api/export/clusters", params={"session_id": session_id})
    cluster_rows = list(csv.DictReader(io.StringIO(clusters.content.decode("utf-8-sig"))))
    assert clusters.status_code == 200
    assert len(cluster_rows) == 2
    assert all(DECISION_SUPPORT in row["recommendations"] for row in cluster_rows)


def test_scatter_allocation_respects_the_caps():
    small = allocate_scatter({0: 10, 1: 10})
    assert small == {0: 10, 1: 10}
    assert allocate_scatter({0: 10_000}) == {0: SCATTER_PER_CLUSTER}
    wide = allocate_scatter({index: 500 for index in range(6)})
    assert sum(wide.values()) == SCATTER_POINT_LIMIT
    assert max(wide.values()) <= SCATTER_PER_CLUSTER
    assert min(wide.values()) >= 1

    frame = pd.DataFrame(
        {
            "price_usd": [1.0] * 2000,
            "pct_discount": [10.0] * 2000,
            "qty_sold": [5.0] * 2000,
            "sales_value": [5.0] * 2000,
            "cluster": [0] * 1000 + [1] * 1000,
        }
    )
    first, sampled = sample_scatter(frame)
    second, _sampled_again = sample_scatter(frame)
    assert sampled is True
    assert len(first) == 800
    assert first["cluster"].value_counts().to_dict() == {0: 400, 1: 400}
    pd.testing.assert_frame_equal(first, second)


def test_real_shein_reading_and_export(client):
    if not REAL_DATASET.is_file():
        pytest.skip("Shein CSV is not in data/")

    uploaded = client.post(
        "/api/dataset/upload",
        files={"file": (REAL_DATASET.name, REAL_DATASET.read_bytes(), "text/csv")},
    )
    session_id = uploaded.json()["session_id"]
    client.post("/api/dataset/process", json={"session_id": session_id, "mapping": MAPPING})
    fitted = client.post("/api/clustering/run", json={"session_id": session_id, "k": 2})
    assert fitted.status_code == 200

    summary = client.get("/api/dashboard/summary", params={"session_id": session_id}).json()
    assert summary["total_products"] == 35125
    assert summary["number_of_clusters"] == 2
    assert summary["scatter_sampled"] is True
    assert summary["scatter_sample_size"] == 800
    counts = {}
    for point in summary["scatter"]:
        counts[point["cluster"]] = counts.get(point["cluster"], 0) + 1
    assert counts == {0: 400, 1: 400}
    repeated = client.get("/api/dashboard/summary", params={"session_id": session_id}).json()
    assert repeated["scatter"] == summary["scatter"]

    products = client.get("/api/products", params={"session_id": session_id})
    assert products.json()["total"] == 35125
    assert len(products.json()["products"]) == 20

    exported = client.get("/api/export/products", params={"session_id": session_id})
    exported_rows = list(csv.DictReader(io.StringIO(exported.content.decode("utf-8-sig"))))
    assert len(exported_rows) == 35125

    clusters = client.get("/api/clusters", params={"session_id": session_id}).json()
    assert {item["cluster_id"]: item["cluster_name"] for item in clusters["clusters"]} == {
        0: "Balanced Mix",
        1: "High Value / Best Sellers",
    }
    assert {item["cluster_id"]: item["product_count"] for item in clusters["clusters"]} == {
        0: 32186,
        1: 2939,
    }
