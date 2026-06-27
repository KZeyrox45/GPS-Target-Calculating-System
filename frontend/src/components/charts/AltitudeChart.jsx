import React from 'react';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Title, Tooltip, Legend,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import useTrackingStore from '../../store/trackingStore';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const CHART_MAX_POINTS = 200;

const TICK_COLOR   = '#b0c0d8';
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
        label: 'Độ cao thực (m)',
        data: visibleGT.map((p) => p.alt ?? 0),
        borderColor: 'var(--color-truth)',
        backgroundColor: 'rgba(52,211,153,0.08)',
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
      },
      {
        label: 'Kalman Up (m)',
        data: visibleKF.map((p) => p.kf_up ?? 0),
        borderColor: 'var(--color-kalman)',
        backgroundColor: 'rgba(79,142,247,0.08)',
        borderWidth: 2,
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
        title: { display: true, text: 'Step', color: AXIS_COLOR, font: { size: 10 } },
      },
      y: {
        ...BASE_OPTIONS.scales.y,
        title: { display: true, text: 'Độ cao (m)', color: AXIS_COLOR, font: { size: 10 } },
      },
    },
  };

  return (
    <div className="card" style={{ height: collapsed ? '44px' : '160px', display: 'flex', flexDirection: 'column', overflow: 'hidden', transition: 'height 200ms ease' }}>
      <div className="card-header" style={{ marginBottom: collapsed ? '0' : '0.4rem', cursor: 'pointer' }} onClick={() => setCollapsed((c) => !c)}>
        <span className="card-title">🚁 Độ cao theo thời gian</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {groundTruthHistory.length > 0 && !collapsed && (
            <span className="text-xs text-muted font-mono">{groundTruthHistory.length} steps</span>
          )}
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', transition: 'transform 200ms', transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
        </div>
      </div>
      {!collapsed && (
        <div style={{ flex: 1, minHeight: 0 }}>
          {groundTruthHistory.length < 2 ? (
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
