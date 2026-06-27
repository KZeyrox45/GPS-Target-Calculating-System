import React from 'react';
import { Link } from 'react-router-dom';

const FEATURES = [
  { icon: '📡', title: 'Real-Time Tracking', desc: 'Theo dõi mục tiêu di chuyển liên tục qua WebSocket 10 Hz', link: '/tracking' },
  { icon: '📐', title: 'Static Calculator', desc: 'Tính tọa độ mục tiêu tĩnh từ GPS + azimuth + khoảng cách (Phase 1)', link: '/calculator' },
  { icon: '📊', title: 'Algorithm Comparison', desc: 'So sánh Kalman Filter vs α-β Filter — RMSE theo quỹ đạo', link: '/comparison' },
];

const ALGORITHMS = [
  { name: 'Kalman Filter', color: 'var(--color-kalman)', desc: 'Bộ lọc tối ưu cho hệ tuyến tính. State: [E, N, vE, vN]. Tự động điều chỉnh trọng số bằng Kalman Gain.' },
  { name: 'α-β Filter', color: 'var(--color-alphabeta)', desc: 'Bộ lọc gain cố định (Benedict-Bordner). Đơn giản, tính toán thấp, phù hợp so sánh baseline.' },
  { name: 'Sensor Fusion', color: 'var(--color-truth)', desc: 'Kết hợp GPS + IMU (azimuth/elevation) + Laser rangefinder → tọa độ ENU với ước lượng σ.' },
];

export default function HomePage() {
  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '2rem' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
          🛰️ Real-Time Moving Target Tracking
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', maxWidth: '600px', margin: '0 auto' }}>
          Geolocation using Laser · IMU · GNSS Fusion — Đồ án Kỹ thuật Máy tính, Nhóm 072
        </p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1.5rem' }}>
          <Link to="/tracking" className="btn btn-primary btn-lg">▶ Bắt đầu mô phỏng</Link>
          <Link to="/calculator" className="btn btn-ghost btn-lg">📐 Calculator</Link>
        </div>
      </div>

      {/* Feature cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {FEATURES.map((f) => (
          <Link key={f.title} to={f.link} style={{ textDecoration: 'none' }}>
            <div className="card" style={{ transition: 'transform 200ms, box-shadow 200ms', cursor: 'pointer' }}
              onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-3px)'; e.currentTarget.style.boxShadow = 'var(--shadow-glow)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}
            >
              <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>{f.icon}</div>
              <h3 style={{ marginBottom: '0.4rem', color: 'var(--accent-primary)' }}>{f.title}</h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{f.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Algorithm overview */}
      <h2 style={{ marginBottom: '1rem', fontSize: '1rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Thuật toán
      </h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '2rem' }}>
        {ALGORITHMS.map((a) => (
          <div key={a.name} className="card">
            <div style={{ width: '32px', height: '4px', borderRadius: '2px', background: a.color, marginBottom: '0.75rem' }} />
            <h3 style={{ marginBottom: '0.4rem', color: a.color, fontSize: '0.95rem' }}>{a.name}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{a.desc}</p>
          </div>
        ))}
      </div>

      {/* Thesis info */}
      <div className="card" style={{ background: 'rgba(79,142,247,0.05)', borderColor: 'var(--border-active)' }}>
        <p className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          <strong style={{ color: 'var(--accent-primary)' }}>Đề tài (Giai đoạn 2):</strong>{' '}
          Real-Time Moving Target Tracking and Geolocation Using Laser-IMU-GNSS Fusion<br />
          <strong style={{ color: 'var(--accent-primary)' }}>Giảng viên hướng dẫn:</strong> TS. Võ Tuấn Bình &nbsp;|&nbsp;
          <strong style={{ color: 'var(--accent-primary)' }}>Nhóm:</strong> 072 — Huỳnh Gia Qui · Nguyễn Trung Hiếu · Bùi Nguyễn Thành Luân &nbsp;|&nbsp;
          <strong style={{ color: 'var(--accent-primary)' }}>Yêu cầu:</strong> RMSE &lt; 5m tại cự ly &lt; 1km
        </p>
      </div>
    </div>
  );
}
