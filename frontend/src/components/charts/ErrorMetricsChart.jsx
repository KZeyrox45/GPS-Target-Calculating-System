import React from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import useTrackingStore from '../../store/trackingStore';
import { cssVar } from '../../utils/themeColors';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const CHART_MAX_POINTS = 200;

const TICK_COLOR   = '#475569';
const AXIS_COLOR   = '#475569';
const GRID_COLOR   = 'rgba(34,197,94,0.04)';
const LEGEND_COLOR = '#64748b';
const MONO = { family: "'JetBrains Mono', monospace" };

const BASE_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: {
      labels: { color: LEGEND_COLOR, boxWidth: 12, font: { size: 12, ...MONO } },
    },
    tooltip: {
      mode: 'index', intersect: false,
      backgroundColor: '#131922',
      borderColor: 'rgba(34,197,94,0.2)',
      borderWidth: 1,
      titleColor: '#e2e8f0',
      bodyColor: '#94a3b8',
    },
  },
  scales: {
    x: {
      ticks: { color: TICK_COLOR, maxTicksLimit: 8, font: { size: 11, ...MONO } },
      grid: { color: GRID_COLOR },
    },
    y: {
      ticks: { color: TICK_COLOR, font: { size: 11, ...MONO } },
      grid: { color: GRID_COLOR },
    },
  },
};

export default function ErrorMetricsChart({ defaultCollapsed }) {
  const { metricsHistory } = useTrackingStore();
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed ?? false);
  const visible = metricsHistory.slice(-CHART_MAX_POINTS);

  const labels = visible.map((m) => m.step);
  const data = {
    labels,
    datasets: [
      {
        label: 'KF RMSE',
        data: visible.map((m) => m.kalman_rmse),
        borderColor: cssVar('--color-kalman', '#38bdf8'),
        backgroundColor: 'rgba(34,197,94,0.06)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'AB RMSE',
        data: visible.map((m) => m.alpha_beta_rmse),
        borderColor: cssVar('--color-alphabeta', '#a78bfa'),
        backgroundColor: 'rgba(168,85,247,0.06)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'RAW ERR',
        data: visible.map((m) => m.raw_error),
        borderColor: cssVar('--color-raw', '#eab308'),
        backgroundColor: 'rgba(234,179,8,0.06)',
        borderWidth: 1,
        borderDash: [4, 4],
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
    ],
  };

  const options = {
    ...BASE_OPTIONS,
    plugins: {
      ...BASE_OPTIONS.plugins,
      title: { display: false },
    },
    scales: {
      ...BASE_OPTIONS.scales,
      x: { ...BASE_OPTIONS.scales.x, title: { display: true, text: 'STEP', color: AXIS_COLOR, font: { size: 11, ...MONO } } },
      y: { ...BASE_OPTIONS.scales.y, title: { display: true, text: 'ERR (m)', color: AXIS_COLOR, font: { size: 11, ...MONO } }, min: 0 },
    },
  };

  return (
    <div className="card" style={{ height: collapsed ? '48px' : '220px', display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'height 200ms ease' }}>
      <div className="card-header" style={{ marginBottom: collapsed ? '0' : '0.5rem', cursor: 'pointer' }} onClick={() => setCollapsed((c) => !c)}>
        <span className="card-title">RMSE TIMELINE</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {metricsHistory.length > 0 && !collapsed && (
            <span className="text-sm text-muted font-mono">{metricsHistory.length} steps</span>
          )}
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', transition: 'transform 200ms', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
        </div>
      </div>
      {!collapsed && (
        <div style={{ flex: 1, minHeight: 0 }}>
          {metricsHistory.length < 2 ? (
              <div className="flex items-center justify-center" style={{ height: '100%', color: 'var(--text-muted)', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
              NO DATA
            </div>
          ) : (
            <Line data={data} options={options} />
          )}
        </div>
      )}
    </div>
  );
}
