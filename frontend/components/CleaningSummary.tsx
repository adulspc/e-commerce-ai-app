import type { CleaningReport, ColumnMapping, FeatureReport, ScalingReport } from "@/types";

import { FIELD_LABELS } from "@/lib/dataset";

export function CleaningSummary({
  report,
  mapping,
  featureReport,
  scalingReport,
}: {
  report: CleaningReport;
  mapping?: ColumnMapping | null;
  featureReport?: FeatureReport | null;
  scalingReport?: ScalingReport | null;
}) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Metric label="แถวก่อนทำความสะอาด" value={report.rows_before} />
        <Metric label="แถวที่ใช้วิเคราะห์" value={report.rows_after} />
        <Metric label="แถวที่ขาดค่า" value={report.missing_values_handled} />
        <Metric label="แถวที่ค่าไม่ถูกต้อง" value={report.invalid_rows_removed} />
        <Metric label="แถวซ้ำที่ตัดออก" value={report.duplicate_rows_removed} />
      </div>
      <p className="text-sm text-muted">
        ขาดราคา {report.missing_price.toLocaleString("th-TH")} แถว · ขาดจำนวนขาย{" "}
        {report.missing_quantity.toLocaleString("th-TH")} แถว · ขาดส่วนลด{" "}
        {report.missing_discount.toLocaleString("th-TH")} แถว
      </p>
      {report.rows_after < 10 ? (
        <p className="alert-warn">
          ข้อมูลหลังทำความสะอาดมีน้อยกว่า 10 รายการ จึงยังจัดกลุ่มไม่ได้
        </p>
      ) : (
        <p className="alert-ok">
          ทำความสะอาดแล้ว {report.rows_after.toLocaleString("th-TH")} รายการ
          พร้อมสำหรับขั้นตอนจัดกลุ่ม
        </p>
      )}
      {featureReport ? <FeatureSummary report={featureReport} /> : null}
      {scalingReport ? <ScalingSummary report={scalingReport} /> : null}
      {mapping ? (
        <dl className="grid gap-3 sm:grid-cols-2">
          {FIELD_LABELS.map(([key, label]) => (
            <div key={key}>
              <dt className="text-xs text-muted">{label}</dt>
              <dd className="text-sm">{mapping[key] ?? "ไม่ได้ใช้"}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}

function FeatureSummary({ report }: { report: FeatureReport }) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold">มูลค่าการขาย (sales_value)</h3>
        <p className="mt-1 text-sm text-muted">
          คำนวณจากราคา × จำนวนขาย ทั้ง {report.row_count.toLocaleString("th-TH")} แถว
          ฟีเจอร์สำหรับจัดกลุ่มคือ price_usd, pct_discount, qty_sold และ sales_value
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Amount label="ต่ำสุด" value={report.min_sales_value} />
        <Amount label="มัธยฐาน" value={report.median_sales_value} />
        <Amount label="เฉลี่ย" value={report.mean_sales_value} />
        <Amount label="สูงสุด" value={report.max_sales_value} />
      </div>
    </div>
  );
}

const FEATURE_LABELS: Record<string, string> = {
  price_usd: "ราคา",
  pct_discount: "ส่วนลด",
  qty_sold: "จำนวนขาย",
  sales_value: "มูลค่าการขาย",
};

function ScalingSummary({ report }: { report: ScalingReport }) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-semibold">StandardScaler</h3>
        <p className="mt-1 text-sm text-muted">
          ปรับฟีเจอร์ทั้งสี่จากค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของ{" "}
          {report.sample_count.toLocaleString("th-TH")} แถวในชุดนี้
          ค่าในตารางสินค้ายังเป็นหน่วยเดิม
        </p>
      </div>
      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-foam text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">ฟีเจอร์</th>
              <th className="px-3 py-2 font-medium">ค่าเฉลี่ย</th>
              <th className="px-3 py-2 font-medium">ส่วนเบี่ยงเบนมาตรฐาน</th>
            </tr>
          </thead>
          <tbody>
            {report.features.map((feature) => (
              <tr key={feature.feature} className="border-t border-line">
                <td className="px-3 py-2">
                  {FEATURE_LABELS[feature.feature] ?? feature.feature}
                  <span className="ml-2 text-xs text-muted">{feature.feature}</span>
                </td>
                <td className="px-3 py-2">{formatScale(feature.mean)}</td>
                <td className="px-3 py-2">
                  {formatScale(feature.std)}
                  {feature.constant ? (
                    <span className="ml-2 text-xs text-earth">ค่านี้เท่ากันทุกแถว</span>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatScale(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 4 });
}

function Amount({ label, value }: { label: string; value: number }) {
  const text = value.toLocaleString("th-TH", { maximumFractionDigits: 2 });
  return (
    <div className="card px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{text}</p>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  const text = value.toLocaleString("th-TH");
  return (
    <div className="card px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold">{text}</p>
    </div>
  );
}
