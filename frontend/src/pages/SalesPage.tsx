import React, { useEffect, useState } from 'react';
import { 
  fetchSalesSummary, 
  fetchProductsList, 
  fetchStoresList, 
  fetchProductPerformance, 
  fetchStorePerformance, 
  fetchStoreProductComparison,
  fetchCategoryPerformance 
} from '../api/client';
import { 
  SalesSummary, 
  ProductMeta, 
  StoreMeta, 
  ProductPerformance, 
  StorePerformance, 
  StoreProductComparison,
  CategoryResponse 
} from '../api/types';
import { KpiCard } from '../components/KpiCard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorAlert } from '../components/ErrorAlert';
import { 
  TrendingUp, 
  DollarSign, 
  ShoppingBag, 
  Store, 
  Package, 
  PieChart, 
  Award,
  Layers
} from 'lucide-react';

export const SalesPage: React.FC = () => {
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [products, setProducts] = useState<ProductMeta[]>([]);
  const [stores, setStores] = useState<StoreMeta[]>([]);
  const [categories, setCategories] = useState<CategoryResponse | null>(null);

  // Selected entities for deep dive
  const [selectedProductId, setSelectedProductId] = useState<string>('PRD001');
  const [selectedStoreId, setSelectedStoreId] = useState<string>('STR001');

  // Dynamic analytics state
  const [productData, setProductData] = useState<ProductPerformance | null>(null);
  const [storeProductComp, setStoreProductComp] = useState<StoreProductComparison | null>(null);
  const [storeData, setStoreData] = useState<StorePerformance | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isProductLoading, setIsProductLoading] = useState<boolean>(false);
  const [isStoreLoading, setIsStoreLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Initial load: summary, product list, store list, categories
  useEffect(() => {
    const initSales = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [sumRes, prodsRes, storesRes, catRes] = await Promise.all([
          fetchSalesSummary(),
          fetchProductsList(),
          fetchStoresList(),
          fetchCategoryPerformance(),
        ]);
        setSummary(sumRes);
        setProducts(prodsRes);
        setStores(storesRes);
        setCategories(catRes);

        if (prodsRes.length > 0) {
          setSelectedProductId(prodsRes[0].product_id);
        }
        if (storesRes.length > 0) {
          setSelectedStoreId(storesRes[0].store_id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load sales intelligence baseline.');
      } finally {
        setIsLoading(false);
      }
    };
    initSales();
  }, []);

  // Fetch product performance & store breakdown when selectedProductId changes
  useEffect(() => {
    if (!selectedProductId) return;
    const loadProductAnalytics = async () => {
      setIsProductLoading(true);
      try {
        const [perf, comp] = await Promise.all([
          fetchProductPerformance(selectedProductId),
          fetchStoreProductComparison(selectedProductId),
        ]);
        setProductData(perf);
        setStoreProductComp(comp);
      } catch (err: any) {
        console.error('Failed to load product analytics:', err);
      } finally {
        setIsProductLoading(false);
      }
    };
    loadProductAnalytics();
  }, [selectedProductId]);

  // Fetch store performance when selectedStoreId changes
  useEffect(() => {
    if (!selectedStoreId) return;
    const loadStoreAnalytics = async () => {
      setIsStoreLoading(true);
      try {
        const perf = await fetchStorePerformance(selectedStoreId);
        setStoreData(perf);
      } catch (err: any) {
        console.error('Failed to load store analytics:', err);
      } finally {
        setIsStoreLoading(false);
      }
    };
    loadStoreAnalytics();
  }, [selectedStoreId]);

  return (
    <div className="page-container">
      <div style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>Sales Intelligence</h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
          Deterministic sales analytics across network volume, product velocities, and store contributions.
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Summary KPI Cards */}
      <div className="kpi-grid">
        <KpiCard
          label="Total Network Revenue"
          value={summary?.total_revenue ?? 0}
          description="Cumulative recorded revenue"
          icon={DollarSign}
          variant="blue"
          isCurrency
        />
        <KpiCard
          label="Total Units Sold"
          value={summary?.total_units_sold ?? 0}
          description={`${summary?.total_transactions ?? 0} total transactions`}
          icon={ShoppingBag}
          variant="emerald"
        />
        <KpiCard
          label="Avg Daily Revenue"
          value={summary?.average_daily_revenue ?? 0}
          description={`Across ${summary?.active_selling_days ?? 0} active selling days`}
          icon={TrendingUp}
          variant="purple"
          isCurrency
        />
        <KpiCard
          label="Avg Order Value (AOV)"
          value={summary?.average_order_value ?? 0}
          description="Mean checkout cart revenue"
          icon={Layers}
          variant="amber"
          isCurrency
        />
      </div>

      {/* Product Performance Section */}
      <div className="iq-card animate-fade-in" style={{ marginBottom: '1.5rem' }}>
        <div className="iq-card-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div className="iq-card-title">
              <Package size={18} color="var(--accent-blue)" />
              <span>Product Performance Deep Dive</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              Inspect unit velocities, gross revenue, and cross-store distribution for any catalog product.
            </div>
          </div>

          {/* Product Dropdown Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>
              SELECT SKU:
            </label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              style={{
                background: 'rgba(15, 23, 42, 0.9)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.45rem 0.75rem',
                fontSize: '0.85rem',
                fontFamily: 'var(--font-sans)',
                cursor: 'pointer',
              }}
            >
              {products.map((p) => (
                <option key={p.product_id} value={p.product_id}>
                  {p.product_id} — {p.product_name} (₹{p.unit_price})
                </option>
              ))}
            </select>
          </div>
        </div>

        {isProductLoading || !productData ? (
          <LoadingSkeleton rows={3} height="50px" />
        ) : (
          <div>
            {/* Product Metrics Bar */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                gap: '1rem',
                marginBottom: '1.25rem',
                background: 'rgba(15, 23, 42, 0.5)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '1rem',
              }}
            >
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Product Name</div>
                <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
                  {productData.product_name}
                </div>
                <span className="badge badge-medium" style={{ marginTop: '0.35rem' }}>{productData.category}</span>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Revenue</div>
                <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-blue)', marginTop: '0.15rem' }}>
                  ₹{productData.total_revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>@ ₹{productData.unit_price} / unit</div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Units Sold</div>
                <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginTop: '0.15rem' }}>
                  {productData.total_units_sold.toLocaleString()}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>across network</div>
              </div>

              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Daily Velocity</div>
                <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--accent-emerald)', marginTop: '0.15rem' }}>
                  {productData.average_daily_sales.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>units / active day</div>
              </div>
            </div>

            {/* Store Comparison for this Product */}
            {storeProductComp && storeProductComp.stores.length > 0 && (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <div style={{ fontSize: '0.825rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Award size={15} color="var(--accent-amber)" />
                    <span>Store Breakdown for {productData.product_name}</span>
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Top location by revenue: <strong style={{ color: 'var(--accent-blue)' }}>{storeProductComp.best_store_by_revenue}</strong>
                  </span>
                </div>

                <div className="table-container">
                  <table className="iq-table">
                    <thead>
                      <tr>
                        <th>Store Location</th>
                        <th>City</th>
                        <th>Units Sold</th>
                        <th>Revenue Generated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {storeProductComp.stores.map((s) => (
                        <tr key={s.store_id}>
                          <td style={{ fontWeight: 600 }}>{s.store_name}</td>
                          <td style={{ color: 'var(--text-secondary)' }}>{s.city}</td>
                          <td className="mono">{s.units_sold.toLocaleString()}</td>
                          <td className="mono" style={{ fontWeight: 700, color: 'var(--accent-blue)' }}>
                            ₹{s.revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Store Performance & Category Breakdown */}
      <div className="equal-two-col">
        {/* Store Performance Selector */}
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
            <div className="iq-card-title">
              <Store size={18} color="var(--accent-purple)" />
              <span>Store Location Deep Dive</span>
            </div>

            <select
              value={selectedStoreId}
              onChange={(e) => setSelectedStoreId(e.target.value)}
              style={{
                background: 'rgba(15, 23, 42, 0.9)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: 'var(--radius-sm)',
                padding: '0.35rem 0.65rem',
                fontSize: '0.8rem',
              }}
            >
              {stores.map((s) => (
                <option key={s.store_id} value={s.store_id}>
                  {s.store_name} ({s.city})
                </option>
              ))}
            </select>
          </div>

          {isStoreLoading || !storeData ? (
            <LoadingSkeleton rows={4} height="40px" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.85rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>LOCATION</div>
                <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>
                  {storeData.store_name}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--accent-blue)' }}>{storeData.city} hub</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>REVENUE</div>
                  <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
                    ₹{storeData.total_revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>UNITS SOLD</div>
                  <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {storeData.total_units_sold.toLocaleString()}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>DAILY REVENUE</div>
                  <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--accent-emerald)' }}>
                    ₹{storeData.average_daily_revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </div>
                </div>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '0.75rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ORDERS</div>
                  <div className="mono" style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {storeData.total_transactions.toLocaleString()}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Category Contribution Breakdown */}
        <div className="iq-card animate-fade-in">
          <div className="iq-card-header">
            <div className="iq-card-title">
              <PieChart size={18} color="var(--accent-amber)" />
              <span>Category Revenue Shares</span>
            </div>
            <span className="badge badge-medium">Portfolio Contribution</span>
          </div>

          {isLoading || !categories ? (
            <LoadingSkeleton rows={5} height="40px" />
          ) : (
            <div className="table-container">
              <table className="iq-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Share %</th>
                    <th>Units</th>
                    <th>Revenue</th>
                  </tr>
                </thead>
                <tbody>
                  {categories.categories.map((c) => (
                    <tr key={c.category}>
                      <td style={{ fontWeight: 600 }}>{c.category}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className="mono" style={{ fontWeight: 700, color: 'var(--accent-blue)', fontSize: '0.8rem' }}>
                            {c.revenue_percentage}%
                          </span>
                          <div style={{ width: '45px', height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: `${c.revenue_percentage}%`, height: '100%', background: 'var(--accent-blue)' }} />
                          </div>
                        </div>
                      </td>
                      <td className="mono">{c.units_sold.toLocaleString()}</td>
                      <td className="mono" style={{ fontWeight: 700 }}>
                        ₹{c.revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
