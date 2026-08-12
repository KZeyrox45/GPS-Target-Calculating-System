import React from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import useTrackingStore from '../../store/trackingStore';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

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

export default function AltitudeChart({ defaultCollapsed }) {
  const { groundTruthHistory, kalmanHistory } = useTrackingStore();
  const [collapsed, setCollapsed] = React.useState(defaultCollapsed ?? false);

  const visibleGT = groundTruthHistory.slice(-CHART_MAX_POINTS);
  const visibleKF = kalmanHistory.slice(-CHART_MAX_POINTS);

  const labels = visibleGT.map((_, i) => i + 1);

  const data = {
    labels,
    datasets: [
      {
        label: 'ALT TRUE',
        data: visibleGT.map((p) => p.alt ?? 0),
        borderColor: 'var(--color-truth)',
        backgroundColor: 'rgba(34,197,94,0.06)',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'KF UP',
        data: visibleKF.map((p) => p.kf_up ?? 0),
        borderColor: 'var(--color-kalman)',
        backgroundColor: 'rgba(34,197,94,0.06)',
        borderWidth: 1.5,
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
      x: {
        ...BASE_OPTIONS.scales.x,
        title: { display: true, text: 'STEP', color: AXIS_COLOR, font: { size: 11, ...MONO } },
      },
      y: {
        ...BASE_OPTIONS.scales.y,
        title: { display: true, text: 'ALT (m)', color: AXIS_COLOR, font: { size: 11, ...MONO } },
      },
    },
  };

  return (
    <div className="card" style={{ height: collapsed ? '48px' : '180px', display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'height 200ms ease' }}>
      <div className="card-header" style={{ marginBottom: collapsed ? '0' : '0.5rem', cursor: 'pointer' }} onClick={() => setCollapsed((c) => !c)}>
        <span className="card-title">ALT PROFILE</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          {groundTruthHistory.length > 0 && !collapsed && (
            <span className="text-sm text-muted font-mono">{groundTruthHistory.length} steps</span>
          )}
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', transition: 'transform 200ms', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
        </div>
      </div>
      {!collapsed && (
        <div style={{ flex: 1, minHeight: 0 }}>
          {groundTruthHistory.length < 2 ? (
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
