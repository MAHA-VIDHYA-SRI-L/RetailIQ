import React from 'react';
import { AttentionItem } from '../api/types';
import { 
  AlertTriangle, 
  Flame, 
  TrendingDown, 
  Layers, 
  CheckCircle2, 
  ArrowRightCircle, 
  Info
} from 'lucide-react';

interface InventoryAlertFeedProps {
  items: AttentionItem[];
  isLoading?: boolean;
}

export const InventoryAlertFeed: React.FC<InventoryAlertFeedProps> = ({
  items,
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="iq-card">
        <div className="iq-card-header">
          <div className="iq-card-title">
            <AlertTriangle size={18} color="var(--accent-amber)" />
            <span>Inventory Attention</span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ height: '70px', borderRadius: 'var(--radius-sm)' }} />
          ))}
        </div>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="iq-card">
        <div className="iq-card-header">
          <div className="iq-card-title">
            <CheckCircle2 size={18} color="var(--accent-emerald)" />
            <span>Inventory Attention</span>
          </div>
        </div>
        <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)' }}>
          <CheckCircle2 size={32} color="var(--accent-emerald)" style={{ margin: '0 auto 0.5rem', opacity: 0.8 }} />
          <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>All Stock Levels Nominal</div>
          <div style={{ fontSize: '0.75rem', marginTop: '0.25rem' }}>No critical stockouts, severe demand surges, or excess capital warnings.</div>
        </div>
      </div>
    );
  }

  const getTypeIcon = (type: AttentionItem['type']) => {
    switch (type) {
      case 'STOCK_OUT':
        return <AlertTriangle size={16} color="var(--accent-rose)" />;
      case 'SALES_SPIKE':
        return <Flame size={16} color="var(--accent-amber)" />;
      case 'SALES_DROP':
        return <TrendingDown size={16} color="var(--accent-purple)" />;
      case 'OVERSTOCK':
        return <Layers size={16} color="var(--accent-blue)" />;
      default:
        return <Info size={16} color="var(--text-muted)" />;
    }
  };

  const getSeverityBadge = (severity: AttentionItem['severity']) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-critical">Critical</span>;
      case 'HIGH':
        return <span className="badge badge-high">High</span>;
      case 'MEDIUM':
        return <span className="badge badge-medium">Medium</span>;
      default:
        return <span className="badge">{severity}</span>;
    }
  };

  return (
    <div className="iq-card animate-fade-in">
      <div className="iq-card-header">
        <div className="iq-card-title">
          <AlertTriangle size={18} color="var(--accent-amber)" />
          <span>Inventory Attention</span>
        </div>
        <span className="badge badge-high">{items.length} Actions</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '420px', overflowY: 'auto' }}>
        {items.map((item, idx) => (
          <div
            key={idx}
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              border: '1px solid var(--border-color)',
              borderLeft: `4px solid ${
                item.severity === 'CRITICAL'
                  ? 'var(--accent-rose)'
                  : item.severity === 'HIGH'
                  ? 'var(--accent-amber)'
                  : 'var(--accent-blue)'
              }`,
              borderRadius: 'var(--radius-sm)',
              padding: '0.85rem 1rem',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.3)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                {getTypeIcon(item.type)}
                <span style={{ fontSize: '0.825rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {item.title}
                </span>
              </div>
              {getSeverityBadge(item.severity)}
            </div>

            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', marginBottom: '0.45rem', lineHeight: 1.35 }}>
              {item.description}
            </p>

            {item.recommended_action && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  fontSize: '0.75rem',
                  color: 'var(--accent-blue)',
                  background: 'rgba(56, 189, 248, 0.08)',
                  padding: '0.3rem 0.6rem',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(56, 189, 248, 0.15)',
                }}
              >
                <ArrowRightCircle size={14} />
                <span style={{ fontWeight: 600 }}>Action:</span>
                <span>{item.recommended_action}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
