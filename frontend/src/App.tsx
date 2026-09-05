import React, { useState } from 'react';
import { Sidebar, ActiveTab } from './components/Sidebar';
import { Header } from './components/Header';
import { DashboardPage } from './pages/DashboardPage';
import { SalesPage } from './pages/SalesPage';
import { InventoryPage } from './pages/InventoryPage';
import { CopilotPage } from './pages/CopilotPage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>('dashboard');
  const [isMobileNavOpen, setIsMobileNavOpen] = useState<boolean>(false);
  const [refreshKey, setRefreshKey] = useState<number>(0);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setRefreshKey((prev) => prev + 1);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const getHeaderMeta = () => {
    switch (activeTab) {
      case 'dashboard':
        return {
          title: 'Retail Intelligence Overview',
          subtitle: 'Holistic overview of cross-store revenue, product velocity, and priority stock alerts.',
        };
      case 'sales':
        return {
          title: 'Sales Intelligence Engine',
          subtitle: 'Deterministic revenue aggregation, SKU velocities, and store-by-store sales breakdowns.',
        };
      case 'inventory':
        return {
          title: 'Inventory Intelligence & Risk Control',
          subtitle: 'Automated stockout risk detection, buffer replenishment calculations, and overstock analysis.',
        };
      case 'copilot':
        return {
          title: 'Evidence-First Retail Copilot',
          subtitle: 'Natural language retail questions translated into deterministic analytics and grounded explanations.',
        };
    }
  };

  const meta = getHeaderMeta();

  return (
    <div className="app-layout">
      {/* Navigation Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isMobileOpen={isMobileNavOpen}
        setIsMobileOpen={setIsMobileNavOpen}
      />

      {/* Main Content Area */}
      <main className="main-content">
        <Header
          title={meta.title}
          subtitle={meta.subtitle}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
          onOpenMobileNav={() => setIsMobileNavOpen(true)}
        />

        {/* Dynamic Page Rendering */}
        <div key={refreshKey} style={{ flex: 1 }}>
          {activeTab === 'dashboard' && <DashboardPage />}
          {activeTab === 'sales' && <SalesPage />}
          {activeTab === 'inventory' && <InventoryPage />}
          {activeTab === 'copilot' && <CopilotPage />}
        </div>
      </main>
    </div>
  );
};

export default App;
