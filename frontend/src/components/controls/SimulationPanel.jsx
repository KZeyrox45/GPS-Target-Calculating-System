import React, { useState } from 'react';
import useTrackingStore from '../../store/trackingStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import formatApiError from '../../utils/apiError';

export default function SimulationPanel() {
  const { simConfig, setSimConfig, setTargetType, isRunning, setIsRunning, setSessionId, reset, clearHistory, clearMetrics, setSimulationEnded } = useTrackingStore();
  const { connect, disconnect } = useWebSocket();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart() {
    setLoading(true);
    setError(null);
    disconnect();
    reset();
    clearHistory();
    clearMetrics();
    setSimulationEnded(false);
    try {
      const res = await fetch('/api/simulation/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simConfig),
      });
      if (!res.ok) {
        let detail = null;
        try { detail = (await res.json()).detail; } catch { detail = null; }
        throw new Error(formatApiError(res.status, detail));
      }
      const data = await res.json();
      setSessionId(data.session_id);
      setIsRunning(true);
      connect(data.session_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleStop() {
    const { sessionId } = useTrackingStore.getState();
    disconnect();
    setIsRunning(false);
    if (sessionId) {
      await fetch(`/api/simulation/stop/${sessionId}`, { method: 'POST' }).catch(() => {});
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">SIM CTRL</span>
      </div>

      <div className="flex-col gap-2">
        <p className="section-title">Observer Position</p>
        <div className="form-group">
          <label className="form-label">LAT</label>
          <input
            type="number" step="0.000001" className="form-input"
            value={simConfig.observer_lat}
            onChange={(e) => setSimConfig({ observer_lat: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label className="form-label">LON</label>
          <input
            type="number" step="0.000001" className="form-input"
            value={simConfig.observer_lon}
            onChange={(e) => setSimConfig({ observer_lon: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        <p className="section-title">Target Type</p>
        <div className="form-group">
          <select
            className="form-select"
            value={simConfig.target_type}
            onChange={(e) => setTargetType(e.target.value)}
            disabled={isRunning}
          >
            <option value="pedestrian">PEDESTRIAN</option>
            <option value="motorcycle">MOTORCYCLE</option>
            <option value="drone">DRONE</option>
          </select>
        </div>

        <div className="divider" />

        <p className="section-title">Filter Algorithm</p>
        <div className="form-group">
          <select
            className="form-select"
            value={simConfig.algorithm}
            onChange={(e) => setSimConfig({ algorithm: e.target.value })}
            disabled={isRunning}
          >
            <option value="both">KF + AB</option>
            <option value="kalman">KF ONLY</option>
            <option value="alpha_beta">AB ONLY</option>
          </select>
        </div>

        {simConfig.algorithm !== 'kalman' && (
          <div className="form-group">
            <label className="form-label">ALPHA ({simConfig.alpha})</label>
            <input
              type="range" min="0.1" max="0.9" step="0.05"
              value={simConfig.alpha}
              onChange={(e) => setSimConfig({ alpha: parseFloat(e.target.value) })}
              disabled={isRunning}
              style={{ width: '100%', accentColor: 'var(--accent-primary)' }}
            />
          </div>
        )}

        <div className="divider" />

        <p className="section-title">Duration</p>
        <div className="form-group">
          <label className="form-label">SECONDS</label>
          <input
            type="number" min="5" max="600" step="5" className="form-input"
            value={simConfig.duration_s}
            onChange={(e) => setSimConfig({ duration_s: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        <p className="section-title">Boundary</p>
        <div className="form-group">
          <label className="form-label">RADIUS ({simConfig.boundary_radius_m}m)</label>
          <input
            type="number" min="100" max="1000" step="50" className="form-input"
            value={simConfig.boundary_radius_m}
            onChange={(e) => setSimConfig({ boundary_radius_m: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        <p className="section-title">Trajectory Source</p>
        <div className="toggle-row">
          <span className="toggle-label">Real-World Data</span>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={simConfig.use_realistic_sim}
              onChange={(e) => setSimConfig({ use_realistic_sim: e.target.checked })}
              disabled={isRunning}
            />
            <span className="toggle-track" />
          </label>
        </div>
        <p className="text-xs" style={{ color: 'var(--text-muted)', marginTop: '-0.1rem', paddingLeft: '0.1rem' }}>
          {simConfig.use_realistic_sim
            ? (simConfig.target_type === 'motorcycle'
                ? 'Road network motorcycle trajectories'
                : 'Geolife / AMIT dataset trajectories')
            : 'Synthetic kinematic trajectories'}
        </p>

        <div className="divider" />

        {error && (
          <p className="text-sm text-danger" style={{ padding: '0.4rem', background: 'rgba(239,68,68,0.1)', borderRadius: '3px' }}>
            ERR: {error}
          </p>
        )}

        {isRunning ? (
          <button className="btn btn-danger btn-full" onClick={handleStop}>
            HALT
          </button>
        ) : (
          <button className="btn btn-primary btn-full" onClick={handleStart} disabled={loading}>
            {loading ? <><span className="spinner" /> INIT...</> : 'ENGAGE'}
          </button>
        )}
      </div>
    </div>
  );
}
