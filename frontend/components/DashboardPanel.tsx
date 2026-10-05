"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DashboardView } from "@/components/DashboardView";
import { API_BASE_URL } from "@/lib/api";
import { rememberedSession } from "@/lib/dataset";
import type { DashboardSummary } from "@/types";

type Hint = "upload" | "cluster" | null;

export function DashboardPanel() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<Hint>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sessionId = rememberedSession();
    if (!sessionId) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      setHint("upload");
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function load(storedSessionId: string) {
      try {
        const [response, sessionResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/dashboard/summary?session_id=${storedSessionId}`),
          fetch(`${API_BASE_URL}/api/sessions/${storedSessionId}`),
        ]);
        const payload = (await response.json()) as DashboardSummary & { message?: string };
        const sessionPayload = (await sessionResponse.json()) as { original_filename?: string | null };
        if (cancelled) return;
        if (sessionResponse.ok) setFilename(sessionPayload.original_filename ?? null);
        if (response.status === 409) {
          setError(payload.message ?? "ยังไม่ได้จัดกลุ่ม");
          setHint("cluster");
          return;
        }
        if (!response.ok) {
          setError(payload.message ?? "อ่านสรุปไม่สำเร็จ");
          return;
        }
        setSummary(payload);
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
      <div className="mt-6 space-y-4" aria-busy="true">
        <p className="text-sm text-muted">กำลังโหลดสรุป...</p>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="skeleton h-24" />
          ))}
        </div>
        <div className="skeleton h-72" />
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      {error ? (
        <div className="alert-danger">
          <p>{error}</p>
          {hint === "upload" ? (
            <Link href="/upload" className="mt-2 inline-block font-medium underline">
              ไปอัปโหลดชุดข้อมูล
            </Link>
          ) : null}
          {hint === "cluster" ? (
            <Link href="/clusters" className="mt-2 inline-block font-medium underline">
              ไปจัดกลุ่มที่หน้า Cluster Analysis
            </Link>
          ) : null}
        </div>
      ) : null}
      {summary ? (
        <>
          <DashboardView summary={summary} filename={filename} />
          <div className="flex flex-wrap gap-4">
            <Link href="/clusters" className="text-sm font-medium underline">
              ดูคำแนะนำของแต่ละกลุ่ม
            </Link>
            <Link href="/products" className="text-sm font-medium underline">
              เปิดรายการสินค้า
            </Link>
            <Link href="/analysis" className="text-sm font-medium underline">
              ดู Elbow และ Silhouette
            </Link>
          </div>
        </>
      ) : null}
    </div>
  );
}
