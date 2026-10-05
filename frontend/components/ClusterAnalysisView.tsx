import Link from "next/link";

import { CLUSTER_COLORS } from "@/lib/clusterColors";
import { clusterFallback } from "@/lib/theme";
import type { ClusterFit } from "@/types";

export function ClusterAnalysisView({ clusters }: { clusters: ClusterFit[] }) {
  return (
    <div id="cluster-analysis" className="grid gap-4 lg:grid-cols-2">
      {clusters.map((cluster) => {
        const stats = [
          ["จำนวนสินค้า", formatNumber(cluster.product_count)],
          ["ราคาเฉลี่ย (USD)", formatNumber(cluster.centroid_price_usd)],
          ["ส่วนลดเฉลี่ย (%)", formatNumber(cluster.centroid_pct_discount)],
          ["จำนวนขายเฉลี่ย", formatNumber(cluster.centroid_qty_sold)],
          ["มูลค่าการขายเฉลี่ย (USD)", formatNumber(cluster.centroid_sales_value)],
        ] as const;
        return (
          <article
            key={cluster.cluster_id}
            id={`cluster-card-${cluster.cluster_id}`}
            className="card p-5 transition duration-200 hover:-translate-y-0.5"
          >
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: CLUSTER_COLORS[cluster.cluster_id] ?? clusterFallback }}
                />
              <p className="text-xs text-muted">กลุ่ม {cluster.cluster_id}</p>
            </div>
            <h2 className="mt-3 text-lg font-semibold text-ink">{cluster.cluster_name}</h2>
            <dl className="mt-4 grid grid-cols-2 gap-4">
              {stats.map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-muted">{label}</dt>
                  <dd className="text-sm font-medium">{value}</dd>
                </div>
              ))}
            </dl>
            <h3 className="mt-5 border-t border-line pt-4 text-sm font-semibold text-ink">ลักษณะ</h3>
            <p className="mt-1 text-sm leading-6 text-ink">{cluster.characteristics}</p>
            <h3 className="mt-4 border-t border-line pt-4 text-sm font-semibold text-ink">คำแนะนำ</h3>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm leading-6 text-ink">
              {cluster.recommendations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <Link
              id={`cluster-products-${cluster.cluster_id}`}
              href={`/products?cluster=${cluster.cluster_id}`}
              className="mt-4 inline-block text-sm font-medium underline"
            >
              ดูสินค้าในกลุ่มนี้
            </Link>
          </article>
        );
      })}
    </div>
  );
}

function formatNumber(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 2 });
}
