import { UploadForm } from "@/components/UploadForm";

export default function UploadPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        อัปโหลดไฟล์ CSV แล้วยืนยันคอลัมน์ราคา ส่วนลด และจำนวนขาย
        จากนั้นทำความสะอาดข้อมูล คำนวณมูลค่าการขาย และปรับสเกลฟีเจอร์บนหน้านี้
        การจัดกลุ่มทำในขั้นตอนถัดไป
      </p>
      <UploadForm />
    </section>
  );
}
