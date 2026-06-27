import React, { useState } from 'react';
import useTrackingStore from '../../store/trackingStore';
import { useWebSocket } from '../../hooks/useWebSocket';

export default function SimulationPanel() {
  const { simConfig, setSimConfig, isRunning, setIsRunning, setSessionId, reset, clearHistory, clearMetrics, setSimulationEnded } = useTrackingStore();
  const { connect, disconnect } = useWebSocket();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleStart() {
    setLoading(true);
    setError(null);
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
      if (!res.ok) throw new Error(`Server error ${res.status}`);
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
        <span className="card-title">🎮 Simulation Control</span>
      </div>

      <div className="flex-col gap-2">
        {/* Observer position */}
        <p className="section-title">Vị trí quan sát viên</p>

        <div className="form-group">
          <label className="form-label">Vĩ độ (Lat)</label>
          <input
            type="number" step="0.000001" className="form-input"
            value={simConfig.observer_lat}
            onChange={(e) => setSimConfig({ observer_lat: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Kinh độ (Lon)</label>
          <input
            type="number" step="0.000001" className="form-input"
            value={simConfig.observer_lon}
            onChange={(e) => setSimConfig({ observer_lon: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        {/* Target configuration */}
        <p className="section-title">Loại mục tiêu</p>
        <div className="form-group">
          <select
            className="form-select"
            value={simConfig.target_type}
            onChange={(e) => setSimConfig({ target_type: e.target.value })}
            disabled={isRunning}
          >
            <option value="pedestrian">🚶 Người đi bộ</option>
            <option value="motorcycle">🏍️ Xe máy</option>
            <option value="drone">🚁 Drone</option>
          </select>
        </div>

        <div className="divider" />

        {/* Algorithm */}
        <p className="section-title">Thuật toán lọc</p>
        <div className="form-group">
          <select
            className="form-select"
            value={simConfig.algorithm}
            onChange={(e) => setSimConfig({ algorithm: e.target.value })}
            disabled={isRunning}
          >
            <option value="both">Kalman + α-β</option>
            <option value="kalman">Kalman Filter only</option>
            <option value="alpha_beta">α-β Filter only</option>
          </select>
        </div>

        {/* Alpha param for alpha-beta */}
        {simConfig.algorithm !== 'kalman' && (
          <div className="form-group">
            <label className="form-label">α value ({simConfig.alpha})</label>
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

        {/* Timing */}
        <p className="section-title">Thời gian</p>
        <div className="form-group">
          <label className="form-label">Thời lượng (giây)</label>
          <input
            type="number" min="5" max="600" step="5" className="form-input"
            value={simConfig.duration_s}
            onChange={(e) => setSimConfig({ duration_s: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        {/* Boundary radius */}
        <p className="section-title">Vùng mô phỏng</p>
        <div className="form-group">
          <label className="form-label">
            Bán kính ranh giới ({simConfig.boundary_radius_m} m)
          </label>
          <input
            type="number"
            min="100"
            max="1000"
            step="50"
            className="form-input"
            value={simConfig.boundary_radius_m}
            onChange={(e) => setSimConfig({ boundary_radius_m: parseFloat(e.target.value) })}
            disabled={isRunning}
          />
        </div>

        <div className="divider" />

        {/* Error message */}
        {error && (
          <p className="text-xs text-danger" style={{ padding: '0.3rem', background: 'rgba(239,68,68,0.1)', borderRadius: '6px' }}>
            ⚠️ {error}
          </p>
        )}

        {/* Start / Stop */}
        {isRunning ? (
          <button className="btn btn-danger btn-full" onClick={handleStop}>
            ⏹ Dừng lại
          </button>
        ) : (
          <button className="btn btn-primary btn-full" onClick={handleStart} disabled={loading}>
            {loading ? <><span className="spinner" /> Đang khởi động…</> : '▶ Bắt đầu mô phỏng'}
          </button>
        )}
      </div>
    </div>
  );
}
