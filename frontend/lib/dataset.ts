import type { ColumnMapping } from "@/types";

export const SESSION_STORAGE_KEY = "ecommerce-session-id";

export const FIELD_LABELS: Array<[keyof ColumnMapping, string]> = [
  ["price_usd", "ราคา (price_usd)"],
  ["pct_discount", "ส่วนลด (pct_discount)"],
  ["retail_price", "ราคาเต็ม (retail_price)"],
  ["qty_sold", "จำนวนขาย (qty_sold)"],
  ["product_name", "ชื่อสินค้า"],
  ["category", "หมวดหมู่"],
];

export function missingRequired(mapping: ColumnMapping): string[] {
  const missing: string[] = [];
  if (!mapping.price_usd) missing.push("price_usd");
  if (!mapping.qty_sold) missing.push("qty_sold");
  if (!mapping.pct_discount && !mapping.retail_price) missing.push("pct_discount");
  return missing;
}

export function rememberSession(sessionId: string) {
  sessionStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

export function rememberedSession() {
  return sessionStorage.getItem(SESSION_STORAGE_KEY);
}
