from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class SuggestedMapping(BaseModel):
    price_usd: str | None = None
    pct_discount: str | None = None
    retail_price: str | None = None
    qty_sold: str | None = None
    product_name: str | None = None
    category: str | None = None


class DatasetUploadResponse(BaseModel):
    session_id: str
    filename: str
    columns: list[str]
    row_count: int
    preview: list[dict[str, str]]
    suggested_mapping: SuggestedMapping
    missing_required: list[str] = Field(default_factory=list)


class ColumnMappingInput(BaseModel):
    price_usd: str
    qty_sold: str
    pct_discount: str | None = None
    retail_price: str | None = None
    product_name: str | None = None
    category: str | None = None

    @field_validator("*", mode="before")
    @classmethod
    def strip_blank(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        stripped = value.strip()
        return stripped or None


class FeatureScale(BaseModel):
    feature: str
    mean: float
    std: float
    constant: bool


class ScalingReport(BaseModel):
    sample_count: int
    features: list[FeatureScale]


class FeatureReport(BaseModel):
    row_count: int
    min_sales_value: float
    median_sales_value: float
    mean_sales_value: float
    max_sales_value: float


class CleaningReport(BaseModel):
    rows_before: int
    rows_after: int
    missing_values_handled: int
    duplicate_rows_removed: int
    invalid_rows_removed: int
    missing_price: int
    missing_quantity: int
    missing_discount: int


class ProcessRequest(BaseModel):
    session_id: UUID
    mapping: ColumnMappingInput


class DatasetCleaningResponse(BaseModel):
    session_id: str
    status: Literal["processed", "clustered"]
    filename: str | None = None
    mapping: ColumnMappingInput
    cleaning_report: CleaningReport
    feature_report: FeatureReport
    scaling_report: ScalingReport
