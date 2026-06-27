import React from 'react';
import useTrackingStore from '../../store/trackingStore';

const LAYERS = [
  { key: 'showGroundTruth', label: 'Ground Truth', color: 'var(--color-truth)' },
  { key: 'showRaw',         label: 'Raw Measurement', color: 'var(--color-raw)' },
  { key: 'showKalman',      label: 'Kalman Filter', color: 'var(--color-kalman)' },
  { key: 'showAlphaBeta',   label: 'α-β Filter', color: 'var(--color-alphabeta)' },
];

export default function LayerControl() {
  const store = useTrackingStore();
  const { metricsHistory } = useTrackingStore();

  const lastMetrics = metricsHistory[metricsHistory.length - 1];

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">🗂️ Layers & Metrics</span>
      </div>

      {/* Layer toggles */}
      <p className="section-title">Hiển thị quỹ đạo</p>
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

      {/* Current RMSE */}
      {lastMetrics && (
        <>
          <div className="divider" style={{ margin: '0.6rem 0' }} />
          <p className="section-title">RMSE hiện tại</p>

          <div className="flex-col gap-1" style={{ marginTop: '0.25rem' }}>
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--color-kalman)' }}>Kalman RMSE</span>
              <span className="font-mono text-xs text-accent">
                {lastMetrics.kalman_rmse.toFixed(2)} m
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--color-alphabeta)' }}>α-β RMSE</span>
              <span className="font-mono text-xs" style={{ color: 'var(--color-alphabeta)' }}>
                {lastMetrics.alpha_beta_rmse.toFixed(2)} m
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--color-raw)' }}>Raw Error</span>
              <span className="font-mono text-xs" style={{ color: 'var(--color-raw)' }}>
                {lastMetrics.raw_error.toFixed(2)} m
              </span>
            </div>

            {/* Thesis spec indicator */}
            <div style={{
              marginTop: '0.4rem',
              padding: '0.35rem 0.5rem',
              borderRadius: 'var(--radius-sm)',
              background: lastMetrics.kalman_rmse < 5
                ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
              border: `1px solid ${lastMetrics.kalman_rmse < 5 ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
            }}>
              <span className="text-xs" style={{ color: lastMetrics.kalman_rmse < 5 ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                {lastMetrics.kalman_rmse < 5 ? '✅' : '❌'} Thesis spec: Kalman RMSE {'<'} 5m
              </span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
