import React from 'react';
import { Link } from 'react-router-dom';

const FEATURES = [
  { icon: '#', title: 'TELEMETRY DASH', desc: 'Hardware diagnostics, 59µs pipeline latency budget & MTBF metrics', link: '/dashboard' },
  { icon: '+', title: 'LIVE TRACK', desc: 'Real-time target tracking via WebSocket at 10 Hz update rate', link: '/tracking' },
  { icon: '=', title: 'STATIC CALC', desc: 'Compute static target coordinates from GPS + azimuth + range', link: '/calculator' },
  { icon: '~', title: 'DELTA COMPARE', desc: 'Compare Kalman Filter vs alpha-beta Filter · RMSE across trajectory', link: '/comparison' },
];

const ALGORITHMS = [
  { name: 'Kalman Filter', color: 'var(--color-kalman)', desc: 'Optimal linear estimator. State: [E, N, vE, vN]. Auto-weights measurements via Kalman Gain for minimal RMSE.' },
  { name: 'Alpha-Beta Filter', color: 'var(--color-alphabeta)', desc: 'Fixed-gain filter (Benedict-Bordner critically damped). Low-computational baseline for comparison.' },
  { name: 'Sensor Fusion', color: 'var(--color-truth)', desc: 'Combines GPS + IMU (azimuth/elevation) + Laser rangefinder into ENU coordinates with sigma estimation.' },
];

export default function HomePage() {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '2rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}>
          GPS-TT C2 SYSTEM
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '1rem', fontFamily: 'var(--font-mono)', maxWidth: '600px', margin: '0 auto' }}>
          Laser-IMU-GNSS Sensor Fusion · Moving Target Geolocation
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1.25rem' }}>
          <Link to="/tracking" className="btn btn-primary btn-lg">ENGAGE</Link>
          <Link to="/calculator" className="btn btn-ghost btn-lg">CALC</Link>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {FEATURES.map((f) => (
          <Link key={f.title} to={f.link} style={{ textDecoration: 'none' }}>
            <div className="card" style={{ cursor: 'pointer' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.5rem', color: 'var(--accent-primary)', marginBottom: '0.6rem' }}>{f.icon}</div>
              <h3 style={{ marginBottom: '0.4rem', color: 'var(--text-primary)', fontSize: '1rem', fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}>{f.title}</h3>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>{f.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      <h2 style={{ marginBottom: '1rem', fontSize: '0.85rem', color: 'var(--text-label)', textTransform: 'uppercase', letterSpacing: '0.1em', fontFamily: 'var(--font-mono)' }}>
        Algorithms
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {ALGORITHMS.map((a) => (
          <div key={a.name} className="card">
            <div style={{ width: '32px', height: '3px', background: a.color, marginBottom: '0.65rem', borderRadius: '2px' }} />
            <h3 style={{ marginBottom: '0.4rem', color: a.color, fontSize: '0.95rem', fontFamily: 'var(--font-mono)' }}>{a.name}</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>{a.desc}</p>
          </div>
        ))}
      </div>

      <div className="card" style={{ borderColor: 'var(--border-active)' }}>
        <p className="text-sm font-mono" style={{ color: 'var(--text-muted)', lineHeight: 1.8 }}>
          <strong style={{ color: 'var(--accent-primary)' }}>PROJECT:</strong>{' '}
          Real-Time Moving Target Tracking via Laser-IMU-GNSS Fusion<br />
          <strong style={{ color: 'var(--accent-primary)' }}>ADVISOR:</strong> TS. Vo Tuan Binh &nbsp;|&nbsp;
          <strong style={{ color: 'var(--accent-primary)' }}>TEAM:</strong> 024 &nbsp;|&nbsp;
          <strong style={{ color: 'var(--accent-primary)' }}>SPEC:</strong> RMSE &lt; 5m at range &lt; 1km
        </p>
      </div>
    </div>
  );
}
