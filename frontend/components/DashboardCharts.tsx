"use client";

import type { ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CLUSTER_COLORS } from "@/lib/clusterColors";
import { chartAxis, chartGrid, clusterFallback } from "@/lib/theme";
import type { ClusterSummary, DashboardSummary, ScatterPoint } from "@/types";

export function DashboardCharts({ summary }: { summary: DashboardSummary }) {
  const distribution = summary.clusters.map((cluster) => ({
    cluster_id: cluster.cluster_id,
    cluster_name: cluster.cluster_name,
    label: `กลุ่ม ${cluster.cluster_id}`,
    product_count: cluster.product_count,
    fill: colorFor(cluster.cluster_id),
  }));
  const series = summary.clusters.map((cluster) => ({
    cluster,
    points: summary.scatter.filter((point) => point.cluster === cluster.cluster_id),
  }));
  const scatterNote = summary.scatter_sampled
    ? `กราฟกระจายใช้ตัวอย่างสุ่ม ${formatNumber(summary.scatter_sample_size)} จุด จาก ${formatNumber(summary.total_products)} รายการ และไม่เกิน 400 จุดต่อกลุ่ม`
    : `กราฟกระจายใช้ทุกแถว ${formatNumber(summary.total_products)} รายการ`;

  return (
    <div className="space-y-4">
      <ChartCard id="chart-distribution" title="จำนวนสินค้าแต่ละกลุ่ม">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={distribution}>
            <CartesianGrid stroke={chartGrid} />
            <XAxis dataKey="label" interval={0} tick={{ fontSize: 12, fill: chartAxis }} />
            <YAxis tickFormatter={formatTick} width={64} tick={{ fill: chartAxis }} />
            <Tooltip content={<DistributionTooltip />} />
            <Bar dataKey="product_count" name="จำนวนสินค้า">
              {distribution.map((item) => (
                <Cell key={item.cluster_id} fill={item.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <p className="text-sm text-muted">{scatterNote}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ScatterCard
          id="chart-price-qty"
          title="ราคา กับ จำนวนขาย"
          xKey="price_usd"
          xLabel="ราคา (USD)"
          series={series}
        />
        <ScatterCard
          id="chart-discount-qty"
          title="ส่วนลด กับ จำนวนขาย"
          xKey="pct_discount"
          xLabel="ส่วนลด (%)"
          series={series}
        />
        <ScatterCard
          id="chart-sales-qty"
          title="มูลค่าการขาย กับ จำนวนขาย"
          xKey="sales_value"
          xLabel="มูลค่าการขาย (USD)"
          series={series}
        />
      </div>

      <section>
        <h2 className="text-sm font-semibold">ค่าเฉลี่ยของแต่ละกลุ่ม</h2>
        <p className="mt-1 text-sm text-muted">แต่ละกราฟใช้หน่วยของตัวเอง เพื่อเทียบกลุ่มในมิติเดียว</p>
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          <MetricCard id="chart-profile-price" title="ราคาเฉลี่ย (USD)" dataKey="avg_price" clusters={summary.clusters} />
          <MetricCard id="chart-profile-discount" title="ส่วนลดเฉลี่ย (%)" dataKey="avg_discount" clusters={summary.clusters} />
          <MetricCard id="chart-profile-qty" title="จำนวนขายเฉลี่ย" dataKey="avg_qty_sold" clusters={summary.clusters} />
          <MetricCard id="chart-profile-sales" title="มูลค่าการขายเฉลี่ย (USD)" dataKey="avg_sales_value" clusters={summary.clusters} />
        </div>
      </section>
    </div>
  );
}

function ScatterCard({
  id,
  title,
  xKey,
  xLabel,
  series,
}: {
  id: string;
  title: string;
  xKey: "price_usd" | "pct_discount" | "sales_value";
  xLabel: string;
  series: Array<{ cluster: ClusterSummary; points: ScatterPoint[] }>;
}) {
  return (
    <ChartCard id={id} title={title}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart>
          <CartesianGrid stroke={chartGrid} />
          <XAxis type="number" dataKey={xKey} name={xLabel} tickFormatter={formatTick} tick={{ fill: chartAxis }} />
          <YAxis type="number" dataKey="qty_sold" name="จำนวนขาย" tickFormatter={formatTick} width={64} tick={{ fill: chartAxis }} />
          <Tooltip content={<ScatterTooltip xKey={xKey} xLabel={xLabel} />} />
          {series.map(({ cluster, points }) => (
            <Scatter
              key={cluster.cluster_id}
              name={`กลุ่ม ${cluster.cluster_id} · ${cluster.cluster_name}`}
              data={points}
              fill={colorFor(cluster.cluster_id)}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function MetricCard({
  id,
  title,
  dataKey,
  clusters,
}: {
  id: string;
  title: string;
  dataKey: "avg_price" | "avg_discount" | "avg_qty_sold" | "avg_sales_value";
  clusters: ClusterSummary[];
}) {
  const data = clusters.map((cluster) => ({
    cluster_id: cluster.cluster_id,
    cluster_name: cluster.cluster_name,
    label: `กลุ่ม ${cluster.cluster_id}`,
    value: cluster[dataKey],
    fill: colorFor(cluster.cluster_id),
  }));
  return (
    <ChartCard id={id} title={title}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <CartesianGrid stroke={chartGrid} />
          <XAxis dataKey="label" interval={0} tick={{ fontSize: 12, fill: chartAxis }} />
          <YAxis tickFormatter={formatTick} width={64} tick={{ fill: chartAxis }} />
          <Tooltip content={<MetricTooltip />} />
          <Bar dataKey="value" name={title}>
            {data.map((item) => (
              <Cell key={item.cluster_id} fill={item.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

function ChartCard({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="card p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-3 h-72">{children}</div>
    </section>
  );
}

function DistributionTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { cluster_id: number; cluster_name: string; product_count: number } }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-xl bg-moss px-3 py-2 text-xs text-cream shadow-[0_8px_20px_rgba(48,56,42,0.18)]">
      <p>
        กลุ่ม {row.cluster_id} · {row.cluster_name}
      </p>
      <p>{formatNumber(row.product_count)} รายการ</p>
    </div>
  );
}

function MetricTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { cluster_id: number; cluster_name: string; value: number } }>;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-xl bg-moss px-3 py-2 text-xs text-cream shadow-[0_8px_20px_rgba(48,56,42,0.18)]">
      <p>
        กลุ่ม {row.cluster_id} · {row.cluster_name}
      </p>
      <p>{formatNumber(row.value)}</p>
    </div>
  );
}

function ScatterTooltip({
  active,
  payload,
  xKey,
  xLabel,
}: {
  active?: boolean;
  payload?: Array<{ payload: ScatterPoint & { cluster_name?: string } }>;
  xKey: "price_usd" | "pct_discount" | "sales_value";
  xLabel: string;
}) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-xl bg-moss px-3 py-2 text-xs text-cream shadow-[0_8px_20px_rgba(48,56,42,0.18)]">
      <p>กลุ่ม {row.cluster}</p>
      <p>
        {xLabel} {formatNumber(row[xKey])}
      </p>
      <p>จำนวนขาย {formatNumber(row.qty_sold)}</p>
    </div>
  );
}

function colorFor(clusterId: number) {
  return CLUSTER_COLORS[clusterId] ?? clusterFallback;
}

function formatNumber(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 2 });
}

function formatTick(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 0 });
}
