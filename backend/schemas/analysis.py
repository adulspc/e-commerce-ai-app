"""Responses for cluster lists, the product table, and the dashboard."""

from pydantic import BaseModel, Field


class ClusterSummary(BaseModel):
    cluster_id: int
    cluster_name: str
    product_count: int
    avg_price: float
    avg_discount: float
    avg_qty_sold: float
    avg_sales_value: float
    characteristics: str
    recommendations: list[str]


class ClusterListResponse(BaseModel):
    session_id: str
    k: int
    clusters: list[ClusterSummary]


class ClusterDetailResponse(ClusterSummary):
    session_id: str


class ProductRow(BaseModel):
    id: str
    product_name: str
    category: str
    price_usd: float
    pct_discount: float
    qty_sold: float
    sales_value: float
    cluster: int
    cluster_name: str


class ProductDetail(ProductRow):
    explanation: str


class ProductPage(BaseModel):
    session_id: str
    page: int
    page_size: int
    total: int
    categories: list[str]
    products: list[ProductRow]


class ScatterPoint(BaseModel):
    price_usd: float
    pct_discount: float
    qty_sold: float
    sales_value: float
    cluster: int


class DashboardSummary(BaseModel):
    session_id: str
    k: int
    total_products: int
    average_price: float
    average_discount: float
    total_quantity_sold: float
    total_sales_value: float
    number_of_clusters: int
    clusters: list[ClusterSummary]
    scatter: list[ScatterPoint]
    scatter_sample_size: int = Field(description="Number of points in scatter, at most 2000")
    scatter_sampled: bool
