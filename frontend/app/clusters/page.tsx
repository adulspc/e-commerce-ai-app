import { ClusterRun } from "@/components/ClusterRun";

export default function ClustersPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        เลือกจำนวนกลุ่มได้ 2 ถึง 10 การ์ดแต่ละใบแสดงค่าเฉลี่ย ลักษณะ และคำแนะนำ
        ชื่อกลุ่มบอกลักษณะของค่าเฉลี่ย และคำแนะนำเป็นข้อมูลประกอบการตัดสินใจ
      </p>
      <ClusterRun />
    </section>
  );
}
