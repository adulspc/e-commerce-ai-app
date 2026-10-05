export type SessionState = "uploaded" | "processed" | "clustered";

export type ColumnMapping = {
  price_usd: string | null;
  pct_discount: string | null;
  retail_price: string | null;
  qty_sold: string | null;
  product_name: string | null;
  category: string | null;
};

export type FeatureScale = {
  feature: string;
  mean: number;
  std: number;
  constant: boolean;
};

export type ScalingReport = {
  sample_count: number;
  features: FeatureScale[];
};

export type FeatureReport = {
  row_count: number;
  min_sales_value: number;
  median_sales_value: number;
  mean_sales_value: number;
  max_sales_value: number;
};

export type CleaningReport = {
  rows_before: number;
  rows_after: number;
  missing_values_handled: number;
  duplicate_rows_removed: number;
  invalid_rows_removed: number;
  missing_price: number;
  missing_quantity: number;
  missing_discount: number;
};

export type ClusterFit = {
  cluster_id: number;
  product_count: number;
  centroid_price_usd: number;
  centroid_pct_discount: number;
  centroid_qty_sold: number;
  centroid_sales_value: number;
  cluster_name: string;
  characteristics: string;
  recommendations: string[];
};

export type ClusteringResult = {
  session_id: string;
  status: "clustered";
  k: number;
  inertia: number;
  clusters: ClusterFit[];
};

export type ClusterSummary = {
  cluster_id: number;
  cluster_name: string;
  product_count: number;
  avg_price: number;
  avg_discount: number;
  avg_qty_sold: number;
  avg_sales_value: number;
  characteristics: string;
  recommendations: string[];
};

export type ProductRow = {
  id: string;
  product_name: string;
  category: string;
  price_usd: number;
  pct_discount: number;
  qty_sold: number;
  sales_value: number;
  cluster: number;
  cluster_name: string;
};

export type ProductDetail = ProductRow & {
  explanation: string;
};

export type ProductPage = {
  session_id: string;
  page: number;
  page_size: number;
  total: number;
  categories: string[];
  products: ProductRow[];
};

export type ClusterList = {
  session_id: string;
  k: number;
  clusters: ClusterSummary[];
};

export type ClusterDetail = ClusterSummary & {
  session_id: string;
};

export type ScatterPoint = {
  price_usd: number;
  pct_discount: number;
  qty_sold: number;
  sales_value: number;
  cluster: number;
};

export type DashboardSummary = {
  session_id: string;
  k: number;
  total_products: number;
  average_price: number;
  average_discount: number;
  total_quantity_sold: number;
  total_sales_value: number;
  number_of_clusters: number;
  clusters: ClusterSummary[];
  scatter: ScatterPoint[];
  scatter_sample_size: number;
  scatter_sampled: boolean;
};
