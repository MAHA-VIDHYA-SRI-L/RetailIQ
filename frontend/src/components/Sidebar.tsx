import React from 'react';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Boxes, 
  Sparkles, 
  Database,
  Activity,
  ShieldCheck
} from 'lucide-react';

export type ActiveTab = 'dashboard' | 'sales' | 'inventory' | 'copilot';

interface SidebarProps {
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  isMobileOpen: boolean;
  setIsMobileOpen: (open: boolean) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isMobileOpen,
  setIsMobileOpen,
}) => {
  const navItems = [
    {
      id: 'dashboard' as ActiveTab,
      label: 'Dashboard',
      icon: LayoutDashboard,
      badge: 'Overview',
    },
    {
      id: 'sales' as ActiveTab,
      label: 'Sales Intelligence',
      icon: TrendingUp,
      badge: 'Analytics',
    },
    {
      id: 'inventory' as ActiveTab,
      label: 'Inventory Intelligence',
      icon: Boxes,
      badge: 'Risk Engine',
    },
    {
      id: 'copilot' as ActiveTab,
      label: 'Copilot',
      icon: Sparkles,
      badge: 'AI Grounded',
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div 
          onClick={() => setIsMobileOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            zIndex: 40,
            backdropFilter: 'blur(4px)',
          }}
        />
      )}

      <aside
        style={{
          width: '260px',
          background: 'var(--bg-sidebar)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 50,
          transition: 'transform 0.3s ease',
          position: 'relative',
        }}
      >
        {/* Brand Header */}
        <div style={{ padding: '1.5rem 1.25rem', borderBottom: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: '0 0 15px rgba(2, 132, 199, 0.4)',
              }}
            >
              <Activity size={20} strokeWidth={2.5} />
            </div>
            <div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, letterSpacing: '-0.03em', lineHeight: 1.1 }}>
                Retail<span style={{ color: 'var(--accent-blue)' }}>IQ</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 500, marginTop: '2px' }}>
                Evidence-First Intelligence
              </div>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav style={{ padding: '1rem 0.75rem', flex: 1, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          <div style={{ padding: '0 0.5rem 0.5rem', fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsMobileOpen(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem',
                  width: '100%',
                  padding: '0.7rem 0.85rem',
                  borderRadius: 'var(--radius-sm)',
                  border: isActive ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid transparent',
                  background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                  color: isActive ? 'var(--accent-blue)' : 'var(--text-secondary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.875rem',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }
                }}
              >
                <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.id === 'copilot' && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      padding: '0.1rem 0.4rem',
                      borderRadius: 'var(--radius-full)',
                      background: 'rgba(168, 85, 247, 0.2)',
                      color: 'var(--accent-purple)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                    }}
                  >
                    AI
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Engine Security & Grounding Status */}
        <div style={{ padding: '1rem', margin: '0 0.75rem 1rem', background: 'var(--bg-card-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
            <ShieldCheck size={16} color="var(--accent-emerald)" />
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Deterministic Engine
            </span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>
            Python executes analytics. Gemini explains evidence. Zero hallucinations.
          </div>
        </div>

        {/* Footer / Status Area */}
        <div
          style={{
            padding: '0.9rem 1.25rem',
            borderTop: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Database size={13} color="var(--accent-blue)" />
            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>RetailIQ • PS03</span>
          </div>
          <span className="badge badge-healthy" style={{ padding: '0.1rem 0.45rem', fontSize: '0.65rem' }}>
            Active
          </span>
        </div>
      </aside>
    </>
  );
};
