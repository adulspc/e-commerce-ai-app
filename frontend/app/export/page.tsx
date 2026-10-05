import { ExportPanel } from "@/components/ExportPanel";

export default function ExportPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        ดาวน์โหลดผลจัดกลุ่มล่าสุดเป็น CSV ของสินค้าทุกแถว และสรุปของแต่ละกลุ่ม
      </p>
      <ExportPanel />
    </section>
  );
}
