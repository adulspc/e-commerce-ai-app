"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ClusterAnalysisView } from "@/components/ClusterAnalysisView";
import { API_BASE_URL } from "@/lib/api";
import { rememberedSession } from "@/lib/dataset";
import type { ClusteringResult } from "@/types";

export function ClusterRun() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [k, setK] = useState(4);
  const [result, setResult] = useState<ClusteringResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [recommendedK, setRecommendedK] = useState<number | null>(null);
  const [needsUpload, setNeedsUpload] = useState(false);

  useEffect(() => {
    const stored = rememberedSession();
    setSessionId(stored);
    if (!stored) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      setNeedsUpload(true);
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function load(storedSessionId: string) {
      try {
        const [response, sessionResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/clustering/result?session_id=${storedSessionId}`),
          fetch(`${API_BASE_URL}/api/sessions/${storedSessionId}`),
        ]);
        const payload = (await response.json()) as ClusteringResult & { message?: string };
        const sessionPayload = (await sessionResponse.json()) as { recommended_k?: number | null };
        if (cancelled) return;
        if (sessionResponse.ok && sessionPayload.recommended_k) {
          setRecommendedK(sessionPayload.recommended_k);
          setK(sessionPayload.recommended_k);
        }
        if (response.status === 409) return;
        if (!response.ok) {
          setError(payload.message ?? "อ่านผลการจัดกลุ่มไม่สำเร็จ");
          return;
        }
        setResult(payload);
        setK(payload.k);
      } catch {
        if (!cancelled) {
          setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load(stored);
    return () => {
      cancelled = true;
    };
  }, []);

  async function onRun() {
    if (!sessionId) return;
    setRunning(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/clustering/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, k }),
      });
      const payload = (await response.json()) as ClusteringResult & { message?: string };
      if (!response.ok) {
        setError(payload.message ?? "จัดกลุ่มไม่สำเร็จ");
        return;
      }
      setResult(payload);
    } catch {
      setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return (
      <div className="mt-6 space-y-3" aria-busy="true">
        <p className="text-sm text-muted">กำลังอ่านผลการจัดกลุ่ม...</p>
        <div className="skeleton h-28" />
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="skeleton h-48" />
          <div className="skeleton h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-6">
      <div className="card p-5">
        <label htmlFor="cluster-k" className="block text-sm font-medium">
          จำนวนกลุ่ม (K)
        </label>
        <p className="mt-1 text-sm text-muted">
          เลือกได้ 2 ถึง 10 หมายเลขกลุ่มใช้ระบุกลุ่มเท่านั้น
          {recommendedK
            ? ` Silhouette สูงสุดอยู่ที่ K = ${recommendedK} และเปลี่ยนค่านี้ได้`
            : ""}
        </p>
        <select
          id="cluster-k"
          className="field mt-3 max-w-xs"
          value={k}
          onChange={(event) => setK(Number(event.target.value))}
        >
          {Array.from({ length: 9 }, (_, index) => index + 2).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
        <button
          id="run-clustering"
          type="button"
          disabled={running || !sessionId}
          onClick={onRun}
          className="mt-4 btn-primary"
        >
          {running ? "กำลังจัดกลุ่ม..." : "จัดกลุ่ม"}
        </button>
      </div>

      {error ? (
        <div className="alert-danger">
          <p>{error}</p>
          {needsUpload ? (
            <Link href="/upload" className="mt-2 inline-block font-medium underline">
              ไปอัปโหลดชุดข้อมูล
            </Link>
          ) : null}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <p className="text-sm text-muted">
            จัดเป็น {result.k.toLocaleString("th-TH")} กลุ่ม · inertia{" "}
            {result.inertia.toLocaleString("th-TH", { maximumFractionDigits: 2 })}
          </p>
          <ClusterAnalysisView clusters={result.clusters} />
        </div>
      ) : null}
    </div>
  );
}
