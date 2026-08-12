import React, { useState } from 'react';

const DEFAULT = {
  observer_lat: 10.762622, observer_lon: 106.660172, observer_alt: 10.0,
  azimuth_deg: 45.0, elevation_deg: 2.0, distance_m: 500.0,
};

function ResultRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.3rem 0', borderBottom: '1px solid var(--border-subtle)' }}>
      <span className="text-sm text-muted font-mono">{label}</span>
      <span className="font-mono text-sm" style={{ color: color || 'var(--text-primary)' }}>{value}</span>
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
    return `${sign * deg}deg ${min}' ${sec}"`;
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', maxWidth: '800px', margin: '0 auto', width: '100%' }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.3rem', fontFamily: 'var(--font-mono)' }}>STATIC CALC</h1>
      <p className="text-sm text-muted font-mono" style={{ marginBottom: '1.5rem' }}>
        Compute static target position from GPS + azimuth + laser range
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="card">
          <div className="card-header"><span className="card-title">INPUT</span></div>

          <div className="flex-col gap-2">
            <p className="section-title">Observer</p>
            {[
              { key: 'observer_lat', label: 'LAT (deg)', step: '0.000001' },
              { key: 'observer_lon', label: 'LON (deg)', step: '0.000001' },
              { key: 'observer_alt', label: 'ALT (m)', step: '0.1' },
            ].map(({ key, label, step }) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <input type="number" step={step} className="form-input" value={form[key]} onChange={set(key)} />
              </div>
            ))}

            <div className="divider" />
            <p className="section-title">Measurement</p>

            {[
              { key: 'azimuth_deg',   label: 'AZ (deg)',  step: '0.1', min: 0,   max: 360 },
              { key: 'elevation_deg', label: 'EL (deg)',  step: '0.1', min: -90,  max: 90 },
              { key: 'distance_m',    label: 'RNG (m)',   step: '1',   min: 1,   max: 100000 },
            ].map(({ key, label, step, min, max }) => (
              <div className="form-group" key={key}>
                <label className="form-label">{label}</label>
                <input type="number" step={step} min={min} max={max} className="form-input" value={form[key]} onChange={set(key)} />
              </div>
            ))}

            <button className="btn btn-primary btn-full" onClick={calculate} disabled={loading} style={{ marginTop: '0.5rem' }}>
              {loading ? <><span className="spinner" /> CALC...</> : 'CALC'}
            </button>

            {error && (
              <div style={{ padding: '0.4rem', background: 'rgba(239,68,68,0.08)', borderRadius: '2px', fontSize: '0.85rem', color: 'var(--accent-danger)' }}>
                ERR: {error}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">OUTPUT</span>
            {result && <span className="badge badge-connected">DONE</span>}
          </div>

          {!result ? (
            <div style={{ textAlign: 'center', padding: '2rem 0.5rem', color: 'var(--text-muted)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              SET INPUT AND PRESS CALC
            </div>
          ) : (
            <div className="flex-col">
              <p className="section-title">TARGET COORD</p>
              <ResultRow label="LAT DEC" value={result.target_lat.toFixed(8)} color="var(--accent-primary)" />
              <ResultRow label="LAT DMS" value={decimalToDMS(result.target_lat)} color="var(--accent-primary)" />
              <ResultRow label="LON DEC" value={result.target_lon.toFixed(8)} color="var(--accent-primary)" />
              <ResultRow label="LON DMS" value={decimalToDMS(result.target_lon)} color="var(--accent-primary)" />
              <ResultRow label="ALT" value={result.target_alt.toFixed(1) + 'm'} />

              <p className="section-title" style={{ marginTop: '0.5rem' }}>VERIFICATION</p>
              <ResultRow label="RANGE" value={result.distance_m.toFixed(1) + 'm'} />
              <ResultRow label="BEARING" value={result.bearing_deg.toFixed(2) + 'deg'} />

              <p className="section-title" style={{ marginTop: '0.5rem' }}>ERROR EST</p>
              <ResultRow label="RSS" value={'+/- ' + result.estimated_error_m.toFixed(1) + 'm'} color="var(--accent-warning)" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
