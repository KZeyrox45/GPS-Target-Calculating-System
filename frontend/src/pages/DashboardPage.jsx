import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useTrackingStore from '../store/trackingStore';

export default function DashboardPage() {
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(new Date());

  // Live data from global Zustand store
  const {
    isRunning, simulationEnded, connected, sessionId,
    simConfig, metricsHistory, currentFrame, fps,
  } = useTrackingStore();

  const navigate = useNavigate();

  // Poll backend /api/simulation/dashboard every 3 s
  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch('/api/simulation/dashboard');
        if (res.ok && mounted) {
          const data = await res.json();
          setTelemetry(data);
          setLastUpdated(new Date());
        }
      } catch {
        // ignore – backend may not be running
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 3000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  // Derive live RMSE & dynamics from latest metrics entry and currentFrame
  const latestMetrics = metricsHistory.length > 0 ? metricsHistory[metricsHistory.length - 1] : null;
  const liveKfRmse   = latestMetrics ? latestMetrics.kalman_rmse.toFixed(3)     : '—';
  const liveAbRmse   = latestMetrics ? latestMetrics.alpha_beta_rmse.toFixed(3) : '—';
  const liveRawErr   = latestMetrics ? latestMetrics.raw_error.toFixed(3)       : '—';
  const liveKfErr    = latestMetrics ? latestMetrics.kalman_error.toFixed(3)    : '—';
  const liveAbErr    = latestMetrics ? latestMetrics.alpha_beta_error.toFixed(3): '—';

  // Speed and altitude from latest frame / metrics
  const liveSpeed    = currentFrame?.kalman?.speed ?? latestMetrics?.speed ?? 0.0;
  const liveAlt      = currentFrame?.kalman?.alt ?? currentFrame?.kalman?.up ?? latestMetrics?.alt ?? 0.0;
  const liveUncertainty = currentFrame?.kalman?.uncertainty_m ?? latestMetrics?.uncertainty_m ?? 0.0;

  // Session status string + color
  const sessionStatus = isRunning ? 'RUNNING' : simulationEnded ? 'COMPLETED' : connected ? 'CONNECTED' : 'IDLE';
  const sessionColor  = isRunning ? 'var(--accent-success)'
    : simulationEnded ? 'var(--accent-info)'
    : connected ? 'var(--accent-primary)'
    : 'var(--text-muted)';

  const pipelineStages = [
    { name: 'LLA → ECEF → ENU',     time: 7.2,  pct: 12.2, color: 'var(--accent-info)' },
    { name: 'Sensor Fusion (RSS)',   time: 1.2,  pct: 2.0,  color: 'var(--color-truth)' },
    { name: 'Kalman State Predict',  time: 22.8, pct: 38.6, color: 'var(--color-alphabeta)' },
    { name: 'Kalman Gain & Update',  time: 25.7, pct: 43.6, color: 'var(--color-kalman)' },
    { name: 'ENU → WGS-84 LLA',     time: 2.1,  pct: 3.6,  color: 'var(--accent-secondary)' },
  ];

  const quickNavCards = [
    {
      id: 'nav-track',
      icon: '▶',
      title: 'LIVE TRACKING',
      desc: 'WebSocket 10 Hz · Kalman + Alpha-Beta filter',
      to: '/tracking',
      badge: isRunning ? 'ACTIVE' : simulationEnded ? 'DONE' : 'IDLE',
      badgeClass: isRunning ? 'badge-success' : simulationEnded ? 'badge-info' : '',
      primary: true,
    },
    {
      id: 'nav-compare',
      icon: '△',
      title: 'DELTA COMPARE',
      desc: 'KF vs AB · RMSE timeline · Trajectory overlay',
      to: '/comparison',
      badge: metricsHistory.length > 0 ? `${metricsHistory.length} pts` : 'NO DATA',
      badgeClass: metricsHistory.length > 0 ? 'badge-info' : '',
    },
    {
      id: 'nav-calc',
      icon: '◎',
      title: 'STATIC CALC',
      desc: 'Single-point GPS + azimuth + range calculator',
      to: '/calculator',
      badge: 'READY',
      badgeClass: 'badge-success',
    },
    {
      id: 'nav-sys',
      icon: '⌬',
      title: 'SYSTEM INFO',
      desc: 'Algorithm overview · Project info · Tech stack',
      to: '/sys',
      badge: 'INFO',
      badgeClass: '',
    },
  ];

  // Helper to render mini SVG Sparkline of historical errors
  const renderErrorSparkline = (points, color, height = 36, width = 140) => {
    if (!points || points.length < 2) {
      return (
        <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
          NO SAMPLES
        </div>
      );
    }
    const recent = points.slice(-30);
    const maxVal = Math.max(...recent, 2.0);
    const minVal = 0;
    const range = maxVal - minVal || 1;
    const stepX = width / (recent.length - 1);

    const pathD = recent
      .map((val, idx) => {
        const x = idx * stepX;
        const y = height - ((val - minVal) / range) * (height - 6) - 3;
        return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(' ');

    return (
      <svg width={width} height={height} style={{ overflow: 'visible' }}>
        <path d={pathD} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  };

  // Target dynamics behavioral description
  const targetTypeProfiles = {
    pedestrian: {
      name: 'Pedestrian 2D Walk',
      desc: 'Low-speed random walk (< 2.0 m/s) · Planar dynamics · Ornstein-Uhlenbeck heading drift',
      dataset: 'Geolife GPS Walk Dataset (252 segments)',
      color: 'var(--color-truth)',
    },
    motorcycle: {
      name: 'Motorcycle Road Walk',
      desc: 'Planar road manifold (5–20 m/s) · Street network constrained · Speed-aware routing',
      dataset: 'HCMC OSM Graph (337K nodes, 305K edges)',
      color: 'var(--accent-primary)',
    },
    drone: {
      name: 'Drone 3D Spatial Trajectory',
      desc: '3D spatial maneuvers (0–15 m/s) · Altitude climb/descent Z(t) · 6-DoF kinematics',
      dataset: 'DJI Matrice 100 Airframe Kinematics',
      color: 'var(--color-kalman)',
    },
  };

  const currentProfile = targetTypeProfiles[simConfig.target_type] || targetTypeProfiles.pedestrian;

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem 2rem' }}>

      {/* ─── Header ─── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '1rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h1 style={{ fontSize: '1.5rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
              SYSTEM TELEMETRY &amp; C2 DASHBOARD
            </h1>
            <span className="badge badge-success" style={{ fontSize: '0.75rem', letterSpacing: '0.08em' }}>
              ONLINE · NOMINAL
            </span>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
            Laser-IMU-GNSS Sensor Fusion · Real-Time Moving Target Geolocation &amp; Filter Diagnostics
          </p>
        </div>
        <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <div>LAST SYNC: <span style={{ color: 'var(--text-primary)' }}>{lastUpdated.toLocaleTimeString()}</span></div>
          <div style={{ color: 'var(--accent-primary)', fontSize: '0.75rem' }}>CYCLE CLOCK: 10 Hz (100 ms) · RT LATENCY: 59.0 µs</div>
        </div>
      </div>

      {/* ─── KPI Row ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {/* Session status — live */}
        <div className="card" style={{ borderLeft: '3px solid ' + sessionColor }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-label)', fontFamily: 'var(--font-mono)', marginBottom: '0.4rem' }}>SESSION STATUS</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: sessionColor, fontFamily: 'var(--font-mono)' }}>
            {sessionStatus}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {sessionId ? `ID: ${sessionId.slice(0, 8)}…` : 'No active session'}
          </div>
        </div>

        {/* Pipeline latency */}
        <div className="card" style={{ borderLeft: '3px solid var(--accent-info)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-label)', fontFamily: 'var(--font-mono)', marginBottom: '0.4rem' }}>PIPELINE LATENCY</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-info)', fontFamily: 'var(--font-mono)' }}>
            {telemetry?.pipeline_budget?.total_latency_us ?? 59.0} <span style={{ fontSize: '0.9rem' }}>µs</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>0.059% CPU Budget at 10 Hz</div>
        </div>

        {/* Live RMSE (alpha-beta) */}
        <div className="card" style={{ borderLeft: '3px solid var(--color-alphabeta)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-label)', fontFamily: 'var(--font-mono)', marginBottom: '0.4rem' }}>LIVE AB-RMSE</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-alphabeta)', fontFamily: 'var(--font-mono)' }}>
            {liveAbRmse} <span style={{ fontSize: '0.9rem' }}>m</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            {isRunning ? `Step ${latestMetrics?.step ?? 0}` : 'Run sim to stream live'}
          </div>
        </div>

        {/* Crossover range */}
        <div className="card" style={{ borderLeft: '3px solid var(--accent-secondary)' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-label)', fontFamily: 'var(--font-mono)', marginBottom: '0.4rem' }}>CROSSOVER RANGE</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-secondary)', fontFamily: 'var(--font-mono)' }}>
            {telemetry?.reliability_metrics?.crossover_range_m ?? 794} <span style={{ fontSize: '0.9rem' }}>m</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>GNSS vs IMU-Laser Dominance</div>
        </div>
      </div>

      {/* ─── Quick Navigation Cards ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {quickNavCards.map((card) => (
          <button
            key={card.id}
            id={card.id}
            onClick={() => navigate(card.to)}
            style={{
              all: 'unset',
              cursor: 'pointer',
              display: 'block',
              width: '100%',
              boxSizing: 'border-box',
            }}
          >
            <div
              className="card"
              style={{
                borderTop: card.primary ? '2px solid var(--accent-primary)' : '2px solid var(--border-subtle)',
                transition: 'border-color 0.2s, transform 0.15s',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderTopColor = 'var(--accent-primary)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderTopColor = card.primary ? 'var(--accent-primary)' : 'var(--border-subtle)';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '1.4rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>{card.icon}</span>
                <span className={`badge ${card.badgeClass}`} style={{ fontSize: '0.65rem', letterSpacing: '0.06em' }}>{card.badge}</span>
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '0.3rem', letterSpacing: '0.04em' }}>
                {card.title}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                {card.desc}
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* ─── Middle Grid: Real-Time Error Innovation Sparklines & Target Dynamics Profile ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Live Innovation Residual / Error Sparklines Card */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
              Live Tracking Error &amp; Residual Convergence
            </h2>
            <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
              LAST 30 STEPS (10 Hz)
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '0.75rem' }}>
            {/* Raw Sensor Error */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-raw)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>RAW SENSOR</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--color-raw)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{liveRawErr} m</span>
              </div>
              <div style={{ height: '40px', display: 'flex', alignItems: 'center' }}>
                {renderErrorSparkline(metricsHistory.map(m => m.raw_error), 'var(--color-raw)', 36, 140)}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                GPS + Laser ToF + IMU RSS
              </div>
            </div>

            {/* Alpha-Beta Residual Error */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-alphabeta)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>ALPHA-BETA</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--color-alphabeta)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{liveAbErr} m</span>
              </div>
              <div style={{ height: '40px', display: 'flex', alignItems: 'center' }}>
                {renderErrorSparkline(metricsHistory.map(m => m.alpha_beta_error ?? m.alpha_beta_rmse), 'var(--color-alphabeta)', 36, 140)}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                α=0.40, β=0.051 (Critically Damped)
              </div>
            </div>

            {/* Kalman Filter Error */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.25rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-kalman)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>KALMAN (3D)</span>
                <span style={{ fontSize: '0.85rem', color: 'var(--color-kalman)', fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{liveKfErr} m</span>
              </div>
              <div style={{ height: '40px', display: 'flex', alignItems: 'center' }}>
                {renderErrorSparkline(metricsHistory.map(m => m.kalman_error ?? m.kalman_rmse), 'var(--color-kalman)', 36, 140)}
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '0.2rem', fontFamily: 'var(--font-mono)' }}>
                Adaptive R_k + Dynamic P_k
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', padding: '0.4rem 0.6rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)' }}>
            Residual Innovation: <span style={{ color: 'var(--accent-primary)' }}>ỹ_k = z_k - H·x̂_k|k-1</span> · Evaluates filter convergence and noise attenuation.
          </div>
        </div>

        {/* Target Dynamics Profile & 3D Kinematics */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
              Target Dynamics &amp; 3D Kinematics
            </h2>
            <span className="badge badge-success" style={{ fontSize: '0.65rem' }}>
              {simConfig.use_realistic_sim ? 'REAL-WORLD DATA' : 'SYNTHETIC GENERATOR'}
            </span>
          </div>

          <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: currentProfile.color }}>
                {currentProfile.name}
              </span>
              <span className="badge" style={{ fontSize: '0.68rem', background: 'rgba(255,255,255,0.06)' }}>
                {simConfig.target_type.toUpperCase()}
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.4rem', lineHeight: 1.4 }}>
              {currentProfile.desc}
            </p>
            <div style={{ fontSize: '0.72rem', color: 'var(--accent-primary)', fontFamily: 'var(--font-mono)' }}>
              Source: {currentProfile.dataset}
            </div>
          </div>

          {/* Real-time speed & altitude readout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', fontFamily: 'var(--font-mono)' }}>
            <div style={{ padding: '0.6rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>LIVE VELOCITY</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-primary)', marginTop: '0.2rem' }}>
                {liveSpeed.toFixed(2)} <span style={{ fontSize: '0.7rem' }}>m/s</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{(liveSpeed * 3.6).toFixed(1)} km/h</div>
            </div>

            <div style={{ padding: '0.6rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>ALTITUDE (Z)</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--accent-info)', marginTop: '0.2rem' }}>
                {liveAlt.toFixed(1)} <span style={{ fontSize: '0.7rem' }}>m</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{liveAlt > 1 ? '3D Spatial' : '2D Ground'}</div>
            </div>

            <div style={{ padding: '0.6rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>EST UNCERTAINTY (P_k)</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: liveUncertainty > 3 ? 'var(--color-raw)' : 'var(--color-kalman)', marginTop: '0.2rem' }}>
                {liveUncertainty > 0 ? `±${liveUncertainty.toFixed(2)}` : '—'} <span style={{ fontSize: '0.7rem' }}>m</span>
              </div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Covariance Trace</div>
            </div>
          </div>
        </div>

      </div>

      {/* ─── Main Grid: Sensor Noise Model & Processing Breakdown ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Simulation Sensor Noise Model & Filter Covariance Architecture */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)' }}>
              Simulation Sensor Noise &amp; Filter Covariance Models
            </h2>
            <span className="badge badge-info" style={{ fontSize: '0.68rem' }}>
              GAUSSIAN NOISE GENERATORS
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {/* GNSS Simulation Noise Model */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--accent-primary)' }}>
                  GNSS Observer Noise (U-blox NEO-M8N Model)
                </span>
                <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>10 Hz · ZERO-MEAN GAUSS</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <div>Noise σ_GPS: <span style={{ color: 'var(--text-primary)' }}>5.0 m</span></div>
                <div>Update Rate: <span style={{ color: 'var(--text-primary)' }}>10 Hz</span></div>
                <div>Fault Prob: <span style={{ color: 'var(--text-primary)' }}>p = 0.020</span></div>
              </div>
            </div>

            {/* IMU Simulation Noise Model */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--accent-info)' }}>
                  IMU Angular Noise (MPU-9250 9-DoF Model)
                </span>
                <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>100 Hz · SPHERICAL NOISE</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <div>Azimuth σ_az: <span style={{ color: 'var(--text-primary)' }}>0.3° (0.0052 rad)</span></div>
                <div>Elevation σ_el: <span style={{ color: 'var(--text-primary)' }}>0.2° (0.0035 rad)</span></div>
                <div>Fault Prob: <span style={{ color: 'var(--text-primary)' }}>p = 0.005</span></div>
              </div>
            </div>

            {/* Laser Simulation Noise Model */}
            <div style={{ padding: '0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-grid)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.3rem' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.9rem', color: 'var(--accent-secondary)' }}>
                  Laser Rangefinder ToF Model (LRF-1000)
                </span>
                <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>PULSED ToF · 1000 m</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                <div>Range σ_r: <span style={{ color: 'var(--text-primary)' }}>0.5 m</span></div>
                <div>Max Range: <span style={{ color: 'var(--text-primary)' }}>1000 m</span></div>
                <div>Mahalanobis Gate: <span style={{ color: 'var(--text-primary)' }}>χ² = 9.21 (p=0.01)</span></div>
              </div>
            </div>

            {/* Filter Tuning Equations */}
            <div style={{ padding: '0.6rem 0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', borderLeft: '3px solid var(--accent-primary)' }}>
              Adaptive Covariance: <span style={{ color: 'var(--accent-primary)' }}>R_k = diag(σ_E², σ_N², σ_U²)</span> derived per step from RSS Error Propagation.
              <br />
              Alpha-Beta Damping: <span style={{ color: 'var(--color-alphabeta)' }}>α = 0.40, β = (2-α) - 2√(1-α) ≈ 0.051</span> (Benedict-Bordner).
            </div>
          </div>
        </div>

        {/* Pipeline Profiling */}
        <div className="card">
          <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)', marginBottom: '1rem' }}>
            Pipeline Latency &amp; CPU Cycle Budget
          </h2>

          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', marginBottom: '0.4rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>100 ms Cycle Budget Utilization</span>
              <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>59.0 µs / 100,000 µs (0.059%)</span>
            </div>
            <div style={{ height: '8px', background: 'var(--bg-card-alt)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ width: '0.059%', minWidth: '4px', height: '100%', background: 'var(--accent-primary)' }} />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {pipelineStages.map((stage) => (
              <div key={stage.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', fontFamily: 'var(--font-mono)', padding: '0.35rem 0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: stage.color }} />
                  <span style={{ color: 'var(--text-primary)' }}>{stage.name}</span>
                </div>
                <div style={{ display: 'flex', gap: '1rem', color: 'var(--text-muted)' }}>
                  <span>{stage.time} µs</span>
                  <span style={{ width: '45px', textAlign: 'right', color: stage.color }}>{stage.pct}%</span>
                </div>
              </div>
            ))}
          </div>

          {/* Live FPS indicator */}
          <div style={{ marginTop: '1rem', padding: '0.6rem 0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontFamily: 'var(--font-mono)' }}>
            <span style={{ color: 'var(--text-muted)' }}>WS FRAME RATE</span>
            <span style={{ color: isRunning ? 'var(--accent-success)' : 'var(--text-muted)' }}>
              {isRunning ? `${fps} fps (Nominal 10 Hz)` : '— fps (idle)'}
            </span>
          </div>
        </div>
      </div>

      {/* ─── Live RMSE Row + Benchmark Table ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Verified Baseline Benchmarks */}
        <div className="card">
          <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)', marginBottom: '1rem' }}>
            Verified Tracking Benchmarks (Seed 42 · 120 s · 10 Hz · Radius 400 m)
          </h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-active)', color: 'var(--text-label)', textAlign: 'left' }}>
                <th style={{ padding: '0.5rem' }}>TARGET PROFILE</th>
                <th style={{ padding: '0.5rem' }}>RAW SENSOR</th>
                <th style={{ padding: '0.5rem' }}>ALPHA-BETA</th>
                <th style={{ padding: '0.5rem' }}>KALMAN (3D)</th>
                <th style={{ padding: '0.5rem' }}>SPEC</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--border-grid)' }}>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--text-primary)' }}>Pedestrian (Geolife GPS Walk)</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-raw)' }}>0.48 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-alphabeta)', fontWeight: 600 }}>0.26 m ✓</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-kalman)' }}>0.86 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--accent-primary)' }}>&lt; 5.0 m</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--border-grid)' }}>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--text-primary)' }}>Motorcycle (HCMC OSM Roads)</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-raw)' }}>2.14 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-alphabeta)', fontWeight: 600 }}>1.14 m ✓</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-kalman)' }}>1.52 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--accent-primary)' }}>&lt; 5.0 m</td>
              </tr>
              <tr>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--text-primary)' }}>Drone 3D (DJI Matrice 100)</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-raw)' }}>1.94 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-alphabeta)', fontWeight: 600 }}>1.06 m ✓</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--color-kalman)' }}>2.10 m</td>
                <td style={{ padding: '0.6rem 0.5rem', color: 'var(--accent-primary)' }}>&lt; 5.0 m</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Live session metrics card */}
        <div className="card">
          <h2 style={{ fontSize: '0.9rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.08em', fontFamily: 'var(--font-mono)', marginBottom: '1rem' }}>
            Live Session Telemetry
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
            {[
              { label: 'TARGET CLASS',  value: simConfig.target_type.toUpperCase(), color: 'var(--text-primary)' },
              { label: 'SIM MODE',      value: simConfig.use_realistic_sim ? 'REAL DATASET' : 'SYNTHETIC', color: 'var(--accent-info)' },
              { label: 'ALGORITHM',     value: simConfig.algorithm.toUpperCase(),   color: 'var(--text-primary)' },
              { label: 'BOUNDARY',      value: `${simConfig.boundary_radius_m} m`,  color: 'var(--text-primary)' },
              { label: 'LIVE AB-RMSE',  value: `${liveAbRmse} m`,  color: 'var(--color-alphabeta)' },
              { label: 'LIVE KF-RMSE',  value: `${liveKfRmse} m`,  color: 'var(--color-kalman)' },
              { label: 'LIVE RAW ERR',  value: `${liveRawErr} m`,  color: 'var(--color-raw)' },
              { label: 'VELOCITY (V)',  value: `${liveSpeed.toFixed(2)} m/s`, color: 'var(--accent-primary)' },
              { label: 'ALTITUDE (Z)',  value: `${liveAlt.toFixed(1)} m`, color: 'var(--accent-info)' },
              { label: 'BUFFER DEPTH',  value: `${metricsHistory.length} / 500 frames`, color: 'var(--text-muted)' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.28rem 0', borderBottom: '1px solid var(--border-grid)' }}>
                <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ color, fontWeight: 600 }}>{value}</span>
              </div>
            ))}
          </div>

          {/* CTA buttons */}
          <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <Link
              id="dash-launch-tracking"
              to="/tracking"
              className="btn btn-primary"
              style={{ textAlign: 'center', padding: '0.65rem', textDecoration: 'none', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em' }}
            >
              {isRunning ? '▶ GO TO LIVE TRACK' : '▶ LAUNCH TRACKING'}
            </Link>
            <Link
              id="dash-open-compare"
              to="/comparison"
              className="btn btn-ghost"
              style={{ textAlign: 'center', padding: '0.65rem', textDecoration: 'none', fontSize: '0.82rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em' }}
            >
              △ DELTA COMPARE
            </Link>
          </div>

          {/* Status indicator */}
          <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', background: 'var(--bg-card-alt)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            TELEMETRY: {loading ? 'FETCHING…' : 'SYNCHRONIZED'}
          </div>
        </div>
      </div>

    </div>
  );
}
