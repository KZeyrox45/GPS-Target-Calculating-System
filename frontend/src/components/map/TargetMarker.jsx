import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';

const ICONS = {
  observer: { color: '#8898b3', symbol: '👁️', size: 28 },
  truth:    { color: '#22c55e', symbol: '🎯', size: 24 },
  kalman:   { color: '#4f8ef7', symbol: '◈',  size: 22 },
  alpha_beta: { color: '#e879f9', symbol: '◇', size: 22 },
  raw:      { color: '#f59e0b', symbol: '·',  size: 18 },
};

function createIcon(type) {
  const cfg = ICONS[type] || ICONS.truth;
  const s = cfg.size;
  const html = `
    <div style="
      width:${s}px; height:${s}px; border-radius:50%;
      background:${cfg.color}22; border:2px solid ${cfg.color};
      display:flex; align-items:center; justify-content:center;
      font-size:${s * 0.5}px; color:${cfg.color};
      box-shadow: 0 0 8px ${cfg.color}55;
    ">${cfg.symbol}</div>
  `;
  return L.divIcon({ html, className: '', iconSize: [s, s], iconAnchor: [s / 2, s / 2] });
}

const iconCache = {};
function getIcon(type) {
  if (!iconCache[type]) iconCache[type] = createIcon(type);
  return iconCache[type];
}

export default function TargetMarker({ position, type = 'truth', label }) {
  if (!position || position[0] == null || position[1] == null) return null;
  return (
    <Marker position={position} icon={getIcon(type)}>
      {label && <Popup>{label}</Popup>}
    </Marker>
  );
}
