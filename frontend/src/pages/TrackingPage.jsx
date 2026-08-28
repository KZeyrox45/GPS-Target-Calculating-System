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
      <aside className="sidebar" style={{ width: '320px' }}>
        <SimulationPanel />
        <LayerControl />
      </aside>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        {simulationEnded && (
          <div style={{
            padding: '0.4rem 1rem',
            background: 'rgba(34,197,94,0.06)',
            borderBottom: '1px solid var(--border-subtle)',
            fontSize: '0.85rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--accent-success)',
            textAlign: 'center',
            flexShrink: 0,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}>
            SIM COMPLETE · FULL TRAJECTORY DATA
          </div>
        )}

        <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
          <TrackingMap observerPos={observerPos} />
        </div>

        <div style={{ flexShrink: 0, padding: '0.5rem', background: 'var(--bg-secondary)', borderTop: '1px solid var(--border-subtle)' }}>
          <ErrorMetricsChart />
          {simConfig.target_type === 'drone' && <AltitudeChart />}
        </div>
      </div>

      <aside className="sidebar sidebar-right" style={{ width: '260px' }}>
        <CoordDisplay />

        <div className="card">
          <div className="card-header"><span className="card-title">SESSION</span></div>
          <div className="flex-col gap-1 text-sm text-secondary font-mono">
            <div className="flex justify-between">
              <span>TGT</span>
              <span className="text-primary">{simConfig.target_type.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span>ALG</span>
              <span className="text-primary">{simConfig.algorithm.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span>RATE</span>
              <span className="text-primary">{simConfig.update_rate_hz}Hz</span>
            </div>
            <div className="flex justify-between">
              <span>STATUS</span>
              <span className={isRunning ? 'text-accent' : simulationEnded ? 'text-success' : 'text-muted'}>
                {isRunning ? 'RUN' : simulationEnded ? 'DONE' : 'IDLE'}
              </span>
            </div>
          </div>
        </div>
      </aside>
    </div>
  );
}
