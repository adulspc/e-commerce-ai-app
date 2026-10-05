"""Request and response models for a K-Means fit."""

from uuid import UUID

from pydantic import BaseModel, field_validator

from backend.utils.errors import InvalidKError


class ClusteringRunRequest(BaseModel):
    session_id: UUID
    k: int

    @field_validator("k", mode="before")
    @classmethod
    def k_must_be_an_integer(cls, value: object) -> object:
        if isinstance(value, bool) or not isinstance(value, int):
            raise InvalidKError()
        return value


class ClusterFitSummary(BaseModel):
    cluster_id: int
    product_count: int
    centroid_price_usd: float
    centroid_pct_discount: float
    centroid_qty_sold: float
    centroid_sales_value: float
    cluster_name: str
    characteristics: str
    recommendations: list[str]


class ClusterReport(BaseModel):
    k: int
    inertia: float
    clusters: list[ClusterFitSummary]


class OptimalKPoint(BaseModel):
    k: int
    inertia: float
    silhouette: float


class OptimalKReport(BaseModel):
    sample_count: int
    silhouette_sample_size: int
    silhouette_sampled: bool
    recommended_k: int
    elbow_k: int
    scores: list[OptimalKPoint]


class OptimalKResponse(OptimalKReport):
    session_id: str


class ClusteringRunResponse(BaseModel):
    session_id: str
    status: str
    k: int
    inertia: float
    clusters: list[ClusterFitSummary]
