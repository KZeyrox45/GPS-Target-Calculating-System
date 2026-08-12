import React from 'react';
import { Marker, Popup } from 'react-leaflet';
import L from 'leaflet';

const ICONS = {
  observer:   { color: '#475569', symbol: '+',  size: 30 },
  truth:      { color: '#16a34a', symbol: '+',  size: 30 },
  kalman:     { color: '#0ea5e9', symbol: 'x',  size: 28 },
  alpha_beta: { color: '#8b5cf6', symbol: 'o',  size: 26 },
  raw:        { color: '#ca8a04', symbol: '.',  size: 20 },
};

function createIcon(type) {
  const cfg = ICONS[type] || ICONS.truth;
  const s = cfg.size;
  const html = `
    <div style="
      width:${s}px; height:${s}px;
      display:flex; align-items:center; justify-content:center;
      font-size:${s * 0.7}px; font-weight:700; font-family:'JetBrains Mono',monospace;
      color:${cfg.color};
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
