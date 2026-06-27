import React from 'react';
import { Polyline } from 'react-leaflet';

export default function TrajectoryPolyline({ positions, color = '#4f8ef7', weight = 2, dashArray }) {
  if (!positions || positions.length < 2) return null;
  const latLons = positions.map(p => [p.lat, p.lon]);
  return (
    <Polyline
      positions={latLons}
      pathOptions={{ color, weight, dashArray, opacity: 0.85 }}
    />
  );
}
