import { OptimalKPanel } from "@/components/OptimalKPanel";

export default function OptimalKPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        เปรียบเทียบจำนวนกลุ่มตั้งแต่ 2 ถึง 10 ด้วยกราฟ Elbow และ Silhouette
        ระบบเสนอค่าที่ Silhouette สูงสุด และผู้ใช้เปลี่ยนจำนวนกลุ่มได้
      </p>
      <OptimalKPanel />
    </section>
  );
}
