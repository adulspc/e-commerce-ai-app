import { DashboardPanel } from "@/components/DashboardPanel";

export default function DashboardPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        สรุปสินค้าที่จัดกลุ่มแล้ว พร้อมจำนวนสินค้าแต่ละกลุ่ม กราฟกระจาย และค่าเฉลี่ยของกลุ่ม
      </p>
      <DashboardPanel />
    </section>
  );
}
