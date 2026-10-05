import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ClusterAnalysisView } from "../components/ClusterAnalysisView";
import { DashboardView } from "../components/DashboardView";
import { ExportView } from "../components/ExportView";
import { ProductExplorerView } from "../components/ProductExplorerView";
import type { ClusterFit, DashboardSummary, ProductPage } from "../types";

const clusters: ClusterFit[] = [
  {
    cluster_id: 0,
    product_count: 8,
    centroid_price_usd: 2.35,
    centroid_pct_discount: 10,
    centroid_qty_sold: 100,
    centroid_sales_value: 235,
    cluster_name: "Popular Low-Price Products",
    characteristics: "ราคาต่ำกว่าค่าเฉลี่ยทั้งตาราง",
    recommendations: ["ข้อมูลนี้เป็นข้อเสนอประกอบการตัดสินใจ ไม่ได้สั่งดำเนินการให้อัตโนมัติ"],
  },
];

const summary: DashboardSummary = {
  session_id: "sample",
  k: 2,
  total_products: 16,
  average_price: 41,
  average_discount: 7.5,
  total_quantity_sold: 880,
  total_sales_value: 7000,
  number_of_clusters: 2,
  scatter_sample_size: 16,
  scatter_sampled: false,
  scatter: [{ price_usd: 2, pct_discount: 10, qty_sold: 100, sales_value: 200, cluster: 0 }],
  clusters: [
    {
      cluster_id: 0,
      cluster_name: "Popular Low-Price Products",
      product_count: 8,
      avg_price: 2.35,
      avg_discount: 10,
      avg_qty_sold: 100,
      avg_sales_value: 235,
      characteristics: "ราคาต่ำกว่าค่าเฉลี่ยทั้งตาราง",
      recommendations: [],
    },
  ],
};

const products: ProductPage = {
  session_id: "sample",
  page: 1,
  page_size: 20,
  total: 16,
  categories: ["alpha"],
  products: [
    {
      id: "1",
      product_name: "low-0",
      category: "alpha",
      price_usd: 2,
      pct_discount: 10,
      qty_sold: 100,
      sales_value: 200,
      cluster: 0,
      cluster_name: "Popular Low-Price Products",
    },
  ],
};

const screens = [
  renderToStaticMarkup(createElement(DashboardView, { summary })),
  renderToStaticMarkup(
    createElement(ProductExplorerView, {
      result: products,
      clusters: summary.clusters,
      draftSearch: "",
      category: "",
      cluster: "",
      sort: "",
      order: "desc",
      loading: false,
      selectedId: "1",
      detail: {
        ...products.products[0],
        explanation: "สินค้าอยู่ใกล้จุดศูนย์กลางของกลุ่ม Popular Low-Price Products ราคาใกล้ค่าเฉลี่ยของกลุ่ม",
      },
      detailLoading: false,
      detailError: null,
      onDraftSearch: () => undefined,
      onSearch: (event) => event.preventDefault(),
      onCategory: () => undefined,
      onCluster: () => undefined,
      onSort: () => undefined,
      onOrder: () => undefined,
      onPage: () => undefined,
      onSelect: () => undefined,
      onCloseDetail: () => undefined,
    }),
  ),
  renderToStaticMarkup(createElement(ClusterAnalysisView, { clusters })),
  renderToStaticMarkup(
    createElement(ExportView, {
      filename: "shop.csv",
      k: 2,
      busy: null,
      onDownload: () => undefined,
    }),
  ),
];
const html = screens.join("\n");

const labels = [
  "สินค้าทั้งหมด",
  "chart-distribution",
  "chart-price-qty",
  "chart-discount-qty",
  "chart-sales-qty",
  "chart-profile-price",
  "กราฟกระจายใช้ทุกแถว",
  "product-search",
  "product-category",
  "product-cluster",
  "product-sort",
  "product-table",
  "product-detail-explanation",
  "ราคาใกล้ค่าเฉลี่ยของกลุ่ม",
  "cluster-card-0",
  "จำนวนสินค้า",
  "คำแนะนำ",
  'href="/products?cluster=0"',
  "ข้อมูลนี้เป็นข้อเสนอประกอบการตัดสินใจ ไม่ได้สั่งดำเนินการให้อัตโนมัติ",
  "export-products",
  "export-clusters",
  "products.csv",
  "clusters.csv",
  "sales_value",
];

const missing = labels.filter((label) => !html.includes(label));
assert.equal(missing.length, 0, missing.join(", "));
console.log("FRONTEND_ACCEPTANCE_OK");
