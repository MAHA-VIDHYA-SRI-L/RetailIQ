/**
 * TypeScript definitions for RetailIQ API responses and models.
 * All numerical and intelligence metrics correspond 1:1 with Python SQLite analytics.
 */

export interface SalesPeriod {
  start_date: string;
  end_date: string;
  expected_calendar_days?: number;
  is_partial?: boolean;
}

export interface SalesSummary {
  has_data: boolean;
  total_revenue: number;
  total_units_sold: number;
  total_transactions: number;
  average_daily_revenue: number;
  average_daily_units_sold: number;
  average_order_value: number;
  active_selling_days: number;
  period: SalesPeriod;
  store_id?: string | null;
}

export interface ProductPerformance {
  has_data: boolean;
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  total_revenue: number;
  total_units_sold: number;
  average_daily_sales: number;
  selling_days: number;
  period: SalesPeriod;
}

export interface StorePerformance {
  has_data: boolean;
  store_id: string;
  store_name: string;
  city: string;
  total_revenue: number;
  total_units_sold: number;
  total_transactions: number;
  average_daily_revenue: number;
  selling_days: number;
  period: SalesPeriod;
}

export interface StoreRankingItem {
  store_id: string;
  store_name: string;
  city: string;
  revenue: number;
  units_sold: number;
  share_of_total_revenue?: number;
}

export interface StoreProductComparison {
  product_id: string;
  product_name: string;
  best_store_by_units: string;
  best_store_by_revenue: string;
  stores: StoreRankingItem[];
  period: SalesPeriod;
}

export interface TopProductItem {
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  units_sold: number;
  revenue: number;
}

export interface TopProductsResponse {
  top_products: TopProductItem[];
  metric: string;
  period: SalesPeriod;
}

export interface SalesTrendPoint {
  date: string;
  revenue: number;
  units: number;
  transactions: number;
}

export interface SalesTrendResponse {
  trend: SalesTrendPoint[];
  filters: {
    start_date?: string;
    end_date?: string;
    store_id?: string;
    product_id?: string;
  };
}

export interface CategoryItem {
  category: string;
  revenue: number;
  units_sold: number;
  revenue_percentage: number;
}

export interface CategoryResponse {
  categories: CategoryItem[];
  total_revenue: number;
  period: SalesPeriod;
}

export interface InventoryHealthRiskDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface InventoryHealthPercentages {
  critical_pct: number;
  high_pct: number;
  medium_pct: number;
  healthy_pct: number;
}

export interface InventoryHealthSummary {
  store_id: string | null;
  total_products_tracked: number;
  total_stock_units: number;
  total_stock_value_inr: number;
  risk_distribution: InventoryHealthRiskDistribution;
  percentages: InventoryHealthPercentages;
  overstocked_records: number;
  overstocked_excess_units: number;
  overstocked_excess_value_inr: number;
  analysis_period: {
    history_window_days: number;
    sales_min_date: string;
    sales_max_date: string;
  };
}

export interface ReorderRecommendation {
  recommended_reorder_quantity: number;
  replenishment_needed: boolean;
  target_coverage_days: number;
  target_stock_units: number;
}

export interface ProductRisk {
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  store_id: string;
  store_name: string;
  city: string;
  current_stock: number;
  average_daily_sales: number;
  days_of_coverage: number;
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  reorder_recommendation: ReorderRecommendation;
}

export interface OverstockItem {
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  store_id: string;
  store_name: string;
  city: string;
  current_stock: number;
  average_daily_sales: number;
  days_of_coverage: number;
  excess_inventory_units: number;
  excess_capital_inr: number;
  overstock_threshold_days: number;
}

export interface AttentionItem {
  type: 'STOCK_OUT' | 'SALES_SPIKE' | 'SALES_DROP' | 'OVERSTOCK';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  title: string;
  description: string;
  recommended_action: string;
  data: Record<string, any>;
}

export interface CopilotResponse {
  answer: string;
  intent: string;
  data_status: 'complete' | 'incomplete' | 'no_data' | 'ambiguous' | 'unavailable';
  needs_clarification: boolean;
  clarification_question: string | null;
  evidence: Array<Record<string, any>>;
  assumptions: string[];
  recommendations: string[];
  error?: string | null;
}

export interface ProductMeta {
  product_id: string;
  product_name: string;
  category: string;
  unit_price: number;
  reorder_level: number;
}

export interface StoreMeta {
  store_id: string;
  store_name: string;
  city: string;
}
