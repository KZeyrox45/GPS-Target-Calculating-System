import React from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import useTrackingStore from '../../store/trackingStore';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

const CHART_MAX_POINTS = 200;

const TICK_COLOR   = '#b0c0d8';   // matches --text-secondary
const AXIS_COLOR   = '#b0c0d8';
const GRID_COLOR   = 'rgba(255,255,255,0.07)';
const LEGEND_COLOR = '#b0c0d8';

const BASE_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: {
      labels: { color: LEGEND_COLOR, boxWidth: 14, font: { size: 11 } },
    },
    tooltip: {
      mode: 'index', intersect: false,
      backgroundColor: '#141b2d',
      borderColor: 'rgba(79,142,247,0.3)',
      borderWidth: 1,
      titleColor: '#f0f4ff',
      bodyColor: '#b0c0d8',
    },
  },
  scales: {
    x: {
      ticks: { color: TICK_COLOR, maxTicksLimit: 8, font: { size: 10 } },
      grid: { color: GRID_COLOR },
    },
    y: {
      ticks: { color: TICK_COLOR, font: { size: 10 } },
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
        label: 'Kalman RMSE (m)',
        data: visible.map((m) => m.kalman_rmse),
        borderColor: 'var(--color-kalman)',
        backgroundColor: 'rgba(79,142,247,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'α-β RMSE (m)',
        data: visible.map((m) => m.alpha_beta_rmse),
        borderColor: 'var(--color-alphabeta)',
        backgroundColor: 'rgba(232,121,249,0.06)',
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'Raw Error (m)',
        data: visible.map((m) => m.raw_error),
        borderColor: 'var(--color-raw)',
        backgroundColor: 'rgba(245,158,11,0.06)',
        borderWidth: 1.5,
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
      annotation: {
        annotations: {
          thresholdLine: {
            type: 'line',
            yMin: 5, yMax: 5,
            borderColor: 'rgba(239,68,68,0.4)',
            borderWidth: 1,
            borderDash: [4, 4],
            label: { content: '5m spec', enabled: true, color: 'var(--accent-danger)', font: { size: 10 } },
          },
        },
      },
    },
    scales: {
      ...BASE_OPTIONS.scales,
      x: { ...BASE_OPTIONS.scales.x, title: { display: true, text: 'Step', color: AXIS_COLOR, font: { size: 10 } } },
      y: { ...BASE_OPTIONS.scales.y, title: { display: true, text: 'Error (m)', color: AXIS_COLOR, font: { size: 10 } }, min: 0 },
    },
  };

  return (
    <div className="card" style={{ height: collapsed ? '44px' : '200px', display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'height 200ms ease' }}>
      <div className="card-header" style={{ marginBottom: collapsed ? '0' : '0.4rem', cursor: 'pointer' }} onClick={() => setCollapsed((c) => !c)}>
        <span className="card-title">📈 RMSE theo thời gian</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {metricsHistory.length > 0 && !collapsed && (
            <span className="text-xs text-muted font-mono">{metricsHistory.length} steps</span>
          )}
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', transition: 'transform 200ms', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
        </div>
      </div>
      {!collapsed && (
        <div style={{ flex: 1, minHeight: 0 }}>
          {metricsHistory.length < 2 ? (
            <div className="flex items-center justify-center" style={{ height: '100%', color: 'var(--text-muted)', fontSize: '0.78rem' }}>
              Chưa có dữ liệu…
            </div>
          ) : (
            <Line data={data} options={options} />
          )}
        </div>
      )}
    </div>
  );
}
