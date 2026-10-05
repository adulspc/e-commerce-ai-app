"""Name each cluster from its means versus the catalog means.

Cluster ids stay as color and sort keys. A name is the strongest matching
pattern. The same name may be used by more than one cluster.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.schemas.clustering import ClusterFitSummary
from backend.services.scaling import FEATURE_COLUMNS

Z_CLEAR = 0.5
NEAR_MEAN_RATIO = 0.15

ARCHETYPE_PRIORITY = (
    "High Value / Best Sellers",
    "Popular Low-Price Products",
    "Premium Low-Volume",
    "Promotion Driven",
    "Low Performance",
    "Balanced Mix",
)
DECISION_SUPPORT = "ข้อมูลนี้เป็นข้อเสนอประกอบการตัดสินใจ ไม่ได้สั่งดำเนินการให้อัตโนมัติ"
FEATURE_LABELS = (
    ("price_usd", "ราคา"),
    ("pct_discount", "ส่วนลด"),
    ("qty_sold", "จำนวนขาย"),
    ("sales_value", "มูลค่าการขาย"),
)
_RECOMMENDATIONS = {
    "High Value / Best Sellers": "ใช้เป็นสินค้าหลักของแคมเปญ และดูแลสต็อกให้พร้อมขาย",
    "Popular Low-Price Products": "ใช้ดึงทราฟฟิก จับคู่ขาย หรือเสนอสินค้าที่ราคาสูงขึ้น",
    "Premium Low-Volume": "เจาะกลุ่มลูกค้าเฉพาะ และคุมปริมาณสต็อกให้สอดคล้องกับยอดขาย",
    "Promotion Driven": "ทดลองปรับส่วนลดแทนการเพิ่มส่วนลดต่อเนื่อง แล้วดูผลต่อยอดขาย",
    "Low Performance": "ทบทวนสต็อก การลดราคา หรือตำแหน่งของสินค้าก่อนตัดสินใจสั่งเพิ่ม",
    "Balanced Mix": "อ่านค่าเฉลี่ยของกลุ่มก่อนกำหนดโปรโมชั่นหรือการสั่งซื้อ",
}


def describe_clusters(
    frame: pd.DataFrame,
    centers: np.ndarray | None = None,
) -> list[ClusterFitSummary]:
    labels = np.asarray(frame["cluster"], dtype=int)
    cluster_ids = range(int(labels.max()) + 1 if len(labels) else 0)
    if centers is not None:
        cluster_ids = range(len(centers))
    values = frame.loc[:, FEATURE_COLUMNS].to_numpy(dtype="float64")
    global_mean = values.mean(axis=0) if len(values) else np.zeros(4)
    global_std = values.std(axis=0) if len(values) else np.zeros(4)
    summaries: list[ClusterFitSummary] = []
    for cluster_id in cluster_ids:
        member_mask = labels == cluster_id
        count = int(member_mask.sum())
        if count:
            means = values[member_mask].mean(axis=0)
        elif centers is not None:
            means = np.asarray(centers[cluster_id], dtype="float64")
        else:
            means = global_mean.copy()
        published = means if centers is None else np.asarray(centers[cluster_id], dtype="float64")
        score = _z(means, global_mean, global_std)
        name = _archetype(score)
        summaries.append(
            ClusterFitSummary(
                cluster_id=cluster_id,
                product_count=count,
                centroid_price_usd=float(published[0]),
                centroid_pct_discount=float(published[1]),
                centroid_qty_sold=float(published[2]),
                centroid_sales_value=float(published[3]),
                cluster_name=name,
                characteristics=_characteristics(score),
                recommendations=[_RECOMMENDATIONS[name], DECISION_SUPPORT],
            )
        )
    return summaries


def explain_product(
    values: dict[str, float],
    cluster_means: dict[str, float],
    cluster_name: str,
) -> str:
    comparisons = []
    for column, label in FEATURE_LABELS:
        position = _position(float(values[column]), float(cluster_means[column]))
        if position == "near":
            comparisons.append(f"{label}ใกล้ค่าเฉลี่ยของกลุ่ม")
        elif position == "above":
            comparisons.append(f"{label}สูงกว่าค่าเฉลี่ยของกลุ่ม")
        else:
            comparisons.append(f"{label}ต่ำกว่าค่าเฉลี่ยของกลุ่ม")
    detail = " ".join(comparisons)
    return (
        f"สินค้าอยู่ใกล้จุดศูนย์กลางของกลุ่ม {cluster_name} ในข้อมูลที่ปรับสเกลแล้ว {detail}"
    )


def nearest_cluster(scaled_row: np.ndarray, scaled_centers: np.ndarray) -> int:
    distances = np.linalg.norm(scaled_centers - scaled_row, axis=1)
    return int(np.argmin(distances))


def _archetype(score: np.ndarray) -> str:
    price, discount, quantity, sales = (float(item) for item in score)
    candidates: list[tuple[str, float]] = []
    if _high(sales) and _high(quantity):
        candidates.append(("High Value / Best Sellers", min(sales, quantity)))
    if _low(price) and _high(quantity):
        candidates.append(("Popular Low-Price Products", min(-price, quantity)))
    if _high(price) and _low(quantity):
        candidates.append(("Premium Low-Volume", min(price, -quantity)))
    others = (price, quantity, sales)
    if _high(discount) and discount > max(others):
        candidates.append(("Promotion Driven", discount))
    if _low(sales) and _low(quantity):
        candidates.append(("Low Performance", min(-sales, -quantity)))
    if not candidates:
        return "Balanced Mix"
    priority = {name: index for index, name in enumerate(ARCHETYPE_PRIORITY)}
    return max(candidates, key=lambda item: (item[1], -priority[item[0]]))[0]


def _characteristics(score: np.ndarray) -> str:
    phrases = []
    for index, (_, label) in enumerate(FEATURE_LABELS):
        value = float(score[index])
        if _high(value):
            phrases.append(f"{label}สูงกว่าค่าเฉลี่ยทั้งตาราง")
        elif _low(value):
            phrases.append(f"{label}ต่ำกว่าค่าเฉลี่ยทั้งตาราง")
        else:
            phrases.append(f"{label}ใกล้ค่าเฉลี่ยทั้งตาราง")
    return " ".join(phrases)


def _z(means: np.ndarray, global_mean: np.ndarray, global_std: np.ndarray) -> np.ndarray:
    safe_std = np.where(global_std == 0, 1.0, global_std)
    scores = (means - global_mean) / safe_std
    scores = np.where(global_std == 0, 0.0, scores)
    return scores


def _high(value: float) -> bool:
    return value >= Z_CLEAR


def _low(value: float) -> bool:
    return value <= -Z_CLEAR


def _position(value: float, center: float) -> str:
    if center == 0:
        if value == 0:
            return "near"
        return "above" if value > 0 else "below"
    if abs(value - center) / abs(center) <= NEAR_MEAN_RATIO:
        return "near"
    return "above" if value > center else "below"
