import React from 'react';
import useTrackingStore from '../../store/trackingStore';

const LAYERS = [
  { key: 'showGroundTruth', label: 'TRUTH', color: 'var(--color-truth)' },
  { key: 'showRaw',         label: 'RAW', color: 'var(--color-raw)' },
  { key: 'showKalman',      label: 'KF', color: 'var(--color-kalman)' },
  { key: 'showAlphaBeta',   label: 'AB', color: 'var(--color-alphabeta)' },
];

export default function LayerControl() {
  const store = useTrackingStore();
  const { metricsHistory } = useTrackingStore();

  const lastMetrics = metricsHistory[metricsHistory.length - 1];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">LAYERS</span>
      </div>

      {LAYERS.map(({ key, label, color }) => (
        <div className="toggle-row" key={key}>
          <label className="toggle-label" htmlFor={`toggle-${key}`}>
            <span className="toggle-swatch" style={{ background: color }} />
            {label}
          </label>
          <label className="toggle-switch">
            <input
              id={`toggle-${key}`}
              type="checkbox"
              checked={store[key]}
              onChange={() => store.toggleLayer(key)}
            />
            <span className="toggle-track" />
          </label>
        </div>
      ))}

      {lastMetrics && (
        <>
          <div className="divider" style={{ margin: '0.5rem 0' }} />
          <p className="section-title">RMSE LIVE</p>

          <div className="flex-col gap-1" style={{ marginTop: '0.3rem' }}>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: 'var(--color-kalman)' }}>KF</span>
              <span className="font-mono text-sm text-accent">
                {lastMetrics.kalman_rmse.toFixed(2)}m
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: 'var(--color-alphabeta)' }}>AB</span>
              <span className="font-mono text-sm" style={{ color: 'var(--color-alphabeta)' }}>
                {lastMetrics.alpha_beta_rmse.toFixed(2)}m
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm" style={{ color: 'var(--color-raw)' }}>RAW</span>
              <span className="font-mono text-sm" style={{ color: 'var(--color-raw)' }}>
                {lastMetrics.raw_error.toFixed(2)}m
              </span>
            </div>

            <div style={{
              marginTop: '0.4rem',
              padding: '0.35rem 0.5rem',
              borderRadius: '3px',
              background: lastMetrics.kalman_rmse < 5
                ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
              border: `1px solid ${lastMetrics.kalman_rmse < 5 ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
            }}>
              <span className="text-sm font-mono" style={{ color: lastMetrics.kalman_rmse < 5 ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                {lastMetrics.kalman_rmse < 5 ? 'PASS' : 'FAIL'} KF &lt; 5m
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
