"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CleaningSummary } from "@/components/CleaningSummary";
import { API_BASE_URL } from "@/lib/api";
import { rememberedSession } from "@/lib/dataset";
import type { CleaningReport, ColumnMapping, FeatureReport, ScalingReport } from "@/types";

type CleaningResult = {
  session_id: string;
  status: "processed" | "clustered";
  filename: string | null;
  mapping: ColumnMapping;
  cleaning_report: CleaningReport;
  feature_report: FeatureReport;
  scaling_report: ScalingReport;
};

export function ProcessingReport() {
  const [result, setResult] = useState<CleaningResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sessionId = rememberedSession();
    if (!sessionId) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function load(sessionId: string) {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/dataset/cleaning?session_id=${sessionId}`,
        );
        const payload = (await response.json()) as CleaningResult & { message?: string };
        if (cancelled) return;
        if (!response.ok) {
          setError(payload.message ?? "อ่านรายงานไม่สำเร็จ");
          return;
        }
        setResult(payload);
      } catch {
        if (!cancelled) {
          setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load(sessionId);
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="mt-6 space-y-3" aria-busy="true">
        <p className="text-sm text-muted">กำลังอ่านรายงาน...</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, index) => (
            <div key={index} className="skeleton h-16" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-6">
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          "อัปโหลด",
          "ตรวจสอบ",
          "ทำความสะอาด",
          "สร้างฟีเจอร์",
          "ปรับสเกล",
          "K-Means",
          "วิเคราะห์กลุ่ม",
        ].map((label, index) => {
          const done = result ? (result.status === "clustered" ? true : index < 5) : false;
          return (
            <li key={label} className="card px-4 py-3 text-sm">
              <span className="flex items-center gap-2 text-ink">
                <span className={`h-2 w-2 rounded-full ${done ? "bg-pea" : "bg-sage"}`} aria-hidden />
                {label}
              </span>
              <span className="mt-1 block text-xs text-muted">{done ? "เสร็จแล้ว" : "รอดำเนินการ"}</span>
            </li>
          );
        })}
      </ol>
      <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-muted">
        <li>ตัดแถวที่ไม่มีราคา ส่วนลด หรือจำนวนขาย และไม่เติมส่วนลดที่ว่างเป็น 0%</li>
        <li>ถ้าช่องส่วนลดว่าง แต่มีราคาเต็ม จะคำนวณส่วนลดจากราคาเต็ม ราคาเต็มที่เป็น 0 จะไม่ถูกนำมาหาร</li>
        <li>ตัดค่าที่ไม่ใช่ตัวเลข ราคาติดลบ จำนวนขายติดลบ และส่วนลดที่อยู่นอก 0–100</li>
        <li>ตัดแถวที่ชื่อ หมวด ราคา ส่วนลด และจำนวนขายซ้ำกัน โดยเก็บแถวแรก</li>
        <li>สินค้าที่ขายสูงยังอยู่ในตาราง เพราะเป็นสัญญาณทางธุรกิจ</li>
        <li>คำนวณ sales_value จากราคาคูณจำนวนขาย เป็นฟีเจอร์ที่สี่ของทุกแถวที่เหลือ</li>
        <li>ปรับฟีเจอร์ทั้งสี่ด้วย StandardScaler จากค่าเฉลี่ยและส่วนเบี่ยงเบนมาตรฐานของชุดนี้</li>
      </ul>

      {error ? (
        <p className="alert-warn">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            ไฟล์ {result.filename ?? result.session_id} · สถานะ{" "}
            {result.status === "clustered" ? "จัดกลุ่มแล้ว" : "ประมวลผลแล้ว"}
          </p>
          <CleaningSummary
            report={result.cleaning_report}
            mapping={result.mapping}
            featureReport={result.feature_report}
            scalingReport={result.scaling_report}
          />
          <div className="flex flex-wrap gap-4">
            <Link href="/analysis" className="text-sm font-medium underline">
              ไปดู Elbow และ Silhouette
            </Link>
            <Link href="/clusters" className="text-sm font-medium underline">
              ไปจัดกลุ่มที่หน้า Cluster Analysis
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
