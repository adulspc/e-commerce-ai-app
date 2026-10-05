const PRODUCT_COLUMNS = [
  "product_name",
  "category",
  "price_usd",
  "pct_discount",
  "qty_sold",
  "sales_value",
  "cluster",
  "cluster_name",
];

const CLUSTER_COLUMNS = [
  "cluster",
  "cluster_name",
  "product_count",
  "avg_price",
  "avg_discount",
  "avg_qty_sold",
  "avg_sales_value",
  "characteristics",
  "recommendations",
];

export function ExportView({
  filename,
  k,
  busy,
  onDownload,
}: {
  filename: string | null;
  k: number | null;
  busy: "products" | "clusters" | null;
  onDownload: (kind: "products" | "clusters") => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        ไฟล์ {filename ?? "ชุดข้อมูลนี้"}
        {k ? ` · จัดเป็น ${k.toLocaleString("th-TH")} กลุ่ม` : ""}
        {" · "}มีเฉพาะแถวที่ผ่านการทำความสะอาดและจัดกลุ่มแล้ว
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <ExportCard
          id="export-products"
          title="สินค้า"
          fileName="products.csv"
          columns={PRODUCT_COLUMNS}
          busy={busy === "products"}
          disabled={busy !== null}
          onClick={() => onDownload("products")}
        />
        <ExportCard
          id="export-clusters"
          title="สรุปกลุ่ม"
          fileName="clusters.csv"
          columns={CLUSTER_COLUMNS}
          busy={busy === "clusters"}
          disabled={busy !== null}
          onClick={() => onDownload("clusters")}
        />
      </div>
    </div>
  );
}

function ExportCard({
  id,
  title,
  fileName,
  columns,
  busy,
  disabled,
  onClick,
}: {
  id: string;
  title: string;
  fileName: string;
  columns: string[];
  busy: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <article className="card p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <p className="mt-1 text-xs text-muted">{fileName}</p>
      <ul className="mt-3 space-y-1 text-sm text-ink">
        {columns.map((column) => (
          <li key={column}>{column}</li>
        ))}
      </ul>
      <button
        id={id}
        type="button"
        disabled={disabled}
        onClick={onClick}
        className="mt-4 btn-primary"
      >
        {busy ? "กำลังดาวน์โหลด..." : "ดาวน์โหลด CSV"}
      </button>
    </article>
  );
}
