/**
 * RetailIQ API Client.
 * Communicates exclusively with the Python FastAPI backend.
 * Zero client-side computation of business metrics.
 */

import {
  SalesSummary,
  SalesTrendResponse,
  TopProductsResponse,
  CategoryResponse,
  ProductPerformance,
  StorePerformance,
  StoreProductComparison,
  InventoryHealthSummary,
  ProductRisk,
  OverstockItem,
  AttentionItem,
  CopilotResponse,
  ProductMeta,
  StoreMeta,
} from './types';

const API_BASE = '/api';

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const message = errorBody.detail || `Request failed with status ${res.status}`;
      throw new Error(message);
    }

    return await res.json();
  } catch (err: any) {
    console.error(`API Error on [${endpoint}]:`, err.message);
    throw err;
  }
}

// -----------------------------------------------------------------------------
// Catalog
// -----------------------------------------------------------------------------

export async function fetchProductsList(category?: string): Promise<ProductMeta[]> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return request<ProductMeta[]>(`/catalog/products${query}`);
}

export async function fetchStoresList(): Promise<StoreMeta[]> {
  return request<StoreMeta[]>('/catalog/stores');
}

// -----------------------------------------------------------------------------
// Sales Intelligence
// -----------------------------------------------------------------------------

export async function fetchSalesSummary(params?: {
  store_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<SalesSummary> {
  const query = new URLSearchParams();
  if (params?.store_id) query.append('store_id', params.store_id);
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<SalesSummary>(`/analytics/summary${qStr}`);
}

export async function fetchSalesTrend(params?: {
  store_id?: string;
  product_id?: string;
  start_date?: string;
  end_date?: string;
}): Promise<SalesTrendResponse> {
  const query = new URLSearchParams();
  if (params?.store_id) query.append('store_id', params.store_id);
  if (params?.product_id) query.append('product_id', params.product_id);
  if (params?.start_date) query.append('start_date', params.start_date);
  if (params?.end_date) query.append('end_date', params.end_date);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<SalesTrendResponse>(`/analytics/trend${qStr}`);
}

export async function fetchTopProducts(params?: {
  by?: 'revenue' | 'units';
  limit?: number;
  store_id?: string;
}): Promise<TopProductsResponse> {
  const query = new URLSearchParams();
  if (params?.by) query.append('by', params.by);
  if (params?.limit) query.append('limit', String(params.limit));
  if (params?.store_id) query.append('store_id', params.store_id);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<TopProductsResponse>(`/analytics/top-products${qStr}`);
}

export async function fetchCategoryPerformance(): Promise<CategoryResponse> {
  return request<CategoryResponse>('/analytics/categories');
}

export async function fetchProductPerformance(productId: string): Promise<ProductPerformance> {
  return request<ProductPerformance>(`/analytics/products/${encodeURIComponent(productId)}`);
}

export async function fetchStorePerformance(storeId: string): Promise<StorePerformance> {
  return request<StorePerformance>(`/analytics/stores/${encodeURIComponent(storeId)}`);
}

export async function fetchStoreProductComparison(productId: string): Promise<StoreProductComparison> {
  return request<StoreProductComparison>(`/analytics/products/${encodeURIComponent(productId)}/stores`);
}

// -----------------------------------------------------------------------------
// Inventory Intelligence
// -----------------------------------------------------------------------------

export async function fetchInventoryHealth(storeId?: string): Promise<InventoryHealthSummary> {
  const query = storeId ? `?store_id=${encodeURIComponent(storeId)}` : '';
  return request<InventoryHealthSummary>(`/inventory/health${query}`);
}

export async function fetchInventoryRisks(params?: {
  store_id?: string;
  min_severity?: string;
  risk_level?: string;
  category?: string;
}): Promise<ProductRisk[]> {
  const query = new URLSearchParams();
  if (params?.store_id) query.append('store_id', params.store_id);
  if (params?.min_severity) query.append('min_severity', params.min_severity);
  if (params?.risk_level) query.append('risk_level', params.risk_level);
  if (params?.category) query.append('category', params.category);
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<ProductRisk[]>(`/inventory/risks${qStr}`);
}

export async function fetchInventoryOverstock(params?: {
  store_id?: string;
  category?: string;
  threshold_days?: number;
}): Promise<OverstockItem[]> {
  const query = new URLSearchParams();
  if (params?.store_id) query.append('store_id', params.store_id);
  if (params?.category) query.append('category', params.category);
  if (params?.threshold_days) query.append('threshold_days', String(params.threshold_days));
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<OverstockItem[]>(`/inventory/overstock${qStr}`);
}

export async function fetchInventoryAttention(params?: {
  store_id?: string;
  limit?: number;
}): Promise<AttentionItem[]> {
  const query = new URLSearchParams();
  if (params?.store_id) query.append('store_id', params.store_id);
  if (params?.limit) query.append('limit', String(params.limit));
  const qStr = query.toString() ? `?${query.toString()}` : '';
  return request<AttentionItem[]>(`/inventory/attention${qStr}`);
}

// -----------------------------------------------------------------------------
// Retail Copilot
// -----------------------------------------------------------------------------

export async function askCopilot(question: string): Promise<CopilotResponse> {
  return request<CopilotResponse>('/copilot', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}
