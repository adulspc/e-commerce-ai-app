import { Suspense } from "react";

import { ProductExplorer } from "@/components/ProductExplorer";

export default function ProductsPage() {
  return (
    <section className="max-w-6xl">
      <p className="max-w-2xl text-sm leading-6 text-muted">
        ค้นหา กรอง และเรียงสินค้าที่จัดกลุ่มแล้ว คลิกชื่อสินค้าเพื่อดูค่าเทียบกับค่าเฉลี่ยของกลุ่ม
      </p>
      <Suspense fallback={<p className="mt-6 text-sm text-muted">กำลังโหลดรายการ...</p>}>
        <ProductExplorer />
      </Suspense>
    </section>
  );
}
