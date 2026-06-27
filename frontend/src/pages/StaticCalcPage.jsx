import React, { useState } from 'react';

const DEFAULT = {
  observer_lat: 10.762622, observer_lon: 106.660172, observer_alt: 10.0,
  azimuth_deg: 45.0, elevation_deg: 2.0, distance_m: 500.0,
};

function ResultRow({ label, value, color }) {
  return (
    <div className="flex justify-between items-center" style={{ padding: '0.35rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <span className="text-xs text-secondary">{label}</span>
      <span className="font-mono text-xs" style={{ color: color || 'var(--text-primary)' }}>{value}</span>
    </div>
  );
}

export default function StaticCalcPage() {
  const [form, setForm] = useState(DEFAULT);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const set = (k) => (e) => setForm((prev) => ({ ...prev, [k]: parseFloat(e.target.value) || e.target.value }));

  async function calculate() {
    setLoading(true); setError(null); setResult(null);
    try {
      const res = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(JSON.stringify(d.detail || 'Server error'));
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function decimalToDMS(decimal) {
    const sign = decimal < 0 ? -1 : 1;
    const abs = Math.abs(decimal);
    const deg = Math.floor(abs);
    const minFloat = (abs - deg) * 60;
    const min = Math.floor(minFloat);
    const sec = ((minFloat - min) * 60).toFixed(2);
    return `${sign * deg}° ${min}' ${sec}"`;
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '2rem', maxWidth: '900px', margin: '0 auto', width: '100%' }}>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '0.3rem' }}>📐 Static Target Calculator</h1>
      <p className="text-sm text-secondary" style={{ marginBottom: '2rem' }}>
        Phase 1 — Tính tọa độ mục tiêu tĩnh từ GPS + góc ngắm + khoảng cách laser
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Input form */}
        <div className="card">
          <div className="card-header"><span className="card-title">📥 Thông số đầu vào</span></div>

          <div className="flex-col gap-2">
            <p className="section-title">Vị trí quan sát viên</p>
            {[
              { key: 'observer_lat', label: 'Vĩ độ Lat (°)', step: '0.000001' },
              { key: 'observer_lon', label: 'Kinh độ Lon (°)', step: '0.000001' },
              { key: 'observer_alt', label: 'Cao độ Alt (m)', step: '0.1' },
            ].map(({ key, label, step }) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <input type="number" step={step} className="form-input" value={form[key]} onChange={set(key)} />
              </div>
            ))}

            <div className="divider" />
            <p className="section-title">Góc ngắm & khoảng cách</p>

            {[
              { key: 'azimuth_deg',   label: 'Azimuth (° từ Bắc)',  step: '0.1', min: 0,   max: 360 },
              { key: 'elevation_deg', label: 'Elevation (° so HB)', step: '0.1', min: -90,  max: 90 },
              { key: 'distance_m',    label: 'Khoảng cách (m)',      step: '1',   min: 1,   max: 100000 },
            ].map(({ key, label, step, min, max }) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <input type="number" step={step} min={min} max={max} className="form-input" value={form[key]} onChange={set(key)} />
              </div>
            ))}

            <button className="btn btn-primary btn-full" onClick={calculate} disabled={loading} style={{ marginTop: '0.5rem' }}>
              {loading ? <><span className="spinner" /> Đang tính…</> : '🎯 Tính toán'}
            </button>

            {error && (
              <div style={{ padding: '0.4rem', background: 'rgba(239,68,68,0.1)', borderRadius: '6px', fontSize: '0.78rem', color: 'var(--accent-danger)' }}>
                ⚠️ {error}
              </div>
            )}
          </div>
        </div>

        {/* Results */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">📍 Kết quả</span>
            {result && (
              <span className="badge badge-connected">✓ Computed</span>
            )}
          </div>

          {!result ? (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Nhập thông số và nhấn <strong>Tính toán</strong>
            </div>
          ) : (
            <div className="flex-col">
              <p className="section-title">Tọa độ mục tiêu</p>
              <ResultRow label="Vĩ độ (Decimal)" value={result.target_lat.toFixed(8) + '°'} color="var(--accent-primary)" />
              <ResultRow label="Vĩ độ (DMS)" value={decimalToDMS(result.target_lat)} color="var(--accent-primary)" />
              <ResultRow label="Kinh độ (Decimal)" value={result.target_lon.toFixed(8) + '°'} color="var(--accent-primary)" />
              <ResultRow label="Kinh độ (DMS)" value={decimalToDMS(result.target_lon)} color="var(--accent-primary)" />
              <ResultRow label="Cao độ" value={result.target_alt.toFixed(1) + ' m'} />

              <p className="section-title" style={{ marginTop: '0.75rem' }}>Kiểm tra</p>
              <ResultRow label="Khoảng cách ngược" value={result.distance_m.toFixed(1) + ' m'} />
              <ResultRow label="Bearing ngược" value={result.bearing_deg.toFixed(2) + '°'} />

              <p className="section-title" style={{ marginTop: '0.75rem' }}>Ước lượng sai số</p>
              <ResultRow label="Sai số tổng (RSS)" value={'± ' + result.estimated_error_m.toFixed(1) + ' m'} color="var(--accent-warning)" />

              <div style={{
                marginTop: '0.75rem', padding: '0.5rem',
                background: 'rgba(79,142,247,0.05)',
                border: '1px solid var(--border-active)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.75rem', color: 'var(--text-secondary)',
              }}>
                <strong style={{ color: 'var(--accent-primary)' }}>Công thức:</strong>{' '}
                Polar(az, el, r) → ENU → LLA (WGS-84 ECEF)
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
