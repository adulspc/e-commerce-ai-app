import { DashboardCharts } from "@/components/DashboardCharts";
import { CLUSTER_COLORS } from "@/lib/clusterColors";
import { clusterFallback } from "@/lib/theme";
import type { DashboardSummary } from "@/types";

export function DashboardView({
  summary,
  filename,
}: {
  summary: DashboardSummary;
  filename?: string | null;
}) {
  const cards = [
    ["สินค้าทั้งหมด", formatNumber(summary.total_products)],
    ["ราคาเฉลี่ย (USD)", formatNumber(summary.average_price)],
    ["ส่วนลดเฉลี่ย (%)", formatNumber(summary.average_discount)],
    ["จำนวนขายรวม", formatNumber(summary.total_quantity_sold)],
    ["มูลค่าการขายรวม (USD)", formatNumber(summary.total_sales_value)],
    ["จำนวนกลุ่ม", formatNumber(summary.number_of_clusters)],
  ] as const;

  return (
    <div id="dashboard-summary" className="space-y-8">
      <section className="card grain px-6 py-6">
        <p className="text-xs tracking-[0.14em] text-pea-deep uppercase">Product Intelligence</p>
        <h2 className="mt-2 max-w-xl text-2xl font-semibold text-ink">See the patterns behind your products.</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
          Discover product groups, sales behavior and business opportunities through K-Means clustering.
        </p>
        <dl className="mt-5 grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted">Dataset</dt>
            <dd className="mt-1 truncate text-sm font-medium text-ink">{filename || "ชุดข้อมูลนี้"}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Products</dt>
            <dd className="mt-1 text-sm font-medium text-ink">{formatNumber(summary.total_products)}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted">Clusters</dt>
            <dd className="mt-1 text-sm font-medium text-ink">{formatNumber(summary.number_of_clusters)}</dd>
          </div>
        </dl>
      </section>
      <div id="dashboard-kpis" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map(([label, value]) => (
          <article key={label} className="card relative overflow-hidden px-5 py-5">
            <span className="absolute inset-y-4 left-0 w-1 rounded-full bg-pea" aria-hidden />
            <p className="text-xs text-muted">{label}</p>
            <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
          </article>
        ))}
      </div>
      <DashboardCharts summary={summary} />
      <section>
        <h2 className="text-sm font-semibold text-ink">โปรไฟล์กลุ่ม</h2>
        <p className="mt-1 text-sm text-muted">
          ค่าเฉลี่ยมาจากจุดศูนย์กลางของกลุ่มในหน่วยเดิม ชื่อกลุ่มบอกลักษณะของค่าเฉลี่ย ไม่ได้เรียงตามคุณภาพ
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {summary.clusters.map((cluster) => (
            <article
              key={cluster.cluster_id}
              id={`cluster-profile-${cluster.cluster_id}`}
              className="card p-5 transition duration-200 hover:-translate-y-0.5"
            >
              <div className="flex items-center gap-2">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full"
                  style={{ backgroundColor: CLUSTER_COLORS[cluster.cluster_id] ?? clusterFallback }}
                />
                <h3 className="text-sm font-semibold text-ink">{cluster.cluster_name}</h3>
                <span className="text-xs text-muted">กลุ่ม {cluster.cluster_id}</span>
              </div>
              <p className="mt-2 text-sm text-muted">
                {formatNumber(cluster.product_count)} รายการ · ราคา {formatNumber(cluster.avg_price)} · ส่วนลด{" "}
                {formatNumber(cluster.avg_discount)} · จำนวนขาย {formatNumber(cluster.avg_qty_sold)} · มูลค่าการขาย{" "}
                {formatNumber(cluster.avg_sales_value)}
              </p>
              <p className="mt-2 text-sm leading-6 text-ink">{cluster.characteristics}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function formatNumber(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 2 });
}
