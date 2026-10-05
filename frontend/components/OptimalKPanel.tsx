"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { API_BASE_URL } from "@/lib/api";
import { chartAxis, chartGrid, chartLine, tooltipSurface, tooltipText } from "@/lib/theme";
import { rememberedSession } from "@/lib/dataset";

type ScorePoint = {
  k: number;
  inertia: number;
  silhouette: number;
};

type OptimalKResult = {
  session_id: string;
  sample_count: number;
  silhouette_sample_size: number;
  silhouette_sampled: boolean;
  recommended_k: number;
  elbow_k: number;
  scores: ScorePoint[];
};

export function OptimalKPanel() {
  const [result, setResult] = useState<OptimalKResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onCompute() {
    const sessionId = rememberedSession();
    if (!sessionId) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/clustering/optimal-k?session_id=${sessionId}`,
      );
      const payload = (await response.json()) as OptimalKResult & { message?: string };
      if (!response.ok) {
        setError(payload.message ?? "คำนวณจำนวนกลุ่มไม่สำเร็จ");
        return;
      }
      setResult(payload);
    } catch {
      setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-6 space-y-6">
      <div className="card p-5">
        <p className="text-sm leading-6 text-muted">
          Elbow ใช้ inertia ของทุกแถว Silhouette ใช้ตัวอย่างสุ่ม 5,000 แถวเมื่อข้อมูลมากกว่านั้น
          ค่าที่ระบบเสนอคือ Silhouette สูงสุด และเลือกจำนวนกลุ่มอื่นได้ที่หน้า Cluster Analysis
        </p>
        <button
          id="compute-optimal-k"
          type="button"
          disabled={loading}
          onClick={onCompute}
          className="mt-4 btn-primary"
        >
          {loading ? "กำลังคำนวณ..." : "คำนวณ Elbow และ Silhouette"}
        </button>
      </div>

      {error ? (
        <p className="alert-danger">
          {error}
        </p>
      ) : null}

      {result ? <OptimalKResultView result={result} /> : null}
    </div>
  );
}

function OptimalKResultView({ result }: { result: OptimalKResult }) {
  const sameChoice = result.recommended_k === result.elbow_k;
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="card px-4 py-3">
          <p className="text-xs text-muted">Silhouette สูงสุด</p>
          <p className="mt-1 text-lg font-semibold">K = {result.recommended_k}</p>
        </div>
        <div className="card px-4 py-3">
          <p className="text-xs text-muted">Elbow</p>
          <p className="mt-1 text-lg font-semibold">K = {result.elbow_k}</p>
        </div>
      </div>
      <p
        className={`rounded-md border px-4 py-3 text-sm ${
          sameChoice
            ? "border-success/30 bg-success/10 text-moss"
            : "border-warning/40 bg-warning/15 text-earth"
        }`}
      >
        {sameChoice
          ? "Elbow และ Silhouette ชี้ที่จำนวนกลุ่มเดียวกัน ค่านี้เป็นข้อเสนอ ผู้ใช้ยังเลือกจำนวนกลุ่มเองได้"
          : "Elbow และ Silhouette ชี้คนละจำนวนกลุ่ม กราฟทั้งสองแสดงไว้ให้เทียบ ค่าที่ระบบเสนอคือ Silhouette สูงสุด"}
      </p>
      <p className="text-sm text-muted">
        {result.silhouette_sampled
          ? `Silhouette คำนวณจากตัวอย่างสุ่ม ${result.silhouette_sample_size.toLocaleString("th-TH")} แถว จากทั้งหมด ${result.sample_count.toLocaleString("th-TH")} แถว`
          : `Silhouette คำนวณจากทุกแถว ${result.sample_count.toLocaleString("th-TH")} แถว`}
        {" "}Elbow ใช้ inertia ของทุกแถว
      </p>
      <div className="grid gap-4 lg:grid-cols-2">
        <ScoreChart title="Elbow (inertia)" data={result.scores} dataKey="inertia" />
        <ScoreChart title="Silhouette" data={result.scores} dataKey="silhouette" />
      </div>
      <div className="overflow-x-auto card">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-foam text-xs text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">K</th>
              <th className="px-3 py-2 font-medium">Inertia</th>
              <th className="px-3 py-2 font-medium">Silhouette</th>
            </tr>
          </thead>
          <tbody>
            {result.scores.map((point) => (
              <tr key={point.k} className="border-t border-line">
                <td className="px-3 py-2">
                  {point.k}
                  {point.k === result.recommended_k ? (
                    <span className="ml-2 text-xs text-moss">Silhouette สูงสุด</span>
                  ) : null}
                  {point.k === result.elbow_k ? (
                    <span className="ml-2 text-xs text-earth">Elbow</span>
                  ) : null}
                </td>
                <td className="px-3 py-2">{formatScore(point.inertia)}</td>
                <td className="px-3 py-2">{formatScore(point.silhouette)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScoreChart({
  title,
  data,
  dataKey,
}: {
  title: string;
  data: ScorePoint[];
  dataKey: "inertia" | "silhouette";
}) {
  return (
    <div className="card p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="mt-3 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid stroke={chartGrid} />
            <XAxis dataKey="k" allowDecimals={false} tick={{ fill: chartAxis }} />
            <YAxis tick={{ fill: chartAxis }} />
            <Tooltip
              contentStyle={{
                background: tooltipSurface,
                border: "none",
                borderRadius: 12,
                color: tooltipText,
              }}
            />
            <Line type="monotone" dataKey={dataKey} stroke={chartLine} strokeWidth={2} dot={{ fill: chartLine }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function formatScore(value: number) {
  return value.toLocaleString("th-TH", { maximumFractionDigits: 4 });
}
