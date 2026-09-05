import React, { useEffect, useState } from 'react';
import { 
  fetchInventoryHealth, 
  fetchInventoryRisks, 
  fetchInventoryOverstock 
} from '../api/client';
import { 
  InventoryHealthSummary, 
  ProductRisk, 
  OverstockItem 
} from '../api/types';
import { KpiCard } from '../components/KpiCard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorAlert } from '../components/ErrorAlert';
import { 
  Boxes, 
  AlertOctagon, 
  Layers, 
  ShieldAlert, 
  RotateCcw, 
  CheckCircle2, 
  ArrowDownCircle, 
  DollarSign 
} from 'lucide-react';

export const InventoryPage: React.FC = () => {
  const [health, setHealth] = useState<InventoryHealthSummary | null>(null);
  const [risks, setRisks] = useState<ProductRisk[]>([]);
  const [overstock, setOverstock] = useState<OverstockItem[]>([]);

  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [activeTab, setActiveTab] = useState<'risks' | 'overstock' | 'reorder'>('risks');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadInventoryData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [healthRes, risksRes, overstockRes] = await Promise.all([
        fetchInventoryHealth(),
        fetchInventoryRisks(),
        fetchInventoryOverstock(),
      ]);
      setHealth(healthRes);
      setRisks(risksRes);
      setOverstock(overstockRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load inventory intelligence.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInventoryData();
  }, []);

  const filteredRisks = risks.filter((r) => {
    if (filterSeverity === 'ALL') return true;
    return r.risk_level === filterSeverity;
  });

  const reorderCandidates = risks.filter(
    (r) => r.reorder_recommendation?.replenishment_needed && r.reorder_recommendation.recommended_reorder_quantity > 0
  );

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Inventory Intelligence & Stock Risk</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Deterministic coverage calculations, stock-out mitigation, and automated buffer replenishment.
        </p>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadInventoryData} />}

      {/* KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          label="Total On-Hand Units"
          value={health?.total_stock_units ?? 0}
          description="Tracked inventory units across all stores"
          icon={Boxes}
          variant="blue"
        />
        <KpiCard
          label="Inventory Valuation"
          value={health?.total_stock_value_inr ?? 0}
          description="Total capital locked in inventory"
          icon={DollarSign}
          variant="emerald"
          isCurrency
        />
        <KpiCard
          label="Critical Risk SKUs"
          value={health?.risk_distribution?.critical ?? 0}
          description="Coverage < 7.0 days of daily sales"
          icon={AlertOctagon}
          variant="rose"
        />
        <KpiCard
          label="Overstocked Records"
          value={health?.overstocked_records ?? 0}
          description={`₹${((health?.overstocked_excess_value_inr ?? 0) / 100000).toFixed(1)}L excess capital (>45 days coverage)`}
          icon={Layers}
          variant="amber"
        />
      </div>

      {/* Section Navigation Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
        <button
          onClick={() => setActiveTab('risks')}
          className="btn-secondary"
          style={{
            borderColor: activeTab === 'risks' ? 'var(--accent-rose)' : 'transparent',
            background: activeTab === 'risks' ? 'var(--accent-rose-bg)' : 'transparent',
            color: activeTab === 'risks' ? 'var(--accent-rose)' : 'var(--text-secondary)',
            fontWeight: 600,
          }}
        >
          <ShieldAlert size={16} />
          <span>Stock-Out Risks ({risks.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('reorder')}
          className="btn-secondary"
          style={{
            borderColor: activeTab === 'reorder' ? 'var(--accent-blue)' : 'transparent',
            background: activeTab === 'reorder' ? 'var(--accent-blue-bg)' : 'transparent',
            color: activeTab === 'reorder' ? 'var(--accent-blue)' : 'var(--text-secondary)',
            fontWeight: 600,
          }}
        >
          <RotateCcw size={16} />
          <span>Reorder Recommendations ({reorderCandidates.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('overstock')}
          className="btn-secondary"
          style={{
            borderColor: activeTab === 'overstock' ? 'var(--accent-amber)' : 'transparent',
            background: activeTab === 'overstock' ? 'var(--accent-amber-bg)' : 'transparent',
            color: activeTab === 'overstock' ? 'var(--accent-amber)' : 'var(--text-secondary)',
            fontWeight: 600,
          }}
        >
          <Layers size={16} />
          <span>Overstock Items ({overstock.length})</span>
        </button>
      </div>

      {/* Tab 1: Stock-Out Risks Table */}
      {activeTab === 'risks' && (
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <div className="iq-card-title">
                <ShieldAlert size={18} color="var(--accent-rose)" />
                <span>Products at Stock-Out Risk</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Sorted by urgency (lowest days of coverage first). Calculated deterministically.
              </div>
            </div>

            {/* Severity Filter */}
            <div style={{ display: 'flex', gap: '0.35rem' }}>
              {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
                <button
                  key={sev}
                  onClick={() => setFilterSeverity(sev)}
                  className="chip"
                  style={{
                    fontSize: '0.725rem',
                    background: filterSeverity === sev ? 'rgba(56, 189, 248, 0.2)' : undefined,
                    borderColor: filterSeverity === sev ? 'var(--accent-blue)' : undefined,
                    color: filterSeverity === sev ? 'var(--accent-blue)' : undefined,
                  }}
                >
                  {sev}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <LoadingSkeleton rows={6} height="48px" />
          ) : (
            <div className="table-container">
              <table className="iq-table">
                <thead>
                  <tr>
                    <th>Product Name</th>
                    <th>Store Location</th>
                    <th>Current Stock</th>
                    <th>Daily Sales</th>
                    <th>Days Coverage</th>
                    <th>Risk Level</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRisks.map((r, i) => (
                    <tr key={`${r.product_id}-${r.store_id}`}>
                      <td style={{ fontWeight: 600 }}>{r.product_name}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{r.store_name}</td>
                      <td className="mono">{r.current_stock}</td>
                      <td className="mono">{r.average_daily_sales.toFixed(2)}</td>
                      <td>
                        <span
                          className="mono"
                          style={{
                            fontWeight: 700,
                            color:
                              r.days_of_coverage < 7
                                ? 'var(--accent-rose)'
                                : r.days_of_coverage < 14
                                ? 'var(--accent-amber)'
                                : 'var(--accent-blue)',
                          }}
                        >
                          {r.days_of_coverage.toFixed(1)} days
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            r.risk_level === 'CRITICAL'
                              ? 'badge-critical'
                              : r.risk_level === 'HIGH'
                              ? 'badge-high'
                              : 'badge-medium'
                          }`}
                        >
                          {r.risk_level}
                        </span>
                      </td>
                      <td>
                        {r.reorder_recommendation?.recommended_reorder_quantity > 0 ? (
                          <span
                            className="mono"
                            style={{
                              fontSize: '0.8rem',
                              fontWeight: 700,
                              color: 'var(--accent-amber)',
                              background: 'var(--accent-amber-bg)',
                              padding: '0.2rem 0.5rem',
                              borderRadius: 'var(--radius-sm)',
                            }}
                          >
                            Reorder {r.reorder_recommendation.recommended_reorder_quantity} units
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Buffer adequate</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Reorder Recommendations */}
      {activeTab === 'reorder' && (
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header">
            <div>
              <div className="iq-card-title">
                <RotateCcw size={18} color="var(--accent-blue)" />
                <span>Deterministic Reorder Recommendations</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Replenishment targets based on 21-day target buffer and actual 30-day sales velocity.
              </div>
            </div>
            <span className="badge badge-complete">Formula: Target Stock - Current Stock</span>
          </div>

          {isLoading ? (
            <LoadingSkeleton rows={5} height="60px" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              {reorderCandidates.map((item) => (
                <div
                  key={`${item.product_id}-${item.store_id}`}
                  style={{
                    background: 'rgba(15, 23, 42, 0.65)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '1rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '0.9rem' }}>
                        {item.product_name}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {item.store_name} ({item.city})
                      </div>
                    </div>
                    <span className={`badge ${item.risk_level === 'CRITICAL' ? 'badge-critical' : 'badge-high'}`}>
                      {item.risk_level}
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', margin: '0.75rem 0', fontSize: '0.75rem' }}>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Current Stock: </span>
                      <strong className="mono" style={{ color: 'var(--text-primary)' }}>{item.current_stock}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Daily Demand: </span>
                      <strong className="mono" style={{ color: 'var(--text-primary)' }}>{item.average_daily_sales.toFixed(2)}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Coverage: </span>
                      <strong className="mono" style={{ color: item.days_of_coverage < 7 ? 'var(--accent-rose)' : 'var(--accent-amber)' }}>
                        {item.days_of_coverage.toFixed(1)} days
                      </strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--text-muted)' }}>Target Buffer: </span>
                      <strong className="mono" style={{ color: 'var(--text-primary)' }}>21 days</strong>
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'rgba(56, 189, 248, 0.1)',
                      border: '1px solid rgba(56, 189, 248, 0.25)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.5rem 0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      Recommended Quantity:
                    </span>
                    <span className="mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
                      {item.reorder_recommendation.recommended_reorder_quantity} units
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Overstocked Items Table */}
      {activeTab === 'overstock' && (
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header">
            <div>
              <div className="iq-card-title">
                <Layers size={18} color="var(--accent-amber)" />
                <span>Overstocked Inventory & Excess Capital</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                Products with inventory exceeding 45 days of calculated demand.
              </div>
            </div>
            <span className="badge badge-warning">
              Threshold: &gt; 45 Days Coverage
            </span>
          </div>

          {isLoading ? (
            <LoadingSkeleton rows={5} height="48px" />
          ) : (
            <div className="table-container">
              <table className="iq-table">
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Store</th>
                    <th>Current Stock</th>
                    <th>Coverage (Days)</th>
                    <th>Excess Units</th>
                    <th>Excess Capital Locked</th>
                  </tr>
                </thead>
                <tbody>
                  {overstock.map((o) => (
                    <tr key={`${o.product_id}-${o.store_id}`}>
                      <td style={{ fontWeight: 600 }}>{o.product_name}</td>
                      <td style={{ color: 'var(--text-secondary)' }}>{o.store_name}</td>
                      <td className="mono">{o.current_stock}</td>
                      <td>
                        <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-amber)' }}>
                          {o.days_of_coverage.toFixed(1)} days
                        </span>
                      </td>
                      <td className="mono" style={{ fontWeight: 600, color: 'var(--accent-rose)' }}>
                        +{o.excess_inventory_units}
                      </td>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>
                        ₹{o.excess_capital_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
