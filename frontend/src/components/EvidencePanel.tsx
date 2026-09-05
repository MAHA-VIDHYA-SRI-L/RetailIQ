import React from 'react';
import { 
  ShieldCheck, 
  Database, 
  HelpCircle, 
  CheckCircle2, 
  AlertTriangle, 
  Calendar,
  Layers
} from 'lucide-react';

interface EvidencePanelProps {
  evidence: Array<Record<string, any>>;
  assumptions?: string[];
  dataStatus?: 'complete' | 'incomplete' | 'no_data' | 'ambiguous' | 'unavailable';
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence,
  assumptions = [],
  dataStatus = 'complete',
}) => {
  if (!evidence || evidence.length === 0) {
    return null;
  }

  const renderDataStatusBadge = () => {
    switch (dataStatus) {
      case 'complete':
        return (
          <span className="badge badge-complete">
            <CheckCircle2 size={12} /> Verified Grounding
          </span>
        );
      case 'incomplete':
        return (
          <span className="badge badge-warning">
            <AlertTriangle size={12} /> Partial Dataset Window
          </span>
        );
      case 'no_data':
        return (
          <span className="badge badge-critical">
            <AlertTriangle size={12} /> Zero Records Found
          </span>
        );
      case 'ambiguous':
        return (
          <span className="badge badge-high">
            <HelpCircle size={12} /> Ambiguity Detected
          </span>
        );
      default:
        return <span className="badge">{dataStatus}</span>;
    }
  };

  return (
    <div className="evidence-box animate-fade-in">
      <div className="evidence-box-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
          <ShieldCheck size={16} />
          <span>Verified Deterministic Evidence</span>
        </div>
        {renderDataStatusBadge()}
      </div>

      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.65rem' }}>
        Calculated directly from SQLite transactions and inventory tables. Never hallucinated.
      </div>

      {/* Structured Evidence Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {evidence.slice(0, 5).map((item, idx) => (
          <div
            key={idx}
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid rgba(56, 189, 248, 0.18)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.65rem 0.85rem',
              fontSize: '0.785rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                {item.product_name || item.product || item.store_name || item.store || item.category || `Record #${idx + 1}`}
              </span>
              {item.store_name && item.product_name && (
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{item.store_name}</span>
              )}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.85rem', color: 'var(--text-secondary)' }}>
              {item.days_of_coverage !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Coverage: </span>
                  <span className="mono" style={{ color: item.days_of_coverage < 7 ? 'var(--accent-rose)' : 'var(--accent-emerald)', fontWeight: 700 }}>
                    {typeof item.days_of_coverage === 'number' ? item.days_of_coverage.toFixed(1) : item.days_of_coverage} days
                  </span>
                </div>
              )}

              {item.current_stock !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Stock: </span>
                  <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    {item.current_stock} units
                  </span>
                </div>
              )}

              {item.average_daily_sales !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Velocity: </span>
                  <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    {typeof item.average_daily_sales === 'number' ? item.average_daily_sales.toFixed(2) : item.average_daily_sales} / day
                  </span>
                </div>
              )}

              {item.revenue !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Revenue: </span>
                  <span className="mono" style={{ color: 'var(--accent-blue)', fontWeight: 700 }}>
                    ₹{item.revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>
              )}

              {item.units_sold !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Units Sold: </span>
                  <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                    {item.units_sold}
                  </span>
                </div>
              )}

              {item.recommended_reorder_quantity !== undefined && item.recommended_reorder_quantity > 0 && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Target Reorder: </span>
                  <span className="mono" style={{ color: 'var(--accent-amber)', fontWeight: 700 }}>
                    {item.recommended_reorder_quantity} units
                  </span>
                </div>
              )}

              {item.excess_inventory_units !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Excess Units: </span>
                  <span className="mono" style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>
                    {item.excess_inventory_units}
                  </span>
                </div>
              )}

              {item.excess_capital_inr !== undefined && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Excess Capital: </span>
                  <span className="mono" style={{ color: 'var(--accent-purple)', fontWeight: 700 }}>
                    ₹{item.excess_capital_inr.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Assumptions and boundaries */}
      {assumptions && assumptions.length > 0 && (
        <div style={{ marginTop: '0.75rem', paddingTop: '0.65rem', borderTop: '1px solid rgba(56, 189, 248, 0.12)' }}>
          <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem', textTransform: 'uppercase' }}>
            Applied Heuristics & Boundary Checks
          </div>
          <ul style={{ paddingLeft: '1.1rem', fontSize: '0.725rem', color: 'var(--text-secondary)' }}>
            {assumptions.map((asm, i) => (
              <li key={i} style={{ marginBottom: '0.15rem' }}>{asm}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
