import React from 'react';
import TrackingMap     from '../components/map/TrackingMap';
import SimulationPanel from '../components/controls/SimulationPanel';
import LayerControl    from '../components/controls/LayerControl';
import CoordDisplay    from '../components/ui/CoordDisplay';
import ErrorMetricsChart from '../components/charts/ErrorMetricsChart';
import AltitudeChart from '../components/charts/AltitudeChart';
import useTrackingStore from '../store/trackingStore';

export default function TrackingPage() {
  const { simConfig, isRunning, simulationEnded } = useTrackingStore();
  const observerPos = [simConfig.observer_lat, simConfig.observer_lon];

  return (
    <div style={{ display: 'flex', height: '100%', width: '100%', overflow: 'hidden' }}>
      {/* ── Left Sidebar: simulation controls ── */}
      <aside className="sidebar" style={{ width: '280px' }}>
        <SimulationPanel />
        <LayerControl />
      </aside>

      {/* ── Center: map + chart ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        {/* Simulation ended banner */}
        {simulationEnded && (
          <div style={{
            padding: '0.4rem 1rem',
            background: 'rgba(34,197,94,0.1)',
            borderBottom: '1px solid rgba(34,197,94,0.3)',
            fontSize: '0.8rem',
            color: 'var(--accent-success)',
            textAlign: 'center',
            flexShrink: 0,
          }}>
            ✅ Mô phỏng kết thúc — Dữ liệu quỹ đạo đầy đủ được hiển thị bên dưới
          </div>
        )}

        {/* Map — takes most space */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
          <TrackingMap observerPos={observerPos} />
        </div>

        {/* Chart strip at bottom */}
        <div style={{ flexShrink: 0, padding: '0.5rem', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-subtle)' }}>
          <ErrorMetricsChart />
          {simConfig.target_type === 'drone' && <AltitudeChart />}
        </div>
      </div>

      {/* ── Right Sidebar: live coordinate readout ── */}
      <aside className="sidebar sidebar-right" style={{ width: '240px' }}>
        <CoordDisplay />

        {/* Step info */}
        <div className="card">
          <div className="card-header"><span className="card-title">ℹ️ Session Info</span></div>
          <div className="flex-col gap-1 text-xs text-secondary font-mono">
            <div className="flex justify-between">
              <span>Loại:</span>
              <span className="text-primary">{simConfig.target_type}</span>
            </div>
            <div className="flex justify-between">
              <span>Algorithm:</span>
              <span className="text-primary">{simConfig.algorithm}</span>
            </div>
            <div className="flex justify-between">
              <span>Rate:</span>
              <span className="text-primary">{simConfig.update_rate_hz} Hz</span>
            </div>
            <div className="flex justify-between">
              <span>Status:</span>
              <span className={isRunning ? 'text-accent' : simulationEnded ? 'text-success' : 'text-muted'}>
                {isRunning ? '▶ Running' : simulationEnded ? '✓ Done' : '⏸ Idle'}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
