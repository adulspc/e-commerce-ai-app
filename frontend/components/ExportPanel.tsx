"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ExportView } from "@/components/ExportView";
import { API_BASE_URL } from "@/lib/api";
import { rememberedSession } from "@/lib/dataset";
import type { SessionState } from "@/types";

type Hint = "upload" | "cluster" | null;
type DownloadKind = "products" | "clusters";

type SessionPayload = {
  status: SessionState;
  original_filename: string | null;
  k: number | null;
  message?: string;
};

export function ExportPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<Hint>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<DownloadKind | null>(null);

  useEffect(() => {
    const stored = rememberedSession();
    if (!stored) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      setHint("upload");
      setLoading(false);
      return;
    }
    setSessionId(stored);
    let cancelled = false;

    async function load(storedSessionId: string) {
      try {
        const response = await fetch(`${API_BASE_URL}/api/sessions/${storedSessionId}`);
        const payload = (await response.json()) as SessionPayload;
        if (cancelled) return;
        if (!response.ok) {
          setError(payload.message ?? "อ่านชุดข้อมูลไม่สำเร็จ");
          return;
        }
        setSession(payload);
        if (payload.status === "uploaded") {
          setError("ยังไม่ได้ประมวลผลชุดข้อมูล");
          setHint("upload");
        } else if (payload.status === "processed") {
          setError("ยังไม่ได้จัดกลุ่ม");
          setHint("cluster");
        }
      } catch {
        if (!cancelled) setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load(stored);
    return () => {
      cancelled = true;
    };
  }, []);

  async function onDownload(kind: DownloadKind) {
    if (!sessionId || busy) return;
    setBusy(kind);
    setError(null);
    setHint(null);
    const path = kind === "products" ? "/api/export/products" : "/api/export/clusters";
    const filename = kind === "products" ? "products.csv" : "clusters.csv";
    try {
      const response = await fetch(`${API_BASE_URL}${path}?session_id=${sessionId}`);
      if (!response.ok) {
        const payload = (await response.json()) as { message?: string };
        setError(payload.message ?? "ดาวน์โหลดไม่สำเร็จ");
        if (response.status === 409) setHint("cluster");
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setBusy(null);
    }
  }

  if (loading) {
    return (
      <div className="mt-6 space-y-3" aria-busy="true">
        <p className="text-sm text-muted">กำลังตรวจสอบชุดข้อมูล...</p>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="skeleton h-40" />
          <div className="skeleton h-40" />
        </div>
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
              ไปอัปโหลดและประมวลผลชุดข้อมูล
            </Link>
          ) : null}
          {hint === "cluster" ? (
            <Link href="/clusters" className="mt-2 inline-block font-medium underline">
              ไปจัดกลุ่มที่หน้า Cluster Analysis
            </Link>
          ) : null}
        </div>
      ) : null}
      {session?.status === "clustered" ? (
        <ExportView
          filename={session.original_filename}
          k={session.k}
          busy={busy}
          onDownload={(kind) => void onDownload(kind)}
        />
      ) : null}
    </div>
  );
}
