import React from 'react';
import useTrackingStore from '../../store/trackingStore';

function CoordRow({ label, value, unit, color }) {
  return (
    <div className="flex justify-between items-center" style={{ padding: '0.2rem 0' }}>
      <span className="text-xs text-secondary">{label}</span>
      <span className="font-mono text-xs" style={{ color: color || 'var(--text-primary)' }}>
        {value != null ? value : '—'}
        {unit && <span className="text-muted" style={{ marginLeft: '0.2em' }}>{unit}</span>}
      </span>
    </div>
  );
}

export default function CoordDisplay() {
  const { currentFrame, simConfig } = useTrackingStore();
  // Show altitude row only for drone (3D Kalman active)
  const isDrone = simConfig?.target_type === 'drone';

  if (!currentFrame) {
    return (
      <div className="card">
        <div className="card-header"><span className="card-title">📍 Live Position</span></div>
        <p className="text-xs text-muted" style={{ textAlign: 'center', padding: '1rem 0' }}>
          Chưa có dữ liệu
        </p>
      </div>
    );
  }

  const { ground_truth: gt, kalman: kf, alpha_beta: ab, pan_tilt } = currentFrame;

  return (
    <div className="card" style={{ fontSize: '0.78rem' }}>
      <div className="card-header"><span className="card-title">📍 Live Position</span></div>

      <p className="section-title" style={{ marginTop: '0.25rem' }}>Ground Truth</p>
      <CoordRow label="Lat" value={gt.lat.toFixed(6) + '°'} color="var(--color-truth)" />
      <CoordRow label="Lon" value={gt.lon.toFixed(6) + '°'} color="var(--color-truth)" />
      {isDrone && (
        <CoordRow
          label="Độ cao (GT)"
          value={(gt.up ?? gt.alt)?.toFixed(1)}
          unit="m"
          color="var(--color-truth)"
        />
      )}

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">Kalman Filtered</p>
      <CoordRow label="Lat"   value={kf.lat.toFixed(6) + '°'} color="var(--color-kalman)" />
      <CoordRow label="Lon"   value={kf.lon.toFixed(6) + '°'} color="var(--color-kalman)" />
      {isDrone && (
        <CoordRow
          label="Alt (3D KF)"
          value={kf.up != null ? kf.up.toFixed(1) : kf.alt?.toFixed(1)}
          unit="m"
          color="var(--color-kalman)"
        />
      )}
      <CoordRow label="Speed" value={kf.speed?.toFixed(1)} unit="m/s" color="var(--color-kalman)" />
      <CoordRow label="σ pos" value={kf.uncertainty_m?.toFixed(1)} unit="m" />

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">α-β Filtered</p>
      <CoordRow label="Lat"   value={ab.lat.toFixed(6) + '°'} color="var(--color-alphabeta)" />
      <CoordRow label="Lon"   value={ab.lon.toFixed(6) + '°'} color="var(--color-alphabeta)" />
      <CoordRow label="Speed" value={ab.speed?.toFixed(1)} unit="m/s" color="var(--color-alphabeta)" />

      <div className="divider" style={{ margin: '0.4rem 0' }} />

      <p className="section-title">Pan-Tilt Sensor</p>
      <CoordRow label="Azimuth"   value={pan_tilt.azimuth?.toFixed(1)} unit="°" />
      <CoordRow label="Elevation" value={pan_tilt.elevation?.toFixed(1)} unit="°" />
      <CoordRow label="Range"     value={pan_tilt.range?.toFixed(0)} unit="m" />
    </div>
  );
}
