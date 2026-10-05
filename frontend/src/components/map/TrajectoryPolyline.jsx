import React, { useMemo, memo } from 'react';
import { Polyline } from 'react-leaflet';

function TrajectoryPolyline({ positions, color = '#4f8ef7', weight = 2, dashArray }) {
  const latLons = useMemo(() => {
    if (!positions || positions.length < 2) return null;
    return positions.map(p => [p.lat, p.lon]);
  }, [positions]);

  const pathOptions = useMemo(() => ({
    color,
    weight,
    dashArray,
    opacity: 0.85,
  }), [color, weight, dashArray]);

  if (!latLons) return null;

  return (
    <Polyline
      positions={latLons}
      pathOptions={pathOptions}
    />
  );
}

export default memo(TrajectoryPolyline);
