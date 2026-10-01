import React from 'react';
import useTrackingStore from '../../store/trackingStore';

function CoordRow({ label, value, unit, color }) {
  return (
    <div className="flex justify-between items-center" style={{ padding: '0.2rem 0' }}>
      <span className="text-sm text-muted font-mono">{label}</span>
      <span className="font-mono text-sm" style={{ color: color || 'var(--text-primary)' }}>
        {value != null ? value : '--'}
        {unit && <span className="text-muted" style={{ marginLeft: '0.15em' }}>{unit}</span>}
      </span>
    </div>
  );
}

export default function CoordDisplay() {
  const { currentFrame, simConfig } = useTrackingStore();
  const isDrone = simConfig?.target_type === 'drone';

  if (!currentFrame) {
    return (
      <div className="card">
        <div className="card-header"><span className="card-title">POS</span></div>
        <p className="text-sm text-muted font-mono" style={{ textAlign: 'center', padding: '1rem 0' }}>
          NO DATA
        </p>
      </div>
    );
  }

  const { ground_truth: gt, kalman: kf, alpha_beta: ab, pan_tilt } = currentFrame;

  return (
    <div className="card" style={{ fontSize: '0.85rem' }}>
      <div className="card-header"><span className="card-title">POS</span></div>

      <p className="section-title">TRUTH</p>
      <CoordRow label="LAT" value={gt.lat.toFixed(6)} color="var(--color-truth)" />
      <CoordRow label="LON" value={gt.lon.toFixed(6)} color="var(--color-truth)" />
      {isDrone && (
        <CoordRow label="ALT" value={(gt.up ?? gt.alt)?.toFixed(1)} unit="m" color="var(--color-truth)" />
      )}

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">KF</p>
      <CoordRow label="LAT" value={kf.lat.toFixed(6)} color="var(--color-kalman)" />
      <CoordRow label="LON" value={kf.lon.toFixed(6)} color="var(--color-kalman)" />
      {isDrone && (
        <CoordRow label="ALT" value={kf.up != null ? kf.up.toFixed(1) : kf.alt?.toFixed(1)} unit="m" color="var(--color-kalman)" />
      )}
      <CoordRow label="SPD" value={kf.speed?.toFixed(1)} unit="m/s" color="var(--color-kalman)" />
      <CoordRow label="SIGMA" value={kf.uncertainty_m?.toFixed(1)} unit="m" />

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">AB</p>
      <CoordRow label="LAT" value={ab.lat.toFixed(6)} color="var(--color-alphabeta)" />
      <CoordRow label="LON" value={ab.lon.toFixed(6)} color="var(--color-alphabeta)" />
      <CoordRow label="SPD" value={ab.speed?.toFixed(1)} unit="m/s" color="var(--color-alphabeta)" />

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">SENSOR</p>
      <CoordRow label="AZ" value={pan_tilt.azimuth?.toFixed(1)} unit="deg" />
      <CoordRow label="EL" value={pan_tilt.elevation?.toFixed(1)} unit="deg" />
      <CoordRow label="RNG" value={pan_tilt.range?.toFixed(0)} unit="m" />
    </div>
  );
}
