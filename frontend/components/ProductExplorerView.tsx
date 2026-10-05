import type { FormEvent } from "react";

import { CLUSTER_COLORS } from "@/lib/clusterColors";
import { clusterFallback } from "@/lib/theme";
import type { ClusterSummary, ProductDetail, ProductPage } from "@/types";

type SortField = "" | "price_usd" | "qty_sold" | "sales_value";

export function ProductExplorerView({
  result,
  clusters,
  draftSearch,
  category,
  cluster,
  sort,
  order,
  loading,
  selectedId,
  detail,
  detailLoading,
  detailError,
  onDraftSearch,
  onSearch,
  onCategory,
  onCluster,
  onSort,
  onOrder,
  onPage,
  onSelect,
  onCloseDetail,
}: {
  result: ProductPage;
  clusters: ClusterSummary[];
  draftSearch: string;
  category: string;
  cluster: string;
  sort: SortField;
  order: "asc" | "desc";
  loading: boolean;
  selectedId: string | null;
  detail: ProductDetail | null;
  detailLoading: boolean;
  detailError: string | null;
  onDraftSearch: (value: string) => void;
  onSearch: (event: FormEvent<HTMLFormElement>) => void;
  onCategory: (value: string) => void;
  onCluster: (value: string) => void;
  onSort: (value: SortField) => void;
  onOrder: (value: "asc" | "desc") => void;
  onPage: (page: number) => void;
  onSelect: (id: string) => void;
  onCloseDetail: () => void;
}) {
  const start = result.total === 0 ? 0 : (result.page - 1) * result.page_size + 1;
  const end = Math.min(result.page * result.page_size, result.total);
  const pageCount = Math.max(1, Math.ceil(result.total / result.page_size));
  const categories = result.categories.filter((item) => item.trim());

  return (
    <div className="space-y-4">
      <form onSubmit={onSearch} className="card grid gap-4 p-5 md:grid-cols-2 xl:grid-cols-6">
        <label className="text-sm text-ink xl:col-span-2">
          ค้นหาชื่อสินค้า
          <span className="mt-1 flex gap-2">
            <input
              id="product-search"
              value={draftSearch}
              onChange={(event) => onDraftSearch(event.target.value)}
              className="field"
            />
            <button
              id="product-search-submit"
              type="submit"
              className="btn-primary"
            >
              ค้นหา
            </button>
          </span>
        </label>
        <label className="text-sm text-ink">
          หมวดหมู่
          <select
            id="product-category"
            value={category}
            onChange={(event) => onCategory(event.target.value)}
            className="field mt-1"
          >
            <option value="">ทุกหมวด</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-ink">
          กลุ่ม
          <select
            id="product-cluster"
            value={cluster}
            onChange={(event) => onCluster(event.target.value)}
            className="field mt-1"
          >
            <option value="">ทุกกลุ่ม</option>
            {clusters.map((item) => (
              <option key={item.cluster_id} value={String(item.cluster_id)}>
                กลุ่ม {item.cluster_id} · {item.cluster_name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-ink">
          เรียงตาม
          <select
            id="product-sort"
            value={sort}
            onChange={(event) => onSort(event.target.value as SortField)}
            className="field mt-1"
          >
            <option value="">ลำดับในไฟล์</option>
            <option value="price_usd">ราคา</option>
            <option value="qty_sold">จำนวนขาย</option>
            <option value="sales_value">มูลค่าการขาย</option>
          </select>
        </label>
        <label className="text-sm text-ink">
          ทิศทาง
          <select
            id="product-order"
            value={order}
            disabled={!sort}
            onChange={(event) => onOrder(event.target.value as "asc" | "desc")}
            className="field mt-1 disabled:opacity-60"
          >
            <option value="desc">มากไปน้อย</option>
            <option value="asc">น้อยไปมาก</option>
          </select>
        </label>
      </form>

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-muted">
        <p id="product-page-label">
          {loading ? "กำลังโหลดรายการ..." : `${formatNumber(start)}–${formatNumber(end)} จาก ${formatNumber(result.total)} รายการ`}
        </p>
        <div className="flex items-center gap-2">
          <button
            id="product-page-prev"
            type="button"
            disabled={result.page <= 1 || loading}
            onClick={() => onPage(result.page - 1)}
            className="btn-secondary"
          >
            ก่อนหน้า
          </button>
          <span>
            หน้า {formatNumber(result.page)} จาก {formatNumber(pageCount)}
          </span>
          <button
            id="product-page-next"
            type="button"
            disabled={result.page >= pageCount || loading}
            onClick={() => onPage(result.page + 1)}
            className="btn-secondary"
          >
            ถัดไป
          </button>
        </div>
      </div>

      <div className="card overflow-x-auto">
        <table id="product-table" className="min-w-[880px] w-full text-left text-sm">
          <thead className="bg-foam text-xs text-moss">
            <tr>
              <th className="px-3 py-2 font-medium">สินค้า</th>
              <th className="px-3 py-2 font-medium">หมวดหมู่</th>
              <th className="px-3 py-2 font-medium">ราคา</th>
              <th className="px-3 py-2 font-medium">ส่วนลด</th>
              <th className="px-3 py-2 font-medium">จำนวนขาย</th>
              <th className="px-3 py-2 font-medium">มูลค่าการขาย</th>
              <th className="px-3 py-2 font-medium">กลุ่ม</th>
              <th className="px-3 py-2 font-medium">ชื่อกลุ่ม</th>
            </tr>
          </thead>
          <tbody>
            {result.products.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-muted">
                  ไม่พบสินค้าตามเงื่อนไขนี้
                </td>
              </tr>
            ) : (
              result.products.map((product) => {
                const open = selectedId === product.id;
                return (
                  <tr key={product.id} className={`border-b border-line transition duration-200 hover:bg-row ${open ? "bg-foam" : ""}`}>
                    <td className="px-3 py-2">
                      <button
                        id={`product-open-${product.id}`}
                        type="button"
                        onClick={() => onSelect(product.id)}
                        className="text-left font-medium underline"
                      >
                        {product.product_name || "—"}
                      </button>
                    </td>
                    <td className="px-3 py-2">{product.category || "—"}</td>
                    <td className="px-3 py-2">{formatNumber(product.price_usd)}</td>
                    <td className="px-3 py-2">{formatNumber(product.pct_discount)}</td>
                    <td className="px-3 py-2">{formatNumber(product.qty_sold)}</td>
                    <td className="px-3 py-2">{formatNumber(product.sales_value)}</td>
                    <td className="px-3 py-2">{product.cluster}</td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-2 rounded-full bg-foam px-2 py-1 text-xs text-moss">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: CLUSTER_COLORS[product.cluster] ?? clusterFallback }}
                        />
                        กลุ่ม {product.cluster} · {product.cluster_name}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {detailLoading ? <p className="text-sm text-muted">กำลังอ่านรายละเอียด...</p> : null}
      {detailError ? (
        <p className="alert-danger">{detailError}</p>
      ) : null}
      {detail ? (
        <article id="product-detail" className="card p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold">{detail.product_name || "—"}</h2>
              <p className="mt-1 text-sm text-muted">{detail.category || "—"}</p>
            </div>
            <button type="button" onClick={onCloseDetail} className="text-sm underline">
              ปิด
            </button>
          </div>
          <p className="mt-3 text-sm text-ink">
            ราคา {formatNumber(detail.price_usd)} · ส่วนลด {formatNumber(detail.pct_discount)} · จำนวนขาย{" "}
            {formatNumber(detail.qty_sold)} · มูลค่าการขาย {formatNumber(detail.sales_value)}
          </p>
          <p className="mt-2 inline-flex items-center gap-2 text-sm font-medium">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: CLUSTER_COLORS[detail.cluster] ?? clusterFallback }}
            />
            กลุ่ม {detail.cluster} · {detail.cluster_name}
          </p>
          <h3 className="mt-4 text-sm font-semibold">เหตุผลที่อยู่ในกลุ่มนี้</h3>
          <p id="product-detail-explanation" className="mt-1 text-sm leading-6 text-ink">
            {detail.explanation}
          </p>
        </article>
      ) : null}
    </div>
  );
}

function formatNumber(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 2 });
}
