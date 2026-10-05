"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ProductExplorerView } from "@/components/ProductExplorerView";
import { API_BASE_URL } from "@/lib/api";
import { rememberedSession } from "@/lib/dataset";
import type { ClusterList, ProductDetail, ProductPage } from "@/types";

type SortField = "" | "price_usd" | "qty_sold" | "sales_value";
type Hint = "upload" | "cluster" | null;

function clusterFromQuery(value: string | null) {
  if (value && /^\d+$/.test(value)) return value;
  return "";
}

export function ProductExplorer() {
  const requestedCluster = clusterFromQuery(useSearchParams().get("cluster"));
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<ProductPage | null>(null);
  const [clusters, setClusters] = useState<ClusterList["clusters"]>([]);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<Hint>(null);
  const [loading, setLoading] = useState(true);
  const [draftSearch, setDraftSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [category, setCategory] = useState("");
  const [cluster, setCluster] = useState(requestedCluster);
  const [sort, setSort] = useState<SortField>("");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ProductDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    setCluster(requestedCluster);
    setPage(1);
    setSelectedId(null);
    setDetail(null);
    setDetailError(null);
  }, [requestedCluster]);

  useEffect(() => {
    const stored = rememberedSession();
    if (!stored) {
      setError("ยังไม่มีชุดข้อมูล อัปโหลดไฟล์ CSV ก่อน");
      setHint("upload");
      setLoading(false);
      return;
    }
    setSessionId(stored);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    async function load(storedSessionId: string) {
      setLoading(true);
      setError(null);
      setHint(null);
      const params = new URLSearchParams({
        session_id: storedSessionId,
        page: String(page),
      });
      if (appliedSearch) params.set("search", appliedSearch);
      if (category) params.set("category", category);
      if (cluster) params.set("cluster", cluster);
      if (sort) {
        params.set("sort", sort);
        params.set("order", order);
      }
      try {
        const [productsResponse, clustersResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/api/products?${params}`),
          fetch(`${API_BASE_URL}/api/clusters?session_id=${storedSessionId}`),
        ]);
        const productsPayload = (await productsResponse.json()) as ProductPage & { message?: string };
        const clustersPayload = (await clustersResponse.json()) as ClusterList & { message?: string };
        if (cancelled) return;
        if (productsResponse.status === 409) {
          setResult(null);
          setError(productsPayload.message ?? "ยังไม่ได้จัดกลุ่ม");
          setHint("cluster");
          return;
        }
        if (!productsResponse.ok) {
          setError(productsPayload.message ?? "อ่านรายการสินค้าไม่สำเร็จ");
          return;
        }
        setResult(productsPayload);
        if (clustersResponse.ok) setClusters(clustersPayload.clusters);
      } catch {
        if (!cancelled) setError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load(sessionId);
    return () => {
      cancelled = true;
    };
  }, [sessionId, appliedSearch, category, cluster, sort, order, page]);

  function resetPage() {
    setPage(1);
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAppliedSearch(draftSearch.trim());
    resetPage();
  }

  async function onSelect(productId: string) {
    if (!sessionId) return;
    setSelectedId(productId);
    setDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/products/${productId}?session_id=${sessionId}`,
      );
      const payload = (await response.json()) as ProductDetail & { message?: string };
      if (!response.ok) {
        setDetailError(payload.message ?? "อ่านรายละเอียดสินค้าไม่สำเร็จ");
        return;
      }
      setDetail(payload);
    } catch {
      setDetailError("เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ ตรวจสอบว่า API ทำงานอยู่");
    } finally {
      setDetailLoading(false);
    }
  }

  if (!result && loading) {
    return (
      <div className="mt-6 space-y-3" aria-busy="true">
        <p className="text-sm text-muted">กำลังโหลดรายการ...</p>
        <div className="skeleton h-28" />
        <div className="skeleton h-64" />
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
      {result ? (
        <ProductExplorerView
          result={result}
          clusters={clusters}
          draftSearch={draftSearch}
          category={category}
          cluster={cluster}
          sort={sort}
          order={order}
          loading={loading}
          selectedId={selectedId}
          detail={detail}
          detailLoading={detailLoading}
          detailError={detailError}
          onDraftSearch={setDraftSearch}
          onSearch={onSearch}
          onCategory={(value) => {
            setCategory(value);
            resetPage();
          }}
          onCluster={(value) => {
            setCluster(value);
            resetPage();
          }}
          onSort={(value) => {
            setSort(value);
            resetPage();
          }}
          onOrder={(value) => {
            setOrder(value);
            resetPage();
          }}
          onPage={setPage}
          onSelect={(productId) => void onSelect(productId)}
          onCloseDetail={() => {
            setSelectedId(null);
            setDetail(null);
            setDetailError(null);
          }}
        />
      ) : null}
    </div>
  );
}
