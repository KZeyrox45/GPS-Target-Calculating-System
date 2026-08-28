import React, { useMemo } from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, ScatterController,
} from 'chart.js';
import { Scatter, Line } from 'react-chartjs-2';
import useTrackingStore from '../store/trackingStore';
import { cssVar } from '../utils/themeColors';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ScatterController, Title, Tooltip, Legend);

const DARK_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: { labels: { color: '#64748b', boxWidth: 12, font: { size: 12, family: "'JetBrains Mono', monospace" } } },
    tooltip: { backgroundColor: '#131922', borderColor: 'rgba(34,197,94,0.2)', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8' },
  },
  scales: {
    x: { ticks: { color: '#475569', font: { size: 11, family: "'JetBrains Mono', monospace" } }, grid: { color: 'rgba(34,197,94,0.04)' } },
    y: { ticks: { color: '#475569', font: { size: 11, family: "'JetBrains Mono', monospace" } }, grid: { color: 'rgba(34,197,94,0.04)' } },
  },
};

export default function ComparisonPage() {
  const { groundTruthHistory, kalmanHistory, alphaBetaHistory, metricsHistory } = useTrackingStore();

  const hasData = groundTruthHistory.length > 1;

  const summary = useMemo(() => {
    if (!hasData || metricsHistory.length === 0) return null;
    const skip = Math.floor(metricsHistory.length * 0.1);
    const tail = metricsHistory.slice(skip);
    const kfRmse  = Math.sqrt(tail.reduce((s, m) => s + m.kalman_rmse**2, 0) / tail.length);
    const abRmse  = Math.sqrt(tail.reduce((s, m) => s + m.alpha_beta_rmse**2, 0) / tail.length);
    const rawRmse = Math.sqrt(tail.reduce((s, m) => s + m.raw_error**2, 0) / tail.length);
    return { kfRmse, abRmse, rawRmse, steps: tail.length };
  }, [metricsHistory, hasData]);

  const scatterData = {
    datasets: [
      {
        label: 'TRUTH',
        data: groundTruthHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: cssVar('--color-truth', '#22c55e'), backgroundColor: 'transparent',
        pointRadius: 1.5, showLine: true, tension: 0.3,
      },
      {
        label: 'KF',
        data: kalmanHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: cssVar('--color-kalman', '#38bdf8'), backgroundColor: 'transparent',
        pointRadius: 1, showLine: true, tension: 0.3,
      },
      {
        label: 'AB',
        data: alphaBetaHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: cssVar('--color-alphabeta', '#a78bfa'), backgroundColor: 'transparent',
        pointRadius: 1, showLine: true, borderDash: [4, 4], tension: 0.3,
      },
    ],
  };

  const rmseLineData = {
    labels: metricsHistory.map((m) => m.step),
    datasets: [
      {
        label: 'KF RMSE',
        data: metricsHistory.map((m) => m.kalman_rmse),
        borderColor: cssVar('--color-kalman', '#38bdf8'), pointRadius: 0, borderWidth: 1.5, tension: 0.3,
      },
      {
        label: 'AB RMSE',
        data: metricsHistory.map((m) => m.alpha_beta_rmse),
        borderColor: cssVar('--color-alphabeta', '#a78bfa'), pointRadius: 0, borderWidth: 1.5, tension: 0.3,
        borderDash: [4, 4],
      },
    ],
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.5rem', marginBottom: '0.3rem', fontFamily: 'var(--font-mono)' }}>DELTA COMPARE</h1>
      <p className="text-sm text-muted font-mono" style={{ marginBottom: '1rem' }}>
        KF vs AB · Run a simulation on LIVE TRACK first
      </p>

      {!hasData ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 1rem' }}>
          <h2 style={{ color: 'var(--text-muted)', fontSize: '1.1rem', fontWeight: 500, fontFamily: 'var(--font-mono)' }}>NO TRACKING DATA</h2>
          <p className="text-sm text-muted font-mono" style={{ marginTop: '0.5rem' }}>
            Navigate to LIVE TRACK, run a sim, then return here
          </p>
        </div>
      ) : (
        <div className="flex-col gap-3">
          {summary && (
            <div className="card">
              <div className="card-header"><span className="card-title">RMSE SUMMARY (skip 10% init)</span></div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem' }}>METHOD</th>
                    <th style={{ textAlign: 'right', padding: '0.4rem 0.5rem' }}>RMSE</th>
                    <th style={{ textAlign: 'right', padding: '0.4rem 0.5rem' }}>SPEC</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: 'KF', rmse: summary.kfRmse, color: 'var(--color-kalman)' },
                    { name: 'AB', rmse: summary.abRmse, color: 'var(--color-alphabeta)' },
                    { name: 'RAW', rmse: summary.rawRmse, color: 'var(--color-raw)' },
                  ].map(({ name, rmse, color }) => (
                    <tr key={name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '0.45rem', color }}>{name}</td>
                      <td style={{ padding: '0.45rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color }}>{rmse.toFixed(3)}m</td>
                      <td style={{ padding: '0.45rem', textAlign: 'right' }}>
                        <span style={{ color: rmse < 5 ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                          {rmse < 5 ? 'PASS' : 'FAIL'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-sm text-muted font-mono" style={{ marginTop: '0.5rem' }}>{summary.steps} steps</p>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div className="card" style={{ height: '340px' }}>
              <div className="card-header"><span className="card-title">TRAJECTORY (ENU)</span></div>
              <div style={{ flex: 1, height: '290px' }}>
                <Scatter data={scatterData} options={{
                  ...DARK_OPTS,
                  scales: {
                    ...DARK_OPTS.scales,
                    x: { ...DARK_OPTS.scales.x, title: { display: true, text: 'E (m)', color: '#475569' } },
                    y: { ...DARK_OPTS.scales.y, title: { display: true, text: 'N (m)', color: '#475569' } },
                  },
                }} />
              </div>
            </div>

            <div className="card" style={{ height: '340px' }}>
              <div className="card-header"><span className="card-title">RMSE TIMELINE</span></div>
              <div style={{ flex: 1, height: '290px' }}>
                <Line data={rmseLineData} options={{
                  ...DARK_OPTS,
                  scales: {
                    ...DARK_OPTS.scales,
                    x: { ...DARK_OPTS.scales.x, title: { display: true, text: 'STEP', color: '#475569' } },
                    y: { ...DARK_OPTS.scales.y, title: { display: true, text: 'ERR (m)', color: '#475569' }, min: 0 },
                  },
                }} />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
