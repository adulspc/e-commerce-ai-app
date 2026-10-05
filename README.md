# E-Commerce Product Clustering System

ระบบวิเคราะห์และจัดกลุ่มสินค้า E-Commerce ด้วย K-Means Clustering

## โครงโปรเจกต์

- `frontend/` — Next.js, TypeScript, Tailwind CSS
- `backend/` — FastAPI, การทำความสะอาดข้อมูล, StandardScaler และ KMeans
- `data/` — ไฟล์ CSV ต้นทาง
- `data/sessions/` — ผลของแต่ละครั้งที่อัปโหลด

## รันตัวตรวจโครงสร้าง

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

ตรวจที่ `http://localhost:8000/api/health` ควรได้ `{"status":"ok"}`

`GET /api/sessions/{session_id}` อ่านสถานะของชุดข้อมูลที่อัปโหลด หากไม่พบเซสชัน ระบบตอบ 404 พร้อมข้อความภาษาไทย

`POST /api/dataset/upload` รับไฟล์ `.csv` แล้วสร้างเซสชันใหม่ พร้อมตัวอย่าง 20 แถวและการจับคู่คอลัมน์

`GET /api/dataset/preview?session_id=` อ่านตัวอย่างจากไฟล์ที่อัปโหลดไว้

`POST /api/dataset/process` รับ `session_id` และการจับคู่คอลัมน์ แล้วทำความสะอาดข้อมูล คำนวณ `sales_value = price_usd × qty_sold` และ fit StandardScaler จากฟีเจอร์ทั้งสี่ของเซสชันนั้น

`GET /api/dataset/cleaning?session_id=` อ่านรายงานนั้นซ้ำ ใช้ได้หลังประมวลผลแล้ว

`POST /api/clustering/run` รับ `session_id` และ `k` ตั้งแต่ 2 ถึง 10 แล้ว fit K-Means บนข้อมูลที่ปรับสเกลแล้วของเซสชันนั้น จากนั้นตั้งชื่อกลุ่มจากค่าเฉลี่ยเทียบกับทั้งตาราง

`GET /api/clustering/result?session_id=` อ่านผลการจัดกลุ่มล่าสุด หากผลเก่าไม่มีชื่อกลุ่ม ระบบเติมชื่อจากค่าเฉลี่ยแล้วบันทึกกลับ

`GET /api/clustering/optimal-k?session_id=` คำนวณ Elbow จาก inertia ของทุกแถว และ Silhouette สำหรับ K ตั้งแต่ 2 ถึง 10 เมื่อข้อมูลมากกว่า 5,000 แถว Silhouette ใช้ตัวอย่างสุ่ม 5,000 แถว ค่าที่เสนอคือ Silhouette สูงสุด

หลังจัดกลุ่มแล้ว ใช้ `session_id` กับเส้นทางเหล่านี้

`GET /api/clusters` และ `GET /api/clusters/{cluster_id}` อ่านชื่อกลุ่ม ค่าเฉลี่ย และคำแนะนำ

`GET /api/products` ค้นหา กรองกลุ่มหรือหมวด เรียงราคา จำนวนขาย หรือมูลค่าการขาย และแบ่งหน้า หน้าละ 20 รายการ สูงสุด 100

`GET /api/products/{id}` อ่านสินค้าหนึ่งรายการพร้อมข้อความเปรียบเทียบกับค่าเฉลี่ยของกลุ่ม

`GET /api/dashboard/summary` อ่านตัวเลขสรุปและจุดสำหรับกราฟกระจาย สุ่มอย่างมาก 2,000 จุด และไม่เกิน 400 จุดต่อกลุ่ม

`GET /api/export/products` และ `GET /api/export/clusters` ดาวน์โหลด CSV

```bash
pytest
```

จาก `frontend` รัน `npm test` เพื่อตรวจว่าหน้าแดชบอร์ด รายการสินค้า การ์ดกลุ่ม และปุ่มส่งออกเรนเดอร์ส่วนที่ต้องใช้

```bash
cd frontend
npm run dev
```

เปิด `http://localhost:3000` เพื่อดูแถบนำทางทั้ง 7 หน้า หน้าส่งออกดาวน์โหลด `products.csv` และ `clusters.csv` หลังจัดกลุ่มแล้ว
"# e-commerce-ai-app" 
