import React, { useEffect, useState } from 'react';
import { 
  DollarSign, 
  ShoppingBag, 
  Package, 
  Store as StoreIcon, 
  AlertOctagon, 
  Layers, 
  TrendingUp, 
  ShieldCheck, 
  ArrowUpRight 
} from 'lucide-react';
import { 
  fetchSalesSummary, 
  fetchSalesTrend, 
  fetchInventoryHealth, 
  fetchInventoryAttention, 
  fetchTopProducts, 
  fetchStoresList 
} from '../api/client';
import { 
  SalesSummary, 
  SalesTrendPoint, 
  InventoryHealthSummary, 
  AttentionItem, 
  TopProductItem, 
  StoreMeta 
} from '../api/types';
import { KpiCard } from '../components/KpiCard';
import { SalesTrendChart } from '../components/SalesTrendChart';
import { InventoryAlertFeed } from '../components/InventoryAlertFeed';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

export const DashboardPage: React.FC = () => {
  const [salesSummary, setSalesSummary] = useState<SalesSummary | null>(null);
  const [salesTrend, setSalesTrend] = useState<SalesTrendPoint[]>([]);
  const [inventoryHealth, setInventoryHealth] = useState<InventoryHealthSummary | null>(null);
  const [attentionItems, setAttentionItems] = useState<AttentionItem[]>([]);
  const [topProducts, setTopProducts] = useState<TopProductItem[]>([]);
  const [stores, setStores] = useState<StoreMeta[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryRes, trendRes, healthRes, attentionRes, topProdRes, storesRes] = await Promise.all([
        fetchSalesSummary(),
        fetchSalesTrend(),
        fetchInventoryHealth(),
        fetchInventoryAttention({ limit: 10 }),
        fetchTopProducts({ limit: 5, by: 'revenue' }),
        fetchStoresList(),
      ]);

      setSalesSummary(summaryRes);
      setSalesTrend(trendRes.trend || []);
      setInventoryHealth(healthRes);
      setAttentionItems(attentionRes);
      setTopProducts(topProdRes.top_products || []);
      setStores(storesRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load live dashboard analytics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const totalAtRisk = inventoryHealth?.risk_distribution
    ? (inventoryHealth.risk_distribution.critical ?? 0) + (inventoryHealth.risk_distribution.high ?? 0)
    : 0;

  return (
    <div className="page-container">
      {/* Page Title */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Retail Intelligence Overview</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Understand sales performance, inventory risk, and recommended actions from one evidence-first workspace.
        </p>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadDashboardData} />}

      {/* 6 KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          label="Total Revenue"
          value={salesSummary?.total_revenue ?? 0}
          description="Gross transactions across retail network"
          icon={DollarSign}
          variant="blue"
          isCurrency
        />
        <KpiCard
          label="Total Units Sold"
          value={salesSummary?.total_units_sold ?? 0}
          description={`Across ${salesSummary?.total_transactions ?? 0} recorded checkouts`}
          icon={ShoppingBag}
          variant="emerald"
        />
        <KpiCard
          label="Catalog Products"
          value={inventoryHealth?.total_products_tracked ?? 40}
          description="Active tracked retail SKUs"
          icon={Package}
          variant="purple"
        />
        <KpiCard
          label="Store Locations"
          value={stores.length || 4}
          description="Active metropolitan hubs"
          icon={StoreIcon}
          variant="default"
        />
        <KpiCard
          label="Stock-Out Risks"
          value={totalAtRisk}
          description={`${inventoryHealth?.risk_distribution?.critical ?? 0} Critical • ${inventoryHealth?.risk_distribution?.high ?? 0} High priority`}
          icon={AlertOctagon}
          variant="rose"
        />
        <KpiCard
          label="Overstock Records"
          value={inventoryHealth?.overstocked_records ?? 0}
          description={`₹${((inventoryHealth?.overstocked_excess_value_inr ?? 0) / 100000).toFixed(1)}L locked in excess capital`}
          icon={Layers}
          variant="amber"
        />
      </div>

      {/* Main Grid: Trend Chart & Attention Alerts */}
      <div className="two-col-grid">
        <SalesTrendChart data={salesTrend} isLoading={isLoading} />
        <InventoryAlertFeed items={attentionItems} isLoading={isLoading} />
      </div>

      {/* Bottom Grid: Top Products Table & Inventory Health Distribution */}
      <div className="equal-two-col">
        {/* Top Products */}
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header">
            <div className="iq-card-title">
              <TrendingUp size={18} color="var(--accent-emerald)" />
              <span>Top Performing Products</span>
            </div>
            <span className="badge badge-medium">Ranked by Revenue</span>
          </div>

          {isLoading ? (
            <LoadingSkeleton rows={5} height="48px" />
          ) : (
            <div className="table-container">
              <table className="iq-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Category</th>
                    <th>Units</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {topProducts.map((p, i) => (
                    <tr key={p.product_id}>
                      <td style={{ fontWeight: 600 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            #{i + 1}
                          </span>
                          <span>{p.product_name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="badge" style={{ background: 'rgba(30,41,59,0.5)', color: 'var(--text-secondary)' }}>
                          {p.category}
                        </span>
                      </td>
                      <td className="mono" style={{ fontWeight: 500 }}>
                        {p.units_sold.toLocaleString()}
                      </td>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>
                        ₹{p.revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Inventory Health Portfolio Breakdown */}
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header">
            <div className="iq-card-title">
              <ShieldCheck size={18} color="var(--accent-blue)" />
              <span>Inventory Health Breakdown</span>
            </div>
            <span className="badge badge-complete">
              {inventoryHealth?.percentages.healthy_pct ?? 0}% Healthy
            </span>
          </div>

          {isLoading || !inventoryHealth ? (
            <LoadingSkeleton rows={4} height="52px" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {/* Progress Bar */}
              <div>
                <div style={{ display: 'flex', height: '12px', borderRadius: 'var(--radius-full)', overflow: 'hidden', gap: '2px', background: 'var(--border-color)' }}>
                  <div
                    style={{
                      width: `${inventoryHealth.percentages.healthy_pct}%`,
                      background: 'var(--accent-emerald)',
                    }}
                    title={`Healthy: ${inventoryHealth.percentages.healthy_pct}%`}
                  />
                  <div
                    style={{
                      width: `${inventoryHealth.percentages.medium_pct}%`,
                      background: 'var(--accent-blue)',
                    }}
                    title={`Medium Risk: ${inventoryHealth.percentages.medium_pct}%`}
                  />
                  <div
                    style={{
                      width: `${inventoryHealth.percentages.high_pct}%`,
                      background: 'var(--accent-amber)',
                    }}
                    title={`High Risk: ${inventoryHealth.percentages.high_pct}%`}
                  />
                  <div
                    style={{
                      width: `${inventoryHealth.percentages.critical_pct}%`,
                      background: 'var(--accent-rose)',
                    }}
                    title={`Critical Risk: ${inventoryHealth.percentages.critical_pct}%`}
                  />
                </div>

                {/* Legend */}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.725rem', color: 'var(--text-secondary)', marginTop: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-emerald)' }} />
                    Healthy: {inventoryHealth.risk_distribution.low}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-blue)' }} />
                    Medium: {inventoryHealth.risk_distribution.medium}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-amber)' }} />
                    High: {inventoryHealth.risk_distribution.high}
                  </span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-rose)' }} />
                    Critical: {inventoryHealth.risk_distribution.critical}
                  </span>
                </div>
              </div>

              {/* Stat Boxes */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.65)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '0.85rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                    Total Inventory Capital
                  </div>
                  <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                    ₹{(inventoryHealth.total_stock_value_inr ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                    {(inventoryHealth.total_stock_units ?? 0).toLocaleString('en-IN')} on-hand units
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.65)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '0.85rem' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                    Excess Locked Capital
                  </div>
                  <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-amber)', marginTop: '0.2rem' }}>
                    ₹{(inventoryHealth.overstocked_excess_value_inr ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                    {(inventoryHealth.overstocked_excess_units ?? 0).toLocaleString('en-IN')} units over target threshold
                  </div>
                </div>
              </div>

              <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                Analysis window: last {inventoryHealth.analysis_period?.history_window_days ?? inventoryHealth.analysis_period?.days ?? 30} days of demand history ({inventoryHealth.analysis_period?.sales_min_date ?? inventoryHealth.analysis_period?.start_date} to {inventoryHealth.analysis_period?.sales_max_date ?? inventoryHealth.analysis_period?.end_date}).
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
