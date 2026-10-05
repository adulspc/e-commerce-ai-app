import { ProcessingReport } from "@/components/ProcessingReport";

export default function ProcessingPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        รายงานจำนวนแถวก่อนและหลังทำความสะอาด ช่วงของมูลค่าการขาย
        และค่าที่ StandardScaler ใช้ของชุดข้อมูลล่าสุดในเบราว์เซอร์นี้
        การจัดกลุ่มทำในขั้นตอนถัดไป
      </p>
      <ProcessingReport />
    </section>
  );
}
