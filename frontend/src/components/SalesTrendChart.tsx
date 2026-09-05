import React, { useState } from 'react';
import { SalesTrendPoint } from '../api/types';
import { TrendingUp, Calendar, AlertCircle } from 'lucide-react';

interface SalesTrendChartProps {
  data: SalesTrendPoint[];
  isLoading?: boolean;
  error?: string | null;
}

export const SalesTrendChart: React.FC<SalesTrendChartProps> = ({
  data,
  isLoading = false,
  error = null,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<SalesTrendPoint | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);

  if (isLoading) {
    return (
      <div className="iq-card" style={{ minHeight: '340px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <div className="skeleton" style={{ width: '40px', height: '40px', borderRadius: '50%', margin: '0 auto 1rem' }} />
          <div style={{ fontSize: '0.875rem' }}>Loading verified sales trend data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="iq-card" style={{ minHeight: '340px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--accent-rose)', maxWidth: '400px' }}>
          <AlertCircle size={32} style={{ margin: '0 auto 0.5rem' }} />
          <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.25rem' }}>Failed to Load Sales Trend</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="iq-card" style={{ minHeight: '340px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <Calendar size={32} style={{ margin: '0 auto 0.5rem', opacity: 0.5 }} />
          <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>No Sales History Found</div>
          <div style={{ fontSize: '0.8rem' }}>No recorded transactions match the active filter criteria.</div>
        </div>
      </div>
    );
  }

  // Calculate scales
  const revenues = data.map((d) => d.revenue);
  const maxRevenue = Math.max(...revenues, 1);
  const minRevenue = Math.min(...revenues, 0);

  const chartWidth = 800;
  const chartHeight = 240;
  const paddingX = 40;
  const paddingY = 25;

  const innerWidth = chartWidth - paddingX * 2;
  const innerHeight = chartHeight - paddingY * 2;

  const points = data.map((d, index) => {
    const x = paddingX + (index / Math.max(data.length - 1, 1)) * innerWidth;
    const y = chartHeight - paddingY - ((d.revenue - minRevenue) / (maxRevenue - minRevenue || 1)) * innerHeight;
    return { x, y, data: d };
  });

  const pathD = points.reduce((acc, p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`), '');
  const areaD = `${pathD} L ${points[points.length - 1].x} ${chartHeight - paddingY} L ${points[0].x} ${chartHeight - paddingY} Z`;

  const totalPeriodRevenue = revenues.reduce((a, b) => a + b, 0);
  const totalPeriodUnits = data.reduce((acc, d) => acc + d.units, 0);

  return (
    <div className="iq-card animate-fade-in" style={{ position: 'relative' }}>
      <div className="iq-card-header">
        <div>
          <div className="iq-card-title">
            <TrendingUp size={18} color="var(--accent-blue)" />
            <span>Sales Revenue Trend</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Daily revenue timeline across {data.length} transaction days
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
            ₹{totalPeriodRevenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {totalPeriodUnits.toLocaleString('en-IN')} units total
          </div>
        </div>
      </div>

      {/* Responsive SVG Container */}
      <div style={{ width: '100%', overflowX: 'auto', position: 'relative' }}>
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          style={{ width: '100%', height: 'auto', minWidth: '500px', display: 'block' }}
          onMouseLeave={() => {
            setHoveredPoint(null);
            setHoverPos(null);
          }}
        >
          <defs>
            <linearGradient id="revenueAreaGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Horizontal Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = chartHeight - paddingY - ratio * innerHeight;
            const val = minRevenue + ratio * (maxRevenue - minRevenue);
            return (
              <g key={ratio}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={chartWidth - paddingX}
                  y2={y}
                  stroke="var(--border-color)"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
                <text
                  x={paddingX - 6}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--text-muted)"
                  fontSize="10"
                  fontFamily="var(--font-mono)"
                >
                  ₹{(val / 1000).toFixed(0)}k
                </text>
              </g>
            );
          })}

          {/* Area Fill */}
          <path d={areaD} fill="url(#revenueAreaGrad)" />

          {/* Trend Line */}
          <path
            d={pathD}
            fill="none"
            stroke="var(--accent-blue)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Data Points */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={hoveredPoint?.date === p.data.date ? 6 : 3.5}
              fill={hoveredPoint?.date === p.data.date ? '#ffffff' : 'var(--accent-blue)'}
              stroke="var(--bg-app)"
              strokeWidth="2"
              style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
              onMouseEnter={(e) => {
                setHoveredPoint(p.data);
                const rect = e.currentTarget.getBoundingClientRect();
                setHoverPos({ x: p.x, y: p.y });
              }}
            />
          ))}

          {/* Date Labels (sampled) */}
          {points
            .filter((_, i) => i === 0 || i === Math.floor(points.length / 2) || i === points.length - 1)
            .map((p, i) => (
              <text
                key={i}
                x={p.x}
                y={chartHeight - 6}
                textAnchor={i === 0 ? 'start' : i === 2 ? 'end' : 'middle'}
                fill="var(--text-muted)"
                fontSize="10"
                fontFamily="var(--font-sans)"
              >
                {p.data.date}
              </text>
            ))}
        </svg>

        {/* Hover Tooltip */}
        {hoveredPoint && hoverPos && (
          <div
            style={{
              position: 'absolute',
              left: `${(hoverPos.x / chartWidth) * 100}%`,
              top: `${(hoverPos.y / chartHeight) * 100}%`,
              transform: 'translate(-50%, -120%)',
              background: 'rgba(15, 23, 42, 0.95)',
              border: '1px solid var(--accent-blue)',
              borderRadius: 'var(--radius-sm)',
              padding: '0.5rem 0.75rem',
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
              pointerEvents: 'none',
              zIndex: 20,
              minWidth: '130px',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
              {hoveredPoint.date}
            </div>
            <div className="mono" style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--accent-blue)' }}>
              ₹{hoveredPoint.revenue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {hoveredPoint.units} units • {hoveredPoint.transactions} orders
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
