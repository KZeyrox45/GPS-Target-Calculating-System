import React, { useMemo } from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, ScatterController,
} from 'chart.js';
import { Scatter, Line } from 'react-chartjs-2';
import useTrackingStore from '../store/trackingStore';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ScatterController, Title, Tooltip, Legend);

const DARK_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: { labels: { color: '#8898b3', boxWidth: 12, font: { size: 11 } } },
    tooltip: { backgroundColor: '#141b2d', borderColor: 'rgba(79,142,247,0.3)', borderWidth: 1, titleColor: '#e8edf7', bodyColor: '#8898b3' },
  },
  scales: {
    x: { ticks: { color: '#4a5a7a', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
    y: { ticks: { color: '#4a5a7a', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
  },
};

export default function ComparisonPage() {
  const { groundTruthHistory, kalmanHistory, alphaBetaHistory, metricsHistory } = useTrackingStore();

  const hasData = groundTruthHistory.length > 1;

  // RMSE summary
  const summary = useMemo(() => {
    if (!hasData || metricsHistory.length === 0) return null;
    const skip = Math.floor(metricsHistory.length * 0.1); // ignore first 10%
    const tail = metricsHistory.slice(skip);
    const kfRmse  = Math.sqrt(tail.reduce((s, m) => s + m.kalman_rmse**2, 0) / tail.length);
    const abRmse  = Math.sqrt(tail.reduce((s, m) => s + m.alpha_beta_rmse**2, 0) / tail.length);
    const rawRmse = Math.sqrt(tail.reduce((s, m) => s + m.raw_error**2, 0) / tail.length);
    return { kfRmse, abRmse, rawRmse, steps: tail.length };
  }, [metricsHistory, hasData]);

  // ENU trajectory scatter data
  const scatterData = {
    datasets: [
      {
        label: 'Ground Truth',
        data: groundTruthHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: 'var(--color-truth)', backgroundColor: 'transparent',
        pointRadius: 1.5, showLine: true, tension: 0.3,
      },
      {
        label: 'Kalman Filter',
        data: kalmanHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: 'var(--color-kalman)', backgroundColor: 'transparent',
        pointRadius: 1, showLine: true, tension: 0.3,
      },
      {
        label: 'α-β Filter',
        data: alphaBetaHistory.map((p) => ({
          x: (p.lon - (groundTruthHistory[0]?.lon || 0)) * 111320 * Math.cos(p.lat * Math.PI / 180),
          y: (p.lat - (groundTruthHistory[0]?.lat || 0)) * 111320,
        })),
        borderColor: 'var(--color-alphabeta)', backgroundColor: 'transparent',
        pointRadius: 1, showLine: true, borderDash: [4, 4], tension: 0.3,
      },
    ],
  };

  // RMSE time series
  const rmseLineData = {
    labels: metricsHistory.map((m) => m.step),
    datasets: [
      {
        label: 'Kalman RMSE (m)',
        data: metricsHistory.map((m) => m.kalman_rmse),
        borderColor: 'var(--color-kalman)', pointRadius: 0, borderWidth: 2, tension: 0.3,
      },
      {
        label: 'α-β RMSE (m)',
        data: metricsHistory.map((m) => m.alpha_beta_rmse),
        borderColor: 'var(--color-alphabeta)', pointRadius: 0, borderWidth: 2, tension: 0.3,
        borderDash: [5, 5],
      },
    ],
  };

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
      <h1 style={{ fontSize: '1.4rem', marginBottom: '0.3rem' }}>📊 So sánh thuật toán</h1>
      <p className="text-sm text-secondary" style={{ marginBottom: '1.5rem' }}>
        Kalman Filter vs α-β Filter — chạy simulation trên trang Live Tracking trước.
      </p>

      {!hasData ? (
        <div className="card" style={{ textAlign: 'center', padding: '4rem 1rem' }}>
          <p style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>📡</p>
          <h2 style={{ color: 'var(--text-secondary)', fontSize: '1rem', fontWeight: 500 }}>Chưa có dữ liệu tracking</h2>
          <p className="text-sm text-muted" style={{ marginTop: '0.5rem' }}>
            Vào trang <strong style={{ color: 'var(--accent-primary)' }}>Live Tracking</strong>, chạy simulation, rồi quay lại đây để so sánh.
          </p>
        </div>
      ) : (
        <div className="flex-col gap-3">
          {/* Summary table */}
          {summary && (
            <div className="card">
              <div className="card-header"><span className="card-title">📋 Bảng tổng kết RMSE (bỏ qua 10% đầu)</span></div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-subtle)' }}>
                    <th style={{ textAlign: 'left', padding: '0.4rem 0.5rem' }}>Phương pháp</th>
                    <th style={{ textAlign: 'right', padding: '0.4rem 0.5rem' }}>RMSE (m)</th>
                    <th style={{ textAlign: 'right', padding: '0.4rem 0.5rem' }}>Thesis Spec</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: 'Kalman Filter', rmse: summary.kfRmse, color: 'var(--color-kalman)' },
                    { name: 'α-β Filter',    rmse: summary.abRmse, color: 'var(--color-alphabeta)' },
                    { name: 'Raw (no filter)', rmse: summary.rawRmse, color: 'var(--color-raw)' },
                  ].map(({ name, rmse, color }) => (
                    <tr key={name} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '0.5rem', color }}>{name}</td>
                      <td style={{ padding: '0.5rem', textAlign: 'right', fontFamily: 'var(--font-mono)', color }}>{rmse.toFixed(3)} m</td>
                      <td style={{ padding: '0.5rem', textAlign: 'right' }}>
                        <span style={{ color: rmse < 5 ? 'var(--accent-success)' : 'var(--accent-danger)', fontSize: '0.8rem' }}>
                          {rmse < 5 ? '✅ Pass' : '❌ Fail'} (&lt;5m)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-muted" style={{ marginTop: '0.5rem' }}>{summary.steps} steps evaluated</p>
            </div>
          )}

          {/* 2-column charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div className="card" style={{ height: '380px' }}>
              <div className="card-header"><span className="card-title">🗺️ Quỹ đạo (ENU — mét)</span></div>
              <div style={{ flex: 1, height: '320px' }}>
                <Scatter data={scatterData} options={{
                  ...DARK_OPTS,
                  scales: {
                    ...DARK_OPTS.scales,
                    x: { ...DARK_OPTS.scales.x, title: { display: true, text: 'East (m)', color: '#4a5a7a' } },
                    y: { ...DARK_OPTS.scales.y, title: { display: true, text: 'North (m)', color: '#4a5a7a' } },
                  },
                }} />
              </div>
            </div>

            <div className="card" style={{ height: '380px' }}>
              <div className="card-header"><span className="card-title">📈 RMSE theo thời gian</span></div>
              <div style={{ flex: 1, height: '320px' }}>
                <Line data={rmseLineData} options={{
                  ...DARK_OPTS,
                  scales: {
                    ...DARK_OPTS.scales,
                    x: { ...DARK_OPTS.scales.x, title: { display: true, text: 'Step', color: '#4a5a7a' } },
                    y: { ...DARK_OPTS.scales.y, title: { display: true, text: 'Error (m)', color: '#4a5a7a' }, min: 0 },
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
