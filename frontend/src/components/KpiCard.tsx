import React from 'react';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  label: string;
  value: string | number;
  description: string;
  icon: LucideIcon;
  variant?: 'blue' | 'emerald' | 'amber' | 'rose' | 'purple' | 'default';
  isCurrency?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  label,
  value,
  description,
  icon: Icon,
  variant = 'default',
  isCurrency = false,
}) => {
  const getColors = () => {
    switch (variant) {
      case 'rose':
        return { bg: 'var(--accent-rose-bg)', color: 'var(--accent-rose)', border: 'rgba(244, 63, 94, 0.25)' };
      case 'amber':
        return { bg: 'var(--accent-amber-bg)', color: 'var(--accent-amber)', border: 'rgba(245, 158, 11, 0.25)' };
      case 'emerald':
        return { bg: 'var(--accent-emerald-bg)', color: 'var(--accent-emerald)', border: 'rgba(16, 185, 129, 0.25)' };
      case 'purple':
        return { bg: 'var(--accent-purple-bg)', color: 'var(--accent-purple)', border: 'rgba(168, 85, 247, 0.25)' };
      case 'blue':
        return { bg: 'var(--accent-blue-bg)', color: 'var(--accent-blue)', border: 'rgba(56, 189, 248, 0.25)' };
      default:
        return { bg: 'rgba(30, 41, 59, 0.5)', color: 'var(--text-secondary)', border: 'var(--border-color)' };
    }
  };

  const colors = getColors();

  const formattedValue = typeof value === 'number'
    ? isCurrency
      ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
      : value.toLocaleString('en-IN')
    : value;

  return (
    <div
      className="iq-card animate-fade-in"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '1.25rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <span
          style={{
            fontSize: '0.725rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            color: 'var(--text-muted)',
          }}
        >
          {label}
        </span>
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: colors.bg,
            color: colors.color,
            border: `1px solid ${colors.border}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon size={18} strokeWidth={2.2} />
        </div>
      </div>

      <div>
        <div
          className="mono"
          style={{
            fontSize: '1.75rem',
            fontWeight: 800,
            color: 'var(--text-primary)',
            letterSpacing: '-0.03em',
            lineHeight: 1.1,
          }}
        >
          {formattedValue}
        </div>
        <div
          style={{
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            marginTop: '0.4rem',
            lineHeight: 1.3,
          }}
        >
          {description}
        </div>
      </div>
    </div>
  );
};
