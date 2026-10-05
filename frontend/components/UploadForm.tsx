"use client";

import { useState, type FormEvent } from "react";

import { CleaningSummary } from "@/components/CleaningSummary";
import { API_BASE_URL } from "@/lib/api";
import { FIELD_LABELS, missingRequired, rememberSession } from "@/lib/dataset";
import type { CleaningReport, ColumnMapping, FeatureReport, ScalingReport } from "@/types";

type UploadResult = {
  session_id: string;
  filename: string;
  columns: string[];
  row_count: number;
  preview: Record<string, string>[];
  suggested_mapping: ColumnMapping;
  missing_required: string[];
};

type CleaningResult = {
  session_id: string;
  status: "processed" | "clustered";
  filename: string | null;
  mapping: ColumnMapping;
  cleaning_report: CleaningReport;
  feature_report: FeatureReport;
  scaling_report: ScalingReport;
};

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping | null>(null);
  const [cleaning, setCleaning] = useState<CleaningResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("เลือกไฟล์ CSV ก่อนอัปโหลด");
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);
    setMapping(null);
    setCleaning(null);
    const body = new FormData();
    body.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/dataset/upload`, {
        method: "POST",
        body,
      });
      const payload = (await response.json()) as UploadResult & { message?: string };
      if (!response.ok) {
        setError(payload.message ?? "อัปโหลดไม่สำเร็จ");
        return;
      }
      setResult(payload);
      setMapping(payload.suggested_mapping);
      rememberSession(payload.session_id);
    } catch {
      setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setUploading(false);
    }
  }

  async function onProcess() {
    if (!result || !mapping) return;
    setProcessing(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/dataset/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: result.session_id, mapping }),
      });
      const payload = (await response.json()) as CleaningResult & { message?: string };
      if (!response.ok) {
        setError(payload.message ?? "ทำความสะอาดข้อมูลไม่สำเร็จ");
        return;
      }
      setCleaning(payload);
      rememberSession(payload.session_id);
    } catch {
      setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setProcessing(false);
    }
  }

  const unresolved = mapping ? missingRequired(mapping) : [];

  return (
    <div className="mt-6 space-y-6">
      <form
        onSubmit={onSubmit}
        className="card border-dashed border-sage p-8 text-center"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          setFile(event.dataTransfer.files?.[0] ?? null);
          setError(null);
        }}
      >
        <label htmlFor="dataset" className="block cursor-pointer">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-foam text-pea-deep">
            <svg width="22" height="22" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path d="M8 11V3M5 6l3-3 3 3" stroke="currentColor" strokeWidth="1.4" />
              <path d="M3 13h10" stroke="currentColor" strokeWidth="1.4" />
            </svg>
          </span>
          <span className="mt-4 block text-base font-semibold text-ink">อัปโหลดชุดข้อมูลสินค้า</span>
          <span className="mt-1 block text-sm text-muted">ลากไฟล์ CSV มาวาง หรือเลือกจากเครื่อง</span>
          <input
            id="dataset"
            name="dataset"
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setError(null);
            }}
          />
        </label>
        {file ? <p className="mt-3 text-sm text-moss">{file.name}</p> : null}
        <button type="submit" disabled={uploading} className="mt-4 btn-primary">
          {uploading ? "กำลังอัปโหลด..." : "อัปโหลด"}
        </button>
      </form>

      {error ? (
        <p className="alert-danger">
          {error}
        </p>
      ) : null}

      {result && mapping ? (
        <UploadResultView
          result={result}
          mapping={mapping}
          unresolved={unresolved}
          processing={processing}
          cleaning={cleaning}
          onMappingChange={(key, value) => {
            setMapping({ ...mapping, [key]: value || null });
            setCleaning(null);
          }}
          onProcess={onProcess}
          fileSize={file?.size ?? null}
        />
      ) : null}
    </div>
  );
}

function UploadResultView({
  result,
  mapping,
  unresolved,
  processing,
  cleaning,
  onMappingChange,
  onProcess,
  fileSize,
}: {
  result: UploadResult;
  mapping: ColumnMapping;
  unresolved: string[];
  processing: boolean;
  cleaning: CleaningResult | null;
  onMappingChange: (key: keyof ColumnMapping, value: string) => void;
  onProcess: () => void;
  fileSize: number | null;
}) {
  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="แถวข้อมูล" value={result.row_count.toLocaleString("th-TH")} />
        <Metric label="คอลัมน์" value={String(result.columns.length)} />
        <Metric label="ไฟล์" value={result.filename} />
        {fileSize !== null ? (
          <Metric label="ขนาดไฟล์" value={`${(fileSize / 1024).toLocaleString("th-TH", { maximumFractionDigits: 1 })} KB`} />
        ) : null}
      </div>

      <div className="card">
        <h2 className="border-b border-line px-4 py-3 text-sm font-semibold">
          ยืนยันคอลัมน์ก่อนทำความสะอาด
        </h2>
        <div className="grid gap-4 p-4 sm:grid-cols-2">
          {FIELD_LABELS.map(([key, label]) => (
            <label key={key} className="block text-sm">
              <span className="text-xs text-muted">{label}</span>
              <select
                id={`mapping-${key}`}
                className="field mt-1"
                value={mapping[key] ?? ""}
                onChange={(event) => onMappingChange(key, event.target.value)}
              >
                <option value="">ไม่ได้ใช้</option>
                {result.columns.map((column, index) => (
                  <option key={`${column}-${index}`} value={column}>
                    {column || "(ว่าง)"}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
        <div className="border-t border-line px-4 py-3">
          {unresolved.length > 0 ? (
            <p className="text-sm text-earth">
              ยังจับคู่คอลัมน์ไม่ครบ: {unresolved.join(", ")}
            </p>
          ) : (
            <p className="text-sm text-moss">จับคู่คอลัมน์ที่จำเป็นได้ครบ</p>
          )}
          <button
            id="clean-dataset"
            type="button"
            disabled={processing || unresolved.length > 0}
            onClick={onProcess}
            className="mt-3 btn-primary"
          >
            {processing ? "กำลังทำความสะอาด..." : "ทำความสะอาดข้อมูล"}
          </button>
        </div>
      </div>

      {cleaning ? (
        <div className="card p-4">
          <h2 className="text-sm font-semibold">ผลการทำความสะอาด</h2>
          <div className="mt-4">
            <CleaningSummary
              report={cleaning.cleaning_report}
              featureReport={cleaning.feature_report}
              scalingReport={cleaning.scaling_report}
            />
          </div>
        </div>
      ) : null}

      <div className="overflow-x-auto card">
        <h2 className="border-b border-line px-4 py-3 text-sm font-semibold">
          ตัวอย่าง 20 แถวแรก
        </h2>
        <table className="min-w-full text-left text-sm">
          <thead className="bg-foam text-xs text-muted">
            <tr>
              {result.columns.map((column, index) => (
                <th key={`${column}-${index}`} className="px-3 py-2 font-medium">
                  {column || "(ว่าง)"}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.preview.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-t border-line">
                {result.columns.map((column, columnIndex) => (
                  <td
                    key={`${rowIndex}-${columnIndex}`}
                    className="max-w-64 truncate px-3 py-2"
                    title={row[column] ?? ""}
                  >
                    {row[column] ?? ""}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="card px-4 py-3">
      <p className="text-xs text-muted">{label}</p>
      <p className="mt-1 truncate text-lg font-semibold" title={value}>
        {value}
      </p>
    </div>
  );
}
